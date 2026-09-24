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
SERVICE_FILE = "service_line.json"

print("Starting Q-SENSE Smart Service Tracking...")

model = YOLO(MODEL_NAME)

# =========================================================
# LOAD QUEUE ZONE
# =========================================================

if not os.path.exists(ROI_FILE):
    print("ERROR: queue_zone.json not found.")
    print("Create the queue zone first.")
    exit()

with open(ROI_FILE, "r") as f:
    queue_zone = json.load(f)

queue_zone = [tuple(point) for point in queue_zone]
contour = np.array(queue_zone, dtype=np.int32)

print("Queue zone loaded.")

# =========================================================
# SERVICE LINE CALIBRATION
# =========================================================

service_points = []
served_side_point = None

if os.path.exists(SERVICE_FILE):

    with open(SERVICE_FILE, "r") as f:
        service_data = json.load(f)

    service_points = [
        tuple(service_data["line"][0]),
        tuple(service_data["line"][1])
    ]

    served_side_point = tuple(
        service_data["served_side"]
    )

    print("Saved service line loaded.")

else:

    print("")
    print("SERVICE LINE NOT CALIBRATED")
    print("Click:")
    print("1. First end of service line")
    print("2. Second end of service line")
    print("3. Any point on the SERVED side")
    print("Then press ENTER to save.")
    print("")


# =========================================================
# GEOMETRY FUNCTIONS
# =========================================================

def side_of_line(point, a, b):
    """
    Returns positive/negative depending on which
    side of directed line A -> B the point lies.
    """

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
    """
    Checks whether movement p1 -> q1 actually crosses
    the finite service line p2 -> q2.
    """

    o1 = orientation(p1, q1, p2)
    o2 = orientation(p1, q1, q2)
    o3 = orientation(p2, q2, p1)
    o4 = orientation(p2, q2, q1)

    if o1 != o2 and o3 != o4:
        return True

    if o1 == 0 and on_segment(p1, p2, q1):
        return True

    if o2 == 0 and on_segment(p1, q2, q1):
        return True

    if o3 == 0 and on_segment(p2, p1, q2):
        return True

    if o4 == 0 and on_segment(p2, q1, q2):
        return True

    return False


# =========================================================
# MOUSE CALLBACK
# =========================================================

def mouse_callback(event, x, y, flags, param):

    global service_points
    global served_side_point

    if event != cv2.EVENT_LBUTTONDOWN:
        return

    # First two clicks = service line
    if len(service_points) < 2:

        service_points.append((x, y))

        print(
            f"Service line point {len(service_points)}: "
            f"({x}, {y})"
        )

    # Third click = served side
    elif served_side_point is None:

        served_side_point = (x, y)

        print(
            f"Served-side point: ({x}, {y})"
        )

        print("Press ENTER to save calibration.")


# =========================================================
# TRACKING MEMORY
# =========================================================

track_data = {}

total_entries = 0
total_served = 0
total_abandoned = 0

waiting_times = []

served_timestamps = deque()

last_wait_time = None

# =========================================================
# CAMERA
# =========================================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("ERROR: Could not open webcam.")
    exit()

