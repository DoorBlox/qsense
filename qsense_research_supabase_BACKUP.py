from ultralytics import YOLO
import cv2
import numpy as np
import json
import os
import csv
import time
import atexit

from datetime import datetime, time as dt_time
from collections import deque

from dotenv import load_dotenv
from supabase import create_client


# =========================================================
# Q-SENSE CONFIG
# =========================================================

MODEL_NAME = "yolo11n.pt"
CONFIDENCE = 0.45

ROI_FILE = "queue_zone.json"
SERVICE_FILE = "service_line.json"

DATA_DIR = "data"

SNAPSHOT_INTERVAL = 5
SUPABASE_UPDATE_INTERVAL = 5

ENTRY_CONFIRM_TIME = 0.75
EXIT_CONFIRM_TIME = 0.75


# =========================================================
# MEAL WINDOWS
# =========================================================

BREAKFAST_START = dt_time(5, 30)
BREAKFAST_END = dt_time(7, 30)

LUNCH_START = dt_time(11, 30)
LUNCH_END = dt_time(13, 30)

DINNER_START = dt_time(17, 0)
DINNER_END = dt_time(19, 0)


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()

# =========================================================
# CAMERA NODE CONFIGURATION
# =========================================================

SECTION = os.getenv(
    "QSENSE_SECTION",
    "male"
).strip().lower()

if SECTION not in {
    "male",
    "female"
}:
    raise ValueError(
        "QSENSE_SECTION must be male or female"
    )


SECTION_ID = (
    1
    if SECTION == "male"
    else 2
)


CAMERA_SOURCE_RAW = os.getenv(
    "QSENSE_CAMERA_SOURCE",
    "0"
).strip()


if CAMERA_SOURCE_RAW.isdigit():

    CAMERA_SOURCE = int(
        CAMERA_SOURCE_RAW
    )

else:

    CAMERA_SOURCE = (
        CAMERA_SOURCE_RAW
    )


ROI_FILE = os.getenv(
    "QSENSE_ROI_FILE",
    f"queue_zone_{SECTION}.json"
)


SERVICE_FILE = os.getenv(
    "QSENSE_SERVICE_FILE",
    f"service_line_{SECTION}.json"
)


# Backward-compatible fallback during PoC
if not os.path.exists(ROI_FILE):
    ROI_FILE = "queue_zone.json"

if not os.path.exists(SERVICE_FILE):
    SERVICE_FILE = "service_line.json"


print("")
print(
    f"Q-SENSE SECTION: {SECTION.upper()}"
)

print(
    f"Camera source: {CAMERA_SOURCE}"
)

print(
    f"ROI: {ROI_FILE}"
)

print(
    f"Service line: {SERVICE_FILE}"
)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

TEST_MODE = (
    os.getenv("QSENSE_TEST_MODE", "false")
    .strip()
    .lower()
    == "true"
)

if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL missing from .env")

if not SUPABASE_SERVICE_KEY:
    raise ValueError("SUPABASE_SERVICE_KEY missing from .env")


# =========================================================
# SUPABASE
# =========================================================

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY
)


def safe_supabase_update(data):

    try:

        payload = {
            **data,
            "id": SECTION_ID,
            "section": SECTION
        }

        supabase.table(
            "live_status"
        ).upsert(
            payload,
            on_conflict="id"
        ).execute()

    except Exception as e:

        print(
            f"[SUPABASE] "
            f"{SECTION} live_status error: {e}"
        )


def safe_supabase_snapshot(
    session_id,
    meal,
    queue_count,
    throughput
):

    try:

        supabase.table(
            "queue_snapshots"
        ).insert({
	    "section": SECTION,
	    "session_id": session_id,
	    "meal_period": meal,
	    "queue_count": queue_count,
	    "throughput_per_min": throughput
        }).execute()

    except Exception as e:

        print(
            f"[SUPABASE] snapshot error: {e}"
        )


def safe_supabase_event(
    session_id,
    track_id,
    event,
    wait_seconds,
    queue_count
):

    try:

        supabase.table(
            "queue_events"
        ).insert({
            "section": SECTION,
            "session_id": session_id,
            "track_id": int(track_id),
            "event": event,
            "wait_seconds": wait_seconds,
            "queue_count": queue_count
        }).execute()

    except Exception as e:

        print(
            f"[SUPABASE] "
            f"event error: {e}"
        )

