import os
import math
import pandas as pd

# =========================================================
# Q-SENSE ANALYTICS ENGINE
# =========================================================

DATA_DIR = "demo_data"
OUTPUT_DIR = "analytics"

os.makedirs(OUTPUT_DIR, exist_ok=True)

SESSIONS_FILE = os.path.join(DATA_DIR, "sessions.csv")
SNAPSHOTS_FILE = os.path.join(DATA_DIR, "queue_snapshots.csv")
EVENTS_FILE = os.path.join(DATA_DIR, "queue_events.csv")
MEALS_FILE = os.path.join(DATA_DIR, "meal_log.csv")
VALIDATION_FILE = os.path.join(DATA_DIR, "manual_validation.csv")

print("")
print("=" * 50)
print("        Q-SENSE ANALYTICS ENGINE")
print("=" * 50)
print("")
print("DATA SOURCE: SYNTHETIC DEMO")
print("These are NOT real field results.")
print("")

# =========================================================
# LOAD DATA
# =========================================================

sessions = pd.read_csv(SESSIONS_FILE)

snapshots = pd.read_csv(
    SNAPSHOTS_FILE,
    parse_dates=["timestamp"]
)

events = pd.read_csv(
    EVENTS_FILE,
    parse_dates=["timestamp"]
)

meals = pd.read_csv(MEALS_FILE)

validation = pd.read_csv(
    VALIDATION_FILE
)

sessions["date"] = sessions["date"].astype(str)
meals["date"] = meals["date"].astype(str)

# =========================================================
# SESSION ANALYTICS
# =========================================================

session_results = []

for session_id, group in snapshots.groupby("session_id"):

    group = group.sort_values("timestamp").copy()

    # ---------------------------------------------
    # Basic queue statistics
    # ---------------------------------------------

    mean_queue = group["queue_count"].mean()
    median_queue = group["queue_count"].median()
    min_queue = group["queue_count"].min()
    peak_queue = group["queue_count"].max()
    p95_queue = group["queue_count"].quantile(0.95)
    std_queue = group["queue_count"].std()

    # ---------------------------------------------
    # Peak time
    # ---------------------------------------------

    peak_row = group.loc[
        group["queue_count"].idxmax()
    ]

    peak_time = peak_row["timestamp"]

    # ---------------------------------------------
    # Queue burden / AUC
    #
    # queue_count × time
    # unit = person-minutes
    # ---------------------------------------------

    group["next_timestamp"] = (
        group["timestamp"].shift(-1)
    )

    group["interval_minutes"] = (
        (
            group["next_timestamp"]
            - group["timestamp"]
        ).dt.total_seconds()
        / 60
    )

    typical_interval = (
        group["interval_minutes"]
        .dropna()
        .median()
    )

    if pd.isna(typical_interval):
        typical_interval = 0

    group["interval_minutes"] = (
        group["interval_minutes"]
        .fillna(typical_interval)
    )

    group["queue_person_minutes"] = (
        group["queue_count"]
        * group["interval_minutes"]
    )

    queue_burden = (
        group["queue_person_minutes"].sum()
    )

    # ---------------------------------------------
    # Throughput
    # ---------------------------------------------

    mean_throughput = (
        group["throughput_per_min"].mean()
    )

    peak_throughput = (
        group["throughput_per_min"].max()
    )

    # ---------------------------------------------
    # Event statistics
    # ---------------------------------------------

    event_group = events[
        events["session_id"] == session_id
    ]

    served = event_group[
        event_group["event"] == "SERVED"
    ]

    abandoned = event_group[
        event_group["event"] == "ABANDONED"
    ]

    entered = event_group[
        event_group["event"] == "ENTER"
    ]

    total_entered = len(entered)
    total_served = len(served)
    total_abandoned = len(abandoned)

    waiting_times = pd.to_numeric(
        served["wait_seconds"],
        errors="coerce"
    ).dropna()

    if len(waiting_times) > 0:

        mean_wait_seconds = (
            waiting_times.mean()
        )

        median_wait_seconds = (
            waiting_times.median()
        )

        p95_wait_seconds = (
            waiting_times.quantile(0.95)
        )

    else:

        mean_wait_seconds = 0
        median_wait_seconds = 0
        p95_wait_seconds = 0

    # ---------------------------------------------
    # Abandonment rate
    # ---------------------------------------------

    if total_entered > 0:

        abandonment_rate = (
            total_abandoned
            / total_entered
            * 100
        )

    else:

        abandonment_rate = 0

    session_results.append(
        {
            "session_id": session_id,
            "mean_queue": round(mean_queue, 2),
            "median_queue": round(median_queue, 2),
            "min_queue": int(min_queue),
            "peak_queue": int(peak_queue),
            "peak_time": peak_time,
            "p95_queue": round(p95_queue, 2),
            "std_queue": round(std_queue, 2),
            "queue_burden_person_min":
                round(queue_burden, 2),
            "mean_throughput_per_min":
                round(mean_throughput, 2),
            "peak_throughput_per_min":
                round(peak_throughput, 2),
            "total_entered": total_entered,
            "total_served": total_served,
            "total_abandoned":
                total_abandoned,
            "abandonment_rate_pct":
                round(abandonment_rate, 2),
            "mean_wait_seconds":
                round(mean_wait_seconds, 2),
            "median_wait_seconds":
                round(median_wait_seconds, 2),
            "p95_wait_seconds":
                round(p95_wait_seconds, 2)
        }
    )

