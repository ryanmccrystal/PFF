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


def download_week(week):
    print(f"\n--- Week {week} ---")

    # Get Time to Throw data
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

    # An empty response means this week is not available yet.
    if not qb_rows:
        print(f"Week {week}: no Time to Throw data")
        return None

    print(f"Time to Throw records: {len(qb_rows)}")

    # Get game reference data
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

    # Save raw weekly files for troubleshooting
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


def build_team_lookup(games):
    """
    Build a lookup that maps a franchise ID to the opposing defense
    for each game.
    """

    defense_by_game = {}

    for game in games:
        game_id = game.get("id")

        away_id = game.get("away_franchise_id")
        home_id = game.get("home_franchise_id")

        if game_id is None or away_id is None or home_id is None:
            continue

        defense_by_game[game_id] = {
            away_id: game.get("home_team", {}),
            home_id: game.get("away_team", {})
        }

    return defense_by_game


def add_value(target, key, value):
    """
    Safely add a numeric value to an aggregate.
    """
    if value is None:
        return

    try:
        target[key] += float(value)
    except (TypeError, ValueError):
        pass


# ------------------------------------------------------------------
# Download all available weeks
# ------------------------------------------------------------------

all_weeks = []

for week in range(1, MAX_WEEKS + 1):
    result = download_week(week)

    if result is None:
        print(f"\nStopping at Week {week}.")
        break

    all_weeks.append(result)


if not all_weeks:
    raise RuntimeError("No completed weeks of Time to Throw data found.")


# ------------------------------------------------------------------
# Aggregate by defense
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

    defense_by_game = build_team_lookup(games)

    # Build a mapping from QB franchise/game to opposing defense.
    #
    # PFF's time_in_pockets data contains franchise_id. A franchise
    # represents the QB's team, so we use the game data to determine
    # the opponent.
    #
    # If a QB record contains game_id, use that directly.
    # Otherwise, fall back to the franchise/team information where
    # possible.

    for row in qb_rows:

        franchise_id = row.get("franchise_id")

        if franchise_id is None:
            total_unmatched += 1
            continue

        game_id = (
            row.get("game_id")
            or row.get("game_pk")
            or row.get("game_id_int")
        )

        opponent = None

        if game_id in defense_by_game:
            opponent = defense_by_game[game_id].get(franchise_id)

        # Some PFF responses identify the game through player_game_id.
        # Try matching against common game identifiers if needed.
        if opponent is None:
            for candidate_game_id, teams in defense_by_game.items():
                if franchise_id in teams:
                    # Only use this fallback when the QB record has
                    # enough information to identify that game.
                    row_game = (
                        row.get("game_id")
                        or row.get("game_pk")
                        or row.get("game_id_int")
                    )

                    if row_game == candidate_game_id:
                        opponent = teams[franchise_id]
                        break

        if opponent is None:
            total_unmatched += 1
            continue

        defense_id = None

        # The opponent team object should contain the franchise ID.
        defense_id = opponent.get("franchise_id")

        if defense_id is None:
            # Fall back to a stable abbreviation.
            defense_id = opponent.get("abbreviation")

        if defense_id is None:
            total_unmatched += 1
            continue

        d = defenses[defense_id]

        d["games"].add(game_id)
        d["weeks"].add(week)

        player_id = row.get("player_id")
        if player_id is not None:
            d["qbs"].add(player_id)

        # ----------------------------------------------------------
        # < 2.5 seconds
        # ----------------------------------------------------------

        add_value(d, "less_dropbacks", row.get("less_dropbacks"))
        add_value(d, "less_attempts", row.get("less_attempts"))
        add_value(d, "less_completions", row.get("less_completions"))
        add_value(d, "less_yards", row.get("less_yards"))
        add_value(d, "less_touchdowns", row.get("less_touchdowns"))
        add_value(d, "less_interceptions", row.get("less_interceptions"))
        add_value(d, "less_sacks", row.get("less_sacks"))
        add_value(
            d,
            "less_pressures",
            row.get("less_def_gen_pressures")
        )

        # ----------------------------------------------------------
        # 2.5 seconds or more
        # ----------------------------------------------------------

        add_value(d, "more_dropbacks", row.get("more_dropbacks"))
        add_value(d, "more_attempts", row.get("more_attempts"))
        add_value(d, "more_completions", row.get("more_completions"))
        add_value(d, "more_yards", row.get("more_yards"))
        add_value(d, "more_touchdowns", row.get("more_touchdowns"))
        add_value(d, "more_interceptions", row.get("more_interceptions"))
        add_value(d, "more_sacks", row.get("more_sacks"))
        add_value(
            d,
            "more_pressures",
            row.get("more_def_gen_pressures")
        )


