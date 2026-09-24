import cv2
import json
import os
import numpy as np
from dotenv import load_dotenv

load_dotenv()

source_raw = os.getenv(
    "QSENSE_CAMERA_SOURCE",
    "0"
).strip()

camera_source = (
    int(source_raw)
    if source_raw.isdigit()
    else source_raw
)

ROI_FILE = os.getenv(
    "QSENSE_ROI_FILE",
    "queue_zone_male.json"
)

OUTPUT_FILE = os.getenv(
    "QSENSE_SERVICE_FILE",
    "service_line_male.json"
)

line_points = []
served_side = None


# =========================================================
# LOAD QUEUE ZONE
# =========================================================

if not os.path.exists(ROI_FILE):
    raise FileNotFoundError(
        f"Queue zone file not found: {ROI_FILE}"
    )

with open(ROI_FILE, "r") as f:
    queue_zone = json.load(f)

queue_zone = [
    tuple(point)
    for point in queue_zone
]

contour = np.array(
    queue_zone,
    dtype=np.int32
)


# =========================================================
# MOUSE
# =========================================================

def mouse_callback(
    event,
    x,
    y,
    flags,
    param
):

    global line_points
    global served_side

    if event != cv2.EVENT_LBUTTONDOWN:
        return

    if len(line_points) < 2:

        line_points.append(
            (x, y)
        )

        print(
            f"Line point {len(line_points)}: "
            f"{(x, y)}"
        )

    elif served_side is None:

        served_side = (
            x,
            y
        )

        print(
            "Served-side point:",
            served_side
        )


# =========================================================
# CAMERA
# =========================================================

cap = cv2.VideoCapture(
    camera_source
)

if not cap.isOpened():

    raise RuntimeError(
        f"Cannot open camera: "
        f"{camera_source}"
    )


WINDOW = (
    "Q-SENSE Service Line Calibration"
)

cv2.namedWindow(WINDOW)

cv2.setMouseCallback(
    WINDOW,
    mouse_callback
)


print("")
print(
    "Q-SENSE SERVICE LINE CALIBRATION"
)
print(
    "--------------------------------"
)
print(
    "CYAN = queue zone"
)
print(
    "RED  = service line"
)
print(
    "PINK = served side"
)
print("")
print(
    "1. Click first end of service line"
)
print(
    "2. Click second end"
)
print(
    "3. Click on the SERVED side"
)
print("")
print(
    "ENTER = save"
)
print(
    "R     = reset service calibration"
)
print(
    "Q     = quit"
)
print("")


# =========================================================
# LOOP
# =========================================================

while True:

    ret, frame = cap.read()

    if not ret:

        print(
            "Camera frame failed."
        )

        break


    display = frame.copy()


    # =====================================================
    # DRAW QUEUE ZONE
    # =====================================================

    cv2.polylines(
        display,
        [contour],
        True,
        (255, 255, 0),
        3
    )


    cv2.putText(
        display,
        "QUEUE ZONE",
        tuple(contour[0]),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 0),
        2
    )


    # =====================================================
    # DRAW SERVICE POINTS
    # =====================================================

    for point in line_points:

        cv2.circle(
            display,
            point,
            7,
            (0, 0, 255),
            -1
        )


    # =====================================================
    # DRAW SERVICE LINE
    # =====================================================

    if len(line_points) == 2:

        cv2.line(
            display,
            line_points[0],
            line_points[1],
            (0, 0, 255),
            4
        )


    # =====================================================
    # DRAW SERVED SIDE
    # =====================================================

    if served_side is not None:

        cv2.circle(
            display,
            served_side,
            9,
            (255, 0, 255),
            -1
        )


        cv2.putText(
            display,
            "SERVED SIDE",
            (
                served_side[0] + 10,
                served_side[1]
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 0, 255),
            2
        )


    # =====================================================
    # INSTRUCTIONS
    # =====================================================

    cv2.putText(
        display,
        "CYAN=queue | RED=service | PINK=served",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )


    cv2.putText(
        display,
        "Click 2 line ends, then served side",
        (20, 65),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )


    cv2.putText(
        display,
        "ENTER save | R reset | Q quit",
        (20, 95),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 255, 255),
        2
    )


    cv2.imshow(
        WINDOW,
        display
    )


    key = (
        cv2.waitKey(1)
        & 0xFF
    )


    if key == ord("r"):

        line_points = []
        served_side = None

        print(
            "Service calibration reset."
        )


    elif key == 13:

        if (
            len(line_points) != 2
            or served_side is None
        ):

            print(
                "Complete all 3 clicks first."
            )

        else:

            data = {

                "line": [
                    list(
                        line_points[0]
                    ),
                    list(
                        line_points[1]
                    )
                ],

                "served_side":
                    list(
                        served_side
                    )
            }


            with open(
                OUTPUT_FILE,
                "w"
            ) as f:

                json.dump(
                    data,
                    f,
                    indent=2
                )


            print("")
            print(
                f"SAVED: {OUTPUT_FILE}"
            )

            break


    elif key == ord("q"):

        break


cap.release()

cv2.destroyAllWindows()