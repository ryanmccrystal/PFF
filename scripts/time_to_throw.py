import json
import subprocess
from pathlib import Path

SEASON = 2026
MAX_WEEKS = 20

OUTPUT_FILE = Path("data/time_to_throw.json")


def run_restish(args):
    """Run a Restish command and return parsed JSON."""
    command = ["restish"] + args

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True
    )

    return json.loads(result.stdout)


def get_team_directory():
    """
    Get PFF's NCAA team directory.

    Returns:
        dict keyed by franchise_id with:
            - name
            - city
            - abbreviation
            - group_ids
            - is_fbs
            - is_fcs
    """

    print("Loading PFF NCAA team directory...")

    data = run_restish([
        "pff",
        "team-directory",
        "ncaa",
        "-p",
        "ci"
    ])

    teams = {}

    for row in data.get("rows", []):
        franchise_id = row.get("franchiseId")

        if franchise_id is None:
            continue

        group_ids = []

        raw_group_ids = row.get("groupIds", "")

        if raw_group_ids:
            for value in str(raw_group_ids).split(";"):
                try:
                    group_ids.append(int(value))
                except ValueError:
                    pass

        teams[int(franchise_id)] = {
            "franchise_id": int(franchise_id),
            "name": row.get("name"),
            "city": row.get("city"),
            "abbreviation": row.get("abbreviation"),
            "group_ids": group_ids,
            "is_fbs": 11 in group_ids,
            "is_fcs": 12 in group_ids,
        }

    return teams


def get_week_games(week):
    """Get NCAA games for a specific week."""

    data = run_restish([
        "pff",
        "ref-games",
        "ncaa",
        str(SEASON),
        str(week),
        "-p",
        "ci"
    ])

    return data.get("games", [])


def get_time_to_throw(week):
    """Get PFF Time to Throw data for a specific week."""

    data = run_restish([
        "pff",
        "signature-passing-time-in-pocket",
        "ncaa",
        str(SEASON),
        str(week),
        "-p",
        "ci"
    ])

    return data.get("time_in_pockets", [])


def build_team_games(games):
    """
    Build:

        offense franchise_id -> {
            game_id,
            opponent_id
        }

    Each team plays one game per week, so franchise_id
    is sufficient to identify that week's opponent.
    """

    team_games = {}

    for game in games:
        game_id = game.get("id")

        away_team = game.get("away_team", {})
        home_team = game.get("home_team", {})

        away_id = away_team.get("franchise_id")
        home_id = home_team.get("franchise_id")

        if away_id is None or home_id is None:
            continue

        team_games[int(away_id)] = {
            "game_id": game_id,
            "opponent_id": int(home_id)
        }

        team_games[int(home_id)] = {
            "game_id": game_id,
            "opponent_id": int(away_id)
        }

    return team_games


def create_empty_bucket():
    """Create an empty statistical bucket."""

    return {
        "dropbacks": 0,
        "attempts": 0,
        "completions": 0,
        "yards": 0,
        "touchdowns": 0,
        "interceptions": 0,
        "sacks": 0,
        "pressures": 0,
    }


def add_bucket(target, row, prefix):
    """Add one PFF Time to Throw bucket to a defense."""

    target["dropbacks"] += row.get(f"{prefix}_dropbacks", 0) or 0
    target["attempts"] += row.get(f"{prefix}_attempts", 0) or 0
    target["completions"] += row.get(f"{prefix}_completions", 0) or 0
    target["yards"] += row.get(f"{prefix}_yards", 0) or 0
    target["touchdowns"] += row.get(f"{prefix}_touchdowns", 0) or 0
    target["interceptions"] += row.get(f"{prefix}_interceptions", 0) or 0
    target["sacks"] += row.get(f"{prefix}_sacks", 0) or 0
    target["pressures"] += row.get(
        f"{prefix}_def_gen_pressures", 0
    ) or 0


def calculate_bucket(bucket):
    """Calculate the displayed statistics from raw totals."""

    attempts = bucket["attempts"]
    dropbacks = bucket["dropbacks"]

    if attempts:
        comp_pct = bucket["completions"] / attempts * 100
        ypa = bucket["yards"] / attempts
    else:
        comp_pct = 0
        ypa = 0

    if dropbacks:
        pressure_pct = bucket["pressures"] / dropbacks * 100
    else:
        pressure_pct = 0

    return {
        "dropbacks": bucket["dropbacks"],
        "attempts": attempts,
        "completions": bucket["completions"],
        "yards": bucket["yards"],
        "comp_pct": round(comp_pct, 1),
        "ypa": round(ypa, 1),
        "td": bucket["touchdowns"],
        "int": bucket["interceptions"],
        "sacks": bucket["sacks"],
        "pressures": bucket["pressures"],
        "pressure_pct": round(pressure_pct, 1),
    }