session_metrics = pd.DataFrame(
    session_results
)

# =========================================================
# ATTACH SESSION INFORMATION
# =========================================================

session_metrics = session_metrics.merge(
    sessions[
        [
            "session_id",
            "date",
            "weekday",
            "meal_period"
        ]
    ],
    on="session_id",
    how="left"
)

# =========================================================
# ATTACH MENU INFORMATION
# =========================================================

session_metrics = session_metrics.merge(
    meals,
    on=[
        "date",
        "meal_period"
    ],
    how="left",
    suffixes=("", "_menu")
)

# =========================================================
# MEAL-PERIOD BASELINES
# =========================================================

meal_baseline = (
    session_metrics
    .groupby("meal_period")
    ["peak_queue"]
    .mean()
    .to_dict()
)

def calculate_peak_uplift(row):

    baseline = meal_baseline.get(
        row["meal_period"],
        None
    )

    if baseline is None or baseline == 0:
        return 0

    return (
        (
            row["peak_queue"]
            - baseline
        )
        / baseline
        * 100
    )

session_metrics[
    "peak_uplift_vs_meal_pct"
] = session_metrics.apply(
    calculate_peak_uplift,
    axis=1
).round(2)

# =========================================================
# SAVE SESSION ANALYTICS
# =========================================================

session_metrics.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "session_metrics.csv"
    ),
    index=False
)

# =========================================================
# BREAKFAST / LUNCH / DINNER SUMMARY
# =========================================================

meal_summary = (
    session_metrics
    .groupby("meal_period")
    .agg(
        sessions=(
            "session_id",
            "count"
        ),

        mean_queue=(
            "mean_queue",
            "mean"
        ),

        median_queue=(
            "median_queue",
            "mean"
        ),

        mean_peak_queue=(
            "peak_queue",
            "mean"
        ),

        maximum_peak_queue=(
            "peak_queue",
            "max"
        ),

        mean_queue_burden=(
            "queue_burden_person_min",
            "mean"
        ),

        mean_wait_seconds=(
            "mean_wait_seconds",
            "mean"
        ),

        median_wait_seconds=(
            "median_wait_seconds",
            "mean"
        ),

        mean_served=(
            "total_served",
            "mean"
        ),

        mean_abandonment_rate=(
            "abandonment_rate_pct",
            "mean"
        )
    )
    .reset_index()
)

meal_summary = meal_summary.round(2)

meal_summary.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "meal_period_summary.csv"
    ),
    index=False
)

# =========================================================
# MENU ANALYTICS
# =========================================================

if "menu_id" in session_metrics.columns:

    menu_summary = (
        session_metrics
        .groupby("menu_id")
        .agg(
            occurrences=(
                "session_id",
                "count"
            ),

            meal_period=(
                "meal_period",
                "first"
            ),

            staple=(
                "staple",
                "first"
            ),

            animal_protein=(
                "animal_protein",
                "first"
            ),

            mean_queue=(
                "mean_queue",
                "mean"
            ),

            mean_peak_queue=(
                "peak_queue",
                "mean"
            ),

            peak_queue_std=(
                "peak_queue",
                "std"
            ),

            mean_queue_burden=(
                "queue_burden_person_min",
                "mean"
            ),

            mean_wait_seconds=(
                "mean_wait_seconds",
                "mean"
            ),

            mean_served=(
                "total_served",
                "mean"
            ),

            mean_abandonment_pct=(
                "abandonment_rate_pct",
                "mean"
            ),

            mean_peak_uplift_pct=(
                "peak_uplift_vs_meal_pct",
                "mean"
            )
        )
        .reset_index()
    )

    menu_summary = menu_summary.round(2)

    menu_summary.to_csv(
        os.path.join(
            OUTPUT_DIR,
            "menu_summary.csv"
        ),
        index=False
    )

else:

    menu_summary = pd.DataFrame()

# =========================================================
# WEEKDAY SUMMARY
# =========================================================

weekday_order = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
]

weekday_summary = (
    session_metrics
    .groupby("weekday")
    .agg(
        sessions=(
            "session_id",
            "count"
        ),

        mean_queue=(
            "mean_queue",
            "mean"
        ),

        mean_peak_queue=(
            "peak_queue",
            "mean"
        ),

        mean_wait_seconds=(
            "mean_wait_seconds",
            "mean"
        ),

        mean_served=(
            "total_served",
            "mean"
        )
    )
    .reindex(weekday_order)
    .dropna()
    .reset_index()
    .round(2)
)

