
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone


SEASON = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
LEAGUE = "ncaa"
DIVISION = "fbs"

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_FILE = DATA_DIR / f"pass_protection_{SEASON}_raw.json"

COMMAND = [
    "restish",
    "pff",
    "facet-offense-pass-blocking",
    "--league", LEAGUE,
    "--season", str(SEASON),
    "--division", DIVISION,
    "-p", "ci",
]


def get_pass_blocking_data():
    print(f"Requesting {SEASON} {DIVISION.upper()} pass-blocking data...")
    print("Command:", " ".join(COMMAND))

    result = subprocess.run(
        COMMAND,
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "PFF request failed.\n"
            f"Error:\n{result.stderr}\n"
            f"Output:\n{result.stdout}"
        )

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "PFF response was not valid JSON.\n"
            f"Output:\n{result.stdout[:3000]}"
        ) from exc


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    data = get_pass_blocking_data()

    output = {
        "season": SEASON,
        "league": LEAGUE,
        "division": DIVISION,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source": "/v1/facet/offense/pass_blocking",
        "raw_response": data,
    }

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved response to: {OUTPUT_FILE}")

    if isinstance(data, dict):
        print("\nTop-level keys:")
        for key in data:
            print(f"  - {key}")

        rows = data.get("pass_blocking", [])
        print(f"\nNumber of qualifying blockers: {len(rows)}")

        if rows:
            print("\nFirst record:")
            print(json.dumps(rows[0], indent=2))

            print("\nFields in first record:")
            for key in rows[0]:
                print(f"  - {key}")

        print("\nRestricted fields:")
        print(json.dumps(data.get("restricted", []), indent=2))

    elif isinstance(data, list):
        print(f"\nNumber of records: {len(data)}")
        if data:
            print(json.dumps(data[0], indent=2))


if __name__ == "__main__":
    main()
