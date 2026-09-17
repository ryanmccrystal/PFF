import json
from collections import defaultdict
from pathlib import Path


# ============================================================
# LOAD DATA
# ============================================================

with open("time_in_pocket_week1.json") as f:
    tip_data = json.load(f)

with open("games_week1.json") as f:
    game_data = json.load(f)

qb_rows = tip_data["time_in_pockets"]
games = game_data["games"]


# ============================================================
# BUILD OPPONENT LOOKUP
# ============================================================

opponents = {}

for game in games:

    away_id = game["away_franchise_id"]
    home_id = game["home_franchise_id"]

    away_team = game["away_team"]
    home_team = game["home_team"]

    opponents[away_id] = {
        "defense_franchise_id": home_id,
        "defense_abbreviation": home_team["display_abbreviation"],
        "defense_name": f'{home_team["city"]} {home_team["nickname"]}',
        "game_id": game["id"],
    }

    opponents[home_id] = {
        "defense_franchise_id": away_id,
        "defense_abbreviation": away_team["display_abbreviation"],
        "defense_name": f'{away_team["city"]} {away_team["nickname"]}',
        "game_id": game["id"],
    }


# ============================================================
# AGGREGATE BY DEFENSE
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

unmatched = []


for row in qb_rows:

    offense_franchise_id = row.get("franchise_id")

    if offense_franchise_id not in opponents:

        unmatched.append({
            "player": row.get("player"),
            "team": row.get("team"),
            "franchise_id": offense_franchise_id,
        })

        continue

    opponent = opponents[offense_franchise_id]

    defense_id = opponent["defense_franchise_id"]

    defense = defenses[defense_id]

    defense["games"].add(opponent["game_id"])
    defense["quarterbacks"].add(row.get("player"))

    # --------------------------------------------------------
    # UNDER 2.5 SECONDS
    # --------------------------------------------------------

    defense["less_dropbacks"] += row.get("less_dropbacks") or 0
    defense["less_attempts"] += row.get("less_attempts") or 0
    defense["less_completions"] += row.get("less_completions") or 0
    defense["less_yards"] += row.get("less_yards") or 0
    defense["less_touchdowns"] += row.get("less_touchdowns") or 0
    defense["less_interceptions"] += row.get("less_interceptions") or 0
    defense["less_sacks"] += row.get("less_sacks") or 0
    defense["less_pressures"] += row.get("less_def_gen_pressures") or 0

    # --------------------------------------------------------
    # 2.5 SECONDS OR MORE
    # --------------------------------------------------------

    defense["more_dropbacks"] += row.get("more_dropbacks") or 0
    defense["more_attempts"] += row.get("more_attempts") or 0
    defense["more_completions"] += row.get("more_completions") or 0
    defense["more_yards"] += row.get("more_yards") or 0
    defense["more_touchdowns"] += row.get("more_touchdowns") or 0
    defense["more_interceptions"] += row.get("more_interceptions") or 0
    defense["more_sacks"] += row.get("more_sacks") or 0
    defense["more_pressures"] += row.get("more_def_gen_pressures") or 0


# ============================================================
# CALCULATIONS
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

        # Keep raw values for auditing/future use.
        "attempts": attempts,
        "completions": completions,
        "yards": yards,
        "pressures": pressures,
    }


# ============================================================
# BUILD FINAL OUTPUT
# ============================================================

output = []

for defense_id, defense in defenses.items():

    # Find the team information from any game involving this defense.
    defense_info = None

    for offense_id, opponent in opponents.items():

        if opponent["defense_franchise_id"] == defense_id:
            defense_info = opponent
            break

    if defense_info is None:
        continue

    output.append({

        "franchise_id": defense_id,

        "team": defense_info["defense_abbreviation"],

        "team_name": defense_info["defense_name"],

        "games": len(defense["games"]),

        "quarterbacks": len(defense["quarterbacks"]),

        "less": calculate_stats(defense, "less"),

        "more": calculate_stats(defense, "more"),
    })


# Sort alphabetically for now.
output.sort(key=lambda x: x["team"])


# ============================================================
# SAVE
# ============================================================

output_path = Path("time_to_throw.json")

with open(output_path, "w") as f:
    json.dump(output, f, indent=2)


# ============================================================
# SUMMARY
# ============================================================

print()
print("========================================")
print("TIME TO THROW DATA")
print("========================================")
print()

print("QB records:", len(qb_rows))
print("Games:", len(games))
print("Defenses:", len(output))
print("Unmatched QB records:", len(unmatched))
print()

if unmatched:
    print("First unmatched records:")

    for row in unmatched[:20]:
        print(row)

    print()

print("First 10 defenses:")

for row in output[:10]:

    print()
    print(row["team"], "-", row["team_name"])

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
print("Saved:", output_path)
