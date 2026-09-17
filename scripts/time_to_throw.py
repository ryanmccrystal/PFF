import json
import subprocess
from collections import defaultdict
from pathlib import Path


# ============================================================
# SETTINGS
# ============================================================

SEASON = 2026

# Maximum possible NCAA weeks.
# The script stops automatically when PFF returns no data.
MAX_WEEKS = 20


# ============================================================
# PFF DATA DOWNLOAD
# ============================================================

def run_pff_command(command):

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("PFF command failed:")
        print(" ".join(command))
        print(result.stderr)
        return None

    try:
        return json.loads(result.stdout)

    except json.JSONDecodeError:
        print("Could not decode PFF response:")
        print(result.stdout[:1000])
        return None


def download_week(week):

    print()
    print("========================================")
    print(f"CHECKING WEEK {week}")
    print("========================================")

    # --------------------------------------------------------
    # Time in pocket
    # --------------------------------------------------------

    tip_command = [
        "restish",
        "pff",
        "signature-passing-time-in-pocket",
        "ncaa",
        str(SEASON),
        str(week),
        "-p",
        "ci",
    ]

    tip_data = run_pff_command(tip_command)

    if tip_data is None:
        return None

    qb_rows = tip_data.get("time_in_pockets", [])

    print("Time-in-pocket records:", len(qb_rows))

    # If PFF returns an empty list, this week isn't available yet.
    if not qb_rows:
        print("No time-in-pocket data.")
        return None

    # --------------------------------------------------------
    # Games
    # --------------------------------------------------------

    games_command = [
        "restish",
        "pff",
        "ref-games",
        "ncaa",
        str(SEASON),
        str(week),
        "-p",
        "ci",
    ]

    game_data = run_pff_command(games_command)

    if game_data is None:
        return None

    games = game_data.get("games", [])

    print("Games:", len(games))

    # Save the raw data for this week.
    with open(f"time_in_pocket_week{week}.json", "w") as f:
        json.dump(tip_data, f)

    with open(f"games_week{week}.json", "w") as f:
        json.dump(game_data, f)

    return {
        "qb_rows": qb_rows,
        "games": games,
    }


# ============================================================
# DOWNLOAD ALL AVAILABLE WEEKS
# ============================================================

all_weeks = []

for week in range(1, MAX_WEEKS + 1):

    result = download_week(week)

    if result is None:
        print()
        print(f"Stopping at Week {week}.")
        break

    all_weeks.append({
        "week": week,
        "qb_rows": result["qb_rows"],
        "games": result["games"],
    })


# ============================================================
# AGGREGATION STRUCTURE
# ============================================================

def new_defense():

    return {
        "games": set(),
        "quarterbacks": set(),

        "less_dropbacks": 0,
        "less_attempts": 0,
        "less_completions": 0,
        "less_yards": 0,
        "less_touchdowns": 0,
        "less_interceptions": 0,
        "less_sacks": 0,
        "less_pressures": 0,

        "more_dropbacks": 0,
        "more_attempts": 0,
        "more_completions": 0,
        "more_yards": 0,
        "more_touchdowns": 0,
        "more_interceptions": 0,
        "more_sacks": 0,
        "more_pressures": 0,
    }


defenses = defaultdict(new_defense)


# ============================================================
# PROCESS EACH WEEK
# ============================================================

total_qb_records = 0
total_games = 0
total_unmatched = 0

processed_weeks = []


for week_data in all_weeks:

    week = week_data["week"]

    qb_rows = week_data["qb_rows"]
    games = week_data["games"]

    total_qb_records += len(qb_rows)
    total_games += len(games)

    processed_weeks.append(week)

    # --------------------------------------------------------
    # Build opponent lookup
    # --------------------------------------------------------

    opponents = {}

    for game in games:

        if game.get("season") != SEASON:
            continue

        away_id = game["away_franchise_id"]
        home_id = game["home_franchise_id"]

        away_team = game["away_team"]
        home_team = game["home_team"]

        opponents[away_id] = {
            "defense_franchise_id": home_id,
            "defense_abbreviation": home_team["display_abbreviation"],
            "defense_name": (
                f'{home_team["city"]} {home_team["nickname"]}'
            ),
            "game_id": game["id"],
        }

        opponents[home_id] = {
            "defense_franchise_id": away_id,
            "defense_abbreviation": away_team["display_abbreviation"],
            "defense_name": (
                f'{away_team["city"]} {away_team["nickname"]}'
            ),
            "game_id": game["id"],
        }

    # --------------------------------------------------------
    # Join QB records to opposing defense
    # --------------------------------------------------------

    unmatched = 0

    for row in qb_rows:

        offense_franchise_id = row.get("franchise_id")

        if offense_franchise_id not in opponents:

            unmatched += 1

            if unmatched <= 10:
                print(
                    "UNMATCHED:",
                    row.get("player"),
                    row.get("team"),
                    offense_franchise_id
                )

            continue

        opponent = opponents[offense_franchise_id]

        defense_id = opponent["defense_franchise_id"]

        defense = defenses[defense_id]

        defense["games"].add(opponent["game_id"])
        defense["quarterbacks"].add(row.get("player"))

        # ----------------------------------------------------
        # UNDER 2.5 SECONDS
        # ----------------------------------------------------

        defense["less_dropbacks"] += row.get("less_dropbacks") or 0
        defense["less_attempts"] += row.get("less_attempts") or 0
        defense["less_completions"] += row.get("less_completions") or 0
        defense["less_yards"] += row.get("less_yards") or 0
        defense["less_touchdowns"] += row.get("less_touchdowns") or 0
        defense["less_interceptions"] += row.get("less_interceptions") or 0
        defense["less_sacks"] += row.get("less_sacks") or 0
        defense["less_pressures"] += (
            row.get("less_def_gen_pressures") or 0
        )

        # ----------------------------------------------------
        # 2.5 SECONDS OR MORE
        # ----------------------------------------------------

        defense["more_dropbacks"] += row.get("more_dropbacks") or 0
        defense["more_attempts"] += row.get("more_attempts") or 0
        defense["more_completions"] += row.get("more_completions") or 0
        defense["more_yards"] += row.get("more_yards") or 0
        defense["more_touchdowns"] += row.get("more_touchdowns") or 0
        defense["more_interceptions"] += row.get("more_interceptions") or 0
        defense["more_sacks"] += row.get("more_sacks") or 0
        defense["more_pressures"] += (
            row.get("more_def_gen_pressures") or 0
        )

    total_unmatched += unmatched


