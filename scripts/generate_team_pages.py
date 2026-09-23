import json
import re
from pathlib import Path


# =========================================================
# SETTINGS
# =========================================================

SEASONS = [2025, 2026]

DATA_DIR = Path("data")


# =========================================================
# SLUGIFY
# =========================================================

def slugify(value):

    value = value.lower()

    value = value.replace("&", "and")

    value = re.sub(
        r"[^a-z0-9]+",
        "-",
        value
    )

    value = re.sub(
        r"^-+|-+$",
        "",
        value
    )

    return value


# =========================================================
# BUILD TEAM PAGE
# =========================================================

def build_team_page(team, season):

    team_name = team["team_name"]
    team_id = str(team["franchise_id"])

    if season == 2025:

        # 2025 team page lives at:
        # teams/2025/team.html

        back_link = "../../time-to-throw-2025.html"

        year_link = "../../time-to-throw-2026.html"
        year_text = "2026"

        data_path = "../../data/time_to_throw_2025.json"

    else:

        # 2026 team page lives at:
        # teams/team.html

        back_link = "../time-to-throw.html"

        year_link = "../time-to-throw-2025.html"
        year_text = "2025"

        data_path = "../data/time_to_throw_2026.json"


    return f"""<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>{team_name} Time to Throw | PFF</title>

<style>

body {{
    font-family: "Times New Roman", Times, serif;
    background: #ffffff;
    color: #111111;
    margin: 0;
    padding: 30px 15px;
}}

.container {{
    max-width: 1400px;
    margin: 0 auto;
}}

.top-nav {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
    font-size: 14px;
}}

.top-nav a {{
    color: #111111;
    text-decoration: none;
}}

.top-nav a:hover {{
    text-decoration: underline;
}}

.back {{
    font-size: 14px;
}}

.year {{
    font-size: 14px;
}}

h1 {{
    text-align: center;
    margin: 0;
    font-size: 32px;
}}

.subtitle {{
    text-align: center;
    margin-top: 5px;
    margin-bottom: 20px;
    font-size: 16px;
}}

.team-info {{
    text-align: center;
    font-size: 14px;
    margin-bottom: 25px;
}}

.section-title {{
    font-size: 21px;
    font-weight: bold;
    margin-top: 25px;
    margin-bottom: 8px;
    border-bottom: 2px solid #111111;
    padding-bottom: 5px;
}}

.table-wrapper {{
    overflow-x: auto;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
    min-width: 1050px;
}}

th {{
    border-top: 1px solid #111111;
    border-bottom: 1px solid #111111;
    padding: 7px 6px;
    text-align: center;
    white-space: nowrap;
}}

td {{
    padding: 6px;
    border-bottom: 1px solid #dddddd;
    text-align: center;
    white-space: nowrap;
}}

th:first-child,
td:first-child {{
    text-align: left;
}}

tbody tr:last-child td {{
    border-bottom: 2px solid #111111;
}}

.bucket-header {{
    font-weight: bold;
    font-size: 14px;
}}

.bucket-less {{
    border-left: 2px solid #111111;
}}

.game-row {{
    border-top: 1px solid #aaaaaa;
}}

.loading,
.error {{
    text-align: center;
    margin-top: 30px;
    font-size: 16px;
}}

</style>

</head>

<body>

<div class="container">

<div class="top-nav">

<div class="back">
<a href="{back_link}">
← Back to Time to Throw
</a>
</div>

<div class="year">
<a href="{year_link}">
{year_text}
</a>
</div>

</div>

<h1>{team_name}</h1>

<div class="subtitle">
Time to Throw
</div>

<div id="teamInfo" class="team-info">
Loading...
</div>


<div class="section-title">
Offense
</div>

<div
    id="offenseTable"
    class="table-wrapper"
>
<div class="loading">
Loading...
</div>
</div>


<div class="section-title">
Defense
</div>

<div
    id="defenseTable"
    class="table-wrapper"
>
<div class="loading">
Loading...
</div>
</div>

</div>


<script>

const teamId = "{team_id}";


function formatNumber(value) {{

    return Number(value).toLocaleString("en-US");

}}


function formatPercent(value) {{

    return Number(value).toFixed(1) + "%";

}}


function formatYPA(value) {{

    return Number(value).toFixed(1);

}}


function buildTable(games) {{

    if (!games || games.length === 0) {{

        return `
            <div class="loading">
                No games available.
            </div>
        `;

    }}


    let html = `

<table>

<thead>

<tr>

<th rowspan="2">
Week
</th>

<th rowspan="2">
Opponent
</th>

<th colspan="7"
    class="bucket-header bucket-less">
&lt; 2.5 sec
</th>

<th colspan="7"
    class="bucket-header">
2.5+ sec
</th>

</tr>


<tr>

<th class="bucket-less">
Dropbacks
</th>

<th>
Comp%
</th>

<th>
Yds/Att
</th>

<th>
TD
</th>

<th>
INT
</th>

<th>
Sacks
</th>

<th>
Pressure%
</th>


<th>
Dropbacks
</th>

<th>
Comp%
</th>

<th>
Yds/Att
</th>

<th>
TD
</th>

<th>
INT
</th>

<th>
Sacks
</th>

<th>
Pressure%
</th>

</tr>

</thead>


<tbody>

`;


    games.forEach(game => {{

        const less = game.less_2_5;
        const more = game.more_2_5;


        html += `

<tr class="game-row">

<td>
Week ${{game.week}}
</td>

<td>
<b>
${{game.opponent}}
</b>
</td>


<td class="bucket-less">
${{formatNumber(less.dropbacks)}}
</td>

<td>
${{formatPercent(less.comp_pct)}}
</td>

<td>
${{formatYPA(less.ypa)}}
</td>

<td>
${{formatNumber(less.td)}}
</td>

<td>
${{formatNumber(less.int)}}
</td>

<td>
${{formatNumber(less.sacks)}}
</td>

<td>
${{formatPercent(less.pressure_pct)}}
</td>


<td>
${{formatNumber(more.dropbacks)}}
</td>

<td>
${{formatPercent(more.comp_pct)}}
</td>

<td>
${{formatYPA(more.ypa)}}
</td>

<td>
${{formatNumber(more.td)}}
</td>

<td>
${{formatNumber(more.int)}}
</td>

<td>
${{formatNumber(more.sacks)}}
</td>

<td>
${{formatPercent(more.pressure_pct)}}
</td>

</tr>

`;

    }});


    html += `

</tbody>

</table>

`;

    return html;

}}


fetch("{data_path}")

.then(response => {{

    if (!response.ok) {{

        throw new Error(
            "Unable to load Time to Throw data."
        );

    }}

    return response.json();

}})

.then(data => {{

    console.log(
        "Time to Throw data loaded"
    );


    console.log(
        "Team ID:",
        teamId
    );


    const gameLogs =
        data.game_logs || {{}};


    const defenseLogs =
        gameLogs.defense || {{}};


    const offenseLogs =
        gameLogs.offense || {{}};


    const defenseGames =
        defenseLogs[String(teamId)] || {{}};


    const offenseGames =
        offenseLogs[String(teamId)] || {{}};


    console.log(
        "Defense games:",
        defenseGames.length
    );


    console.log(
        "Offense games:",
        offenseGames.length
    );


    const weeks =
        data.weeks_processed || [];


    let weekText = "";


    if (weeks.length === 1) {{

        weekText =
            `Week ${{weeks[0]}}`;

    }} else if (weeks.length > 1) {{

        weekText =
            `Weeks ${{weeks[0]}}–${{weeks[weeks.length - 1]}}`;

    }} else {{

        weekText =
            "No weeks available";

    }}


    document.getElementById(
        "teamInfo"
    ).textContent =
        `${{data.season}} • ${{weekText}} • FBS vs FBS`;


    document.getElementById(
        "offenseTable"
    ).innerHTML =
        buildTable(offenseGames);


    document.getElementById(
        "defenseTable"
    ).innerHTML =
        buildTable(defenseGames);

}})

.catch(error => {{

    console.error(
        "Time to Throw error:",
        error
    );


    document.getElementById(
        "offenseTable"
    ).innerHTML =
        '<div class="error">Unable to load data.</div>';


    document.getElementById(
        "defenseTable"
    ).innerHTML =
        '<div class="error">Unable to load data.</div>';

}});

</script>

</body>

</html>
"""


