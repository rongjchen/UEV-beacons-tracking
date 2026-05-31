import time
import random

STABLE_SAMPLES = 3
MOVE_SAMPLES_MIN = 1
MOVE_SAMPLES_MAX = 2

POINT_DELAY_MS = 8
JITTER = 0.0015
MOVE_NOISE = 0.08


def sleep_ms(ms):
    try:
        time.sleep_ms(ms)
    except AttributeError:
        time.sleep(ms / 1000)


def rand_float(a, b):
    return a + (b - a) * random.random()


def noisy(point, amount):
    x, y = point
    return (
        x + rand_float(-amount, amount),
        y + rand_float(-amount, amount),
    )


def send_point(point):
    x, y = point
    print("%.4f,%.4f" % (x, y))


beacons = [
    (0.0000, -6.5000),  # 1 top
    (6.5000, 0.0000),   # 2 right
    (0.0000, 6.5000),   # 3 bottom
    (-6.5000, 0.0000),  # 4 left
]

# Pivot pattern:
# 1 2 3 4 1 4 3 2
order = [0, 1, 2, 3, 0, 3, 2, 1]

# Start from a random place to simulate opening the serial port mid-stream.
order_index = random.randint(0, len(order) - 1)

while True:
    current_index = order[order_index]
    next_order_index = (order_index + 1) % len(order)
    next_index = order[next_order_index]

    current = beacons[current_index]
    next_point = beacons[next_index]

    for _ in range(STABLE_SAMPLES):
        send_point(noisy(current, JITTER))
        sleep_ms(POINT_DELAY_MS)

    move_samples = random.randint(MOVE_SAMPLES_MIN, MOVE_SAMPLES_MAX)

    for j in range(move_samples):
        t = float(j + 1) / float(move_samples + 1)
        x = current[0] + (next_point[0] - current[0]) * t
        y = current[1] + (next_point[1] - current[1]) * t

        send_point(noisy((x, y), MOVE_NOISE))
        sleep_ms(POINT_DELAY_MS)

    order_index = next_order_index
