import subprocess


result = subprocess.run(
    [
        "restish",
        "pff",
        "whoami",
        "-p",
        "ci",
    ],
    capture_output=True,
    text=True,
)

print("===== STDOUT =====")
print(result.stdout)

print("===== STDERR =====")
print(result.stderr)

print(f"===== EXIT CODE: {result.returncode} =====")

if result.returncode != 0:
    raise SystemExit(result.returncode)
