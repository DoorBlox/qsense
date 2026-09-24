import os
import math
import random
import statistics
from datetime import datetime, date, time, timedelta, timezone

from dotenv import load_dotenv
from supabase import create_client


# =========================================================
# Q-SENSE PRESENTATION DATA
# =========================================================
# Main-dish names = supplied cafeteria menu names.
# Queue metrics, validation observations, side dishes,
# demand scores, and acceptance scores = SYNTHETIC DEMO DATA.
# =========================================================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL missing from .env")

if not SUPABASE_SERVICE_KEY:
    raise ValueError("SUPABASE_SERVICE_KEY missing from .env")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY
)

random.seed(20260924)

WIB = timezone(
    timedelta(hours=7)
)

DATA_SOURCE = "SYNTHETIC_DEMO"


MENUS = [
    {
        "menu_id": "M2209B",
        "date": "2026-09-22",
        "meal": "breakfast",
        "main": "NASI GORENG",
        "staple": "Nasi goreng",
        "animal": "Telur orak-arik (demo side)",
        "plant": "Tempe goreng (demo side)",
        "vegetable": "Acar timun-wortel (demo side)",
        "fruit": "Semangka (demo)",
        "drink": "Air putih",
        "other": "Kerupuk (demo)",
        "demand": 82,
        "acceptance": 88,
        "peak_scale": 14,
        "served_target": 104,
    },
    {
        "menu_id": "M2209L",
        "date": "2026-09-22",
        "meal": "lunch",
        "main": "EMPAL",
        "staple": "Nasi putih",
        "animal": "Empal",
        "plant": "Tempe orek (demo side)",
        "vegetable": "Sayur asem (demo side)",
        "fruit": "Pepaya (demo)",
        "drink": "Air putih",
        "other": "Sambal (demo)",
        "demand": 94,
        "acceptance": 92,
        "peak_scale": 22,
        "served_target": 137,
    },
    {
        "menu_id": "M2209D",
        "date": "2026-09-22",
        "meal": "dinner",
        "main": "IKAN DORY CRISPY",
        "staple": "Nasi putih",
        "animal": "Ikan dory crispy",
        "plant": "Tahu goreng (demo side)",
        "vegetable": "Tumis sayuran (demo side)",
        "fruit": "Melon (demo)",
        "drink": "Air putih",
        "other": "Saus (demo)",
        "demand": 86,
        "acceptance": 87,
        "peak_scale": 17,
        "served_target": 116,
    },
    {
        "menu_id": "M2309B",
        "date": "2026-09-23",
        "meal": "breakfast",
        "main": "TELUR PUYUH",
        "staple": "Nasi putih",
        "animal": "Telur puyuh",
        "plant": "Tahu goreng (demo side)",
        "vegetable": "Sayur sop (demo side)",
        "fruit": "Melon (demo)",
        "drink": "Air putih",
        "other": "Sambal (demo)",
        "demand": 69,
        "acceptance": 76,
        "peak_scale": 11,
        "served_target": 91,
    },
    {
        "menu_id": "M2309L",
        "date": "2026-09-23",
        "meal": "lunch",
        "main": "TUNA ASAM MANIS",
        "staple": "Nasi putih",
        "animal": "Tuna asam manis",
        "plant": "Tempe goreng (demo side)",
        "vegetable": "Tumis sawi (demo side)",
        "fruit": "Pisang (demo)",
        "drink": "Air putih",
        "other": "Sambal (demo)",
        "demand": 80,
        "acceptance": 84,
        "peak_scale": 18,
        "served_target": 119,
    },
    {
        "menu_id": "M2309D",
        "date": "2026-09-23",
        "meal": "dinner",
        "main": "BOLA BOLA DAGING",
        "staple": "Nasi putih",
        "animal": "Bola-bola daging",
        "plant": "Tahu kecap (demo side)",
        "vegetable": "Capcay (demo side)",
        "fruit": "Jeruk (demo)",
        "drink": "Air putih",
        "other": "Saus (demo)",
        "demand": 91,
        "acceptance": 90,
        "peak_scale": 20,
        "served_target": 128,
    },
    {
        "menu_id": "M2409B",
        "date": "2026-09-24",
        "meal": "breakfast",
        "main": "CHICKEN KARAGE",
        "staple": "Nasi putih",
        "animal": "Chicken karaage",
        "plant": "Tempe orek (demo side)",
        "vegetable": "Capcay (demo side)",
        "fruit": "Jeruk (demo)",
        "drink": "Air putih",
        "other": "Saus (demo)",
        "demand": 90,
        "acceptance": 91,
        "peak_scale": 18,
        "served_target": 121,
    },
    {
        "menu_id": "M2409L",
        "date": "2026-09-24",
        "meal": "lunch",
        "main": "AYAM MENTEGA",
        "staple": "Nasi putih",
        "animal": "Ayam mentega",
        "plant": "Tahu goreng (demo side)",
        "vegetable": "Tumis buncis-wortel (demo side)",
        "fruit": "Pisang (demo)",
        "drink": "Air putih",
        "other": "Sambal (demo)",
        "demand": 97,
        "acceptance": 94,
        "peak_scale": 24,
        "served_target": 145,
    },
    {
        "menu_id": "M2409D",
        "date": "2026-09-24",
        "meal": "dinner",
        "main": "TELUR GULAI",
        "staple": "Nasi putih",
        "animal": "Telur gulai",
        "plant": "Tempe goreng (demo side)",
        "vegetable": "Sayur bening (demo side)",
        "fruit": "Pepaya (demo)",
        "drink": "Air putih",
        "other": "Sambal (demo)",
        "demand": 73,
        "acceptance": 79,
        "peak_scale": 13,
        "served_target": 99,
    },
]


