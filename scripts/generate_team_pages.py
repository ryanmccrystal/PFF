import json
import re
from pathlib import Path


DATA_FILE = Path("data/time_to_throw.json")
OUTPUT_DIR = Path("teams")


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


def build_team_page(team):

    team_name = team["team_name"]
    team_id = team["franchise_id"]
    abbreviation = team["team"]

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

.back {{
    font-size: 14px;
    margin-bottom: 15px;
}}

.back a {{
    color: #111111;
    text-decoration: none;
}}

.back a:hover {{
    text-decoration: underline;
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

<div class="back">
<a href="../time-to-throw.html">
← Back to Time to Throw
</a>
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

const teamName = {json.dumps(team_name)};

const abbreviation = {json.dumps(abbreviation)};


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

        const less =
            game.less_2_5;

        const more =
            game.more_2_5;


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


fetch("../data/time_to_throw.json")

.then(response => {{

    if (!response.ok) {{

        throw new Error(
            "Unable to load Time to Throw data."
        );

    }}

    return response.json();

}})


.then(data => {{

    const defenseGames =
        data.game_logs &&
        data.game_logs.defense
            ? data.game_logs.defense[teamId]
            : [];


    const offenseGames =
        data.game_logs &&
        data.game_logs.offense
            ? data.game_logs.offense[teamId]
            : [];


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

    console.error(error);


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


def main():

    print("=" * 50)
    print("GENERATING TEAM PAGES")
    print("=" * 50)

    with DATA_FILE.open(
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)


    OUTPUT_DIR.mkdir(
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

        output_file = OUTPUT_DIR / filename
            

        page = build_team_page(team)


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
        f"Generated {generated} team pages."
    )

    print("=" * 50)


if __name__ == "__main__":
    main()