def mark_offline():

    try:

        supabase.table(
            "live_status"
        ).update({

            "camera_online":
                False,

            "queue_status":
                "offline",

            "queue_count":
                0,

            "updated_at":
                datetime.now().isoformat()

        }).eq(
            "id",
            SECTION_ID
        ).execute()


        print(
            f"[SUPABASE] "
            f"{SECTION.upper()} camera offline."
        )

    except Exception as e:

        print(
            f"[SUPABASE] "
            f"Could not mark "
            f"{SECTION} offline: {e}"
        )


# =========================================================
# CREATE DATA FOLDER
# =========================================================

os.makedirs(
    DATA_DIR,
    exist_ok=True
)

SESSIONS_FILE = os.path.join(
    DATA_DIR,
    "sessions.csv"
)

SNAPSHOTS_FILE = os.path.join(
    DATA_DIR,
    "queue_snapshots.csv"
)

EVENTS_FILE = os.path.join(
    DATA_DIR,
    "queue_events.csv"
)


# =========================================================
# CSV HELPER
# =========================================================

def append_csv(
    filename,
    headers,
    row
):

    file_exists = os.path.exists(
        filename
    )

    with open(
        filename,
        "a",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=headers
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(
            row
        )


# =========================================================
# MEAL CLASSIFICATION
# =========================================================

def get_meal_period():

    now_time = datetime.now().time()

    if (
        BREAKFAST_START
        <= now_time
        < BREAKFAST_END
    ):
        return "breakfast"

    if (
        LUNCH_START
        <= now_time
        < LUNCH_END
    ):
        return "lunch"

    if (
        DINNER_START
        <= now_time
        < DINNER_END
    ):
        return "dinner"

    return "outside_meal"


# =========================================================
# SESSION ID
# =========================================================

def get_session_id(meal):

    today = datetime.now().strftime(
        "%Y%m%d"
    )

    section_prefix = {
        "male": "M",
        "female": "F"
    }[SECTION]

    if meal == "test":

        return (
            f"{section_prefix}_TEST_{today}"
        )

    meal_prefix = {
        "breakfast": "B",
        "lunch": "L",
        "dinner": "D"
    }[meal]

    return (
        f"{section_prefix}_"
        f"{meal_prefix}_"
        f"{today}"
    )

# =========================================================
# SESSION CHECK
# =========================================================

def session_exists(
    session_id
):

    if not os.path.exists(
        SESSIONS_FILE
    ):
        return False

    with open(
        SESSIONS_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        reader = csv.DictReader(
            f
        )

        for row in reader:

            if (
                row["session_id"]
                == session_id
            ):
                return True

    return False


# =========================================================
# CREATE SESSION
# =========================================================

def create_session(
    session_id,
    meal
):

    # Never put test sessions in research CSV
    if meal == "test":
        return

    if session_exists(
        session_id
    ):
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
            "session_id":
                session_id,

            "date":
                now.strftime(
                    "%Y-%m-%d"
                ),

            "weekday":
                now.strftime(
                    "%A"
                ),

            "meal_period":
                meal,

            "start_timestamp":
                now.isoformat(
                    timespec="seconds"
                ),

            "model":
                MODEL_NAME,

            "confidence_threshold":
                CONFIDENCE
        }
    )

    print("")
    print("=" * 45)
    print(
        f"NEW Q-SENSE SESSION: "
        f"{session_id}"
    )
    print(
        f"Meal: {meal.upper()}"
    )
    print("=" * 45)
    print("")


# =========================================================
# LOAD QUEUE ZONE
# =========================================================

if not os.path.exists(
    ROI_FILE
):

    print(
        "ERROR: queue_zone.json "
        "not found."
    )

    raise SystemExit


with open(
    ROI_FILE,
    "r"
) as f:

    queue_zone = json.load(
        f
    )


queue_zone = [
    tuple(x)
    for x in queue_zone
]


contour = np.array(
    queue_zone,
    dtype=np.int32
)


print(
    "Loaded queue zone:",
    queue_zone
)


# =========================================================
# LOAD SERVICE LINE
# =========================================================

