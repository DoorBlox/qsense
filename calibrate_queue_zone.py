import cv2
import json
import os
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

OUTPUT_FILE = "queue_zone_male.json"

points = []


def mouse_callback(event, x, y, flags, param):
    global points

    if event == cv2.EVENT_LBUTTONDOWN:
        points.append((x, y))
        print(f"Point added: {(x, y)}")


cap = cv2.VideoCapture(camera_source)

if not cap.isOpened():
    raise RuntimeError(
        f"Cannot open camera: {camera_source}"
    )


cv2.namedWindow("Q-SENSE Queue Zone Calibration")
cv2.setMouseCallback(
    "Q-SENSE Queue Zone Calibration",
    mouse_callback
)


print("")
print("Q-SENSE QUEUE ZONE CALIBRATION")
print("--------------------------------")
print("LEFT CLICK = add polygon point")
print("R          = reset")
print("ENTER      = save")
print("Q          = quit")
print("")


while True:

    ret, frame = cap.read()

    if not ret:
        print("Camera frame failed.")
        break

    display = frame.copy()


    for point in points:
        cv2.circle(
            display,
            point,
            6,
            (0, 255, 255),
            -1
        )


    if len(points) >= 2:

        for i in range(len(points) - 1):
            cv2.line(
                display,
                points[i],
                points[i + 1],
                (255, 255, 0),
                2
            )


    if len(points) >= 3:

        cv2.line(
            display,
            points[-1],
            points[0],
            (255, 255, 0),
            2
        )


    cv2.putText(
        display,
        "Click around QUEUE AREA",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )


    cv2.putText(
        display,
        "ENTER save | R reset | Q quit",
        (20, 65),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )


    cv2.imshow(
        "Q-SENSE Queue Zone Calibration",
        display
    )


    key = cv2.waitKey(1) & 0xFF


    if key == ord("r"):

        points = []

        print("Points reset.")


    elif key == 13:

        if len(points) < 3:

            print(
                "Need at least 3 points."
            )

        else:

            with open(
                OUTPUT_FILE,
                "w"
            ) as f:

                json.dump(
                    points,
                    f,
                    indent=2
                )

            print("")
            print(
                f"SAVED: {OUTPUT_FILE}"
            )
            print(points)

            break


    elif key == ord("q"):
        break


cap.release()
cv2.destroyAllWindows()