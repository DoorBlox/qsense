import csv
import os
import math
import random
from datetime import datetime, timedelta, time

# =========================================================
# Q-SENSE SYNTHETIC DEMO DATA GENERATOR
# =========================================================

random.seed(42)

DATA_DIR = "demo_data"
os.makedirs(DATA_DIR, exist_ok=True)

SESSIONS_FILE = os.path.join(DATA_DIR, "sessions.csv")
SNAPSHOTS_FILE = os.path.join(DATA_DIR, "queue_snapshots.csv")
EVENTS_FILE = os.path.join(DATA_DIR, "queue_events.csv")
MEAL_FILE = os.path.join(DATA_DIR, "meal_log.csv")
VALIDATION_FILE = os.path.join(DATA_DIR, "manual_validation.csv")

# =========================================================
# IMPORTANT
# =========================================================

print("")
print("============================================")
print(" Q-SENSE SYNTHETIC DEMO DATA GENERATOR")
print("============================================")
print("")
print("WARNING:")
print("All generated data are SIMULATED.")
print("They are NOT real research findings.")
print("")

# =========================================================
# SAMPLE MENUS
# =========================================================

menus = {

    "M001": {
        "meal": "breakfast",
        "staple": "Bubur ayam",
        "animal_protein": "Ayam suwir",
        "plant_protein": "",
        "vegetable": "",
        "fruit": "Pisang",
        "drink": "Teh",
        "demand_factor": 0.90
    },

    "M002": {
        "meal": "breakfast",
        "staple": "Nasi goreng",
        "animal_protein": "Telur",
        "plant_protein": "Tempe",
        "vegetable": "Acar",
        "fruit": "Jeruk",
        "drink": "Teh",
        "demand_factor": 1.15
    },

    "M003": {
        "meal": "breakfast",
        "staple": "Roti",
        "animal_protein": "Telur",
        "plant_protein": "",
        "vegetable": "",
        "fruit": "Semangka",
        "drink": "Susu",
        "demand_factor": 0.78
    },

    "M004": {
        "meal": "lunch",
        "staple": "Nasi putih",
        "animal_protein": "Ayam goreng",
        "plant_protein": "Tempe",
        "vegetable": "Sayur sop",
        "fruit": "Semangka",
        "drink": "Air putih",
        "demand_factor": 1.30
    },

    "M005": {
        "meal": "lunch",
        "staple": "Nasi putih",
        "animal_protein": "Ikan goreng",
        "plant_protein": "Tahu",
        "vegetable": "Capcay",
        "fruit": "Pisang",
        "drink": "Air putih",
        "demand_factor": 0.92
    },

    "M006": {
        "meal": "lunch",
        "staple": "Nasi putih",
        "animal_protein": "Daging sapi",
        "plant_protein": "Tempe",
        "vegetable": "Sayur asem",
        "fruit": "Melon",
        "drink": "Air putih",
        "demand_factor": 1.18
    },

    "M007": {
        "meal": "dinner",
        "staple": "Nasi putih",
        "animal_protein": "Ayam kecap",
        "plant_protein": "Tahu",
        "vegetable": "Tumis sawi",
        "fruit": "Jeruk",
        "drink": "Air putih",
        "demand_factor": 1.12
    },

    "M008": {
        "meal": "dinner",
        "staple": "Mie goreng",
        "animal_protein": "Ayam suwir",
        "plant_protein": "Tempe",
        "vegetable": "Sawi",
        "fruit": "Semangka",
        "drink": "Air putih",
        "demand_factor": 1.24
    },

    "M009": {
        "meal": "dinner",
        "staple": "Nasi putih",
        "animal_protein": "Ikan",
        "plant_protein": "Tahu",
        "vegetable": "Sup sayur",
        "fruit": "Pisang",
        "drink": "Air putih",
        "demand_factor": 0.88
    }
}

menu_rotation = {

    "breakfast": [
        "M001",
        "M002",
        "M003"
    ],

    "lunch": [
        "M004",
        "M005",
        "M006"
    ],

    "dinner": [
        "M007",
        "M008",
        "M009"
    ]
}

# =========================================================
# MEAL WINDOWS
# =========================================================

meal_settings = {

    "breakfast": {
        "prefix": "B",
        "start": time(5, 30),
        "end": time(7, 30),
        "base_peak": 10,
        "peak_minute": 35
    },

    "lunch": {
        "prefix": "L",
        "start": time(11, 30),
        "end": time(13, 30),
        "base_peak": 17,
        "peak_minute": 30
    },

    "dinner": {
        "prefix": "D",
        "start": time(17, 0),
        "end": time(19, 0),
        "base_peak": 13,
        "peak_minute": 40
    }
}

# =========================================================
# DATE RANGE
#
# 14 days lets menus repeat several times.
# =========================================================

START_DATE = datetime(2026, 9, 1)
NUMBER_OF_DAYS = 14

SNAPSHOT_SECONDS = 30

# =========================================================
# HELPERS
# =========================================================

def write_csv(filename, headers, rows):

    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=headers
        )

        writer.writeheader()

        writer.writerows(rows)


