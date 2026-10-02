
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone


# Usage:
# python scripts/pass_protection.py 2026
#
# Retrieves the raw PFF pass-blocking response.
# We will add field mapping and calculations after confirming
# the endpoint's actual response structure.

SEASON = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
LEAGUE = "ncaa"

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_FILE = DATA_DIR / f"pass_protection_{SEASON}_raw.json"

# Expected Restish operation based on the PFF endpoint:
# GET /v1/player/offense/pass_blocking
COMMAND = [
    "restish",
    "pff",
    "player-offense-pass-blocking",
    LEAGUE,
    str(SEASON),
    "-p",
    "ci",
]


def get_pass_blocking_data():
    print(f"Requesting PFF pass-blocking data for {SEASON}...")

    result = subprocess.run(
        COMMAND,
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "PFF request failed.\n"
            f"Command: {' '.join(COMMAND)}\n"
            f"Error:\n{result.stderr}\n"
            f"Output:\n{result.stdout}"
        )

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "The PFF response was not valid JSON.\n"
            f"Output:\n{result.stdout[:3000]}"
        ) from exc


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    data = get_pass_blocking_data()

    output = {
        "season": SEASON,
        "league": LEAGUE,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source": "/v1/player/offense/pass_blocking",
        "raw_response": data,
    }

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Saved response to: {OUTPUT_FILE}")
    print(f"Response type: {type(data).__name__}")

    if isinstance(data, dict):
        print("Top-level keys:")
        for key in data.keys():
            print(f"  - {key}")

    elif isinstance(data, list):
        print(f"Number of records: {len(data)}")
        if data:
            print("First record:")
            print(json.dumps(data[0], indent=2)[:4000])


if __name__ == "__main__":
    main()
