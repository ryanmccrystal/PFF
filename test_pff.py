import os
import requests

API_KEY = os.environ["PFF_API_KEY"]

url = "https://api.pff.com/v1/auth/whoami"

headers = {
    "Authorization": API_KEY,
    "Accept": "application/json",
}

response = requests.get(
    url,
    headers=headers,
    timeout=30,
)

print(f"Status: {response.status_code}")
print(response.text)

response.raise_for_status()
