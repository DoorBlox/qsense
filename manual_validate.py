import csv
import os
from datetime import datetime, time as dt_time

DATA_DIR = "data"
VALIDATION_FILE = os.path.join(DATA_DIR, "manual_validation.csv")
SNAPSHOTS_FILE = os.path.join(DATA_DIR, "queue_snapshots.csv")

os.makedirs(DATA_DIR, exist_ok=True)


def get_meal_period():

    now = datetime.now().time()

    if dt_time(5, 30) <= now < dt_time(7, 30):
        return "breakfast"

    if dt_time(11, 30) <= now < dt_time(13, 30):
        return "lunch"

    if dt_time(17, 0) <= now < dt_time(19, 0):
        return "dinner"

    return "outside_meal"


def get_session_id(meal):

    prefixes = {
        "breakfast": "B",
        "lunch": "L",
        "dinner": "D"
    }

    if meal not in prefixes:
        return ""

    date = datetime.now().strftime("%Y%m%d")

    return f"{prefixes[meal]}_{date}"


def get_latest_qsense_count(session_id):

    if not os.path.exists(SNAPSHOTS_FILE):
        return None, None

    latest_count = None
    latest_time = None

    with open(
        SNAPSHOTS_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            if row["session_id"] == session_id:

                latest_count = int(
                    row["queue_count"]
                )

                latest_time = row[
                    "timestamp"
                ]

    return latest_count, latest_time


print("")
print("====================================")
print("      Q-SENSE MANUAL VALIDATION")
print("====================================")
print("")

meal = get_meal_period()

if meal == "outside_meal":

    print("Currently outside a meal period.")
    print("")
    print(
        "You can still test validation, "
        "but normal research validation "
        "should be done during meals."
    )

session_id = get_session_id(meal)

if session_id:
    print(f"Session: {session_id}")
    print(f"Meal:    {meal.upper()}")
    print("")

manual_input = input(
    "Actual number of people in queue: "
).strip()

try:

    manual_count = int(
        manual_input
    )

except ValueError:

    print("Please enter a whole number.")
    exit()


detected_count, snapshot_time = (
    get_latest_qsense_count(
        session_id
    )
)

if detected_count is None:

    print("")
    print(
        "No Q-SENSE snapshot found "
        "for this session."
    )

    detected_input = input(
        "Enter Q-SENSE count manually: "
    ).strip()

    try:

        detected_count = int(
            detected_input
        )

    except ValueError:

        print("Invalid count.")
        exit()

    snapshot_time = ""

now = datetime.now()

error = detected_count - manual_count
absolute_error = abs(error)

file_exists = os.path.exists(
    VALIDATION_FILE
)

headers = [
    "session_id",
    "validation_timestamp",
    "snapshot_timestamp",
    "meal_period",
    "actual_count",
    "detected_count",
    "error",
    "absolute_error",
    "notes"
]

notes = input(
    "Notes [optional]: "
).strip()

with open(
    VALIDATION_FILE,
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
        {
            "session_id":
                session_id,

            "validation_timestamp":
                now.isoformat(
                    timespec="seconds"
                ),

            "snapshot_timestamp":
                snapshot_time,

            "meal_period":
                meal,

            "actual_count":
                manual_count,

            "detected_count":
                detected_count,

            "error":
                error,

            "absolute_error":
                absolute_error,

            "notes":
                notes
        }
    )

print("")
print("VALIDATION SAVED")
print("")
print(f"Actual:     {manual_count}")
print(f"Q-SENSE:    {detected_count}")
print(f"Error:      {error:+d}")
print(f"Abs. error: {absolute_error}")
print("")