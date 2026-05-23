"""Command-line entry point for the converted MATLAB beacon solver."""

from __future__ import annotations

import argparse

from beacon_solver.solver import run_loop


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Converted MATLAB beacon solver")
    parser.add_argument("--config", help="Path to configuration CSV. If omitted, opens a file picker when available.")
    parser.add_argument("--no-serial", action="store_true", help="Do not attempt serial input; use the config CSV values only.")
    parser.add_argument("--port", help="Serial port to use, for example COM3. If omitted, uses the first available port.")
    parser.add_argument("--baud-rate", type=int, default=115200, help="Serial baud rate.")
    parser.add_argument("--min-beacons", type=int, help="Number of unique beacon measurements required before solving. Default: all beacons.")
    parser.add_argument("--serial-timeout", type=float, help="Seconds to wait for serial data before failing. Default: wait forever.")
    parser.add_argument(
        "--serial-format",
        choices=["raw", "pixel"],
        default="raw",
        help="raw: use y,z directly like MATLAB. pixel: convert absolute pixel centers to camera-centered offsets.",
    )
    parser.add_argument("--image-width", type=float, default=320.0, help="OpenMV image width in pixels, used only with --serial-format pixel.")
    parser.add_argument("--image-height", type=float, default=240.0, help="OpenMV image height in pixels, used only with --serial-format pixel.")
    parser.add_argument("--no-flip-y", action="store_true", help="With --serial-format pixel, use pixel_y - center_y instead of center_y - pixel_y.")
    parser.add_argument("--focal-length", type=float, default=320.0, help="Focal length fallback for first measurement column.")
    parser.add_argument("--tolerance", type=float, default=1e-5, help="Solver convergence tolerance.")
    parser.add_argument("--max-iters", type=int, default=200, help="Maximum solver iterations.")
    parser.add_argument("--once", action="store_true", help="Run one solve instead of looping forever.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_loop(
        csv_path=args.config,
        use_serial=not args.no_serial,
        focal_length=args.focal_length,
        tolerance=args.tolerance,
        max_iters=args.max_iters,
        once=args.once,
        port=args.port,
        baud_rate=args.baud_rate,
        min_beacons=args.min_beacons,
        serial_timeout=args.serial_timeout,
        serial_format=args.serial_format,
        image_width=args.image_width,
        image_height=args.image_height,
        flip_y=not args.no_flip_y,
    )


if __name__ == "__main__":
    main()
