import streamlit as st
import pandas as pd
import openai
import random
import numpy as np 
from docx import Document
import zipfile
import io
import re

openai.api_key = st.secrets["openai"]["api_key"]

# A short, summarized list of the key behaviors from the EPA 2 chart.
epa_2_bullets = [
    "Behavior A: Cannot gather or synthesize data to inform an acceptable diagnosis",
    "Behavior B: Differential is too narrow or too broad or contains inaccuracies",
    "Behavior C: Struggles to make connections between or prioritize sources of information",
    "Behavior D: Proposes a reasonable differential but may neglect supporting information",
    "Behavior E: Differential is relevant and well supported by clinical data",
    "Behavior F: New information is disregarded",
    "Behavior G: Defensive when questioned about the differential",
    "Behavior H: Displays discomfort with ambiguity",
    "Behavior I: Seeks and integrates new information to refine the differential",
    "Behavior J: Encourages questions and challenges from patients and team",
    "Behavior K: Disregards team input",
    "Behavior L: Does not/cannot explain clinical reasoning clearly",
    "Behavior M: Depends heavily on the team for development of the differential",
    "Behavior N: Can explain clinical reasoning in general terms",
    "Behavior O: Clinical reasoning is complete and succinct"
]

def match_to_epa_2_behavior(answer_text_8, answer_text_9, entrustable_behavior_text, epa_2_bullets):
    """
    Calls the OpenAI API to figure out which bullet (1 to N) from 'epa_2_bullets'
    best matches the textual feedback. Returns only the bullet number as a string.
    """
    user_text = (
        f"Answer 8: {answer_text_8}\n\n"
        f"Answer 9: {answer_text_9}\n\n"
        f"Entrustable Behavior: {entrustable_behavior_text}"
    )

    bullet_list = "\n".join([f"{i+1}. {bullet}" for i, bullet in enumerate(epa_2_bullets)])
    
    prompt = f"""
You are an expert clinical educator. You have a summarized set of possible EPA 2 behaviors:

{bullet_list}

Below is feedback from a preceptor about a learner:
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
    
    raw_text = response.choices[0].message["content"].strip()
    
    # Use a regex to find the first digit
    match = re.search(r"\b(\d+)\b", raw_text)
    if match:
        return match.group(1)  # e.g., "5"
    else:
        return "Unknown"

def main():
    st.title("Learner Evaluation Analysis (with OpenAI)")

    uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])
    
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.subheader("Original Data Preview")
        st.dataframe(df.head())

        required_cols = ["Student AAMC ID", "3 Multiple Choice Value", "8 Answer text", "9 Answer text"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"Missing columns in the uploaded file: {missing_cols}")
            return

        # Assign random numbers for each unique AAMC ID
        unique_ids = df["Student AAMC ID"].unique()
        random_mapping = {id_: np.round(np.random.uniform(10, 20), 1) for id_ in unique_ids}
        df["Random_Number"] = df["Student AAMC ID"].map(random_mapping)

        # Map numeric scores (1–5) to entrustable behavior text
        def map_score_to_text(score):
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

        # For each row, call OpenAI to find the best matching bullet from epa_2_bullets
        best_matches = []
        for idx, row in df.iterrows():
            answer_8 = str(row["8 Answer text"])
            answer_9 = str(row["9 Answer text"])
            e_behavior = str(row["Entrustable_Behavior"])

            # 1) GPT returns the bullet number as a string, e.g. "5"
            bullet_num_str = match_to_epa_2_behavior(answer_8, answer_9, e_behavior, epa_2_bullets)

            # 2) Convert bullet_num_str to an integer index
            try:
                bullet_index = int(bullet_num_str) - 1
                # 3) Get the actual text from epa_2_bullets
                if 0 <= bullet_index < len(epa_2_bullets):
                    bullet_text = epa_2_bullets[bullet_index]
                else:
                    bullet_text = "Unknown bullet"
            except ValueError:
                bullet_text = "Unknown bullet"

            best_matches.append(bullet_text)
        
        df["Closest_EPA2_Bullet"] = best_matches

        # Build final DataFrame with only needed columns
        processed_df = df[["Random_Number", "Entrustable_Behavior", "8 Answer text", "9 Answer text", "Closest_EPA2_Bullet"]]
        
        st.subheader("Processed Data Preview")
        st.dataframe(processed_df.head())

        csv = processed_df.to_csv(index=False)
        st.download_button(
            label="Download Processed Data",
            data=csv,
            file_name='processed_data.csv',
            mime='text/csv'
        )

if __name__ == "__main__":
    main()