# ============================================================
# CALCULATE DISPLAY STATISTICS
# ============================================================

def calculate_stats(defense, prefix):

    dropbacks = defense[f"{prefix}_dropbacks"]
    attempts = defense[f"{prefix}_attempts"]
    completions = defense[f"{prefix}_completions"]
    yards = defense[f"{prefix}_yards"]
    pressures = defense[f"{prefix}_pressures"]

    comp_pct = (
        completions / attempts * 100
        if attempts
        else 0
    )

    ypa = (
        yards / attempts
        if attempts
        else 0
    )

    pressure_pct = (
        pressures / dropbacks * 100
        if dropbacks
        else 0
    )

    return {
        "dropbacks": dropbacks,
        "comp_pct": round(comp_pct, 1),
        "ypa": round(ypa, 1),
        "td": defense[f"{prefix}_touchdowns"],
        "int": defense[f"{prefix}_interceptions"],
        "sacks": defense[f"{prefix}_sacks"],
        "pressure_pct": round(pressure_pct, 1),

        # Raw values retained for auditing.
        "attempts": attempts,
        "completions": completions,
        "yards": yards,
        "pressures": pressures,
    }


# ============================================================
# BUILD FINAL JSON
# ============================================================

output = []

for defense_id, defense in defenses.items():

    # Find team information from the games processed.
    defense_info = None

    for week_data in all_weeks:

        for game in week_data["games"]:

            if game.get("home_franchise_id") == defense_id:

                team = game["home_team"]

                defense_info = {
                    "abbreviation": team["display_abbreviation"],
                    "name": f'{team["city"]} {team["nickname"]}',
                }

                break

            if game.get("away_franchise_id") == defense_id:

                team = game["away_team"]

                defense_info = {
                    "abbreviation": team["display_abbreviation"],
                    "name": f'{team["city"]} {team["nickname"]}',
                }

                break

        if defense_info:
            break

    if defense_info is None:
        continue

    output.append({

        "franchise_id": defense_id,

        "team": defense_info["abbreviation"],

        "team_name": defense_info["name"],

        "games": len(defense["games"]),

        "quarterbacks": len(defense["quarterbacks"]),

        "less": calculate_stats(defense, "less"),

        "more": calculate_stats(defense, "more"),
    })


# Alphabetical order for now.
output.sort(key=lambda x: x["team"])


# ============================================================
# SAVE
# ============================================================

Path("data").mkdir(exist_ok=True)

with open("data/time_to_throw.json", "w") as f:
    json.dump(output, f, indent=2)


# ============================================================
# SUMMARY
# ============================================================

print()
print("========================================")
print("2026 TIME TO THROW")
print("========================================")
print()

print("Season:", SEASON)
print("Weeks processed:", processed_weeks)
print("QB records:", total_qb_records)
print("Games:", total_games)
print("Defenses:", len(output))
print("Unmatched QB records:", total_unmatched)
print()

print("First 10 defenses:")

for row in output[:10]:

    print()
    print(row["team"], "-", row["team_name"])
    print("  Games:", row["games"])
    print("  QBs:", row["quarterbacks"])

    print(
        "  <2.5:",
        row["less"]["dropbacks"],
        "DB,",
        row["less"]["comp_pct"],
        "Comp%,",
        row["less"]["ypa"],
        "YPA,",
        row["less"]["td"],
        "TD,",
        row["less"]["int"],
        "INT,",
        row["less"]["sacks"],
        "Sacks,",
        row["less"]["pressure_pct"],
        "Pressure%"
    )

    print(
        "  2.5+:",
        row["more"]["dropbacks"],
        "DB,",
        row["more"]["comp_pct"],
        "Comp%,",
        row["more"]["ypa"],
        "YPA,",
        row["more"]["td"],
        "TD,",
        row["more"]["int"],
        "INT,",
        row["more"]["sacks"],
        "Sacks,",
        row["more"]["pressure_pct"],
        "Pressure%"
    )

print()
print("Saved: data/time_to_throw.json")
