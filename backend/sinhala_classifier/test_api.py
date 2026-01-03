import requests

url = "http://localhost:2000/predict"

samples = [
    "ආණ්ඩුව නව බදු පනත් හඳුන්වා දීමට තීරණය කර ඇත",
    "හෙට සිට සියලුම බැංකු වසා දමන බව සමාජ මාධ්‍ය වල පැතිරෙයි"
]

for text in samples:
    r = requests.post(url, json={"text": text})
    print("\nText:", text)
    print("Response:", r.json())
