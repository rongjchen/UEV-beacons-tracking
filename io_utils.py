"""I/O helpers converted from getConfig.m and getSerial.m.

CSV data and serial data have different meanings:
- CSV columns 2-4 are optional measurement values from a file.
- CSV last three columns are real beacon positions Ri = [depth, Y, Z] in meters.
- Serial lines are OpenMV measurements: beacon_number,y,z.

By default, serial y,z are treated like the MATLAB reference: they are copied
straight into bmeasure columns 2 and 3. If your OpenMV sends absolute pixel
centers, use serial_format="pixel" so the code subtracts the image center first.
"""

from __future__ import annotations

from pathlib import Path
import time

import numpy as np
import pandas as pd


class SerialNoDeviceError(RuntimeError):
    """Raised when no serial device is available."""


def get_config(csv_path: str | Path | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Load configuration CSV.

    Matches the MATLAB getConfig reference for measurements:
        bmeasure = columns 2-4, ignoring Point_Name.

    For beacon positions, this uses the last three columns. In your CSV those are
    the real-world beacon coordinates [depth, Y, Z] in meters, relative to the
    object center.
    """
    if csv_path is None:
        try:
            from tkinter import Tk, filedialog
        except Exception as exc:  # pragma: no cover - environment-dependent
            raise ValueError("csv_path is required when tkinter is unavailable") from exc

        root = Tk()
        root.withdraw()
        selected = filedialog.askopenfilename(
            title="Select the Configuration CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        root.destroy()
        if not selected:
            raise RuntimeError("Program Terminated: No configuration file was selected.")
        csv_path = selected

    csv_path = Path(csv_path)
    config_data = pd.read_csv(csv_path)

    if config_data.shape[1] < 7:
        raise ValueError("Configuration CSV must have at least 7 columns")

    # MATLAB reference: bmeasure = configData{:, 2:4}
    bmeasure = config_data.iloc[:, 1:4].to_numpy(dtype=float)

    # Your file meaning: last 3 columns are real beacon positions [depth, Y, Z].
    ri = config_data.iloc[:, -3:].to_numpy(dtype=float)

    print(f"Successfully loaded configuration from: {csv_path.name}")
    print(f"Loaded {ri.shape[0]} beacon positions from last three CSV columns.")
    return bmeasure, ri


def list_serial_ports() -> list[str]:
    """Return available serial port names."""
    try:
        from serial.tools import list_ports
    except ImportError as exc:
        raise ImportError("pyserial is required for serial input. Install it with: pip install pyserial") from exc

    return [p.device for p in list_ports.comports()]


def parse_sensor_line(raw_data: str, rows: int) -> tuple[int, float, float] | None:
    """Parse one sensor line: beacon_number,y,z.

    Example: "1,36,32" returns row index 0 and values 36, 32.
    """
    raw_data = raw_data.strip()
    if not raw_data:
        return None

    parts = raw_data.split(",")
    if len(parts) < 3:
        print(f"Serial warning: ignored invalid line: {raw_data!r}")
        return None

    try:
        beacon_number = int(round(float(parts[0])))
        y_val = float(parts[1])
        z_val = float(parts[2])
    except ValueError:
        print(f"Serial warning: ignored non-numeric line: {raw_data!r}")
        return None

    if not 1 <= beacon_number <= rows:
        print(f"Serial warning: invalid beacon number {beacon_number}. Line ignored.")
        return None

    return beacon_number - 1, y_val, z_val


def get_serial(
    port: str | None = None,
    baud_rate: int = 115200,
    rows: int = 6,
    min_required: int | None = None,
    timeout_seconds: float | None = None,
    serial_format: str = "raw",
    image_width: float = 320.0,
    image_height: float = 240.0,
    flip_y: bool = True,
) -> np.ndarray:
    """Read serial measurements until enough unique beacon rows are received.

    Expected line format from OpenMV:
        beacon_number,y,z

    serial_format="raw" matches the MATLAB reference exactly:
        bmeasure[row, 1] = y
        bmeasure[row, 2] = z

    serial_format="pixel" is for absolute OpenMV pixel centers:
        y becomes pixel_x - image_width/2
        z becomes image_height/2 - pixel_y when flip_y=True

    The first column remains zero here. The solver fills it with focal length,
    just like MASTERLOOP.m.
    """
    try:
        import serial
    except ImportError as exc:
        raise ImportError("pyserial is required for serial input. Install it with: pip install pyserial") from exc

    if min_required is None:
        min_required = rows
    if min_required < 1 or min_required > rows:
        raise ValueError("min_required must be between 1 and rows")

    if serial_format not in {"raw", "pixel"}:
        raise ValueError('serial_format must be either "raw" or "pixel"')

    if port is None:
        available_ports = list_serial_ports()
        if not available_ports:
            raise SerialNoDeviceError("No serial connections detected. Looking for file instead.")
        port = available_ports[0]
        print(f"Available serial ports: {available_ports}")

    print(f"Connecting to device on {port} at {baud_rate} baud...")
    print(f"Waiting for {min_required} unique beacon measurement(s)...")
    print('Expected format: "beacon_number,y,z", for example: "1,36,32"')
    print(f"Serial format: {serial_format}")

    bmeasure = np.zeros((rows, 3), dtype=float)
    received = np.zeros(rows, dtype=bool)
    start_time = time.time()

    with serial.Serial(port, baud_rate, timeout=1) as open_mv:
        while np.count_nonzero(received) < min_required:
            if timeout_seconds is not None and time.time() - start_time > timeout_seconds:
                raise TimeoutError(
                    f"Timed out waiting for serial data. "
                    f"Received {np.count_nonzero(received)} of {min_required} required beacons."
                )

            raw_data = open_mv.readline().decode("utf-8", errors="replace").strip()
            parsed = parse_sensor_line(raw_data, rows)
            if parsed is None:
                continue

            row_index, y_val, z_val = parsed

            if serial_format == "pixel":
                pixel_x = y_val
                pixel_y = z_val
                y_measure = pixel_x - image_width / 2.0
                z_measure = image_height / 2.0 - pixel_y if flip_y else pixel_y - image_height / 2.0
            else:
                y_measure = y_val
                z_measure = z_val

            # Match MATLAB getSerial: column 0 stays zero; columns 1 and 2 get measurements.
            bmeasure[row_index, 1] = y_measure
            bmeasure[row_index, 2] = z_measure
            received[row_index] = True

            print(
                f"Beacon {row_index + 1}: raw=({y_val}, {z_val}), "
                f"measurement=({y_measure}, {z_measure}) "
                f"[{np.count_nonzero(received)}/{min_required}]"
            )

    print("Matrix bmeasure successfully populated.")
    return bmeasure
