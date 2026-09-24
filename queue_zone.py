from ultralytics import YOLO
import cv2
import numpy as np
import json
import os

MODEL_NAME = "yolo11n.pt"
CONFIDENCE = 0.45
ROI_FILE = "queue_zone.json"

print("Loading Q-SENSE...")
model = YOLO(MODEL_NAME)

# -----------------------------
# Load previously saved queue zone
# -----------------------------

queue_zone = []

if os.path.exists(ROI_FILE):
    with open(ROI_FILE, "r") as f:
        queue_zone = json.load(f)

    queue_zone = [tuple(point) for point in queue_zone]

    print("Saved queue zone loaded.")
else:
    print("No queue zone saved yet.")
    print("Click points around the queue area.")
    print("Press ENTER when finished.")


# -----------------------------
# Mouse click handler
# -----------------------------

def mouse_callback(event, x, y, flags, param):

    if event == cv2.EVENT_LBUTTONDOWN:

        queue_zone.append((x, y))

        print(f"Point added: ({x}, {y})")


# -----------------------------
# Webcam
# -----------------------------

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("ERROR: Could not open webcam.")
    exit()

cv2.namedWindow("Q-SENSE")
cv2.setMouseCallback("Q-SENSE", mouse_callback)


# -----------------------------
# Main loop
# -----------------------------

while True:

    ret, frame = cap.read()

    if not ret:
        print("ERROR: Could not read webcam.")
        break

    display = frame.copy()

    # -----------------------------
    # Draw queue polygon
    # -----------------------------

    if len(queue_zone) > 0:

        pts = np.array(queue_zone, dtype=np.int32)

        # Draw each selected point
        for point in queue_zone:
            cv2.circle(
                display,
                point,
                5,
                (0, 255, 255),
                -1
            )

        # Draw lines
        if len(queue_zone) >= 2:
            cv2.polylines(
                display,
                [pts],
                len(queue_zone) >= 3,
                (255, 255, 0),
                2
            )

    queue_count = 0

    # Only start queue counting after polygon has >= 3 points
    if len(queue_zone) >= 3:

        contour = np.array(queue_zone, dtype=np.int32)

        # -----------------------------
        # YOLO detection
        # -----------------------------

        results = model(frame, verbose=False)[0]

        for box in results.boxes:

            class_id = int(box.cls[0])
            confidence = float(box.conf[0])

            # COCO class 0 = person
            if class_id != 0:
                continue

            if confidence < CONFIDENCE:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            # Approximate person's location using
            # bottom-center of bounding box
            foot_x = (x1 + x2) // 2
            foot_y = y2

            inside = cv2.pointPolygonTest(
                contour,
                (foot_x, foot_y),
                False
            ) >= 0

            if inside:

                queue_count += 1

                color = (0, 255, 0)
                label = f"QUEUE {confidence:.2f}"

            else:

                color = (120, 120, 120)
                label = f"OTHER {confidence:.2f}"

            # Person box
            cv2.rectangle(
                display,
                (x1, y1),
                (x2, y2),
                color,
                2
            )

            # Foot point
            cv2.circle(
                display,
                (foot_x, foot_y),
                6,
                color,
                -1
            )

            # Label
            cv2.putText(
                display,
                label,
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2
            )


    # -----------------------------
    # Main Q-SENSE display
    # -----------------------------

    cv2.rectangle(
        display,
        (10, 10),
        (310, 100),
        (0, 0, 0),
        -1
    )

    cv2.putText(
        display,
        "Q-SENSE",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )

    cv2.putText(
        display,
        f"Queue count: {queue_count}",
        (20, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2
    )

    # Instructions
    cv2.putText(
        display,
        "Click: add point | ENTER: save | R: reset | Q: quit",
        (20, display.shape[0] - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 255, 255),
        1
    )

    cv2.imshow("Q-SENSE", display)

    key = cv2.waitKey(1) & 0xFF


    # -----------------------------
    # ENTER = save ROI
    # -----------------------------

    if key == 13:

        if len(queue_zone) >= 3:

            with open(ROI_FILE, "w") as f:
                json.dump(queue_zone, f)

            print("Queue zone saved!")

        else:
            print("You need at least 3 points.")


    # -----------------------------
    # R = reset ROI
    # -----------------------------

    elif key == ord("r"):

        queue_zone.clear()

        if os.path.exists(ROI_FILE):
            os.remove(ROI_FILE)

        print("Queue zone reset.")
        print("Click new points.")


    # -----------------------------
    # Q = quit
    # -----------------------------

    elif key == ord("q"):
        break


cap.release()
cv2.destroyAllWindows()