def queue_curve(
    elapsed_minutes,
    peak,
    peak_minute
):

    # Gaussian-shaped queue rush
    width = 18

    value = (
        peak
        * math.exp(
            -(
                (
                    elapsed_minutes
                    - peak_minute
                ) ** 2
            )
            /
            (
                2 * width ** 2
            )
        )
    )

    # small background queue
    value += 1

    # random real-world variation
    value += random.gauss(
        0,
        0.8
    )

    return max(
        0,
        int(round(value))
    )


# =========================================================
# STORAGE
# =========================================================

session_rows = []
snapshot_rows = []
event_rows = []
meal_rows = []

# =========================================================
# GENERATE 14 DAYS
# =========================================================

for day_index in range(NUMBER_OF_DAYS):

    date = (
        START_DATE
        + timedelta(days=day_index)
    )

    date_text = date.strftime("%Y-%m-%d")

    for meal_name, settings in meal_settings.items():

        # -----------------------------------------
        # Choose repeating menu
        # -----------------------------------------

        rotation = menu_rotation[
            meal_name
        ]

        menu_id = rotation[
            day_index % len(rotation)
        ]

        menu = menus[
            menu_id
        ]

        # -----------------------------------------
        # Session
        # -----------------------------------------

        session_id = (
            f"{settings['prefix']}_"
            f"{date.strftime('%Y%m%d')}"
        )

        start_datetime = datetime.combine(
            date.date(),
            settings["start"]
        )

        end_datetime = datetime.combine(
            date.date(),
            settings["end"]
        )

        session_rows.append(
            {
                "session_id":
                    session_id,

                "date":
                    date_text,

                "weekday":
                    date.strftime("%A"),

                "meal_period":
                    meal_name,

                "start_timestamp":
                    start_datetime.isoformat(
                        timespec="seconds"
                    ),

                "end_timestamp":
                    end_datetime.isoformat(
                        timespec="seconds"
                    ),

                "model":
                    "yolo11n.pt",

                "confidence_threshold":
                    0.45,

                "data_source":
                    "SYNTHETIC_DEMO"
            }
        )

        # -----------------------------------------
        # Menu log
        # -----------------------------------------

        meal_rows.append(
            {
                "date":
                    date_text,

                "meal_period":
                    meal_name,

                "menu_id":
                    menu_id,

                "staple":
                    menu["staple"],

                "animal_protein":
                    menu["animal_protein"],

                "plant_protein":
                    menu["plant_protein"],

                "vegetable":
                    menu["vegetable"],

                "fruit":
                    menu["fruit"],

                "drink":
                    menu["drink"],

                "data_source":
                    "SYNTHETIC_DEMO"
            }
        )

        # -----------------------------------------
        # Daily random variation
        # -----------------------------------------

        daily_factor = random.uniform(
            0.90,
            1.10
        )

        peak = (
            settings["base_peak"]
            * menu["demand_factor"]
            * daily_factor
        )

        # -----------------------------------------
        # Generate queue snapshots
        # -----------------------------------------

        current = start_datetime

        snapshot_counts = []

        while current < end_datetime:

            elapsed_minutes = (
                current
                - start_datetime
            ).total_seconds() / 60

            count = queue_curve(
                elapsed_minutes,
                peak,
                settings["peak_minute"]
            )

            snapshot_counts.append(
                (
                    current,
                    count
                )
            )

            current += timedelta(
                seconds=SNAPSHOT_SECONDS
            )

        # -----------------------------------------
        # Approximate throughput
        # -----------------------------------------

        served_total = 0

        for timestamp, count in snapshot_counts:

            throughput = max(
                0,
                int(
                    round(
                        2
                        + count * 0.18
                        + random.gauss(0, 0.5)
                    )
                )
            )

            snapshot_rows.append(
                {
                    "session_id":
                        session_id,

                    "timestamp":
                        timestamp.isoformat(
                            timespec="seconds"
                        ),

                    "queue_count":
                        count,

                    "throughput_per_min":
                        throughput,

                    "data_source":
                        "SYNTHETIC_DEMO"
                }
            )

        # -----------------------------------------
        # Generate fake individual service events
        # -----------------------------------------

        approximate_students = random.randint(
            80,
            150
        )

        if meal_name == "lunch":
            approximate_students += 25

        for person_number in range(
            1,
            approximate_students + 1
        ):

            arrival_offset = random.gauss(
                settings["peak_minute"],
                20
            )

            arrival_offset = max(
                0,
                min(
                    110,
                    arrival_offset
                )
            )

            entry_time = (
                start_datetime
                + timedelta(
                    minutes=arrival_offset
                )
            )

            approximate_queue = queue_curve(
                arrival_offset,
                peak,
                settings["peak_minute"]
            )

            wait_minutes = (
                0.8
                + approximate_queue * 0.22
                + random.uniform(
                    -0.5,
                    0.7
                )
            )

            wait_minutes = max(
                0.3,
                wait_minutes
            )

            served_time = (
                entry_time
                + timedelta(
                    minutes=wait_minutes
                )
            )

            track_id = person_number

            event_rows.append(
                {
                    "session_id":
                        session_id,

                    "timestamp":
                        entry_time.isoformat(
                            timespec="seconds"
                        ),

                    "track_id":
                        track_id,

                    "event":
                        "ENTER",

                    "wait_seconds":
                        "",

                    "queue_count":
                        approximate_queue,

                    "data_source":
                        "SYNTHETIC_DEMO"
                }
            )

            # Small simulated abandonment probability
            abandoned = (
                random.random() < 0.02
            )

            if abandoned:

                event_rows.append(
                    {
                        "session_id":
                            session_id,

                        "timestamp":
                            (
                                entry_time
                                + timedelta(
                                    minutes=
                                    wait_minutes / 2
                                )
                            ).isoformat(
                                timespec="seconds"
                            ),

                        "track_id":
                            track_id,

                        "event":
                            "ABANDONED",

                        "wait_seconds":
                            "",

                        "queue_count":
                            approximate_queue,

                        "data_source":
                            "SYNTHETIC_DEMO"
                    }
                )

            else:

                event_rows.append(
                    {
                        "session_id":
                            session_id,

                        "timestamp":
                            served_time.isoformat(
                                timespec="seconds"
                            ),

                        "track_id":
                            track_id,

                        "event":
                            "SERVED",

                        "wait_seconds":
                            round(
                                wait_minutes * 60,
                                1
                            ),

                        "queue_count":
                            approximate_queue,

                        "data_source":
                            "SYNTHETIC_DEMO"
                    }
                )

