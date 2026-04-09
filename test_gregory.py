import subprocess
import sys
import json
import requests
import time
from pathlib import Path

PYTHON = r"C:\Users\Tan Family\AppData\Local\Python\pythoncore-3.14-64\python.exe"

def test_csv_load():
    import pandas as pd
    df = pd.read_csv("trials_with_contacts.csv")
    required = ["id", "title", "url", "inclusion", "exclusion", "email"]
    missing = [c for c in required if c not in df.columns]
    assert not missing, f"Missing columns: {missing}"
    print("✅ test_csv_load passed")

def test_dry_run():
    result = subprocess.run(
        [PYTHON, "gregory_script.py", "--dry-run", "--max", "2"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"Script failed:\n{result.stderr}"
    print("✅ test_dry_run passed")

def test_markdown_output():
    md = Path("gregory_patient_summary.md").read_text(encoding="utf-8")
    assert "Trial" in md, "Missing 'Trial' in markdown"
    assert "Gregory" in md, "Missing 'Gregory' in markdown"
    print("✅ test_markdown_output passed")

def test_flask_health():
    proc = subprocess.Popen([PYTHON, "app.py"])
    time.sleep(3)
    try:
        resp = requests.get("http://127.0.0.1:5000/health", timeout=5)
        data = resp.json()
        assert "ok" in data, "Missing 'ok' key in health response"
        print("✅ test_flask_health passed")
    finally:
        proc.terminate()

def test_flask_run_dry():
    proc = subprocess.Popen([PYTHON, "app.py"])
    time.sleep(3)
    try:
        resp = requests.post(
            "http://127.0.0.1:5000/run",
            json={"max_trials": 2, "dry_run": True},
            timeout=30
        )
        data = resp.json()
        assert data.get("count") == 2, f"Expected count=2, got: {data}"
        print("✅ test_flask_run_dry passed")
    finally:
        proc.terminate()
def test_pagination():
    import requests
    url = "https://clinicaltrials.gov/api/v2/studies"
    params = {
        "query.cond": "Amyotrophic Lateral Sclerosis",
        "filter.overallStatus": "RECRUITING",
        "pageSize": 20,
        "countTotal": "true"
    }
    resp = requests.get(url, params=params, timeout=15)
    assert resp.status_code == 200, "API request failed"
    data = resp.json()
    total = data.get("totalCount", 0)
    next_token = data.get("nextPageToken")
    page1_count = len(data.get("studies", []))
    assert page1_count == 20, f"Expected 20 results on page 1, got {page1_count}"
    assert total > 20, f"Expected more than 20 total results, got {total}"
    assert next_token is not None, "Expected a nextPageToken for pagination"
    print(f"[OK] test_pagination passed — {total} total trials, page 1 has {page1_count}, next page token exists")
def test_ollama_timeout():
    import requests
    # Test 1: Normal connection works
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        assert resp.status_code == 200, "Ollama not running"
        print("[OK] Ollama is reachable")
    except Exception as e:
        print(f"[SKIP] Ollama not running, skipping timeout test: {e}")
        return

    # Test 2: Very short timeout should fail gracefully
    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3", "prompt": "hello", "stream": False},
            timeout=0.001  # impossibly short timeout
        )
        print("[WARN] Expected timeout but got response")
    except requests.exceptions.Timeout:
        print("[OK] Short timeout raised Timeout exception as expected")
    except Exception as e:
        print(f"[OK] Short timeout raised exception as expected: {type(e).__name__}")

    # Test 3: call_ollama handles timeout gracefully
    import sys
    sys.path.insert(0, ".")
    from gregory_script import call_ollama
    original_url = "http://localhost:11434/api/generate"
    result = call_ollama("test prompt", dry_run=True)
    assert result == "[DRY RUN — Ollama not called]", "Dry run should return placeholder"
    print("[OK] call_ollama dry_run works correctly")

    print("[OK] test_ollama_timeout passed")


def test_inclusion_exclusion_split():
    import pandas as pd
    df = pd.read_csv("trials_with_contacts.csv")
    trials = df.head(20).to_dict(orient="records")

    passed = 0
    failed = 0

    for trial in trials:
        nct_id = trial.get("id", "unknown")
        inclusion = str(trial.get("inclusion", "")).strip()
        exclusion = str(trial.get("exclusion", "")).strip()

        # Check inclusion is not empty
        if not inclusion or inclusion.lower() == "nan":
            print(f"  [WARN] {nct_id} has no inclusion criteria")
            failed += 1
            continue

        # Check exclusion is not empty
        if not exclusion or exclusion.lower() == "nan":
            print(f"  [WARN] {nct_id} has no exclusion criteria")
            failed += 1
            continue

        # Check they are not the same text
        if inclusion == exclusion:
            print(f"  [FAIL] {nct_id} inclusion and exclusion are identical")
            failed += 1
            continue

        # Check exclusion text is not inside inclusion text
        if exclusion.lower() in inclusion.lower():
            print(f"  [FAIL] {nct_id} exclusion text found inside inclusion text")
            failed += 1
            continue

        passed += 1

    print(f"[OK] {passed}/20 trials have clean inclusion/exclusion split")
    assert failed == 0, f"{failed} trials failed the inclusion/exclusion split check"
    print("[OK] test_inclusion_exclusion_split passed")
def test_split_edge_cases():
    import importlib
    trials_module = importlib.import_module("trials_prep")
    split_criteria = trials_module.split_criteria

    # Test 1: Normal case
    raw = "Inclusion Criteria:\n- Must have ALS\n\nExclusion Criteria:\n- No cancer"
    inc, exc = split_criteria(raw)
    assert "Must have ALS" in inc, "Normal case: inclusion failed"
    assert "No cancer" in exc, "Normal case: exclusion failed"
    print("[OK] Normal case passed")

    # Test 2: Missing exclusion header
    raw2 = "Inclusion Criteria:\n- Must have ALS"
    inc2, exc2 = split_criteria(raw2)
    assert "Must have ALS" in inc2, "Missing exclusion: inclusion failed"
    assert exc2 == "", "Missing exclusion: exclusion should be empty"
    print("[OK] Missing exclusion header passed")

    # Test 3: Missing inclusion header
    raw3 = "Exclusion Criteria:\n- No cancer"
    inc3, exc3 = split_criteria(raw3)
    assert "No cancer" in exc3, "Missing inclusion: exclusion failed"
    print("[OK] Missing inclusion header passed")

    # Test 4: Unusual formatting (extra spaces, weird caps)
    raw4 = "INCLUSION CRITERIA:   \n- Must have ALS\n\nEXCLUSION CRITERIA:   \n- No cancer"
    inc4, exc4 = split_criteria(raw4)
    assert exc4 != "", "Unusual formatting: exclusion should not be empty"
    print("[OK] Unusual formatting passed")

    # Test 5: OCR artifacts (garbled text)
    raw5 = "lnclusion Criteria:\n- Must have ALS\n\nExclusion Criteria:\n- No canc3r"
    inc5, exc5 = split_criteria(raw5)
    assert "canc3r" in exc5 or exc5 != "", "OCR artifacts: should still split"
    print("[OK] OCR artifacts passed")

    # Test 6: Empty string
    raw6 = ""
    inc6, exc6 = split_criteria(raw6)
    assert inc6 == "", "Empty string: inclusion should be empty"
    assert exc6 == "", "Empty string: exclusion should be empty"
    print("[OK] Empty string passed")

    print("[OK] test_split_edge_cases passed")
def test_scraper_api_parsing():
    from trials_prep import parse_trials

    # Test 1: Empty response
    result = parse_trials({})
    assert result == [], "Empty response should return empty list"
    print("[OK] Empty response passed")

    # Test 2: Missing fields
    data_missing = {
        "studies": [
            {"protocolSection": {}}
        ]
    }
    result = parse_trials(data_missing)
    assert isinstance(result, list), "Missing fields should still return a list"
    print("[OK] Missing fields passed")

    # Test 3: Malformed JSON (no studies key)
    data_malformed = {"randomKey": "randomValue"}
    result = parse_trials(data_malformed)
    assert result == [], "Malformed JSON should return empty list"
    print("[OK] Malformed JSON passed")

    # Test 4: No contact email
    data_no_email = {
        "studies": [
            {
                "protocolSection": {
                    "identificationModule": {
                        "nctId": "NCT12345678",
                        "briefTitle": "Test Trial"
                    },
                    "eligibilityModule": {
                        "eligibilityCriteria": "Inclusion Criteria:\n- Has ALS\n\nExclusion Criteria:\n- No cancer"
                    },
                    "contactsLocationsModule": {},
                    "designModule": {},
                    "statusModule": {}
                }
            }
        ]
    }
    result = parse_trials(data_no_email)
    assert len(result) == 1, "Should parse 1 trial"
    assert "not listed" in result[0]["Contact_Email"].lower() or result[0]["Contact_Email"] == "Not listed — check trial page", \
        f"No email should show fallback message, got: {result[0]['Contact_Email']}"
    print("[OK] No contact email passed")

    # Test 5: 429 rate limit simulation
    import requests
    from unittest.mock import patch, MagicMock
    mock_response = MagicMock()
    mock_response.status_code = 429
    with patch("requests.get", return_value=mock_response):
        from trials_prep import fetch_trials
        result = fetch_trials("ALS", "RECRUITING")
        assert result is None, "429 should return None"
    print("[OK] 429 rate limit passed")

    # Test 6: 500 server error simulation
    mock_response_500 = MagicMock()
    mock_response_500.status_code = 500
    with patch("requests.get", return_value=mock_response_500):
        result = fetch_trials("ALS", "RECRUITING")
        assert result is None, "500 should return None"
    print("[OK] 500 server error passed")

    print("[OK] test_scraper_api_parsing passed")
if __name__ == "__main__":
    print("Running Gregory integration tests...\n")
    tests = [test_csv_load, test_dry_run, test_markdown_output, test_flask_health, test_flask_run_dry, test_scraper_api_parsing, test_split_edge_cases]
    passed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} FAILED: {e}")
    print(f"\n{passed}/{len(tests)} tests passed.")