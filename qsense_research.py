from ultralytics import YOLO
import cv2
import numpy as np
import json
import os
import csv
import time
from datetime import datetime, time as dt_time
from collections import deque

# =========================================================
# Q-SENSE CONFIG
# =========================================================

MODEL_NAME = "yolo11n.pt"
CONFIDENCE = 0.45

ROI_FILE = "queue_zone.json"
SERVICE_FILE = "service_line.json"

DATA_DIR = "data"

SNAPSHOT_INTERVAL = 5       # seconds
ENTRY_CONFIRM_TIME = 0.75   # seconds
EXIT_CONFIRM_TIME = 0.75    # seconds

# =========================================================
# MEAL WINDOWS
# =========================================================

BREAKFAST_START = dt_time(5, 30)
BREAKFAST_END   = dt_time(7, 30)

LUNCH_START = dt_time(11, 30)
LUNCH_END   = dt_time(13, 30)

DINNER_START = dt_time(17, 0)
DINNER_END   = dt_time(19, 0)

# =========================================================
# CREATE DATA FOLDER
# =========================================================

os.makedirs(DATA_DIR, exist_ok=True)

SESSIONS_FILE = os.path.join(DATA_DIR, "sessions.csv")
SNAPSHOTS_FILE = os.path.join(DATA_DIR, "queue_snapshots.csv")
EVENTS_FILE = os.path.join(DATA_DIR, "queue_events.csv")

# =========================================================
# CSV HELPER
# =========================================================

def append_csv(filename, headers, row):

    file_exists = os.path.exists(filename)

    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)

        if not file_exists:
            writer.writeheader()

        writer.writerow(row)


# =========================================================
# MEAL CLASSIFICATION
# =========================================================

def get_meal_period():

    now = datetime.now().time()

    if BREAKFAST_START <= now < BREAKFAST_END:
        return "breakfast"

    if LUNCH_START <= now < LUNCH_END:
        return "lunch"

    if DINNER_START <= now < DINNER_END:
        return "dinner"

    return "outside_meal"


# =========================================================
# SESSION ID
# =========================================================

def get_session_id(meal):

    today = datetime.now().strftime("%Y%m%d")

    prefixes = {
        "breakfast": "B",
        "lunch": "L",
        "dinner": "D"
    }

    return f"{prefixes[meal]}_{today}"


# =========================================================
# CHECK WHETHER SESSION ALREADY EXISTS
# =========================================================

def session_exists(session_id):

    if not os.path.exists(SESSIONS_FILE):
        return False

    with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if row["session_id"] == session_id:
                return True

    return False


# =========================================================
# CREATE SESSION
# =========================================================

def create_session(session_id, meal):

    if session_exists(session_id):
        return

    now = datetime.now()

    append_csv(
        SESSIONS_FILE,

        [
            "session_id",
            "date",
            "weekday",
            "meal_period",
            "start_timestamp",
            "model",
            "confidence_threshold"
        ],

        {
            "session_id": session_id,
            "date": now.strftime("%Y-%m-%d"),
            "weekday": now.strftime("%A"),
            "meal_period": meal,
            "start_timestamp": now.isoformat(timespec="seconds"),
            "model": MODEL_NAME,
            "confidence_threshold": CONFIDENCE
        }
    )

    print("")
    print("=" * 45)
    print(f"NEW Q-SENSE SESSION: {session_id}")
    print(f"Meal: {meal.upper()}")
    print("=" * 45)
    print("")


# =========================================================
# LOAD QUEUE ZONE
# =========================================================

if not os.path.exists(ROI_FILE):
    print("ERROR: queue_zone.json not found.")
    exit()

with open(ROI_FILE, "r") as f:
    queue_zone = json.load(f)

queue_zone = [tuple(x) for x in queue_zone]

contour = np.array(
    queue_zone,
    dtype=np.int32
)

# =========================================================
# LOAD SERVICE LINE
# =========================================================

if not os.path.exists(SERVICE_FILE):
    print("ERROR: service_line.json not found.")
    exit()

with open(SERVICE_FILE, "r") as f:
    service_data = json.load(f)

service_points = [
    tuple(service_data["line"][0]),
    tuple(service_data["line"][1])
]

served_side_point = tuple(
    service_data["served_side"]
)

# =========================================================
# GEOMETRY
# =========================================================

def side_of_line(point, a, b):

    px, py = point
    ax, ay = a
    bx, by = b

    return (
        (bx - ax) * (py - ay)
        - (by - ay) * (px - ax)
    )


def orientation(a, b, c):

    value = (
        (b[1] - a[1]) * (c[0] - b[0])
        - (b[0] - a[0]) * (c[1] - b[1])
    )

    if abs(value) < 0.0001:
        return 0

    return 1 if value > 0 else 2


def on_segment(a, b, c):

    return (
        min(a[0], c[0]) <= b[0] <= max(a[0], c[0])
        and
        min(a[1], c[1]) <= b[1] <= max(a[1], c[1])
    )


