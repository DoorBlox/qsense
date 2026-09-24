from pathlib import Path

ENV_PATH = Path(".env")


def read_env_lines():
    if ENV_PATH.exists():
        return ENV_PATH.read_text(
            encoding="utf-8"
        ).splitlines()

    return []


def current_value(lines, key, default=""):
    prefix = key + "="

    for line in lines:
        if line.startswith(prefix):
            return line[len(prefix):]

    return default


def set_value(lines, key, value):
    prefix = key + "="
    updated = False
    result = []

    for line in lines:
        if line.startswith(prefix):
            result.append(f"{key}={value}")
            updated = True
        else:
            result.append(line)

    if not updated:
        result.append(f"{key}={value}")

    return result


def ask(label, current):
    shown = current or "(blank)"
    value = input(
        f"{label} [{shown}]: "
    ).strip()

    return value or current


print("")
print("=" * 55)
print("Q-SENSE LOCAL CONFIGURATION")
print("=" * 55)
print("")
print("This edits only QSENSE_* settings.")
print("Supabase credentials are left unchanged.")
print("")

lines = read_env_lines()

camera = ask(
    "Camera URL",
    current_value(
        lines,
        "QSENSE_CAMERA_SOURCE",
        "http://10.10.10.113/stream",
    ),
)

section = ask(
    "Section (male/female)",
    current_value(
        lines,
        "QSENSE_SECTION",
        "male",
    ),
).lower()

if section not in {"male", "female"}:
    raise SystemExit(
        "Section must be male or female."
    )

roi = ask(
    "ROI file",
    current_value(
        lines,
        "QSENSE_ROI_FILE",
        "queue_zone_male.json",
    ),
)

service = ask(
    "Service-line file",
    current_value(
        lines,
        "QSENSE_SERVICE_FILE",
        "service_line_male.json",
    ),
)

test_mode = ask(
    "Test mode (true/false)",
    current_value(
        lines,
        "QSENSE_TEST_MODE",
        "true",
    ),
).lower()

if test_mode not in {"true", "false"}:
    raise SystemExit(
        "Test mode must be true or false."
    )

for key, value in [
    ("QSENSE_CAMERA_SOURCE", camera),
    ("QSENSE_SECTION", section),
    ("QSENSE_ROI_FILE", roi),
    ("QSENSE_SERVICE_FILE", service),
    ("QSENSE_TEST_MODE", test_mode),
]:
    lines = set_value(
        lines,
        key,
        value,
    )

ENV_PATH.write_text(
    "\n".join(lines).rstrip() + "\n",
    encoding="utf-8",
)

print("")
print("Saved to .env")
print("")
print(f"Camera:  {camera}")
print(f"Section: {section}")
print(f"ROI:     {roi}")
print(f"Service: {service}")
print(f"Test:    {test_mode}")
