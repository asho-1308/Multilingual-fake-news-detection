import requests
import json
import time

BASE_URL = "http://localhost:1000"

def print_header(title: str):
    print("=" * 60)
    print(title)
    print("=" * 60)

def pretty(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))

def make_request_with_retry(method, url, json_data=None, max_retries=15):
    """
    Helper function to handle Hugging Face 'Model Loading' (503) states.
    It retries the request if the model is cold.
    """
    for attempt in range(max_retries):
        try:
            if method == 'GET':
                r = requests.get(url, timeout=30)
            else:
                r = requests.post(url, json=json_data, timeout=30)
            
            # If model is loading (503), wait and retry
            if r.status_code == 503:
                print(f"   ⏳ Attempt {attempt+1}/{max_retries}: Model is loading... waiting 5s")
                time.sleep(5)
                continue
            
            return r
            
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Connection error: {e}")
            return None
            
    print("   ❌ Max retries reached. Model did not load.")
    return r

def main():
    print_header("Tamil Classifier API Test Suite")

    # 1. Single predictions
    print_header("Testing Single Prediction Endpoint")
    samples = [
        "பாஸ்வேர்டை பகிரும் பயனர்களிடம் கூடுதல் கட்டணம்: நெட்ஃப்ளிக்ஸ் பலே திட்டம்", # Likely Real
        "தமிழ்நாட்டில் இன்று முதல் கனமழை பெய்யும் என வானிலை ஆய்வு மையம் எச்சரிக்கை.", # Likely Real
        "பூமியை நோக்கி வரும் மர்மமான గ్రహశకలం, விஞ்ஞானிகள் பீதி.", # Likely Fake (contains Telugu characters, but good for testing cleaning)
        "This is an english sentence.", # No Tamil characters
    ]
    
    for s in samples:
        print(f"\n🔹 Testing Text: {s[:50]}...")
        try:
            # Use the retry wrapper here and the correct key 'text'
            r = make_request_with_retry('POST', f"{BASE_URL}/predict", {"text": s})
            
            if r:
                print(f"   Status Code: {r.status_code}")
                # Only pretty print if success to save space, or print error
                if r.status_code == 200:
                    resp = r.json()
                    print(f"   Prediction: {resp.get('prediction')} (Conf: {resp.get('confidence')})")
                    print(f"   Cleaned Text: {resp.get('cleaned_text')}")
                else:
                    pretty(r.json())
        except Exception as e:
            print(f"Error: {e}")

    # 2. Error handling
    # We DO NOT use retry here because we EXPECT errors immediately
    print_header("Testing Error Handling (No Retry)")
    
    print("\n1. Testing with missing 'text' field:")
    try:
        # Sending a wrong key to trigger a validation error
        r = requests.post(f"{BASE_URL}/predict", json={"headline": "some text"}, timeout=15)
        print(f"Status Code: {r.status_code} (Expected 422)")
        pretty(r.json())
    except Exception as e:
        print(f"Error: {e}")

    print("\n2. Testing with empty 'text' field:")
    try:
        r = requests.post(f"{BASE_URL}/predict", json={"text": ""}, timeout=15)
        print(f"Status Code: {r.status_code} (Expected 400)")
        pretty(r.json())
    except Exception as e:
        print(f"Error: {e}")

    print_header("All tests completed!")

if __name__ == "__main__":
    main()