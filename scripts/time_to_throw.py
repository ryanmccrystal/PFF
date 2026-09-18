import json
import os
import subprocess
from collections import defaultdict

SEASON = 2026
MAX_WEEKS = 20

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)


def run_pff_command(command):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("Command failed:")
        print(" ".join(command))
        print(result.stderr)
        return None

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Could not decode JSON:")
        print(result.stdout[:1000])
        return None


# ------------------------------------------------------------------
# Get PFF's current FBS teams
# ------------------------------------------------------------------

def get_fbs_teams():

    print("\n--- FBS Teams ---")

    command = [
        "restish",
        "pff",
        "facet-defense-summary",
        "--league",
        "ncaa",
        "--season",
        str(SEASON),
        "--division",
        "fbs",
        "-p",
        "ci"
    ]

    data = run_pff_command(command)

    if data is None:
        raise RuntimeError(
            "Unable to retrieve PFF FBS team list."
        )

    rows = data.get("defense_summary", [])

    teams = {}

    for row in rows:

        franchise_id = row.get("franchise_id")

        if franchise_id is None:
            continue

        teams[franchise_id] = {
            "team": row.get("team"),
            "team_name": row.get("team_name")
        }

    print(f"FBS player records: {len(rows)}")
    print(f"Unique FBS teams:   {len(teams)}")

    if len(teams) != 138:
        print(
            f"WARNING: Expected 138 FBS teams, "
            f"but PFF returned {len(teams)}."
        )

    return teams


# ------------------------------------------------------------------
# Download one week
# ------------------------------------------------------------------

def download_week(week):

    print(f"\n--- Week {week} ---")

    # --------------------------------------------------------------
    # Time to Throw
    # --------------------------------------------------------------

    tip_command = [
        "restish",
        "pff",
        "signature-passing-time-in-pocket",
        "ncaa",
        str(SEASON),
        str(week),
        "-p",
        "ci"
    ]

    tip_data = run_pff_command(tip_command)

    if tip_data is None:
        return None

    qb_rows = tip_data.get("time_in_pockets", [])

    if not qb_rows:
        print(f"Week {week}: no Time to Throw data")
        return None

    print(f"Time to Throw records: {len(qb_rows)}")

    # --------------------------------------------------------------
    # Games
    # --------------------------------------------------------------

    games_command = [
        "restish",
        "pff",
        "ref-games",
        "ncaa",
        str(SEASON),
        str(week),
        "-p",
        "ci"
    ]

    game_data = run_pff_command(games_command)

    if game_data is None:
        return None

    games = game_data.get("games", [])

    print(f"Games: {len(games)}")

    # Save raw weekly files
    with open(
        os.path.join(DATA_DIR, f"time_in_pocket_week{week}.json"),
        "w"
    ) as f:
        json.dump(tip_data, f, indent=2)

    with open(
        os.path.join(DATA_DIR, f"games_week{week}.json"),
        "w"
    ) as f:
        json.dump(game_data, f, indent=2)

    return {
        "week": week,
        "qb_rows": qb_rows,
        "games": games
    }


# ------------------------------------------------------------------
# Load FBS teams
# ------------------------------------------------------------------

fbs_teams = get_fbs_teams()


# ------------------------------------------------------------------
# Download all completed weeks
# ------------------------------------------------------------------

all_weeks = []

for week in range(1, MAX_WEEKS + 1):

    result = download_week(week)

    if result is None:
        print(f"\nStopping at Week {week}.")
        break

    all_weeks.append(result)


if not all_weeks:
    raise RuntimeError(
        "No completed weeks of Time to Throw data found."
    )


# ------------------------------------------------------------------
# Aggregate defensive statistics
# ------------------------------------------------------------------

defenses = defaultdict(
    lambda: {
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

        "games": set(),
        "weeks": set(),
        "qbs": set()
    }
)


total_qb_records = 0
total_games = 0
total_unmatched = 0