# =========================================================
# SYNTHETIC VALIDATION
# =========================================================

validation_rows = []

sample_snapshots = random.sample(
    snapshot_rows,
    80
)

for snap in sample_snapshots:

    detected = int(
        snap["queue_count"]
    )

    # Simulate small counting error
    # Slight undercount tendency at dense queues
    if detected >= 12:

        error = random.choices(
            [-2, -1, 0, 1],
            weights=[10, 35, 45, 10]
        )[0]

    else:

        error = random.choices(
            [-1, 0, 1],
            weights=[20, 60, 20]
        )[0]

    # detected - actual = error
    actual = max(
        0,
        detected - error
    )

    validation_rows.append(
        {
            "session_id":
                snap["session_id"],

            "validation_timestamp":
                snap["timestamp"],

            "snapshot_timestamp":
                snap["timestamp"],

            "meal_period":
                "",

            "actual_count":
                actual,

            "detected_count":
                detected,

            "error":
                detected - actual,

            "absolute_error":
                abs(
                    detected - actual
                ),

            "notes":
                "SYNTHETIC DEMO ONLY",

            "data_source":
                "SYNTHETIC_DEMO"
        }
    )

# =========================================================
# SAVE FILES
# =========================================================

write_csv(
    SESSIONS_FILE,

    [
        "session_id",
        "date",
        "weekday",
        "meal_period",
        "start_timestamp",
        "end_timestamp",
        "model",
        "confidence_threshold",
        "data_source"
    ],

    session_rows
)

write_csv(
    SNAPSHOTS_FILE,

    [
        "session_id",
        "timestamp",
        "queue_count",
        "throughput_per_min",
        "data_source"
    ],

    snapshot_rows
)

write_csv(
    EVENTS_FILE,

    [
        "session_id",
        "timestamp",
        "track_id",
        "event",
        "wait_seconds",
        "queue_count",
        "data_source"
    ],

    event_rows
)

write_csv(
    MEAL_FILE,

    [
        "date",
        "meal_period",
        "menu_id",
        "staple",
        "animal_protein",
        "plant_protein",
        "vegetable",
        "fruit",
        "drink",
        "data_source"
    ],

    meal_rows
)

write_csv(
    VALIDATION_FILE,

    [
        "session_id",
        "validation_timestamp",
        "snapshot_timestamp",
        "meal_period",
        "actual_count",
        "detected_count",
        "error",
        "absolute_error",
        "notes",
        "data_source"
    ],

    validation_rows
)

# =========================================================
# README WARNING
# =========================================================

with open(
    os.path.join(
        DATA_DIR,
        "README_DEMO.txt"
    ),
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "Q-SENSE SYNTHETIC DEMONSTRATION DATA\n"
        "\n"
        "These files contain computer-generated simulated data.\n"
        "They are intended only to demonstrate the proposed\n"
        "Q-SENSE analytics workflow and dashboard.\n"
        "\n"
        "They must NOT be reported as empirical research results.\n"
        "\n"
        "Real measurements will later be stored separately\n"
        "inside the /data directory.\n"
    )

print("Demo dataset successfully generated.")
print("")
print(f"Sessions:             {len(session_rows)}")
print(f"Queue snapshots:      {len(snapshot_rows)}")
print(f"Queue events:         {len(event_rows)}")
print(f"Validation samples:   {len(validation_rows)}")
print("")
print("Location:")
print(os.path.abspath(DATA_DIR))
print("")
print("ALL VALUES ARE SYNTHETIC.")