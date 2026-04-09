import requests
import pandas as pd
import json
import time
import argparse

# --- CONFIGURATION ---
# The official new API for ClinicalTrials.gov
BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
DISEASE_KEYWORD = "Amyotrophic Lateral Sclerosis"  # Change this to your target disease
STATUS_FILTER = "RECRUITING"

def split_criteria(raw: str) -> tuple:
    inc, exc = raw, ""
    lower = raw.lower()
    exc_marker = lower.find("exclusion criteria")
    if exc_marker != -1:
        inc = raw[:exc_marker].strip()
        exc = raw[exc_marker:].strip()
    return inc, exc
def fetch_trials(keyword, status):
    """
    Fetches active trials from ClinicalTrials.gov v2 API.
    """
    print(f"🕵️ Innovator Agent: Scanning for '{keyword}' trials...")

    params = {
        "query.cond": keyword,
        "filter.overallStatus": status,
        "fields": "protocolSection.identificationModule.nctId,protocolSection.identificationModule.briefTitle,"
                  "protocolSection.eligibilityModule.eligibilityCriteria,"
                  "protocolSection.contactsLocationsModule.centralContacts",
        "pageSize": 10  # Start small to save bandwidth
    }

    response = requests.get(BASE_URL, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Error: API request failed with status {response.status_code}")
        return None


def parse_trials(data):
    """
    Cleans the messy JSON into a structured format for the AI to read.
    """
    trials = []
    if not data or 'studies' not in data:
        return []

    for study in data['studies']:
        try:
            protocol = study.get('protocolSection', {})
            id_module = protocol.get('identificationModule', {})
            eligibility = protocol.get('eligibilityModule', {})
            contacts = protocol.get('contactsLocationsModule', {})

            # Extract the "Messy" criteria text
            criteria_text = ""

            if "eligibilityCriteria" in eligibility and eligibility["eligibilityCriteria"]:
                criteria_text = eligibility["eligibilityCriteria"]
            else:
                inclusion = eligibility.get("inclusionCriteria", "")
                exclusion = eligibility.get("exclusionCriteria", "")
                criteria_text = f"Inclusion Criteria:\n{inclusion}\n\nExclusion Criteria:\n{exclusion}"

            if not criteria_text:
                criteria_text = "N/A"
            print("\nRAW CRITERIA FROM API:")
            print(criteria_text)
            print("----------")

            # Extract Contact Email (The Gold Mine)
            contact_list = contacts.get('centralContacts', [])
            email = contact_list[0].get('email') if contact_list else "Not Listed"

            trial_info = {
                "ID": id_module.get('nctId'),
                "Title": id_module.get('briefTitle'),
                "Criteria_Raw": criteria_text[:500] + "...",  # Truncate for preview
                "Contact_Email": email
            }
            trials.append(trial_info)
        except Exception as e:
            print(f"Warning: Skipped a trial due to: {e}")
            continue

    return trials


# --- EXECUTION ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gregory — clinical trial scraper")
    parser.add_argument("--disease", type=str, default=DISEASE_KEYWORD,
                        help="Disease keyword to search for")
    parser.add_argument("--max", type=int, default=None,
                        help="Max number of trials to fetch")
    args = parser.parse_args()

    raw_data = fetch_trials(args.disease, STATUS_FILTER)
    clean_trials = parse_trials(raw_data)

    if clean_trials:
        df = pd.DataFrame(clean_trials)
        print(f"\n✅ Success! Found {len(df)} active trials.")
        print(df[['ID', 'Title', 'Contact_Email']].to_string(index=False))

        # Save to CSV - This is your "Database"
        df.to_csv("gregory_trials_db.csv", index=False)
        print("\nDatabase saved to 'gregory_trials_db.csv'")