
import json
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime, timezone


SEASON = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
LEAGUE = "ncaa"
DIVISION = "fbs"
MIN_SNAPS_PER_TEAM_GAME = 15

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_FILE = DATA_DIR / f"pass_protection_{SEASON}_raw.json"
OUTPUT_FILE = DATA_DIR / f"pass_protection_{SEASON}.json"


def run_restish(command):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(command)}\n"
            f"Error:\n{result.stderr}\n"
            f"Output:\n{result.stdout}"
        )

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Response was not valid JSON:\n{result.stdout[:3000]}"
        ) from exc


def get_pass_blocking_data():
    command = [
        "restish", "pff", "facet-offense-pass-blocking",
        "--league", LEAGUE,
        "--season", str(SEASON),
        "--division", DIVISION,
        "-p", "ci",
    ]

    print(f"Requesting {SEASON} FBS pass-blocking data...")
    return run_restish(command)


def extract_games(data):
    """Find game records containing home/away franchise IDs."""
    found = []

    def walk(obj):
        if isinstance(obj, dict):
            if (
                "home_franchise_id" in obj
                and "away_franchise_id" in obj
            ):
                found.append(obj)
            else:
                for value in obj.values():
                    walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    return found


def get_team_games_played():
    """
    Fetch NCAA schedule weeks and count unique games for each FBS team.
    NCAA regular-season week IDs are 0 through 16.
    """
    team_games = {}
    seen_games = set()

    for week in range(0, 17):
        command = [
            "restish", "pff", "ref-games",
            LEAGUE, str(SEASON), str(week),
            "-p", "ci",
        ]

        print(f"Fetching schedule for week {week}...")

        try:
            data = run_restish(command)
        except RuntimeError as exc:
            print(f"WARNING: Could not retrieve week {week}: {exc}")
            raise

        games = extract_games(data)

        for game in games:
            game_id = game.get("id")
            home = game.get("home_franchise_id")
            away = game.get("away_franchise_id")

            if game_id is None or home is None or away is None:
                continue

            # Count only games for which PFF has published stats.
            if game.get("has_stats") is not True:
                continue

            if game_id in seen_games:
                continue

            seen_games.add(game_id)

            team_games.setdefault(str(home), 0)
            team_games.setdefault(str(away), 0)
            team_games[str(home)] += 1
            team_games[str(away)] += 1


        time.sleep(0.2)

    return team_games


def safe_number(value):
    if value is None:
        return 0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def clean_number(value):
    number = safe_number(value)
    return int(number) if number.is_integer() else number


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    response = get_pass_blocking_data()

    with RAW_FILE.open("w", encoding="utf-8") as f:
        json.dump({
            "season": SEASON,
            "league": LEAGUE,
            "division": DIVISION,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "source": "/v1/facet/offense/pass_blocking",
            "raw_response": response,
        }, f, indent=2)

    rows = response.get("pass_blocking", [])
    if not isinstance(rows, list):
        raise RuntimeError("Expected pass_blocking to be a list.")

    print(f"Received {len(rows)} blocker records.")

    team_games = get_team_games_played()

    processed = []
    missing_team_games = []

    for row in rows:
        position = row.get("position")
        if position not in ("T", "G", "C"):
            continue

        franchise_id = row.get("franchise_id")
        if franchise_id is None:
            continue

        games_played = team_games.get(str(franchise_id), 0)

        if games_played == 0:
            missing_team_games.append({
                "player": row.get("player"),
                "franchise_id": franchise_id,
            })
            continue

        pass_snaps = safe_number(row.get("snap_counts_pass_block"))
        pressures = safe_number(row.get("pressures_allowed"))
        true_snaps = safe_number(
            row.get("true_pass_set_snap_counts_pass_block")
        )
        true_pressures = safe_number(
            row.get("true_pass_set_pressures_allowed")
        )

        minimum_snaps = MIN_SNAPS_PER_TEAM_GAME * games_played

        if pass_snaps < minimum_snaps:
            continue

        pressure_rate = (
            pressures / pass_snaps * 100
            if pass_snaps > 0 else 0
        )

        true_pressure_rate = (
            true_pressures / true_snaps * 100
            if true_snaps > 0 else 0
        )

        processed.append({
            "player_id": row.get("player_id"),
            "player": row.get("player"),
            "team": row.get("team"),
            "team_name": row.get("team_name"),
            "franchise_id": franchise_id,
            "position": position,
            "jersey_number": row.get("jersey_number"),
            "status": row.get("status"),
            "player_game_count": row.get("player_game_count"),
            "team_games_played": games_played,
            "minimum_snaps_required": minimum_snaps,

            "pass_block_snaps": clean_number(pass_snaps),
            "pressures_allowed": clean_number(pressures),
            "sacks_allowed": clean_number(
                row.get("sacks_allowed")
            ),
            "penalties": clean_number(row.get("penalties")),
            "pressure_rate_allowed": round(pressure_rate, 2),

            "true_pass_set_snaps": clean_number(true_snaps),
            "true_pass_set_pressures_allowed": clean_number(
                true_pressures
            ),
            "true_pass_set_pressure_rate_allowed": round(
                true_pressure_rate, 2
            ),

            "hits_allowed": clean_number(row.get("hits_allowed")),
            "hurries_allowed": clean_number(row.get("hurries_allowed")),
            "grades_pass_block": row.get("grades_pass_block"),
            "true_pass_set_grades_pass_block": row.get(
                "true_pass_set_grades_pass_block"
            ),
            "pbe": row.get("pbe"),
            "true_pass_set_pbe": row.get("true_pass_set_pbe"),
        })

    processed.sort(
        key=lambda p: (
            p["position"],
            -p["pass_block_snaps"],
            p["player"] or "",
        )
    )

    output = {
        "season": SEASON,
        "league": LEAGUE,
        "division": DIVISION,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "qualification": {
            "minimum_pass_block_snaps_per_team_game":
                MIN_SNAPS_PER_TEAM_GAME,
            "rule": "pass_block_snaps >= 15 * team_games_played",
        },
        "record_count": len(processed),
        "team_count_with_schedule_data": len(team_games),
        "missing_team_games": missing_team_games,
        "players": processed,
    }

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print("\nBuild complete.")
    print(f"Raw file: {RAW_FILE}")
    print(f"Processed file: {OUTPUT_FILE}")
    print(f"Qualified players: {len(processed)}")
    print(f"Teams with schedule data: {len(team_games)}")
    print(f"Records missing team games: {len(missing_team_games)}")


if __name__ == "__main__":
    main()