cv2.namedWindow("Q-SENSE Smart Service")
cv2.setMouseCallback(
    "Q-SENSE Smart Service",
    mouse_callback
)

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
        0.10,
        display,
        0.90,
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
    # DRAW SERVICE CALIBRATION
    # =====================================================

    for point in service_points:

        cv2.circle(
            display,
            point,
            7,
            (0, 0, 255),
            -1
        )

    if len(service_points) == 2:

        cv2.line(
            display,
            service_points[0],
            service_points[1],
            (0, 0, 255),
            4
        )

        midpoint = (
            (
                service_points[0][0]
                + service_points[1][0]
            ) // 2,
            (
                service_points[0][1]
                + service_points[1][1]
            ) // 2
        )

        cv2.putText(
            display,
            "SERVICE LINE",
            (
                midpoint[0] - 60,
                midpoint[1] - 10
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 255),
            2
        )

    if served_side_point is not None:

        cv2.circle(
            display,
            served_side_point,
            10,
            (255, 0, 255),
            -1
        )

        cv2.putText(
            display,
            "SERVED SIDE",
            (
                served_side_point[0] + 10,
                served_side_point[1]
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 0, 255),
            2
        )

    # =====================================================
    # TRACK PEOPLE
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

    if (
        results.boxes is not None
        and results.boxes.id is not None
    ):

        boxes = (
            results.boxes.xyxy
            .cpu()
            .numpy()
        )

        track_ids = (
            results.boxes.id
            .int()
            .cpu()
            .tolist()
        )

        confidences = (
            results.boxes.conf
            .cpu()
            .tolist()
        )

        for box, track_id, confidence in zip(
            boxes,
            track_ids,
            confidences
        ):

            x1, y1, x2, y2 = map(int, box)

            foot_x = (x1 + x2) // 2
            foot_y = y2

            current_point = (
                foot_x,
                foot_y
            )

            inside = (
                cv2.pointPolygonTest(
                    contour,
                    current_point,
                    False
                )
                >= 0
            )

            # =============================================
            # NEW PERSON
            # =============================================

            if track_id not in track_data:

                track_data[track_id] = {
                    "inside": False,
                    "entry_time": None,
                    "last_seen": current_time,
                    "previous_point": current_point,
                    "served": False
                }

            person = track_data[track_id]

            previous_point = (
                person["previous_point"]
            )

            previous_inside = (
                person["inside"]
            )

            # =============================================
            # ENTER QUEUE
            # =============================================

            if (
                inside
                and not previous_inside
                and not person["served"]
            ):

                person["inside"] = True
                person["entry_time"] = current_time

                total_entries += 1

                print(
                    f"ID {track_id} ENTERED queue"
                )

            # =============================================
            # SERVICE LINE CROSSING
            # =============================================

            crossed_to_served = False

            if (
                len(service_points) == 2
                and served_side_point is not None
            ):

                line_a = service_points[0]
                line_b = service_points[1]

                served_sign = side_of_line(
                    served_side_point,
                    line_a,
                    line_b
                )

                old_sign = side_of_line(
                    previous_point,
                    line_a,
                    line_b
                )

                new_sign = side_of_line(
                    current_point,
                    line_a,
                    line_b
                )

                # Did actual movement intersect
                # the finite service segment?
                crossed_segment = (
                    segments_intersect(
                        previous_point,
                        current_point,
                        line_a,
                        line_b
                    )
                )

                # Determine which side each point is on
                old_on_served_side = (
                    old_sign * served_sign > 0
                )

                new_on_served_side = (
                    new_sign * served_sign > 0
                )

                crossed_to_served = (
                    crossed_segment
                    and not old_on_served_side
                    and new_on_served_side
                )

            # =============================================
            # PERSON SERVED
            # =============================================

            if (
                crossed_to_served
                and not person["served"]
                and person["entry_time"] is not None
            ):

                wait_time = (
                    current_time
                    - person["entry_time"]
                )

                person["served"] = True
                person["inside"] = False

                total_served += 1

                waiting_times.append(
                    wait_time
                )

                served_timestamps.append(
                    current_time
                )

                last_wait_time = wait_time

                print(
                    f"ID {track_id} SERVED "
                    f"after {wait_time:.1f} sec"
                )

            # =============================================
            # LEFT QUEUE WITHOUT SERVICE
            # =============================================

            elif (
                not inside
                and previous_inside
                and not person["served"]
            ):

                person["inside"] = False

                total_abandoned += 1

                print(
                    f"ID {track_id} LEFT EARLY"
                )

                person["entry_time"] = None

            # =============================================
            # QUEUE COUNT
            # =============================================

            if (
                inside
                and not person["served"]
            ):

                queue_count += 1

            # =============================================
            # VISUAL DISPLAY
            # =============================================

            if person["served"]:

                color = (255, 0, 255)

                label = (
                    f"ID {track_id} SERVED"
                )

            elif inside:

                color = (0, 255, 0)

                if person["entry_time"]:

                    dwell = (
                        current_time
                        - person["entry_time"]
                    )

                else:

                    dwell = 0

                label = (
                    f"ID {track_id} "
                    f"| {dwell:.0f}s"
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
                (
                    x1,
                    max(y1 - 10, 20)
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2
            )

            person["previous_point"] = (
                current_point
            )

            person["last_seen"] = (
                current_time
            )

    # =====================================================
    # THROUGHPUT - LAST 60 SEC
    # =====================================================

    while (
        served_timestamps
        and
        current_time
        - served_timestamps[0]
        > 60
    ):

        served_timestamps.popleft()

    throughput = len(
        served_timestamps
    )

    # =====================================================
    # AVERAGE WAIT
    # =====================================================

    if waiting_times:

        average_wait = (
            sum(waiting_times)
            / len(waiting_times)
        )

    else:

        average_wait = 0

    # =====================================================
    # REMOVE STALE IDS
    # =====================================================

    stale_ids = []

    for track_id, data in track_data.items():

        if (
            current_time
            - data["last_seen"]
            > 10
        ):

            stale_ids.append(
                track_id
            )

    for track_id in stale_ids:

        del track_data[track_id]

    # =====================================================
    # DASHBOARD
    # =====================================================

    cv2.rectangle(
        display,
        (10, 10),
        (400, 225),
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
        (200, 105),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )

    cv2.putText(
        display,
        f"Avg wait: {average_wait:.1f}s",
        (20, 135),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )

    cv2.putText(
        display,
        f"Throughput: {throughput}/min",
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
        "Click 2 line pts + served side | ENTER save | R reset | Q quit",
        (
            10,
            display.shape[0] - 15
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        (255, 255, 255),
        1
    )

    cv2.imshow(
        "Q-SENSE Smart Service",
        display
    )

    key = cv2.waitKey(1) & 0xFF

    # =====================================================
    # SAVE SERVICE LINE
    # =====================================================

    if key == 13:

        if (
            len(service_points) == 2
            and served_side_point is not None
        ):

            data = {
                "line": [
                    service_points[0],
                    service_points[1]
                ],
                "served_side":
                    served_side_point
            }

            with open(
                SERVICE_FILE,
                "w"
            ) as f:

                json.dump(
                    data,
                    f
                )

            print(
                "Service calibration saved!"
            )

        else:

            print(
                "Need 2 line points + "
                "1 served-side point."
            )

    # =====================================================
    # RESET SERVICE LINE
    # =====================================================

    elif key == ord("r"):

        service_points.clear()
        served_side_point = None

        if os.path.exists(
            SERVICE_FILE
        ):
            os.remove(
                SERVICE_FILE
            )

        print("")
        print("Service calibration reset.")
        print("Click:")
        print("1. Line start")
        print("2. Line end")
        print("3. Served side")
        print("")

    # =====================================================
    # QUIT
    # =====================================================

    elif key == ord("q"):

        break


cap.release()
cv2.destroyAllWindows()