def main():

    print("=" * 40)
    print("PFF TIME TO THROW BUILD")
    print("=" * 40)

    # ---------------------------------------------------------
    # TEAM DIRECTORY
    # ---------------------------------------------------------

    teams = get_team_directory()

    fbs_teams = {
        franchise_id: team
        for franchise_id, team in teams.items()
        if team["is_fbs"]
    }

    fcs_teams = {
        franchise_id: team
        for franchise_id, team in teams.items()
        if team["is_fcs"]
    }

    print(f"Total NCAA teams: {len(teams)}")
    print(f"FBS teams:        {len(fbs_teams)}")
    print(f"FCS teams:        {len(fcs_teams)}")

    if not fbs_teams:
        raise RuntimeError(
            "No FBS teams were found in PFF team-directory."
        )

    # ---------------------------------------------------------
    # AGGREGATION
    # ---------------------------------------------------------

    defenses = {}

    weeks_processed = []
    total_qb_records = 0
    total_games = 0

    unmatched = 0
    non_fbs_offense = 0
    non_fbs_defense = 0

    # ---------------------------------------------------------
    # PROCESS WEEKS
    # ---------------------------------------------------------

    for week in range(1, MAX_WEEKS + 1):

        print()
        print(f"--- Week {week} ---")

        ttt_rows = get_time_to_throw(week)

        if not ttt_rows:
            print(f"Week {week}: no Time to Throw data")
            print(f"Stopping at Week {week}.")
            break

        games = get_week_games(week)

        print(f"Time to Throw records: {len(ttt_rows)}")
        print(f"Games: {len(games)}")

        weeks_processed.append(week)
        total_qb_records += len(ttt_rows)
        total_games += len(games)

        team_games = build_team_games(games)

        # -----------------------------------------------------
        # PROCESS EACH QB
        # -----------------------------------------------------

        for row in ttt_rows:

            offense_id = row.get("franchise_id")

            if offense_id is None:
                unmatched += 1
                continue

            offense_id = int(offense_id)

            # Find the offense's game to determine its opponent.
            game_info = team_games.get(offense_id)

            if not game_info:
                unmatched += 1
                continue

            defense_id = game_info["opponent_id"]

            # -------------------------------------------------
            # ONLY FBS OFFENSES
            # -------------------------------------------------

            if offense_id not in fbs_teams:
                non_fbs_offense += 1
                continue

            # -------------------------------------------------
            # ONLY FBS DEFENSES
            # -------------------------------------------------

            if defense_id not in fbs_teams:
                non_fbs_defense += 1
                continue

            # -------------------------------------------------
            # INITIALIZE DEFENSE
            # -------------------------------------------------

            if defense_id not in defenses:

                team_info = fbs_teams[defense_id]

                defenses[defense_id] = {
                    "franchise_id": defense_id,

                    # PFF's city field is the school name
                    # without the mascot.
                    "team_name": team_info["city"],

                    "team": team_info["abbreviation"],

                    "games": set(),
                    "weeks": set(),
                    "qbs": set(),

                    "less": create_empty_bucket(),
                    "more": create_empty_bucket(),
                }

            defense = defenses[defense_id]

            # -------------------------------------------------
            # TRACK GAME / WEEK / QB
            # -------------------------------------------------

            defense["games"].add(game_info["game_id"])
            defense["weeks"].add(week)

            player_id = row.get("player_id")

            if player_id is not None:
                defense["qbs"].add(player_id)

            # -------------------------------------------------
            # AGGREGATE BOTH TIME-TO-THROW BUCKETS
            # -------------------------------------------------

            add_bucket(
                defense["less"],
                row,
                "less"
            )

            add_bucket(
                defense["more"],
                row,
                "more"
            )

    # ---------------------------------------------------------
    # BUILD FINAL OUTPUT
    # ---------------------------------------------------------

    output = []

    for defense_id, defense in defenses.items():

        output.append({
            "franchise_id": defense["franchise_id"],
            "team": defense["team"],
            "team_name": defense["team_name"],

            "games": len(defense["games"]),
            "weeks": sorted(defense["weeks"]),
            "qbs": len(defense["qbs"]),

            "less_2_5": calculate_bucket(
                defense["less"]
            ),

            "more_2_5": calculate_bucket(
                defense["more"]
            ),
        })

    # ---------------------------------------------------------
    # SORT BY SCHOOL NAME
    # ---------------------------------------------------------

    output.sort(
        key=lambda x: (
            x["team_name"] or ""
        ).lower()
    )

    # ---------------------------------------------------------
    # WRITE JSON
    # ---------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    result = {
        "season": SEASON,
        "weeks_processed": weeks_processed,

        "filters": {
            "division": "FBS",
            "games": "FBS vs FBS",
            "less_than_2_5": "< 2.5 seconds",
            "more_than_or_equal_2_5": "2.5 seconds or more",
        },

        "teams": output,

        "summary": {
            "fbs_teams_in_directory": len(fbs_teams),
            "defenses_with_data": len(output),
            "total_qb_records": total_qb_records,
            "total_games_processed": total_games,
            "unmatched_qb_records": unmatched,
            "non_fbs_offense_records": non_fbs_offense,
            "non_fbs_defense_records": non_fbs_defense,
        },
    }

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            result,
            f,
            indent=2
        )

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------

    print()
    print("=" * 40)
    print("TIME TO THROW BUILD COMPLETE")
    print("=" * 40)

    print(f"Weeks processed:        {weeks_processed}")
    print(f"QB records:             {total_qb_records}")
    print(f"Games:                  {total_games}")
    print(f"FBS teams:              {len(fbs_teams)}")
    print(f"Defenses with data:     {len(output)}")
    print(f"Unmatched:              {unmatched}")
    print(f"Non-FBS offense rows:   {non_fbs_offense}")
    print(f"Non-FBS defense rows:   {non_fbs_defense}")
    print(f"Output:                 {OUTPUT_FILE}")

    print("=" * 40)


if __name__ == "__main__":
    main()
