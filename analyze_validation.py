import csv
import os
import math
import statistics

FILE = os.path.join(
    "data",
    "manual_validation.csv"
)

if not os.path.exists(FILE):

    print(
        "No manual_validation.csv found."
    )
    exit()

actual = []
detected = []

with open(
    FILE,
    "r",
    encoding="utf-8"
) as f:

    reader = csv.DictReader(f)

    for row in reader:

        actual.append(
            int(row["actual_count"])
        )

        detected.append(
            int(row["detected_count"])
        )


if len(actual) == 0:

    print(
        "No validation observations found."
    )
    exit()


errors = [
    d - a
    for a, d in zip(
        actual,
        detected
    )
]

absolute_errors = [
    abs(e)
    for e in errors
]

squared_errors = [
    e ** 2
    for e in errors
]


# ---------------------------------------
# METRICS
# ---------------------------------------

mae = statistics.mean(
    absolute_errors
)

rmse = math.sqrt(
    statistics.mean(
        squared_errors
    )
)

bias = statistics.mean(
    errors
)

exact = sum(
    1
    for e in absolute_errors
    if e == 0
)

within_1 = sum(
    1
    for e in absolute_errors
    if e <= 1
)

within_2 = sum(
    1
    for e in absolute_errors
    if e <= 2
)

n = len(actual)


# ---------------------------------------
# OUTPUT
# ---------------------------------------

print("")
print("======================================")
print("      Q-SENSE VALIDATION RESULTS")
print("======================================")
print("")

print(
    f"Observations:     {n}"
)

print(
    f"MAE:              {mae:.3f} people"
)

print(
    f"RMSE:             {rmse:.3f} people"
)

print(
    f"Mean bias:        {bias:+.3f} people"
)

print(
    f"Exactly correct:  "
    f"{exact / n * 100:.1f}%"
)

print(
    f"Within +/-1:      "
    f"{within_1 / n * 100:.1f}%"
)

print(
    f"Within +/-2:      "
    f"{within_2 / n * 100:.1f}%"
)

print("")
print("--------------------------------------")
print("Individual observations")
print("--------------------------------------")
print("Actual | Detected | Error")
print("--------------------------------------")

for a, d, e in zip(
    actual,
    detected,
    errors
):

    print(
        f"{a:>6} | "
        f"{d:>8} | "
        f"{e:+5d}"
    )

print("")