MEAL_STARTS = {
    "breakfast": time(5, 30),
    "lunch": time(11, 30),
    "dinner": time(17, 0),
}

MEAL_PREFIX = {
    "breakfast": "B",
    "lunch": "L",
    "dinner": "D",
}

MEAL_CENTER = {
    "breakfast": 8,
    "lunch": 10,
    "dinner": 9,
}


def session_id(menu):
    return (
        f"M_{MEAL_PREFIX[menu['meal']]}_"
        f"{menu['date'].replace('-', '')}"
    )


def queue_curve(menu):
    amplitude = menu["peak_scale"]
    center = MEAL_CENTER[menu["meal"]]
    sigma = 3.0
    values = []

    for i in range(25):
        primary = (
            amplitude
            * math.exp(
                -((i - center) ** 2)
                / (2 * sigma ** 2)
            )
        )

        secondary = (
            amplitude
            * 0.28
            * math.exp(
                -((i - (center + 5)) ** 2)
                / (2 * 2.2 ** 2)
            )
        )

        noise = random.uniform(-1.1, 1.1)

        values.append(
            max(
                0,
                int(
                    round(
                        primary
                        + secondary
                        + noise
                    )
                )
            )
        )

    return values


print("Cleaning previous SYNTHETIC_DEMO data...")

for table in [
    "queue_snapshots",
    "meal_log",
    "manual_validation",
    "session_metrics",
]:
    try:
        (
            supabase
            .table(table)
            .delete()
            .eq("data_source", DATA_SOURCE)
            .execute()
        )
    except Exception as exc:
        print(
            f"Cleanup warning "
            f"({table}): {exc}"
        )


# =========================================================
# MENUS
# =========================================================

meal_rows = []

for menu in MENUS:
    meal_rows.append(
        {
            "menu_id": menu["menu_id"],
            "meal_date": menu["date"],
            "meal_period": menu["meal"],
            "main_dish": menu["main"],
            "staple": menu["staple"],
            "animal_protein": menu["animal"],
            "plant_protein": menu["plant"],
            "vegetable": menu["vegetable"],
            "fruit": menu["fruit"],
            "drink": menu["drink"],
            "other": menu["other"],
            "data_source": DATA_SOURCE,
        }
    )

supabase.table(
    "meal_log"
).insert(
    meal_rows
).execute()

print(
    f"Inserted {len(meal_rows)} menu rows."
)


# =========================================================
# QUEUE SNAPSHOTS + SESSION METRICS
# =========================================================

snapshot_rows = []
metric_rows = []

