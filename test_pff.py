import json
import subprocess


def run_restish(args):
    result = subprocess.run(
        ["restish"] + args,
        capture_output=True,
        text=True,
    )

    print("STDOUT:")
    print(result.stdout)

    print("STDERR:")
    print(result.stderr)

    if result.returncode != 0:
        raise RuntimeError(
            f"Restish failed with exit code {result.returncode}"
        )

    return result.stdout


# --------------------------------------------------
# Test PFF authentication
# --------------------------------------------------

print("===== PFF AUTHENTICATION TEST =====")

auth_result = run_restish([
    "pff",
    "whoami",
    "-p",
    "ci",
])


# --------------------------------------------------
# Test NCAA Week 1 games
# --------------------------------------------------

print("\n===== NCAA WEEK 1 GAMES =====")

games_result = run_restish([
    "pff",
    "games",
    "--league",
    "ncaa",
    "--season",
    "2026",
    "--week",
    "1",
    "-p",
    "ci",
])


# --------------------------------------------------
# Test NCAA Week 1 time in pocket
# --------------------------------------------------

print("\n===== NCAA WEEK 1 TIME IN POCKET =====")

ttt_result = run_restish([
    "pff",
    "time-in-pocket",
    "--league",
    "ncaa",
    "--season",
    "2026",
    "--week",
    "1",
    "-p",
    "ci",
])

print("\n===== TEST COMPLETE =====")