# =========================================================
# GENERATE ONE SEASON
# =========================================================

def generate_season(season):

    data_file = (
        DATA_DIR /
        f"time_to_throw_{season}.json"
    )

    if not data_file.exists():

        raise FileNotFoundError(
            f"Data file not found: {data_file}"
        )


    if season == 2026:

        output_dir = Path("teams")

    else:

        output_dir = (
            Path("teams") /
            str(season)
        )


    print()
    print("=" * 50)
    print(f"GENERATING {season} TEAM PAGES")
    print("=" * 50)

    print(
        f"Data file: {data_file}"
    )

    print(
        f"Output directory: {output_dir}"
    )


    with data_file.open(
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)


    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    teams = {}


    for team in data.get("offenses", []):

        teams[
            team["franchise_id"]
        ] = team


    for team in data.get("defenses", []):

        teams[
            team["franchise_id"]
        ] = team


    print(
        f"Teams to generate: {len(teams)}"
    )


    generated = 0


    for team_id, team in teams.items():

        filename = (
            slugify(team["team_name"])
            + ".html"
        )


        output_file = (
            output_dir /
            filename
        )


        page = build_team_page(
            team,
            season
        )


        with output_file.open(
            "w",
            encoding="utf-8"
        ) as f:

            f.write(page)


        generated += 1


        print(
            f"Created: {output_file}"
        )


    print()

    print(
        f"Generated {generated} {season} team pages."
    )


# =========================================================
# MAIN
# =========================================================

def main():

    print("=" * 50)
    print("PFF TEAM PAGE GENERATOR")
    print("=" * 50)

    for season in SEASONS:

        generate_season(season)

    print()
    print("=" * 50)
    print("TEAM PAGE GENERATION COMPLETE")
    print("=" * 50)


if __name__ == "__main__":
    main()
