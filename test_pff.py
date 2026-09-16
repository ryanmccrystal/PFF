import os
import requests


API_KEY = os.environ["PFF_API_KEY"]

BASE_URL = "https://api.pff.com"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json",
}


def get_pff(endpoint, params):
    url = f"{BASE_URL}{endpoint}"

    response = requests.get(
        url,
        headers=HEADERS,
        params=params,
        timeout=30,
    )

    print(f"\nRequest: {response.url}")
    print(f"Status: {response.status_code}")

    response.raise_for_status()

    return response.json()


# --------------------------------------------------
# 1. Get NCAA Week 1 games
# --------------------------------------------------

games_data = get_pff(
    "/v1/games",
    {
        "league": "ncaa",
        "season": 2026,
        "week": 1,
    },
)

print("\n===== GAMES =====")

print(f"Response type: {type(games_data).__name__}")

if isinstance(games_data, dict):
    print("Top-level keys:", list(games_data.keys()))

    games = (
        games_data.get("games")
        or games_data.get("data")
        or []
    )
else:
    games = games_data

print(f"Games returned: {len(games)}")

for game in games[:5]:
    print(game)


# --------------------------------------------------
# 2. Get NCAA Week 1 time-in-pocket data
# --------------------------------------------------

ttt_data = get_pff(
    "/v1/facet/signature/passing/time_in_pocket",
    {
        "league": "ncaa",
        "season": 2026,
        "week": 1,
    },
)

print("\n===== TIME IN POCKET =====")

print(f"Response type: {type(ttt_data).__name__}")

if isinstance(ttt_data, dict):
    print("Top-level keys:", list(ttt_data.keys()))

    quarterbacks = (
        ttt_data.get("time_in_pockets")
        or ttt_data.get("data")
        or []
    )
else:
    quarterbacks = ttt_data

print(f"QB records returned: {len(quarterbacks)}")


# --------------------------------------------------
# 3. Print the fields we care about
# --------------------------------------------------

print("\n===== QUARTERBACKS =====")

for qb in quarterbacks[:20]:

    print(
        f"{qb.get('player')} | "
        f"{qb.get('team_name')} | "
        f"Under 2.5 DB: {qb.get('less_dropbacks')} | "
        f"2.5+ DB: {qb.get('more_dropbacks')}"
    )
