import streamlit as st
import pandas as pd
import numpy as np

st.title("Learner Evaluation Analysis")

# Upload CSV file
uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

if uploaded_file is not None:
    # Read the CSV into a DataFrame
    df = pd.read_csv(uploaded_file)
    st.subheader("Data Preview")
    st.dataframe(df.head())
    
    # Step 1: Create a random number for each unique AAMC ID
    # Here we generate a random float between 10 and 20 (rounded to 1 decimal) for each unique ID.
    unique_ids = df["Student AAMC ID"].unique()
    random_mapping = {id_: np.round(np.random.uniform(10, 20), 1) for id_ in unique_ids}
    # Map the same random number to all rows with the same AAMC ID.
    df["Random_Number"] = df["Student AAMC ID"].map(random_mapping)
    
    st.subheader("Data with Random Number Column")
    st.dataframe(df.head())
    
    # Step 2: Map the "3 Multiple Choice Value" to entrustable behavior descriptions.
    # Define the mapping function.
    def map_score_to_behavior(score):
        if score == 1:
            return "Unable to create a plausible differential diagnosis. No insight to poor clinical reasoning."
        elif score == 2:
            return "Struggles to create an appropriate differential without significant guidance. Unable to identify diagnostics/treatments."
        elif score == 3:
            return ("Develops a reasonable differential but lacks supporting clinical data or prioritization. "
                    "Lists possible diagnostics/treatments but uncertain which to apply without significant guidance.")
        elif score == 4:
            return ("Develops a reasonable differential; occasionally omits clinical data support differential or treatment. "
                    "Selection of diagnostics and treatments based on the differential but may require refinement.")
        elif score == 5:
            return ("Develops and prioritizes an accurate differential that is consistently supported by clinical data. "
                    "Selection of diagnostics/treatment targeted to the differential.")
        else:
            return "Invalid score"
    
    # Check if the expected column exists.
    col_name = "3 Multiple Choice Value"
    if col_name in df.columns:
        df["Entrustable_Behavior"] = df[col_name].apply(map_score_to_behavior)
        
        st.subheader("Data with Entrustable Behavior Column")
        st.dataframe(df.head())
    else:
        st.error(f"Column '{col_name}' not found in the data.")

    # Optional: Provide a download button for the processed data.
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download Processed Data",
        data=csv,
        file_name='processed_data.csv',
        mime='text/csv'
    )

