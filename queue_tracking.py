from ultralytics import YOLO
import cv2
import numpy as np
import json
import os
import time

MODEL_NAME = "yolo11n.pt"
CONFIDENCE = 0.45
ROI_FILE = "queue_zone.json"

print("Starting Q-SENSE Tracking...")

# ------------------------------------------------
# LOAD MODEL
# ------------------------------------------------

model = YOLO(MODEL_NAME)

# ------------------------------------------------
# LOAD QUEUE ZONE
# ------------------------------------------------

if not os.path.exists(ROI_FILE):
    print("ERROR: queue_zone.json not found.")
    print("Run queue_zone.py first and create your queue zone.")
    exit()

with open(ROI_FILE, "r") as f:
    queue_zone = json.load(f)

queue_zone = [tuple(point) for point in queue_zone]

contour = np.array(queue_zone, dtype=np.int32)

print("Queue zone loaded.")

# ------------------------------------------------
# TRACKING DATA
# ------------------------------------------------

track_data = {}

total_entries = 0
total_exits = 0

# Example:
#
# track_data[7] = {
#     "inside": True,
#     "entry_time": 12345678,
#     "last_seen": 12345679,
#     "previous_point": (200, 300)
# }

# ------------------------------------------------
# CAMERA
# ------------------------------------------------

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("ERROR: Could not open webcam.")
    exit()

# ------------------------------------------------
# MAIN LOOP
# ------------------------------------------------

while True:

    ret, frame = cap.read()

    if not ret:
        print("ERROR: Could not read camera.")
        break

    display = frame.copy()

    current_time = time.time()

    # ------------------------------------------------
    # DRAW QUEUE ZONE
    # ------------------------------------------------

    overlay = display.copy()

    cv2.fillPoly(
        overlay,
        [contour],
        (255, 255, 0)
    )

    display = cv2.addWeighted(
        overlay,
        0.15,
        display,
        0.85,
        0
    )

    cv2.polylines(
        display,
        [contour],
        True,
        (255, 255, 0),
        2
    )

    # ------------------------------------------------
    # YOLO + BYTETRACK
    # ------------------------------------------------

    results = model.track(
        frame,
        persist=True,
        tracker="bytetrack.yaml",
        classes=[0],
        conf=CONFIDENCE,
        verbose=False
    )[0]

    queue_count = 0

    # ------------------------------------------------
    # PROCESS TRACKS
    # ------------------------------------------------

    if results.boxes is not None and results.boxes.id is not None:

        boxes = results.boxes.xyxy.cpu().numpy()
        track_ids = results.boxes.id.int().cpu().tolist()
        confidences = results.boxes.conf.cpu().tolist()

        for box, track_id, confidence in zip(
            boxes,
            track_ids,
            confidences
        ):

            x1, y1, x2, y2 = map(int, box)

            # Bottom-center = approximate standing position
            foot_x = (x1 + x2) // 2
            foot_y = y2

            current_point = (foot_x, foot_y)

            inside = cv2.pointPolygonTest(
                contour,
                current_point,
                False
            ) >= 0

            # ------------------------------------------------
            # FIRST TIME WE SEE THIS ID
            # ------------------------------------------------

            if track_id not in track_data:

                track_data[track_id] = {
                    "inside": False,
                    "entry_time": None,
                    "last_seen": current_time,
                    "previous_point": current_point
                }

            person = track_data[track_id]

            previous_inside = person["inside"]

            # ------------------------------------------------
            # PERSON ENTERS QUEUE
            # ------------------------------------------------

            if inside and not previous_inside:

                person["inside"] = True
                person["entry_time"] = current_time

                total_entries += 1

                print(
                    f"ID {track_id} ENTERED queue"
                )

            # ------------------------------------------------
            # PERSON LEAVES QUEUE
            # ------------------------------------------------

            elif not inside and previous_inside:

                person["inside"] = False

                if person["entry_time"] is not None:

                    duration = (
                        current_time
                        - person["entry_time"]
                    )

                    print(
                        f"ID {track_id} LEFT queue "
                        f"after {duration:.1f} sec"
                    )

                person["entry_time"] = None

                total_exits += 1

            person["last_seen"] = current_time

            # ------------------------------------------------
            # MOVEMENT
            # ------------------------------------------------

            old_x, old_y = person["previous_point"]

            dx = foot_x - old_x
            dy = foot_y - old_y

            movement = (dx ** 2 + dy ** 2) ** 0.5

            person["previous_point"] = current_point

            # ------------------------------------------------
            # DISPLAY
            # ------------------------------------------------

            if inside:

                queue_count += 1
                color = (0, 255, 0)

                if person["entry_time"] is not None:

                    dwell = (
                        current_time
                        - person["entry_time"]
                    )

                else:
                    dwell = 0

                label = (
                    f"ID {track_id} | "
                    f"{dwell:.0f}s"
                )

            else:

                color = (130, 130, 130)

                label = (
                    f"ID {track_id}"
                )

            # Bounding box
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
                current_point,
                6,
                color,
                -1
            )

            # ID label
            cv2.putText(
                display,
                label,
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2
            )

            # Draw movement vector
            if movement > 2:

                cv2.line(
                    display,
                    (old_x, old_y),
                    current_point,
                    color,
                    2
                )

    # ------------------------------------------------
    # REMOVE VERY OLD TRACKS
    # ------------------------------------------------

    stale_ids = []

    for track_id, data in track_data.items():

        if current_time - data["last_seen"] > 10:

            stale_ids.append(track_id)

    for track_id in stale_ids:

        del track_data[track_id]

    # ------------------------------------------------
    # DASHBOARD PANEL
    # ------------------------------------------------

    cv2.rectangle(
        display,
        (10, 10),
        (340, 145),
        (0, 0, 0),
        -1
    )

    cv2.putText(
        display,
        "Q-SENSE TRACKING",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (255, 255, 255),
        2
    )

    cv2.putText(
        display,
        f"Queue: {queue_count}",
        (20, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (0, 255, 0),
        2
    )

    cv2.putText(
        display,
        f"Entries: {total_entries}",
        (20, 105),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.60,
        (255, 255, 255),
        2
    )

    cv2.putText(
        display,
        f"Exits: {total_exits}",
        (175, 105),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.60,
        (255, 255, 255),
        2
    )

    cv2.putText(
        display,
        "Q = quit",
        (20, display.shape[0] - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 255, 255),
        1
    )

    cv2.imshow(
        "Q-SENSE Tracking",
        display
    )

    # ------------------------------------------------
    # QUIT
    # ------------------------------------------------

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


cap.release()
cv2.destroyAllWindows()