for menu in MENUS:
    sid = session_id(menu)
    counts = queue_curve(menu)

    start_dt = datetime.combine(
        date.fromisoformat(
            menu["date"]
        ),
        MEAL_STARTS[
            menu["meal"]
        ],
        tzinfo=WIB,
    )

    for i, count in enumerate(counts):
        timestamp = (
            start_dt
            + timedelta(
                minutes=i * 5
            )
        )

        throughput = round(
            max(
                0,
                0.8
                + count * 0.12
                + random.uniform(
                    -0.3,
                    0.6
                )
            ),
            2,
        )

        snapshot_rows.append(
            {
                "recorded_at":
                    timestamp.isoformat(),
                "session_id":
                    sid,
                "meal_period":
                    menu["meal"],
                "section":
                    "male",
                "queue_count":
                    count,
                "throughput_per_min":
                    throughput,
                "data_source":
                    DATA_SOURCE,
            }
        )

    peak = max(counts)
    mean = statistics.mean(counts)
    median = statistics.median(counts)

    congestion_minutes = sum(
        5
        for value in counts
        if value >= 7
    )

    burden = sum(
        value * 5
        for value in counts
    )

    served = int(
        menu["served_target"]
        + random.randint(-5, 5)
    )

    abandoned = max(
        1,
        round(
            served
            * random.uniform(
                0.012,
                0.032
            )
        )
    )

    entries = served + abandoned

    avg_wait = round(
        38
        + peak * 7.5
        + random.uniform(
            5,
            28
        ),
        1,
    )

    throughput = round(
        served
        / random.uniform(
            43,
            50
        ),
        2,
    )

    metric_rows.append(
        {
            "session_id":
                sid,
            "service_date":
                menu["date"],
            "meal_period":
                menu["meal"],
            "section":
                "male",
            "menu_id":
                menu["menu_id"],
            "queue_entry":
                entries,
            "service_completion":
                served,
            "abandonment":
                abandoned,
            "avg_wait_seconds":
                avg_wait,
            "throughput_per_min":
                throughput,
            "peak_queue":
                peak,
            "mean_queue":
                round(mean, 2),
            "median_queue":
                round(median, 2),
            "congestion_duration_min":
                congestion_minutes,
            "queue_burden_person_min":
                round(burden, 1),
            "meals_served":
                served,
            "menu_demand_index":
                menu["demand"],
            "menu_acceptance_index":
                menu["acceptance"],
            "data_source":
                DATA_SOURCE,
        }
    )


supabase.table(
    "queue_snapshots"
).insert(
    snapshot_rows
).execute()

supabase.table(
    "session_metrics"
).insert(
    metric_rows
).execute()

print(
    f"Inserted "
    f"{len(snapshot_rows)} "
    f"queue snapshots."
)

print(
    f"Inserted "
    f"{len(metric_rows)} "
    f"session metric rows."
)


# =========================================================
# VALIDATION: 48 paired observations
# =========================================================

validation_rows = []

validation_dates = [
    date(2026, 9, 22),
    date(2026, 9, 23),
    date(2026, 9, 24),
]

meal_times = [
    time(6, 0),
    time(6, 30),
    time(12, 0),
    time(12, 30),
    time(17, 30),
    time(18, 0),
]

outside_times = [
    time(9, 15),
    time(10, 5),
    time(14, 30),
    time(15, 20),
    time(20, 5),
    time(21, 0),
]


for i in range(36):
    d = validation_dates[
        i % len(validation_dates)
    ]

    t = meal_times[
        i % len(meal_times)
    ]

    actual = random.randint(
        0,
        18
    )

    error = random.choices(
        population=[
            0,
            1,
            -1,
            2,
            -2,
        ],
        weights=[
            0.56,
            0.18,
            0.18,
            0.04,
            0.04,
        ],
        k=1,
    )[0]

    predicted = max(
        0,
        actual + error
    )

    validation_rows.append(
        {
            "recorded_at":
                datetime.combine(
                    d,
                    t,
                    tzinfo=WIB,
                ).isoformat(),
            "session_id":
                f"VALID_MEAL_{i + 1:02d}",
            "section":
                "male",
            "actual_count":
                actual,
            "qsense_count":
                predicted,
            "absolute_error":
                abs(
                    actual
                    - predicted
                ),
            "context":
                "meal_period",
            "data_source":
                DATA_SOURCE,
        }
    )


for i in range(12):
    d = validation_dates[
        i % len(validation_dates)
    ]

    t = outside_times[
        i % len(outside_times)
    ]

    actual = random.randint(
        0,
        3
    )

    error = random.choices(
        population=[
            0,
            1,
            -1,
        ],
        weights=[
            0.72,
            0.14,
            0.14,
        ],
        k=1,
    )[0]

    predicted = max(
        0,
        actual + error
    )

    validation_rows.append(
        {
            "recorded_at":
                datetime.combine(
                    d,
                    t,
                    tzinfo=WIB,
                ).isoformat(),
            "session_id":
                f"VALID_OUTSIDE_{i + 1:02d}",
            "section":
                "male",
            "actual_count":
                actual,
            "qsense_count":
                predicted,
            "absolute_error":
                abs(
                    actual
                    - predicted
                ),
            "context":
                "outside_meal",
            "data_source":
                DATA_SOURCE,
        }
    )


supabase.table(
    "manual_validation"
).insert(
    validation_rows
).execute()

print(
    f"Inserted "
    f"{len(validation_rows)} "
    f"validation observations."
)

print("")
print("=" * 64)
print("Q-SENSE PRESENTATION DATA READY")
print("=" * 64)
print(
    "Historical analytics = SYNTHETIC_DEMO."
)
print(
    "Live camera metrics remain live prototype data."
)
print("")
