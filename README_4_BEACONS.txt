Four-beacon copy
================

This folder is separate from the original "6 beacons" folder.

Serial input format:
    y,z

Expected physical flash order:
    1,2,3,4,1,4,3,2

The receiver filters stable clusters, rejects transition points, and uses the
pivot pattern 2,1,2 or 4,1,4 to sync beacon 1 even if serial reading starts in
the middle of the stream.

Example:
    python main.py --config "C:\homework\B ENGR 496\4 beacons\Pyramid_Beacon_Config_4beacons_template.csv" --port COM5

If beacon 2 and beacon 4 are swapped because the camera image is mirrored, add:
    --pivot-neighbor auto-x-inverted
