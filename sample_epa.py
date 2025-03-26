import streamlit as st
import pandas as pd
import openai
import random
import numpy as np 
from docx import Document
import zipfile
import io

# OpenAI API key setup (use secrets or environment variable for security)
openai.api_key = st.secrets["openai"]["api_key"]

# A short, summarized list of the key behaviors from the EPA 2 chart.
# Replace these placeholders with your own succinct descriptions from the AAMC’s EPA 2 image.
epa_2_bullets = [
    "Behavior A: Cannot gather or synthesize data to inform an acceptable diagnosis",
    "Behavior B: Lacks basic medical knowledge to reason effectively",
    "Behavior C: Struggles to filter, prioritize, and make connections between sources of information",
    "Behavior D: Gathers pertinent data based on initial diagnostic hypotheses but may neglect important information",
    "Behavior E: Gathers pertinent information from many sources in a hypothesis-driven fashion",
    "Behavior F: Demonstrates difficulty retrieving knowledge for effective reasoning",
    "Behavior G: Proposes a differential diagnosis that is too narrow, too broad, or contains inaccuracies",
    "Behavior H: Proposes a reasonable differential diagnosis but may overlook important diagnostic information",
    "Behavior I: Organizes knowledge into illness scripts (patterns) to generate and support a diagnosis",
    "Behavior J: Disregards emerging diagnostic information",
    "Behavior K: Does not integrate emerging information to update the differential diagnosis",
    "Behavior L: Displays discomfort with ambiguity",
    "Behavior M: Considers emerging information but does not completely integrate to update the differential diagnosis",
    "Behavior N: Acknowledges ambiguity and is open to questions and challenges",
    "Behavior O: Seeks and integrates emerging information to update the differential diagnosis",
    "Behavior P: Becomes defensive and/or belligerent when questioned on differential diagnosis",
    "Behavior Q: Ignores the team’s recommendations",
    "Behavior R: Does not seek assistance from team members",
    "Behavior S: Does not engage or communicate effectively with team members",
    "Behavior T: Engages and communicates with team members for endorsement and verification of the working diagnosis",
    "Behavior U: Seeks assistance from team members to help inform diagnosis and management",
    "Behavior V: Encourages questions and challenges from patients and team",
    "Behavior W: Develops and acts on a management plan before receiving the team’s endorsement",
    "Behavior X: Recommends a broad range of untailored diagnostic evaluations",
    "Behavior Y: Depends on the team for all management plans",
    "Behavior Z: Recommends diagnostic evaluations tailored to the evolving differential diagnosis after consultation with the team",
    "Behavior AA: Proposes diagnostic and management plans reflecting the team’s input",
    "Behavior AB: Cannot explain or document clinical reasoning",
    "Behavior AC: Does not completely explain and document reasoning",
    "Behavior AD: Explains and documents clinical reasoning",
    "Behavior AE: Provides complete and succinct documentation explaining clinical reasoning"
]


import openai
import re

def match_to_epa_2_behavior(answer_text_8, answer_text_9, entrustable_behavior_text, epa_2_bullets):
    """
    Calls the OpenAI API to figure out which bullet (1 to N) from 'epa_2_bullets'
    best matches the textual feedback. Returns only the bullet number as a string.
    """

    # Combine the relevant text from the row
    user_text = (
        f"Answer 8: {answer_text_8}\n\n"
        f"Answer 9: {answer_text_9}\n\n"
        f"Entrustable Behavior: {entrustable_behavior_text}"
    )

    # Build a single string listing the bullet points
    bullet_list = "\n".join([f"{i+1}. {bullet}" for i, bullet in enumerate(epa_2_bullets)])

    # Create the prompt for GPT
    prompt = f"""
You are an expert clinical educator. You have a summarized set of possible EPA 2 behaviors:

{bullet_list}

Below is feedback from a preceptor about a learner (including numeric-based entrustable behavior rating):
---
{user_text}
---

Please determine which bullet point (1 to {len(epa_2_bullets)}) best aligns with this feedback.
Respond with only the bullet number, nothing else.
"""

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant specialized in medical education."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=50,
        temperature=0.0
    )

    # Extract the raw response text (likely just a number)
    raw_text = response.choices[0].message["content"].strip()

    # Use a regex to find a digit in the response
    match = re.search(r"\b(\d+)\b", raw_text)
    if match:
        return match.group(1)  # Return the bullet number as a string
    else:
        # Fallback if no clear digit is found
        return raw_text



def main():
    st.title("Learner Evaluation Analysis (with OpenAI)")

    # 1. Upload the CSV file
    uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])
    
    if uploaded_file is not None:
        # 2. Read the CSV into a DataFrame
        df = pd.read_csv(uploaded_file)
        st.subheader("Original Data Preview")
        st.dataframe(df.head())

        # 3. Ensure the columns we need exist
        required_cols = ["Student AAMC ID", "3 Multiple Choice Value", "8 Answer text", "9 Answer text"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"Missing columns in the uploaded file: {missing_cols}")
            return

        # 4. Assign random numbers for each unique AAMC ID
        unique_ids = df["Student AAMC ID"].unique()
        random_mapping = {id_: np.round(np.random.uniform(10, 20), 1) for id_ in unique_ids}
        df["Random_Number"] = df["Student AAMC ID"].map(random_mapping)

        # 5. Map numeric scores (1–5) to entrustable behavior text
        def map_score_to_text(score):
            # Round & clip
            score_int = int(round(score))
            score_int = min(max(score_int, 1), 5)
            if score_int == 1:
                return ("Unable to create a plausible differential diagnosis. "
                        "No insight to poor clinical reasoning.")
            elif score_int == 2:
                return ("Struggles to create an appropriate differential without significant guidance. "
                        "Unable to identify diagnostics/treatments.")
            elif score_int == 3:
                return ("Develops a reasonable differential but lacks supporting clinical data or prioritization. "
                        "Lists possible diagnostics/treatments but uncertain which to apply without significant guidance.")
            elif score_int == 4:
                return ("Develops a reasonable differential; occasionally omits clinical data support or treatment. "
                        "Diagnostics/treatments mostly appropriate but may need refinement.")
            elif score_int == 5:
                return ("Develops and prioritizes an accurate differential consistently supported by clinical data. "
                        "Selection of diagnostics/treatment is well targeted to the differential.")
        
        df["Entrustable_Behavior"] = df["3 Multiple Choice Value"].apply(map_score_to_text)

        # 6. For each row, call OpenAI to find the best matching bullet from the EPA 2 summary
        #    combining '8 Answer text', '9 Answer text', and 'Entrustable_Behavior'.
        best_matches = []
        for idx, row in df.iterrows():
            answer_8 = str(row["8 Answer text"])
            answer_9 = str(row["9 Answer text"])
            e_behavior = str(row["Entrustable_Behavior"])
            best_match = match_to_epa_2_behavior(answer_8, answer_9, e_behavior)
            best_matches.append(best_match)
        
        df["Closest_EPA2_Bullet"] = best_matches

        # 7. Build the final DataFrame with only the needed columns
        processed_df = df[["Random_Number", "Entrustable_Behavior", "8 Answer text", "9 Answer text", "Closest_EPA2_Bullet"]]
        
        st.subheader("Processed Data Preview")
        st.dataframe(processed_df.head())

        # 8. Download button for the processed data
        csv = processed_df.to_csv(index=False)
        st.download_button(
            label="Download Processed Data",
            data=csv,
            file_name='processed_data.csv',
            mime='text/csv'
        )

if __name__ == "__main__":
    main()

