import csv
import os
from datetime import datetime

DATA_DIR = "data"
MEAL_FILE = os.path.join(
    DATA_DIR,
    "meal_log.csv"
)

os.makedirs(
    DATA_DIR,
    exist_ok=True
)

print("")
print("================================")
print("       Q-SENSE MENU ENTRY")
print("================================")
print("")

# =========================================================
# DATE
# =========================================================

today = datetime.now().strftime(
    "%Y-%m-%d"
)

date_input = input(
    f"Date [{today}]: "
).strip()

if date_input == "":
    date_input = today

# =========================================================
# MEAL
# =========================================================

print("")
print("1 = Breakfast")
print("2 = Lunch")
print("3 = Dinner")
print("")

meal_choice = input(
    "Meal: "
).strip()

meal_map = {
    "1": "breakfast",
    "2": "lunch",
    "3": "dinner"
}

if meal_choice not in meal_map:
    print("Invalid meal.")
    exit()

meal = meal_map[
    meal_choice
]

# =========================================================
# MENU DETAILS
# =========================================================

print("")
print("Enter menu components.")
print("Press ENTER if something is absent.")
print("")

staple = input(
    "Staple/carbohydrate: "
).strip()

animal_protein = input(
    "Animal protein: "
).strip()

plant_protein = input(
    "Plant protein: "
).strip()

vegetable = input(
    "Vegetable: "
).strip()

fruit = input(
    "Fruit: "
).strip()

drink = input(
    "Drink: "
).strip()

other = input(
    "Other / dessert: "
).strip()

# =========================================================
# READ EXISTING DATA
# =========================================================

rows = []

if os.path.exists(
    MEAL_FILE
):

    with open(
        MEAL_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        reader = csv.DictReader(
            f
        )

        rows = list(
            reader
        )

# =========================================================
# NEW RECORD
# =========================================================

record = {
    "date":
        date_input,

    "meal_period":
        meal,

    "staple":
        staple,

    "animal_protein":
        animal_protein,

    "plant_protein":
        plant_protein,

    "vegetable":
        vegetable,

    "fruit":
        fruit,

    "drink":
        drink,

    "other":
        other
}

# =========================================================
# UPDATE EXISTING OR ADD NEW
# =========================================================

updated = False

for i, row in enumerate(
    rows
):

    if (
        row["date"] == date_input
        and
        row["meal_period"] == meal
    ):

        print("")
        print(
            "A menu already exists "
            "for this meal."
        )

        answer = input(
            "Replace it? [y/N]: "
        ).strip().lower()

        if answer == "y":

            rows[i] = record
            updated = True

        else:

            print("Cancelled.")
            exit()

        break

if not updated:

    rows.append(
        record
    )

# =========================================================
# SAVE
# =========================================================

headers = [
    "date",
    "meal_period",
    "staple",
    "animal_protein",
    "plant_protein",
    "vegetable",
    "fruit",
    "drink",
    "other"
]

with open(
    MEAL_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=headers
    )

    writer.writeheader()
    writer.writerows(
        rows
    )

print("")
print("MENU SAVED")
print("")
print(
    f"{date_input} | "
    f"{meal.upper()}"
)
print("")