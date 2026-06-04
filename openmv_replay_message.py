"""OpenMV replay script for testing the 4-beacon PC solver.

Copy this file to the OpenMV camera as main.py, and also copy message.txt to
the OpenMV camera storage. The script streams each x,y line from message.txt
over USB serial forever.
"""

import time
import pyb
import os

DATA_FILES = ["message_openmv_10kb.txt", "message_openmv_6kb.txt", "message.txt"]
BAUD_RATE = 115200
LINE_DELAY_MS = 8
CYCLE_DELAY_MS = 250

# If your PC reads the OpenMV USB COM port, keep this True.
# If you wire OpenMV TX/RX to another device, set this False and choose UART_ID.
USE_USB_VCP = True
UART_ID = 3


def sleep_ms(ms):
    try:
        time.sleep_ms(ms)
    except AttributeError:
        time.sleep(ms / 1000)


def open_output():
    if USE_USB_VCP:
        return pyb.USB_VCP()
    return pyb.UART(UART_ID, BAUD_RATE, timeout_char=1000)


def write_line(output, line):
    data = (line + "\r\n").encode("utf-8")
    output.write(data)


def candidate_paths():
    paths = []
    for data_file in DATA_FILES:
        paths.extend([
            data_file,
            "/" + data_file,
            "/flash/" + data_file,
            "/sd/" + data_file,
        ])
    return paths


def find_data_file():
    for path in candidate_paths():
        try:
            with open(path, "r") as data_file:
                data_file.readline()
            return path
        except OSError:
            pass
    return None


def list_files_for_debug(output):
    for folder in ["/", "/flash", "/sd"]:
        try:
            names = os.listdir(folder)
        except OSError:
            continue
        write_line(output, "FILES {}: {}".format(folder, ",".join(names)))


def stream_file(output):
    data_path = find_data_file()
    if data_path is None:
        write_line(output, "ERROR,replay data file not found")
        list_files_for_debug(output)
        sleep_ms(1000)
        return

    with open(data_path, "r") as data_file:
        for raw_line in data_file:
            line = raw_line.strip()

            # Only send x,y numeric lines. Blank/comment lines are ignored.
            if not line or "," not in line:
                continue

            write_line(output, line)
            sleep_ms(LINE_DELAY_MS)


output = open_output()

while True:
    try:
        stream_file(output)
        sleep_ms(CYCLE_DELAY_MS)
    except OSError:
        write_line(output, "ERROR,replay data file not found")
        list_files_for_debug(output)
        sleep_ms(1000)