if not os.path.exists(
    SERVICE_FILE
):

    print(
        "ERROR: service_line.json "
        "not found."
    )

    raise SystemExit


with open(
    SERVICE_FILE,
    "r"
) as f:

    service_data = json.load(
        f
    )


service_points = [

    tuple(
        service_data[
            "line"
        ][0]
    ),

    tuple(
        service_data[
            "line"
        ][1]
    )
]


served_side_point = tuple(
    service_data[
        "served_side"
    ]
)


print(
    "Loaded service line:",
    service_points
)


# =========================================================
# GEOMETRY
# =========================================================

def side_of_line(
    point,
    a,
    b
):

    px, py = point
    ax, ay = a
    bx, by = b

    return (
        (bx - ax)
        * (py - ay)
        -
        (by - ay)
        * (px - ax)
    )


def orientation(
    a,
    b,
    c
):

    value = (
        (b[1] - a[1])
        * (c[0] - b[0])
        -
        (b[0] - a[0])
        * (c[1] - b[1])
    )

    if abs(value) < 0.0001:
        return 0

    return (
        1
        if value > 0
        else 2
    )


def segments_intersect(
    p1,
    q1,
    p2,
    q2
):

    o1 = orientation(
        p1,
        q1,
        p2
    )

    o2 = orientation(
        p1,
        q1,
        q2
    )

    o3 = orientation(
        p2,
        q2,
        p1
    )

    o4 = orientation(
        p2,
        q2,
        q1
    )

    return (
        o1 != o2
        and
        o3 != o4
    )


# =========================================================
# QUEUE STATUS
# =========================================================

def get_queue_status(
    count
):

    if count == 0:
        return "empty"

    if count <= 3:
        return "low"

    if count <= 7:
        return "moderate"

    return "busy"


def get_trend(
    current,
    previous
):

    if current > previous:
        return "rising"

    if current < previous:
        return "falling"

    return "stable"


# =========================================================
# AI MODEL
# =========================================================

print("")
print(
    "Loading Q-SENSE AI..."
)

model = YOLO(
    MODEL_NAME
)

print(
    "AI loaded."
)


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
last_supabase_update = 0

previous_queue_count = 0

current_session = None


# =========================================================
# CAMERA
# =========================================================

cap = cv2.VideoCapture(
    CAMERA_SOURCE
)

if not cap.isOpened():

    print(
        "ERROR: Cannot open camera."
    )

    raise SystemExit


print("")
print("=" * 50)
print("Q-SENSE RESEARCH LOGGER")
print("=" * 50)
print("")
print(
    "Breakfast: 05:30 - 07:30"
)
print(
    "Lunch:     11:30 - 13:30"
)
print(
    "Dinner:    17:00 - 19:00"
)

if TEST_MODE:

    print("")
    print(
        "*** TEST MODE ACTIVE ***"
    )
    print(
        "Tracking is enabled "
        "outside meal hours."
    )
    print(
        "Test data will NOT be "
        "saved as research data."
    )

print("")
print(
    "Press Q to stop."
)
print("")


# =========================================================
# MAIN LOOP
# =========================================================

