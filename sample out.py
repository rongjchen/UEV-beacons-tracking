import time, random

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
        y + rand_float(-amount, amount)
    )

def send_point(point):
    x, y = point
    print("%.4f,%.4f" % (x, y))

beacons = [
    (0.0665, -6.9440),   # 1
    (6.0928, -3.9307),   # 2
    (6.0928,  2.0956),   # 3
    (0.0665,  5.1090),   # 4
    (-5.9598, 2.0956),   # 5
    (-5.9598, -3.9307),  # 6
]

# Pivot pattern:
# 1 2 3 4 5 6 1 6 5 4 3 2
order = [0, 1, 2, 3, 4, 5, 0, 5, 4, 3, 2, 1]

# Start from a random place in the sequence.
# This simulates the computer beginning to read serial data at any time.
order_index = random.randint(0, len(order) - 1)

while True:
    current_index = order[order_index]
    next_order_index = (order_index + 1) % len(order)
    next_index = order[next_order_index]

    current = beacons[current_index]
    next_point = beacons[next_index]

    # Real beacon: several very close readings
    for _ in range(STABLE_SAMPLES):
        send_point(noisy(current, JITTER))
        sleep_ms(POINT_DELAY_MS)

    # Transfer values between current beacon and next beacon
    move_samples = random.randint(MOVE_SAMPLES_MIN, MOVE_SAMPLES_MAX)

    for j in range(move_samples):
        t = float(j + 1) / float(move_samples + 1)

        x = current[0] + (next_point[0] - current[0]) * t
        y = current[1] + (next_point[1] - current[1]) * t

        send_point(noisy((x, y), MOVE_NOISE))
        sleep_ms(POINT_DELAY_MS)

    order_index = next_order_index
