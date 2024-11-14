import streamlit as st
import pandas as pd
from datetime import datetime

# Function to convert ratings to numerical scores
def convert_rating_to_score(rating):
    rating_to_score = {
        'Excellent': 5,
        'Very Good': 4,
        'Good': 3,
        'Fair': 2,
        'Poor': 1
    }
    return rating_to_score.get(rating, None)

# Function to calculate average scores for each subject
def calculate_average_scores(df):
    average_scores = {}
    subject_scores = {}

    # Dictionary to accumulate scores for each subject
    accumulated_scores = {}

    # Iterate over each column in the DataFrame
    for column in df.columns:
        # Check for both "Subjects [" and "Subject [" patterns
        if (column.startswith('Subjects [') or column.startswith('Subject [')) and column.endswith(']'):
            # Extract subject name
            subject_name = column.split('[')[1].split(']')[0]
            
            # Convert ratings to scores
            scores = df[column].apply(convert_rating_to_score)
            
            # Filter out None values and create list of valid scores
            valid_scores = scores.dropna().tolist()
            
            # Accumulate scores for each subject
            if valid_scores:
                if subject_name not in accumulated_scores:
                    accumulated_scores[subject_name] = []
                accumulated_scores[subject_name].extend(valid_scores)

    # Calculate average scores for each subject
    for subject_name, scores in accumulated_scores.items():
        if scores:
            average_score = sum(scores) / len(scores)
            average_scores[subject_name] = average_score
            subject_scores[subject_name] = scores

    return average_scores, subject_scores

# Streamlit app
st.title("Subject Faculty Rating Calculator")

# File uploader
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if uploaded_file:
    try:
        # Read the Excel file
        df = pd.read_excel(uploaded_file)
        
        # Convert 'Timestamp' column to datetime
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], format='%Y-%m-%d %H:%M:%S')
        
        # Sidebar filters
        st.sidebar.header("Filters")
        
        # Date input for filtering
        st.sidebar.subheader("Filter by Date")
        from_date = st.sidebar.date_input("From Date", value=df['Timestamp'].min())
        to_date = st.sidebar.date_input("To Date", value=df['Timestamp'].max())
        
        # Adjust the to_date to include the entire day
        to_date = pd.to_datetime(to_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        
        # Year and Semester filter
        st.sidebar.subheader("Filter by Year and Semester")
        year_semester_options = df['Choose your Current/Last Academic Year and Semester'].unique().tolist()
        selected_year_semesters = st.sidebar.multiselect(
            "Select Year and Semester", 
            options=year_semester_options, 
            default=year_semester_options
        )
        
        # Gender filter
        st.sidebar.subheader("Filter by Gender")
        gender_options = df['Gender'].unique().tolist()
        selected_genders = st.sidebar.multiselect("Select Gender", options=gender_options, default=gender_options)
        
        # Branch filter
        st.sidebar.subheader("Filter by Branch")
        branch_options = df['Select Branch/Discipline'].unique().tolist()
        selected_branches = st.sidebar.multiselect("Select Branch/Discipline", options=branch_options, default=branch_options)
        
        # Section Type filter
        st.sidebar.subheader("Filter by Section Type")
        section_type_options = df['Section Type'].unique().tolist()
        selected_section_types = st.sidebar.multiselect("Select Section Type", options=section_type_options, default=section_type_options)
        
        # Filter the DataFrame based on the selected criteria
        mask = (
            (df['Timestamp'] >= pd.to_datetime(from_date)) &
            (df['Timestamp'] <= to_date) &
            (df['Choose your Current/Last Academic Year and Semester'].isin(selected_year_semesters)) &
            (df['Gender'].isin(selected_genders)) &
            (df['Select Branch/Discipline'].isin(selected_branches)) &
            (df['Section Type'].isin(selected_section_types))
        )
        filtered_df = df.loc[mask]
        
        # Calculate average scores and individual scores
        average_scores, subject_scores = calculate_average_scores(filtered_df)
        
        # Display average scores
        st.header("Average Scores for Each Subject")
        if average_scores:
            for subject, score in average_scores.items():
                st.write(f"{subject}: {score:.2f}")
        else:
            st.write("No subjects with scores found after filtering.")
        
        # Display individual scores for each subject
        st.header("Individual Scores for Each Subject")
        if subject_scores:
            for subject, scores in subject_scores.items():
                st.write(f"{subject}: {list(map(int, scores))}")
        else:
            st.write("No individual scores found after filtering.")
                
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")