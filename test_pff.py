import subprocess


def run_restish(args):
    result = subprocess.run(
        ["restish"] + args,
        capture_output=True,
        text=True,
    )

    print("===== STDOUT =====")
    print(result.stdout)

    print("===== STDERR =====")
    print(result.stderr)

    if result.returncode != 0:
        raise RuntimeError(
            f"Restish failed with exit code {result.returncode}"
        )

    return result.stdout


print("========================================")
print("PFF NCAA 2026 WEEK 1 TEST")
print("========================================")


# --------------------------------------------------
# 1. Get NCAA Week 1 games
# --------------------------------------------------

print("\n\n===== NCAA WEEK 1 GAMES =====")

run_restish([
    "pff",
    "ref-games",
    "ncaa",
    "2026",
    "1",
    "-p",
    "ci",
])


# --------------------------------------------------
# 2. Get NCAA Week 1 time-in-pocket data
# --------------------------------------------------

print("\n\n===== NCAA WEEK 1 TIME IN POCKET =====")

run_restish([
    "pff",
    "signature-passing-time-in-pocket",
    "ncaa",
    "2026",
    "1",
    "-p",
    "ci",
])


print("\n\n========================================")
print("TEST COMPLETE")
print("========================================")