try:

    while True:

        ret, frame = cap.read()

        if not ret:

            print(
                "Camera frame failed."
            )

            break


        display = frame.copy()

        now = datetime.now()

        now_timestamp = time.time()

        actual_meal = (
            get_meal_period()
        )


        # =================================================
        # DECIDE WHETHER TRACKING IS ACTIVE
        # =================================================

        if (
            actual_meal
            == "outside_meal"
            and TEST_MODE
        ):

            meal = "test"

            tracking_active = True

        elif (
            actual_meal
            == "outside_meal"
        ):

            meal = "outside_meal"

            tracking_active = False

        else:

            meal = actual_meal

            tracking_active = True


        # =================================================
        # OUTSIDE MEAL — NORMAL MODE
        # =================================================

        if not tracking_active:

            current_session = None

            # Draw queue zone anyway
            cv2.polylines(
                display,
                [contour],
                True,
                (255, 255, 0),
                2
            )

            # Draw service line anyway
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
                now.strftime(
                    "%H:%M:%S"
                ),
                (20, 105),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )


            # heartbeat
            if (
                now_timestamp
                - last_supabase_update
                >= SUPABASE_UPDATE_INTERVAL
            ):

		safe_supabase_update({

		    "updated_at":
		        now.isoformat(),
	
		    "meal_period":
		        meal,

		    "queue_count":
		        queue_count,

		    "queue_status":
		        queue_status,

		    "trend":
		        trend,

		    "entries":
		        total_entries,

		    "served":
		        total_served,

		    "abandoned":
		        total_abandoned,

		    "avg_wait_seconds":
		        round(
		            avg_wait,
		            2
		        ),

		    "throughput_per_min":
		        throughput,

		    "camera_online":
		        True
		})

                last_supabase_update = (
                    now_timestamp
                )


            cv2.imshow(
                "Q-SENSE Research",
                display
            )

            if (
                cv2.waitKey(1)
                & 0xFF
                == ord("q")
            ):
                break

            continue


        # =================================================
        # ACTIVATE SESSION
        # =================================================

        session_id = (
            get_session_id(
                meal
            )
        )


        if (
            current_session
            != session_id
        ):

            current_session = (
                session_id
            )

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

            previous_queue_count = 0


        # =================================================
        # DRAW ROI
        # =================================================

        cv2.polylines(
            display,
            [contour],
            True,
            (255, 255, 0),
            3
        )


        # =================================================
        # DRAW SERVICE LINE
        # =================================================

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


        # =================================================
        # YOLO + BYTETRACK
        # =================================================

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
            result.boxes
            is not None
        ):

            # Draw normal YOLO detections
            boxes = (
                result.boxes
                .xyxy
                .cpu()
                .numpy()
            )

            # IDs may briefly be unavailable
            if (
                result.boxes.id
                is not None
            ):

                ids = (
                    result.boxes.id
                    .int()
                    .cpu()
                    .tolist()
                )

            else:

                ids = [
                    -1
                    for _ in boxes
                ]


            for (
                box,
                track_id
            ) in zip(
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


                # =========================================
                # TEMP DETECTION WITHOUT TRACK ID
                # =========================================

                if track_id == -1:

                    color = (
                        0,
                        165,
                        255
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
                        foot,
                        5,
                        color,
                        -1
                    )

                    continue


                # =========================================
                # NEW TRACK
                # =========================================

                if (
                    track_id
                    not in track_data
                ):

                    track_data[
                        track_id
                    ] = {

                        "confirmed_inside":
                            False,

                        "candidate_inside_since":
                            None,

                        "candidate_outside_since":
                            None,

                        "entry_time":
                            None,

                        "previous_point":
                            foot,

                        "last_seen":
                            now_timestamp,

                        "served":
                            False
                    }


                person = track_data[
                    track_id
                ]


                # =========================================
                # ENTRY CONFIRMATION
                # =========================================

                if (
                    inside_now
                    and
                    not person[
                        "confirmed_inside"
                    ]
                    and
                    not person[
                        "served"
                    ]
                ):

                    if (
                        person[
                            "candidate_inside_since"
                        ]
                        is None
                    ):

                        person[
                            "candidate_inside_since"
                        ] = now_timestamp


                    elif (
                        now_timestamp
                        -
                        person[
                            "candidate_inside_since"
                        ]
                        >=
                        ENTRY_CONFIRM_TIME
                    ):

                        person[
                            "confirmed_inside"
                        ] = True

                        person[
                            "entry_time"
                        ] = now_timestamp

                        person[
                            "candidate_inside_since"
                        ] = None

                        total_entries += 1


                        print(
                            f"ID {track_id} ENTERED"
                        )


                        # REAL RESEARCH ONLY
                        if meal != "test":

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
                                    "session_id":
                                        session_id,

                                    "timestamp":
                                        now.isoformat(
                                            timespec="seconds"
                                        ),

                                    "track_id":
                                        track_id,

                                    "event":
                                        "ENTER",

                                    "wait_seconds":
                                        "",

                                    "queue_count":
                                        queue_count + 1
                                }
                            )


                            safe_supabase_event(
                                session_id,
                                track_id,
                                "ENTER",
                                None,
                                queue_count + 1
                            )


                else:

                    if not inside_now:

                        person[
                            "candidate_inside_since"
                        ] = None


                # =========================================
                # SERVICE CROSSING
                # =========================================

                previous = person[
                    "previous_point"
                ]


                served_sign = (
                    side_of_line(
                        served_side_point,
                        service_points[0],
                        service_points[1]
                    )
                )


                old_sign = (
                    side_of_line(
                        previous,
                        service_points[0],
                        service_points[1]
                    )
                )


                new_sign = (
                    side_of_line(
                        foot,
                        service_points[0],
                        service_points[1]
                    )
                )


                old_served_side = (
                    old_sign
                    * served_sign
                    > 0
                )


                new_served_side = (
                    new_sign
                    * served_sign
                    > 0
                )


                crossed = (
                    segments_intersect(
                        previous,
                        foot,
                        service_points[0],
                        service_points[1]
                    )
                )


                crossed_to_served = (
                    crossed
                    and
                    not old_served_side
                    and
                    new_served_side
                )


                if (
                    crossed_to_served
                    and
                    person[
                        "confirmed_inside"
                    ]
                    and
                    not person[
                        "served"
                    ]
                    and
                    person[
                        "entry_time"
                    ]
                    is not None
                ):

                    wait_time = (
                        now_timestamp
                        -
                        person[
                            "entry_time"
                        ]
                    )


                    person[
                        "served"
                    ] = True


                    person[
                        "confirmed_inside"
                    ] = False


                    total_served += 1


                    waiting_times.append(
                        wait_time
                    )


                    served_timestamps.append(
                        now_timestamp
                    )


                    print(
                        f"ID {track_id} "
                        f"SERVED "
                        f"{wait_time:.1f}s"
                    )


                    if meal != "test":

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
                                "session_id":
                                    session_id,

                                "timestamp":
                                    now.isoformat(
                                        timespec="seconds"
                                    ),

                                "track_id":
                                    track_id,

                                "event":
                                    "SERVED",

                                "wait_seconds":
                                    round(
                                        wait_time,
                                        2
                                    ),

                                "queue_count":
                                    max(
                                        queue_count - 1,
                                        0
                                    )
                            }
                        )


                        safe_supabase_event(
                            session_id,
                            track_id,
                            "SERVED",
                            round(
                                wait_time,
                                2
                            ),
                            max(
                                queue_count - 1,
                                0
                            )
                        )


                # =========================================
                # EXIT / ABANDONMENT
                # =========================================

                if (
                    not inside_now
                    and
                    person[
                        "confirmed_inside"
                    ]
                    and
                    not person[
                        "served"
                    ]
                ):

                    if (
                        person[
                            "candidate_outside_since"
                        ]
                        is None
                    ):

                        person[
                            "candidate_outside_since"
                        ] = now_timestamp


                    elif (
                        now_timestamp
                        -
                        person[
                            "candidate_outside_since"
                        ]
                        >=
                        EXIT_CONFIRM_TIME
                    ):

                        person[
                            "confirmed_inside"
                        ] = False


                        person[
                            "candidate_outside_since"
                        ] = None


                        person[
                            "entry_time"
                        ] = None


                        total_abandoned += 1


                        print(
                            f"ID {track_id} "
                            "ABANDONED"
                        )


                        if meal != "test":

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
                                    "session_id":
                                        session_id,

                                    "timestamp":
                                        now.isoformat(
                                            timespec="seconds"
                                        ),

                                    "track_id":
                                        track_id,

                                    "event":
                                        "ABANDONED",

                                    "wait_seconds":
                                        "",

                                    "queue_count":
                                        max(
                                            queue_count - 1,
                                            0
                                        )
                                }
                            )


                            safe_supabase_event(
                                session_id,
                                track_id,
                                "ABANDONED",
                                None,
                                max(
                                    queue_count - 1,
                                    0
                                )
                            )


                else:

                    if inside_now:

                        person[
                            "candidate_outside_since"
                        ] = None


                # =========================================
                # COUNT QUEUE
                # =========================================

                if (
                    person[
                        "confirmed_inside"
                    ]
                    and
                    not person[
                        "served"
                    ]
                ):

                    queue_count += 1

                    color = (
                        0,
                        255,
                        0
                    )


                elif person[
                    "served"
                ]:

                    color = (
                        255,
                        0,
                        255
                    )


                else:

                    color = (
                        130,
                        130,
                        130
                    )


                # =========================================
                # DISPLAY DETECTION
                # =========================================

                cv2.rectangle(
                    display,
                    (x1, y1),
                    (x2, y2),
                    color,
                    2
                )


                cv2.circle(
                    display,
                    foot,
                    5,
                    color,
                    -1
                )


                cv2.putText(
                    display,
                    f"ID {track_id}",
                    (
                        x1,
                        max(
                            y1 - 10,
                            20
                        )
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    2
                )


                if inside_now:

                    cv2.putText(
                        display,
                        "IN ROI",
                        (
                            x1,
                            max(
                                y1 - 30,
                                20
                            )
                        ),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.45,
                        (
                            0,
                            255,
                            0
                        ),
                        2
                    )


                person[
                    "previous_point"
                ] = foot


                person[
                    "last_seen"
                ] = now_timestamp


        # =================================================
        # THROUGHPUT
        # =================================================

        while (
            served_timestamps
            and
            now_timestamp
            -
            served_timestamps[0]
            > 60
        ):

            served_timestamps.popleft()


        throughput = len(
            served_timestamps
        )


        # =================================================
        # AVERAGE WAIT
        # =================================================

        avg_wait = (

            sum(
                waiting_times
            )
            /
            len(
                waiting_times
            )

            if waiting_times

            else 0
        )


        # =================================================
        # TREND
        # =================================================

        trend = get_trend(
            queue_count,
            previous_queue_count
        )


        queue_status = (
            get_queue_status(
                queue_count
            )
        )


        # =================================================
        # REAL SNAPSHOT LOGGING
        # =================================================

        if (
            meal != "test"
            and
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


            safe_supabase_snapshot(
                session_id,
                meal,
                queue_count,
                throughput
            )


            last_snapshot = (
                now_timestamp
            )


        # =================================================
        # LIVE SUPABASE STATUS
        # =================================================

        if (
            now_timestamp
            - last_supabase_update
            >= SUPABASE_UPDATE_INTERVAL
        ):

            safe_supabase_update({

                "updated_at":
                    now.isoformat(),

                "meal_period":
                    meal,

                "queue_count":
                    queue_count,

                "queue_status":
                    queue_status,

                "trend":
                    trend,

                "served":
                    total_served,

                "avg_wait_seconds":
                    round(
                        avg_wait,
                        2
                    ),

                "throughput_per_min":
                    throughput,

                "camera_online":
                    True
            })


            last_supabase_update = (
                now_timestamp
            )


        previous_queue_count = (
            queue_count
        )


        # =================================================
        # DASHBOARD BACKGROUND
        # =================================================

        cv2.rectangle(
            display,
            (10, 10),
            (430, 245),
            (0, 0, 0),
            -1
        )


        # =================================================
        # DASHBOARD TEXT
        # =================================================

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
            (
                0,
                200,
                255
            ),
            2
        )


        cv2.putText(
            display,
            f"Queue: {queue_count}",
            (20, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (
                0,
                255,
                0
            ),
            2
        )


        cv2.putText(
            display,
            f"Status: {queue_status}",
            (20, 130),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (
                255,
                255,
                255
            ),
            2
        )


        cv2.putText(
            display,
            f"Served: {total_served}",
            (20, 160),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (
                255,
                255,
                255
            ),
            2
        )


        cv2.putText(
            display,
            f"Avg wait: {avg_wait:.1f}s",
            (20, 190),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (
                255,
                255,
                255
            ),
            2
        )


        cv2.putText(
            display,
            f"Throughput: {throughput}/min",
            (20, 220),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (
                255,
                255,
                255
            ),
            2
        )


        # =================================================
        # TEST MODE LABEL
        # =================================================

        if meal == "test":

            cv2.putText(
                display,
                "TEST MODE - NOT SAVED AS RESEARCH DATA",
                (
                    20,
                    display.shape[0] - 20
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (
                    0,
                    255,
                    255
                ),
                2
            )


        # =================================================
        # SHOW WINDOW
        # =================================================

        cv2.imshow(
            "Q-SENSE Research",
            display
        )


        if (
            cv2.waitKey(1)
            & 0xFF
            == ord("q")
        ):

            break


except KeyboardInterrupt:

    print(
        "\nQ-SENSE stopped "
        "with Ctrl+C."
    )


finally:

    cap.release()

    cv2.destroyAllWindows()

    mark_offline()