def segments_intersect(p1, q1, p2, q2):

    o1 = orientation(p1, q1, p2)
    o2 = orientation(p1, q1, q2)
    o3 = orientation(p2, q2, p1)
    o4 = orientation(p2, q2, q1)

    if o1 != o2 and o3 != o4:
        return True

    return False


# =========================================================
# AI MODEL
# =========================================================

print("Loading Q-SENSE AI...")

model = YOLO(MODEL_NAME)

# =========================================================
# TRACKING MEMORY
# =========================================================

track_data = {}

waiting_times = []

served_timestamps = deque()

total_entries = 0
total_served = 0
total_abandoned = 0

last_snapshot = 0

current_session = None

# =========================================================
# CAMERA
# =========================================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("ERROR: Cannot open camera.")
    exit()

print("")
print("Q-SENSE 24/7 Research Logger")
print("")
print("Breakfast: 05:30 - 07:30")
print("Lunch:     11:30 - 13:30")
print("Dinner:    17:00 - 19:00")
print("")
print("Press Q to stop.")
print("")

# =========================================================
# MAIN LOOP
# =========================================================

while True:

    ret, frame = cap.read()

    if not ret:
        break

    display = frame.copy()

    now = datetime.now()
    now_timestamp = time.time()

    meal = get_meal_period()

    # =====================================================
    # OUTSIDE MEAL
    # =====================================================

    if meal == "outside_meal":

        current_session = None

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
            "OUTSIDE MEAL PERIOD",
            (20, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 200, 255),
            2
        )

        cv2.putText(
            display,
            now.strftime("%H:%M:%S"),
            (20, 105),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )

        cv2.imshow(
            "Q-SENSE Research",
            display
        )

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        continue

    # =====================================================
    # ACTIVATE SESSION
    # =====================================================

    session_id = get_session_id(meal)

    if current_session != session_id:

        current_session = session_id

        create_session(
            session_id,
            meal
        )

        track_data.clear()

        total_entries = 0
        total_served = 0
        total_abandoned = 0

        waiting_times.clear()
        served_timestamps.clear()

    # =====================================================
    # DRAW ROI
    # =====================================================

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
        service_points[0],
        service_points[1],
        (0, 0, 255),
        4
    )

    cv2.circle(
        display,
        served_side_point,
        8,
        (255, 0, 255),
        -1
    )

    # =====================================================
    # YOLO + BYTETRACK
    # =====================================================

    result = model.track(
        frame,
        persist=True,
        tracker="bytetrack.yaml",
        classes=[0],
        conf=CONFIDENCE,
        verbose=False
    )[0]

    queue_count = 0

    if (
        result.boxes is not None
        and result.boxes.id is not None
    ):

        boxes = result.boxes.xyxy.cpu().numpy()

        ids = (
            result.boxes.id
            .int()
            .cpu()
            .tolist()
        )

        for box, track_id in zip(
            boxes,
            ids
        ):

            x1, y1, x2, y2 = map(
                int,
                box
            )

            foot = (
                (x1 + x2) // 2,
                y2
            )

            inside_now = (
                cv2.pointPolygonTest(
                    contour,
                    foot,
                    False
                )
                >= 0
            )

            # =================================================
            # NEW TRACK
            # =================================================

            if track_id not in track_data:

                track_data[track_id] = {
                    "confirmed_inside": False,
                    "candidate_inside_since": None,
                    "candidate_outside_since": None,
                    "entry_time": None,
                    "previous_point": foot,
                    "last_seen": now_timestamp,
                    "served": False
                }

            person = track_data[track_id]

            # =================================================
            # ENTRY CONFIRMATION
            # =================================================

            if (
                inside_now
                and not person["confirmed_inside"]
                and not person["served"]
            ):

                if person["candidate_inside_since"] is None:

                    person["candidate_inside_since"] = now_timestamp

                elif (
                    now_timestamp
                    - person["candidate_inside_since"]
                    >= ENTRY_CONFIRM_TIME
                ):

                    person["confirmed_inside"] = True

                    person["entry_time"] = now_timestamp

                    person["candidate_inside_since"] = None

                    total_entries += 1

                    append_csv(
                        EVENTS_FILE,

                        [
                            "session_id",
                            "timestamp",
                            "track_id",
                            "event",
                            "wait_seconds",
                            "queue_count"
                        ],

                        {
                            "session_id": session_id,
                            "timestamp":
                                now.isoformat(
                                    timespec="seconds"
                                ),
                            "track_id": track_id,
                            "event": "ENTER",
                            "wait_seconds": "",
                            "queue_count": queue_count
                        }
                    )

                    print(
                        f"{track_id} ENTERED"
                    )

            else:

                person["candidate_inside_since"] = None

            # =================================================
            # SERVICE CROSSING
            # =================================================

            previous = person[
                "previous_point"
            ]

            served_sign = side_of_line(
                served_side_point,
                service_points[0],
                service_points[1]
            )

            old_sign = side_of_line(
                previous,
                service_points[0],
                service_points[1]
            )

            new_sign = side_of_line(
                foot,
                service_points[0],
                service_points[1]
            )

            old_served_side = (
                old_sign * served_sign > 0
            )

            new_served_side = (
                new_sign * served_sign > 0
            )

            crossed = segments_intersect(
                previous,
                foot,
                service_points[0],
                service_points[1]
            )

            crossed_to_served = (
                crossed
                and not old_served_side
                and new_served_side
            )

            if (
                crossed_to_served
                and person["confirmed_inside"]
                and not person["served"]
                and person["entry_time"] is not None
            ):

                wait_time = (
                    now_timestamp
                    - person["entry_time"]
                )

                person["served"] = True
                person["confirmed_inside"] = False

                total_served += 1

                waiting_times.append(
                    wait_time
                )

                served_timestamps.append(
                    now_timestamp
                )

                append_csv(
                    EVENTS_FILE,

                    [
                        "session_id",
                        "timestamp",
                        "track_id",
                        "event",
                        "wait_seconds",
                        "queue_count"
                    ],

                    {
                        "session_id": session_id,
                        "timestamp":
                            now.isoformat(
                                timespec="seconds"
                            ),
                        "track_id": track_id,
                        "event": "SERVED",
                        "wait_seconds":
                            round(wait_time, 2),
                        "queue_count":
                            queue_count
                    }
                )

                print(
                    f"{track_id} SERVED "
                    f"{wait_time:.1f}s"
                )

            # =================================================
            # EXIT / ABANDONMENT CONFIRMATION
            # =================================================

            if (
                not inside_now
                and person["confirmed_inside"]
                and not person["served"]
            ):

                if person["candidate_outside_since"] is None:

                    person["candidate_outside_since"] = now_timestamp

                elif (
                    now_timestamp
                    - person["candidate_outside_since"]
                    >= EXIT_CONFIRM_TIME
                ):

                    person["confirmed_inside"] = False

                    person["candidate_outside_since"] = None

                    person["entry_time"] = None

                    total_abandoned += 1

                    append_csv(
                        EVENTS_FILE,

                        [
                            "session_id",
                            "timestamp",
                            "track_id",
                            "event",
                            "wait_seconds",
                            "queue_count"
                        ],

                        {
                            "session_id": session_id,
                            "timestamp":
                                now.isoformat(
                                    timespec="seconds"
                                ),
                            "track_id": track_id,
                            "event": "ABANDONED",
                            "wait_seconds": "",
                            "queue_count":
                                queue_count
                        }
                    )

            else:

                person["candidate_outside_since"] = None

            # =================================================
            # COUNT QUEUE
            # =================================================

            if (
                person["confirmed_inside"]
                and not person["served"]
            ):

                queue_count += 1

                color = (0, 255, 0)

            elif person["served"]:

                color = (255, 0, 255)

            else:

                color = (130, 130, 130)

            # =================================================
            # DISPLAY
            # =================================================

            cv2.rectangle(
                display,
                (x1, y1),
                (x2, y2),
                color,
                2
            )

            cv2.putText(
                display,
                f"ID {track_id}",
                (
                    x1,
                    max(y1 - 10, 20)
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2
            )

            person["previous_point"] = foot
            person["last_seen"] = now_timestamp

    # =====================================================
    # THROUGHPUT
    # =====================================================

    while (
        served_timestamps
        and
        now_timestamp
        - served_timestamps[0]
        > 60
    ):

        served_timestamps.popleft()

    throughput = len(
        served_timestamps
    )

    # =====================================================
    # SNAPSHOT LOGGING
    # =====================================================

    if (
        now_timestamp
        - last_snapshot
        >= SNAPSHOT_INTERVAL
    ):

        append_csv(
            SNAPSHOTS_FILE,

            [
                "session_id",
                "timestamp",
                "queue_count",
                "throughput_per_min"
            ],

            {
                "session_id":
                    session_id,

                "timestamp":
                    now.isoformat(
                        timespec="seconds"
                    ),

                "queue_count":
                    queue_count,

                "throughput_per_min":
                    throughput
            }
        )

        last_snapshot = now_timestamp

    # =====================================================
    # DASHBOARD
    # =====================================================

    avg_wait = (
        sum(waiting_times)
        / len(waiting_times)
        if waiting_times
        else 0
    )

    cv2.rectangle(
        display,
        (10, 10),
        (400, 210),
        (0, 0, 0),
        -1
    )

    cv2.putText(
        display,
        "Q-SENSE RESEARCH",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (255, 255, 255),
        2
    )

    cv2.putText(
        display,
        meal.upper(),
        (20, 70),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 200, 255),
        2
    )

    cv2.putText(
        display,
        f"Queue: {queue_count}",
        (20, 100),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 255, 0),
        2
    )

    cv2.putText(
        display,
        f"Served: {total_served}",
        (20, 130),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )

    cv2.putText(
        display,
        f"Avg wait: {avg_wait:.1f}s",
        (20, 160),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )

    cv2.putText(
        display,
        f"Throughput: {throughput}/min",
        (20, 190),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )

    cv2.imshow(
        "Q-SENSE Research",
        display
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


cap.release()
cv2.destroyAllWindows()