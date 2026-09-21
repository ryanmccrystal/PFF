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
    """Get PFF's NCAA team directory."""

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

        franchise_id -> {
            game_id,
            opponent_id
        }
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
            "opponent_id": int(home_id),
        }

        team_games[int(home_id)] = {
            "game_id": game_id,
            "opponent_id": int(away_id),
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
    """Add one PFF Time to Throw bucket."""

    target["dropbacks"] += (
        row.get(f"{prefix}_dropbacks", 0) or 0
    )

    target["attempts"] += (
        row.get(f"{prefix}_attempts", 0) or 0
    )

    target["completions"] += (
        row.get(f"{prefix}_completions", 0) or 0
    )

    target["yards"] += (
        row.get(f"{prefix}_yards", 0) or 0
    )

    target["touchdowns"] += (
        row.get(f"{prefix}_touchdowns", 0) or 0
    )

    target["interceptions"] += (
        row.get(f"{prefix}_interceptions", 0) or 0
    )

    target["sacks"] += (
        row.get(f"{prefix}_sacks", 0) or 0
    )

    target["pressures"] += (
        row.get(f"{prefix}_def_gen_pressures", 0) or 0
    )


def calculate_bucket(bucket):
    """Calculate displayed statistics from raw totals."""

    attempts = bucket["attempts"]
    dropbacks = bucket["dropbacks"]

    if attempts:

        comp_pct = (
            bucket["completions"] /
            attempts *
            100
        )

        ypa = (
            bucket["yards"] /
            attempts
        )

    else:

        comp_pct = 0
        ypa = 0

    if dropbacks:

        pressure_pct = (
            bucket["pressures"] /
            dropbacks *
            100
        )

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


def create_team_entry(team_info):

    return {
        "franchise_id": team_info["franchise_id"],
        "team_name": team_info["city"],
        "team": team_info["abbreviation"],

        "games": set(),
        "weeks": set(),
        "qbs": set(),

        "less": create_empty_bucket(),
        "more": create_empty_bucket(),
    }


def create_game_entry(week, game_id, opponent_info):

    return {
        "week": week,
        "game_id": game_id,
        "opponent": opponent_info["city"],
        "opponent_abbreviation": opponent_info["abbreviation"],

        "less": create_empty_bucket(),
        "more": create_empty_bucket(),
    }


def add_team_game(
    game_logs,
    team_id,
    week,
    game_info,
    opponent_info,
    row
):
    """
    Add a QB record to a team's individual game log.

    Multiple QBs in the same game are combined.
    """

    if team_id not in game_logs:

        game_logs[team_id] = {}

    team_games = game_logs[team_id]

    game_id = game_info["game_id"]

    if game_id not in team_games:

        team_games[game_id] = create_game_entry(
            week,
            game_id,
            opponent_info
        )

    game = team_games[game_id]

    add_bucket(
        game["less"],
        row,
        "less"
    )

    add_bucket(
        game["more"],
        row,
        "more"
    )


def convert_game_logs(game_logs):

    output = {}

    for team_id, games in game_logs.items():

        game_list = []

        for game in games.values():

            game_list.append({
                "week": game["week"],
                "game_id": game["game_id"],
                "opponent": game["opponent"],
                "opponent_abbreviation":
                    game["opponent_abbreviation"],

                "less_2_5":
                    calculate_bucket(
                        game["less"]
                    ),

                "more_2_5":
                    calculate_bucket(
                        game["more"]
                    ),
            })

        game_list.sort(
            key=lambda x: (
                x["week"],
                x["game_id"]
            )
        )

        output[str(team_id)] = game_list

    return output


def convert_team_totals(dataset):

    output = []

    for team in dataset.values():

        output.append({

            "franchise_id":
                team["franchise_id"],

            "team":
                team["team"],

            "team_name":
                team["team_name"],

            "games":
                len(team["games"]),

            "weeks":
                sorted(team["weeks"]),

            "qbs":
                len(team["qbs"]),

            "less_2_5":
                calculate_bucket(
                    team["less"]
                ),

            "more_2_5":
                calculate_bucket(
                    team["more"]
                ),
        })

    output.sort(
        key=lambda x: (
            x["team_name"] or ""
        ).lower()
    )

    return output


def main():

    print("=" * 50)
    print("PFF TIME TO THROW BUILD")
    print("=" * 50)

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
    offenses = {}

    defense_game_logs = {}
    offense_game_logs = {}

    weeks_processed = []

    total_qb_records = 0
    total_games = 0

    unmatched = 0
    non_fbs_offense = 0
    non_fbs_defense = 0

    # ---------------------------------------------------------
    # PROCESS WEEKS
    # ---------------------------------------------------------

    for week in range(0, MAX_WEEKS + 1):

        print()
        print(f"--- Week {week} ---")

        ttt_rows = get_time_to_throw(week)

        if not ttt_rows:

            print(
                f"Week {week}: no Time to Throw data"
            )

            if week == 0:

                print(
                    "Week 0 has no data. "
                    "Continuing to Week 1."
                )

                continue

            print(
                f"Stopping at Week {week}."
            )

            break

        games = get_week_games(week)

        print(
            f"Time to Throw records: "
            f"{len(ttt_rows)}"
        )

        print(
            f"Games: {len(games)}"
        )

        weeks_processed.append(week)

        total_qb_records += len(ttt_rows)
        total_games += len(games)

        team_games = build_team_games(games)

        # -----------------------------------------------------
        # PROCESS EACH QB
        # -----------------------------------------------------

        for row in ttt_rows:

            offense_id = row.get(
                "franchise_id"
            )

            if offense_id is None:

                unmatched += 1

                continue

            offense_id = int(offense_id)

            game_info = team_games.get(
                offense_id
            )

            if not game_info:

                unmatched += 1

                continue

            defense_id = game_info[
                "opponent_id"
            ]

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

            offense_info = fbs_teams[
                offense_id
            ]

            defense_info = fbs_teams[
                defense_id
            ]

            # =================================================
            # OFFENSE SEASON TOTAL
            # =================================================

            if offense_id not in offenses:

                offenses[offense_id] = (
                    create_team_entry(
                        offense_info
                    )
                )

            offense = offenses[
                offense_id
            ]

            offense["games"].add(
                game_info["game_id"]
            )

            offense["weeks"].add(
                week
            )

            player_id = row.get(
                "player_id"
            )

            if player_id is not None:

                offense["qbs"].add(
                    player_id
                )

            add_bucket(
                offense["less"],
                row,
                "less"
            )

            add_bucket(
                offense["more"],
                row,
                "more"
            )

            # =================================================
            # OFFENSE GAME LOG
            # =================================================

            add_team_game(
                offense_game_logs,
                offense_id,
                week,
                game_info,
                defense_info,
                row
            )

            # =================================================
            # DEFENSE SEASON TOTAL
            # =================================================

            if defense_id not in defenses:

                defenses[defense_id] = (
                    create_team_entry(
                        defense_info
                    )
                )

            defense = defenses[
                defense_id
            ]

            defense["games"].add(
                game_info["game_id"]
            )

            defense["weeks"].add(
                week
            )

            if player_id is not None:

                defense["qbs"].add(
                    player_id
                )

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

            # =================================================
            # DEFENSE GAME LOG
            # =================================================

            add_team_game(
                defense_game_logs,
                defense_id,
                week,
                game_info,
                offense_info,
                row
            )

    # ---------------------------------------------------------
    # CONVERT DATA
    # ---------------------------------------------------------

    defense_output = convert_team_totals(
        defenses
    )

    offense_output = convert_team_totals(
        offenses
    )

    defense_games_output = convert_game_logs(
        defense_game_logs
    )

    offense_games_output = convert_game_logs(
        offense_game_logs
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

        "weeks_processed":
            weeks_processed,

        "filters": {

            "division":
                "FBS",

            "games":
                "FBS vs FBS",

            "less_than_2_5":
                "< 2.5 seconds",

            "more_than_or_equal_2_5":
                "2.5 seconds or more",
        },

        "defenses":
            defense_output,

        "offenses":
            offense_output,

        "game_logs": {

            "defense":
                defense_games_output,

            "offense":
                offense_games_output,
        },

        "summary": {

            "fbs_teams_in_directory":
                len(fbs_teams),

            "defenses_with_data":
                len(defense_output),

            "offenses_with_data":
                len(offense_output),

            "total_qb_records":
                total_qb_records,

            "total_games_processed":
                total_games,

            "unmatched_qb_records":
                unmatched,

            "non_fbs_offense_records":
                non_fbs_offense,

            "non_fbs_defense_records":
                non_fbs_defense,
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
    print("=" * 50)
    print("TIME TO THROW BUILD COMPLETE")
    print("=" * 50)

    print(
        f"Weeks processed:        "
        f"{weeks_processed}"
    )

    print(
        f"QB records:             "
        f"{total_qb_records}"
    )

    print(
        f"Games:                  "
        f"{total_games}"
    )

    print(
        f"FBS teams:              "
        f"{len(fbs_teams)}"
    )

    print(
        f"Defenses with data:     "
        f"{len(defense_output)}"
    )

    print(
        f"Offenses with data:     "
        f"{len(offense_output)}"
    )

    print(
        f"Defense game logs:      "
        f"{len(defense_games_output)}"
    )

    print(
        f"Offense game logs:      "
        f"{len(offense_games_output)}"
    )

    print(
        f"Unmatched:              "
        f"{unmatched}"
    )

    print(
        f"Non-FBS offense rows:   "
        f"{non_fbs_offense}"
    )

    print(
        f"Non-FBS defense rows:   "
        f"{non_fbs_defense}"
    )

    print(
        f"Output:                 "
        f"{OUTPUT_FILE}"
    )

    print("=" * 50)


if __name__ == "__main__":
    main()
