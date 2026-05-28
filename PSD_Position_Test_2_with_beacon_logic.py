import serial
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.collections import LineCollection
from collections import deque
import numpy as np
import math

# =========================================================
# Serial connection
# =========================================================
# Original Arduino PSD output format:
#     x,y
# Optional detector / OpenMV beacon output format:
#     beacon_id,x,y
# or:
#     SEND,beacon_id,x,y
ser = serial.Serial('COM10', 115200, timeout=0.05)

# =========================================================
# Figure setup -- original plotting behavior kept
# =========================================================
fig, ax = plt.subplots()

ax.set_xlim(-5, 5)
ax.set_ylim(-5, 5)
ax.set_aspect('equal')
ax.set_facecolor('white')

ax.axhline(0, color='gray', lw=0.5)
ax.axvline(0, color='gray', lw=0.5)

ax.set_title('PSD Position + Optional Beacon Reference Map')
ax.set_xlabel('X')
ax.set_ylabel('Y')

# =========================================================
# Original trail settings
# =========================================================
TAIL_LENGTH = 200

xs = deque(maxlen=TAIL_LENGTH)
ys = deque(maxlen=TAIL_LENGTH)

scatter = ax.scatter([], [], s=[])

line_collection = LineCollection([], linewidths=1.5)
ax.add_collection(line_collection)

point, = ax.plot([], [], 'ro', markersize=3, label='Current PSD point')

# =========================================================
# Added beacon/reference logic
# =========================================================
NUM_BEACONS = 6
BEACON_DISPLAY_RADIUS = 4.0
MATCH_DIST = 0.8

# Raw beacon coordinates as received from detector/OpenMV.
# Example line: 1,-52,83
beacon_raw = {i: None for i in range(1, NUM_BEACONS + 1)}

# Normalized beacon coordinates scaled to this plot's -5..5 range.
beacon_plot = {i: None for i in range(1, NUM_BEACONS + 1)}

beacon_scatter = ax.scatter([], [], s=70, marker='x', label='Beacon references')
beacon_line_collection = LineCollection([], linewidths=1.0, linestyles='dashed')
ax.add_collection(beacon_line_collection)

beacon_labels = []
for i in range(NUM_BEACONS):
    txt = ax.text(0, 0, '', fontsize=9, ha='center', va='center')
    beacon_labels.append(txt)

status_text = ax.text(
    0.02,
    0.98,
    'Waiting for PSD position...',
    transform=ax.transAxes,
    va='top',
    ha='left',
    fontsize=9,
    bbox=dict(boxstyle='round', facecolor='white', alpha=0.75)
)

ax.legend(loc='lower right')


def dist2d(p1, p2):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.sqrt(dx * dx + dy * dy)


def parse_serial_line(line):
    """Classify incoming serial lines without breaking the original x,y parser.

    Returns one of:
        ('psd', x, y)
        ('beacon', beacon_id, x, y)
        None
    """
    if not line or ',' not in line:
        return None

    parts = [p.strip() for p in line.split(',')]

    # Original Arduino format: x,y
    if len(parts) == 2:
        try:
            x, y = map(float, parts)
            return 'psd', x, y
        except ValueError:
            return None

    # Detector format: id,x,y
    if len(parts) == 3:
        try:
            beacon_id = int(parts[0])
            x = float(parts[1])
            y = float(parts[2])
            if 1 <= beacon_id <= NUM_BEACONS:
                return 'beacon', beacon_id, x, y
        except ValueError:
            return None

    # Optional detector format: SEND,id,x,y
    if len(parts) == 4 and parts[0].upper() == 'SEND':
        try:
            beacon_id = int(parts[1])
            x = float(parts[2])
            y = float(parts[3])
            if 1 <= beacon_id <= NUM_BEACONS:
                return 'beacon', beacon_id, x, y
        except ValueError:
            return None

    return None