# ------------------------------------------------------------------
# Calculate final statistics
# ------------------------------------------------------------------

def calculate_stats(dropbacks, attempts, completions, yards,
                    touchdowns, interceptions, sacks, pressures):

    def pct(numerator, denominator):
        if denominator == 0:
            return 0
        return round((numerator / denominator) * 100, 1)

    def rate(numerator, denominator):
        if denominator == 0:
            return 0
        return round(numerator / denominator, 1)

    return {
        "dropbacks": int(dropbacks),
        "comp_pct": pct(completions, attempts),
        "ypa": rate(yards, attempts),
        "td": int(touchdowns),
        "int": int(interceptions),
        "sacks": int(sacks),
        "pressure_pct": pct(pressures, dropbacks),

        # Raw values retained for verification.
        "attempts": int(attempts),
        "completions": int(completions),
        "yards": int(yards),
        "pressures": int(pressures)
    }


output = []

for defense_id, d in defenses.items():

    # Determine the display information from the first available
    # game involving this defense.
    team = None

    for week_data in all_weeks:
        for game in week_data["games"]:

            away_id = game.get("away_franchise_id")
            home_id = game.get("home_franchise_id")

            if defense_id == away_id:
                team = game.get("away_team", {})
                break

            if defense_id == home_id:
                team = game.get("home_team", {})
                break

        if team:
            break

    if team is None:
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
        "team": team.get("abbreviation")
            or team.get("display_abbreviation")
            or defense_id,
        "team_name": team.get("name")
            or team.get("nickname")
            or team.get("display_name"),

        "games": len(d["games"]),
        "weeks": sorted(d["weeks"]),
        "qbs": len(d["qbs"]),

        "less_2_5": less,
        "more_2_5": more
    })


# Sort alphabetically by team abbreviation.
output.sort(key=lambda x: x["team"])


# ------------------------------------------------------------------
# Final JSON
# ------------------------------------------------------------------

final_data = {
    "season": SEASON,
    "weeks_processed": [x["week"] for x in all_weeks],
    "total_qb_records": total_qb_records,
    "total_games": total_games,
    "total_defenses": len(output),
    "total_unmatched": total_unmatched,
    "defenses": output
}


output_file = os.path.join(DATA_DIR, "time_to_throw.json")

with open(output_file, "w") as f:
    json.dump(final_data, f, indent=2)


print("\n========================================")
print("TIME TO THROW BUILD COMPLETE")
print("========================================")
print(f"Weeks processed: {final_data['weeks_processed']}")
print(f"QB records:      {total_qb_records}")
print(f"Games:            {total_games}")
print(f"Defenses:         {len(output)}")
print(f"Unmatched:        {total_unmatched}")
print(f"Output:           {output_file}")
print("========================================\n")

# Show a few sample teams
for team in output[:10]:
    print(
        f"{team['team']:6} "
        f"Games={team['games']:2} "
        f"QBs={team['qbs']:2} "
        f"<2.5 DB={team['less_2_5']['dropbacks']:3} "
        f"Comp={team['less_2_5']['comp_pct']:5.1f}% "
        f"YPA={team['less_2_5']['ypa']:4.1f} "
        f"Press={team['less_2_5']['pressure_pct']:5.1f}%"
    )
