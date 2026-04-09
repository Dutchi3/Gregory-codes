import pandas as pd
import requests

# Llama 3 API endpoint and setup (assuming this is how Llama 3 is accessed)
# Modify this to your actual Llama 3 API URL

def get_screening_questions(criteria_text):

    url = "http://localhost:11434/api/generate"

    prompt = f"""
You are a clinical trial screening assistant.

From the eligibility criteria below, generate 4 simple yes/no screening questions
that a patient can answer without adding yes/no as a text response from you. 

Eligibility Criteria:
{criteria_text}

Return only the 4 questions, each on a new line.
"""

    payload = {
        "model": "llama3",
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        result = response.json()
        text = result.get("response", "")

        questions = [q.strip() for q in text.split("\n") if q.strip()]
        return questions[:4]

    else:
        print(f"Error with Llama 3 API: {response.status_code}")
        print(response.text)
        return ["Error", "Error", "Error"]
def process_trials(csv_file):
    # Read the CSV into a DataFrame
    df = pd.read_csv(csv_file)
    
    # Make sure the 'Criteria_Raw' column exists
    if 'Criteria_Raw' not in df.columns:
        print("Error: 'Criteria_Raw' column not found in CSV.")
        return
    
    # Create a list to store the generated questions
    questions = []
    
    # Iterate over each row in the CSV
    for _, row in df.iterrows():
        criteria_text = row['Criteria_Raw']
        print(f"Generating questions for: {criteria_text}")
        
        # Get the screening questions from Llama 3
        screening_questions = get_screening_questions(criteria_text)
        questions.append(screening_questions)
    
    # Add the questions to the DataFrame (Assuming 4 questions per row)
    df['Screening_Q0'] = [q[0] if len(q) > 0 else "" for q in questions]
    df['Screening_Q1'] = [q[1] if len(q) > 1 else "" for q in questions]
    df['Screening_Q2'] = [q[2] if len(q) > 2 else "" for q in questions]
    df['Screening_Q3'] = [q[3] if len(q) > 3 else "" for q in questions]
    
    # Save the new DataFrame to a new CSV
    df.to_csv('gregory_ready_for_patients.csv', index=False)
    print("New CSV saved as 'gregory_ready_for_patients.csv'")

if __name__ == '__main__':
    # Path to the original CSV
    csv_file = 'gregory_trials_db.csv'
    process_trials(csv_file)