def normalize_beacon_map():
    """Scale detector/camera beacon coordinates onto the PSD plot.

    This keeps the original detector geometry but displays it in the same
    -5..5 window as the PSD point. The raw detector values are not changed.
    """
    known = [(bid, p) for bid, p in beacon_raw.items() if p is not None]

    if len(known) < 2:
        for bid in beacon_plot:
            beacon_plot[bid] = None
        return

    cx = sum(p[0] for _, p in known) / len(known)
    cy = sum(p[1] for _, p in known) / len(known)

    radii = [dist2d((cx, cy), p) for _, p in known]
    avg_radius = sum(radii) / len(radii) if radii else 0

    if avg_radius <= 0:
        return

    scale = BEACON_DISPLAY_RADIUS / avg_radius

    for bid, p in known:
        # Detector/OpenMV already flips Y before sending centered_y.
        # Keep that coordinate direction here.
        px = (p[0] - cx) * scale
        py = (p[1] - cy) * scale
        beacon_plot[bid] = (px, py)


def update_beacon_artists():
    known = [(bid, p) for bid, p in beacon_plot.items() if p is not None]

    if known:
        offsets = np.array([p for _, p in known])
        beacon_scatter.set_offsets(offsets)
    else:
        beacon_scatter.set_offsets(np.empty((0, 2)))

    # Draw labels.
    for i, txt in enumerate(beacon_labels, start=1):
        p = beacon_plot.get(i)
        if p is None:
            txt.set_text('')
        else:
            txt.set_position((p[0], p[1] + 0.25))
            txt.set_text(str(i))

    # Draw a dashed hexagon if all six beacons are known.
    if all(beacon_plot[i] is not None for i in range(1, NUM_BEACONS + 1)):
        pts = [beacon_plot[i] for i in range(1, NUM_BEACONS + 1)]
        segments = []
        for i in range(NUM_BEACONS):
            p1 = pts[i]
            p2 = pts[(i + 1) % NUM_BEACONS]
            segments.append([p1, p2])
        beacon_line_collection.set_segments(segments)
    else:
        beacon_line_collection.set_segments([])


def nearest_beacon_to_psd(x, y):
    best_id = None
    best_dist = None

    for bid, p in beacon_plot.items():
        if p is None:
            continue

        d = dist2d((x, y), p)
        if best_dist is None or d < best_dist:
            best_id = bid
            best_dist = d

    return best_id, best_dist


# =========================================================
# Animation update
# =========================================================
def update(_):
    # Read serial data. Original x,y behavior is preserved.
    while ser.in_waiting:
        line = ser.readline().decode(errors='ignore').strip()
        parsed = parse_serial_line(line)

        if parsed is None:
            continue

        if parsed[0] == 'psd':
            _, x, y = parsed
            xs.append(x)
            ys.append(y)

        elif parsed[0] == 'beacon':
            _, beacon_id, x, y = parsed
            beacon_raw[beacon_id] = (x, y)
            normalize_beacon_map()

    artists = [scatter, line_collection, point, beacon_scatter, beacon_line_collection, status_text]
    artists.extend(beacon_labels)

    if len(xs) > 1:
        # Original current point logic
        point.set_data([xs[-1]], [ys[-1]])

        positions = np.column_stack((xs, ys))

        # Original scatter trail coloring
        sizes = np.linspace(2, 4, len(xs))
        colors = []
        n = len(xs)

        for i in range(n):
            t = i / max(n - 1, 1)
            r = t
            g = 0.2 * (1 - t)
            b = 1 - t
            alpha = 0.1 + 0.9 * t
            colors.append((r, g, b, alpha))

        scatter.set_offsets(positions)
        scatter.set_sizes(sizes)
        scatter.set_facecolors(colors)

        points = positions.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        line_collection.set_segments(segments)
        line_collection.set_color(colors[:-1])

        # Added: compare current PSD point to optional beacon reference map.
        known_count = sum(p is not None for p in beacon_plot.values())
        best_id, best_dist = nearest_beacon_to_psd(xs[-1], ys[-1])

        if best_id is not None:
            match_msg = 'nearest beacon: %d, distance: %.2f' % (best_id, best_dist)
            if best_dist <= MATCH_DIST:
                match_msg += '  MATCH'
        else:
            match_msg = 'no beacon map yet'

        status_text.set_text(
            'PSD: x=%.3f, y=%.3f\nBeacons known: %d/%d\n%s' % (
                xs[-1],
                ys[-1],
                known_count,
                NUM_BEACONS,
                match_msg
            )
        )

    update_beacon_artists()

    return artists


# =========================================================
# Animation
# =========================================================
ani = FuncAnimation(
    fig,
    update,
    interval=20,
    blit=False,
    cache_frame_data=False
)

plt.show()
