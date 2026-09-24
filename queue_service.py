from ultralytics import YOLO
import cv2
import numpy as np
import json
import os
import time
from collections import deque

MODEL_NAME = "yolo11n.pt"
CONFIDENCE = 0.45
ROI_FILE = "queue_zone.json"

print("Starting Q-SENSE Service Tracking...")

model = YOLO(MODEL_NAME)

# =========================================================
# LOAD QUEUE ZONE
# =========================================================

if not os.path.exists(ROI_FILE):
    print("ERROR: queue_zone.json not found.")
    exit()

with open(ROI_FILE, "r") as f:
    queue_zone = json.load(f)

queue_zone = [tuple(point) for point in queue_zone]
contour = np.array(queue_zone, dtype=np.int32)

print("Queue zone loaded.")

# =========================================================
# TEMPORARY SERVICE LINE
#
# Your fake queue rectangle was roughly:
#
# (150,120) -------- (500,120)
#     |                  |
#     |                  |
#     |                  |
# (150,420) -------- (500,420)
#
# So we're putting the serving line near the TOP.
# =========================================================

SERVICE_Y = 170
SERVICE_X1 = 170
SERVICE_X2 = 480

# Person must move upward across the line.
# In image coordinates:
#
# smaller Y = higher on screen
# larger Y  = lower on screen

# =========================================================
# TRACKING MEMORY
# =========================================================

track_data = {}

total_entries = 0
total_served = 0
total_abandoned = 0

waiting_times = []

# timestamps of people served
# used for recent throughput calculation
served_timestamps = deque()

last_wait_time = None

# =========================================================
# CAMERA
# =========================================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("ERROR: Could not open webcam.")
    exit()

# =========================================================
# MAIN LOOP
# =========================================================

while True:

    ret, frame = cap.read()

    if not ret:
        print("ERROR: Could not read camera.")
        break

    display = frame.copy()
    current_time = time.time()

    # =====================================================
    # DRAW QUEUE ZONE
    # =====================================================

    overlay = display.copy()

    cv2.fillPoly(
        overlay,
        [contour],
        (255, 255, 0)
    )

    display = cv2.addWeighted(
        overlay,
        0.12,
        display,
        0.88,
        0
    )

    cv2.polylines(
        display,
        [contour],
        True,
        (255, 255, 0),
        2
    )

    # =====================================================
    # DRAW SERVICE LINE
    # =====================================================

    cv2.line(
        display,
        (SERVICE_X1, SERVICE_Y),
        (SERVICE_X2, SERVICE_Y),
        (0, 0, 255),
        4
    )

    cv2.putText(
        display,
        "SERVICE LINE",
        (SERVICE_X1, SERVICE_Y - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 0, 255),
        2
    )

    # =====================================================
    # YOLO + BYTETRACK
    # =====================================================

    results = model.track(
        frame,
        persist=True,
        tracker="bytetrack.yaml",
        classes=[0],
        conf=CONFIDENCE,
        verbose=False
    )[0]

    queue_count = 0

    # =====================================================
    # PROCESS EACH TRACKED PERSON
    # =====================================================

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

            foot_x = (x1 + x2) // 2
            foot_y = y2

            current_point = (foot_x, foot_y)

            inside = cv2.pointPolygonTest(
                contour,
                current_point,
                False
            ) >= 0

            # =================================================
            # NEW TRACK
            # =================================================

            if track_id not in track_data:

                track_data[track_id] = {
                    "inside": False,
                    "entry_time": None,
                    "last_seen": current_time,
                    "previous_point": current_point,
                    "served": False
                }

            person = track_data[track_id]

            old_x, old_y = person["previous_point"]

            previous_inside = person["inside"]

            # =================================================
            # ENTER QUEUE
            # =================================================

            if inside and not previous_inside:

                person["inside"] = True
                person["entry_time"] = current_time
                person["served"] = False

                total_entries += 1

                print(
                    f"ID {track_id} ENTERED queue"
                )

            # =================================================
            # DETECT SERVICE-LINE CROSSING
            #
            # Previous foot was BELOW line:
            # old_y > SERVICE_Y
            #
            # Current foot is ABOVE/on line:
            # foot_y <= SERVICE_Y
            #
            # and person's X position is within line width
            # =================================================

            crossed_service_line = (
                old_y > SERVICE_Y
                and foot_y <= SERVICE_Y
                and SERVICE_X1 <= foot_x <= SERVICE_X2
            )

            if (
                crossed_service_line
                and person["inside"]
                and not person["served"]
                and person["entry_time"] is not None
            ):

                wait_time = (
                    current_time
                    - person["entry_time"]
                )

                person["served"] = True

                total_served += 1

                waiting_times.append(wait_time)

                last_wait_time = wait_time

                served_timestamps.append(current_time)

                print(
                    f"ID {track_id} SERVED "
                    f"after {wait_time:.1f} seconds"
                )

            # =================================================
            # LEAVE QUEUE AREA
            # =================================================

            if not inside and previous_inside:

                person["inside"] = False

                # If they left without crossing service line,
                # consider it abandonment for now.
                if not person["served"]:

                    total_abandoned += 1

                    print(
                        f"ID {track_id} LEFT queue "
                        f"without being served"
                    )

                person["entry_time"] = None

            # =================================================
            # QUEUE COUNT
            #
            # Someone who has crossed the service line
            # is no longer considered waiting.
            # =================================================

            if inside and not person["served"]:
                queue_count += 1

            # =================================================
            # DISPLAY PERSON
            # =================================================

            if person["served"]:

                color = (255, 0, 255)

                label = (
                    f"ID {track_id} SERVED"
                )

            elif inside:

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

            cv2.rectangle(
                display,
                (x1, y1),
                (x2, y2),
                color,
                2
            )

            cv2.circle(
                display,
                current_point,
                6,
                color,
                -1
            )

            cv2.putText(
                display,
                label,
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2
            )

            person["previous_point"] = current_point
            person["last_seen"] = current_time

    # =====================================================
    # RECENT THROUGHPUT
    #
    # Keep only service events from last 60 seconds
    # =====================================================

    while (
        served_timestamps
        and current_time - served_timestamps[0] > 60
    ):
        served_timestamps.popleft()

    throughput_per_minute = len(served_timestamps)

    # =====================================================
    # AVERAGE WAIT
    # =====================================================

    if len(waiting_times) > 0:

        average_wait = (
            sum(waiting_times)
            / len(waiting_times)
        )

    else:

        average_wait = 0

    # =====================================================
    # REMOVE OLD TRACKS
    # =====================================================

    stale_ids = []

    for track_id, data in track_data.items():

        if current_time - data["last_seen"] > 10:

            stale_ids.append(track_id)

    for track_id in stale_ids:
        del track_data[track_id]

    # =====================================================
    # DASHBOARD
    # =====================================================

    cv2.rectangle(
        display,
        (10, 10),
        (390, 220),
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
        f"Queue now: {queue_count}",
        (20, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2
    )

    cv2.putText(
        display,
        f"Entered: {total_entries}",
        (20, 105),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )

    cv2.putText(
        display,
        f"Served: {total_served}",
        (190, 105),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )

    cv2.putText(
        display,
        f"Avg wait: {average_wait:.1f} sec",
        (20, 135),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )

    cv2.putText(
        display,
        f"Throughput: {throughput_per_minute}/min",
        (20, 165),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )

    cv2.putText(
        display,
        f"Left early: {total_abandoned}",
        (20, 195),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
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
        "Q-SENSE Service Tracking",
        display
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()