weekday_summary.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "weekday_summary.csv"
    ),
    index=False
)

# =========================================================
# VALIDATION ANALYTICS
# =========================================================

actual = pd.to_numeric(
    validation["actual_count"],
    errors="coerce"
)

detected = pd.to_numeric(
    validation["detected_count"],
    errors="coerce"
)

valid = (
    actual.notna()
    & detected.notna()
)

actual = actual[valid]
detected = detected[valid]

errors = detected - actual

absolute_errors = errors.abs()

mae = absolute_errors.mean()

rmse = math.sqrt(
    (errors ** 2).mean()
)

bias = errors.mean()

exact_pct = (
    (absolute_errors == 0)
    .mean()
    * 100
)

within_1_pct = (
    (absolute_errors <= 1)
    .mean()
    * 100
)

within_2_pct = (
    (absolute_errors <= 2)
    .mean()
    * 100
)

validation_summary = pd.DataFrame(
    [
        {
            "observations": len(actual),
            "MAE_people":
                round(mae, 3),
            "RMSE_people":
                round(rmse, 3),
            "mean_bias_people":
                round(bias, 3),
            "exact_pct":
                round(exact_pct, 2),
            "within_1_pct":
                round(within_1_pct, 2),
            "within_2_pct":
                round(within_2_pct, 2),
            "data_source":
                "SYNTHETIC_DEMO"
        }
    ]
)

validation_summary.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "validation_summary.csv"
    ),
    index=False
)

# =========================================================
# PRINT SUMMARY
# =========================================================

print("=" * 50)
print("OVERALL DEMO DATASET")
print("=" * 50)

print(
    f"Meal sessions: "
    f"{len(session_metrics)}"
)

print(
    f"Queue observations: "
    f"{len(snapshots)}"
)

print(
    f"Tracking events: "
    f"{len(events)}"
)

print("")

# =========================================================
# MEAL COMPARISON
# =========================================================

print("=" * 50)
print("MEAL PERIOD SUMMARY")
print("=" * 50)
print("")

for _, row in meal_summary.iterrows():

    print(
        f"{row['meal_period'].upper()}"
    )

    print(
        f"  Mean queue: "
        f"{row['mean_queue']:.2f}"
    )

    print(
        f"  Mean peak: "
        f"{row['mean_peak_queue']:.2f}"
    )

    print(
        f"  Mean wait: "
        f"{row['mean_wait_seconds'] / 60:.2f} min"
    )

    print(
        f"  Mean served: "
        f"{row['mean_served']:.1f}"
    )

    print("")

# =========================================================
# MENU COMPARISON
# =========================================================

if not menu_summary.empty:

    print("=" * 50)
    print("MENU DEMAND - SYNTHETIC DEMO")
    print("=" * 50)
    print("")

    ranked = menu_summary.sort_values(
        "mean_peak_uplift_pct",
        ascending=False
    )

    for _, row in ranked.iterrows():

        print(
            f"{row['menu_id']} | "
            f"{row['meal_period'].upper()}"
        )

        print(
            f"  {row['staple']} + "
            f"{row['animal_protein']}"
        )

        print(
            f"  Avg peak: "
            f"{row['mean_peak_queue']:.1f}"
        )

        print(
            f"  Peak uplift: "
            f"{row['mean_peak_uplift_pct']:+.1f}%"
        )

        print(
            f"  Avg wait: "
            f"{row['mean_wait_seconds'] / 60:.2f} min"
        )

        print("")

# =========================================================
# VALIDATION
# =========================================================

print("=" * 50)
print("INSTRUMENT VALIDATION")
print("SYNTHETIC DEMONSTRATION ONLY")
print("=" * 50)

print(
    f"Observations:  {len(actual)}"
)

print(
    f"MAE:           {mae:.3f} people"
)

print(
    f"RMSE:          {rmse:.3f} people"
)

print(
    f"Mean bias:     {bias:+.3f} people"
)

print(
    f"Exactly right: {exact_pct:.1f}%"
)

print(
    f"Within +/-1:   {within_1_pct:.1f}%"
)

print(
    f"Within +/-2:   {within_2_pct:.1f}%"
)

print("")
print("=" * 50)
print("ANALYSIS COMPLETE")
print("=" * 50)
print("")

print("Generated files:")

print(
    "analytics/session_metrics.csv"
)

print(
    "analytics/meal_period_summary.csv"
)

print(
    "analytics/menu_summary.csv"
)

print(
    "analytics/weekday_summary.csv"
)

print(
    "analytics/validation_summary.csv"
)

print("")
print(
    "REMINDER: all current results are "
    "synthetic proof-of-concept data."
)
print("")