for week_data in all_weeks:

    week = week_data["week"]
    qb_rows = week_data["qb_rows"]
    games = week_data["games"]

    total_qb_records += len(qb_rows)
    total_games += len(games)

    # --------------------------------------------------------------
    # Build:
    #
    # offense franchise ID
    #       ↓
    # opponent franchise ID
    #
    # Each team has one game per week.
    # --------------------------------------------------------------

    team_games = {}

    for game in games:

        away_id = game.get("away_franchise_id")
        home_id = game.get("home_franchise_id")

        if away_id is not None and home_id is not None:

            team_games[away_id] = {
                "game_id": game.get("id"),
                "opponent_id": home_id
            }

            team_games[home_id] = {
                "game_id": game.get("id"),
                "opponent_id": away_id
            }

    # --------------------------------------------------------------
    # Match QB to opposing defense
    # --------------------------------------------------------------

    for row in qb_rows:

        offense_id = row.get("franchise_id")

        if offense_id is None:
            total_unmatched += 1
            continue

        game_info = team_games.get(offense_id)

        if game_info is None:
            total_unmatched += 1
            continue

        defense_id = game_info["opponent_id"]

        if defense_id is None:
            total_unmatched += 1
            continue

        # ----------------------------------------------------------
        # Only keep FBS defenses
        # ----------------------------------------------------------

        if defense_id not in fbs_teams:
            continue

        d = defenses[defense_id]

        d["games"].add(game_info["game_id"])
        d["weeks"].add(week)

        player_id = row.get("player_id")

        if player_id is not None:
            d["qbs"].add(player_id)

        # ----------------------------------------------------------
        # < 2.5 seconds
        # ----------------------------------------------------------

        d["less_dropbacks"] += (
            row.get("less_dropbacks", 0) or 0
        )

        d["less_attempts"] += (
            row.get("less_attempts", 0) or 0
        )

        d["less_completions"] += (
            row.get("less_completions", 0) or 0
        )

        d["less_yards"] += (
            row.get("less_yards", 0) or 0
        )

        d["less_touchdowns"] += (
            row.get("less_touchdowns", 0) or 0
        )

        d["less_interceptions"] += (
            row.get("less_interceptions", 0) or 0
        )

        d["less_sacks"] += (
            row.get("less_sacks", 0) or 0
        )

        d["less_pressures"] += (
            row.get("less_def_gen_pressures", 0) or 0
        )

        # ----------------------------------------------------------
        # 2.5 seconds or more
        # ----------------------------------------------------------

        d["more_dropbacks"] += (
            row.get("more_dropbacks", 0) or 0
        )

        d["more_attempts"] += (
            row.get("more_attempts", 0) or 0
        )

        d["more_completions"] += (
            row.get("more_completions", 0) or 0
        )

        d["more_yards"] += (
            row.get("more_yards", 0) or 0
        )

        d["more_touchdowns"] += (
            row.get("more_touchdowns", 0) or 0
        )

        d["more_interceptions"] += (
            row.get("more_interceptions", 0) or 0
        )

        d["more_sacks"] += (
            row.get("more_sacks", 0) or 0
        )

        d["more_pressures"] += (
            row.get("more_def_gen_pressures", 0) or 0
        )


# ------------------------------------------------------------------
# Calculate display statistics
# ------------------------------------------------------------------

def calculate_stats(
    dropbacks,
    attempts,
    completions,
    yards,
    touchdowns,
    interceptions,
    sacks,
    pressures
):

    if attempts:

        comp_pct = round(
            completions / attempts * 100,
            1
        )

        ypa = round(
            yards / attempts,
            1
        )

    else:

        comp_pct = 0
        ypa = 0

    if dropbacks:

        pressure_pct = round(
            pressures / dropbacks * 100,
            1
        )

    else:

        pressure_pct = 0

    return {
        "dropbacks": int(dropbacks),
        "comp_pct": comp_pct,
        "ypa": ypa,
        "td": int(touchdowns),
        "int": int(interceptions),
        "sacks": int(sacks),
        "pressure_pct": pressure_pct,

        # Raw values retained for auditing
        "attempts": int(attempts),
        "completions": int(completions),
        "yards": int(yards),
        "pressures": int(pressures)
    }


# ------------------------------------------------------------------
# Build final output
# ------------------------------------------------------------------

output = []

for defense_id, d in defenses.items():

    team_info = fbs_teams.get(defense_id)

    if team_info is None:
        continue

    less = calculate_stats(
        d["less_dropbacks"],
        d["less_attempts"],
        d["less_completions"],
        d["less_yards"],
        d["less_touchdowns"],
        d["less_interceptions"],
        d["less_sacks"],
        d["less_pressures"]
    )

    more = calculate_stats(
        d["more_dropbacks"],
        d["more_attempts"],
        d["more_completions"],
        d["more_yards"],
        d["more_touchdowns"],
        d["more_interceptions"],
        d["more_sacks"],
        d["more_pressures"]
    )

    output.append({
        "franchise_id": defense_id,

        "team": team_info.get("team"),

        "team_name": team_info.get("team_name"),

        "games": len(d["games"]),

        "weeks": sorted(d["weeks"]),

        "qbs": len(d["qbs"]),

        "less_2_5": less,

        "more_2_5": more
    })


# Sort by school name
output.sort(
    key=lambda x: x["team_name"] or ""
)


# ------------------------------------------------------------------
# Write JSON
# ------------------------------------------------------------------

final_data = {
    "season": SEASON,

    "weeks_processed": [
        x["week"]
        for x in all_weeks
    ],

    "total_qb_records": total_qb_records,

    "total_games": total_games,

    "total_defenses": len(output),

    "total_unmatched": total_unmatched,

    "defenses": output
}


output_file = os.path.join(
    DATA_DIR,
    "time_to_throw.json"
)

with open(output_file, "w") as f:
    json.dump(
        final_data,
        f,
        indent=2
    )


# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------

print("\n========================================")
print("TIME TO THROW BUILD COMPLETE")
print("========================================")
print(
    f"Weeks processed: {final_data['weeks_processed']}"
)
print(
    f"QB records:      {total_qb_records}"
)
print(
    f"Games:           {total_games}"
)
print(
    f"FBS defenses:    {len(output)}"
)
print(
    f"Unmatched:       {total_unmatched}"
)
print(
    f"Output:          {output_file}"
)
print("========================================\n")


for team in output[:10]:

    less = team["less_2_5"]

    print(
        f"{team['team_name']:20} "
        f"Games={team['games']:2} "
        f"QBs={team['qbs']:2} "
        f"<2.5 DB={less['dropbacks']:3} "
        f"Comp={less['comp_pct']:5.1f}% "
        f"YPA={less['ypa']:4.1f} "
        f"Press={less['pressure_pct']:5.1f}%"
    )
