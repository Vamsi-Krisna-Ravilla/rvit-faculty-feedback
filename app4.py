import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

def convert_rating_to_score(rating):
    rating_to_score = {
        'Excellent': 5,
        'Very Good': 4,
        'Good': 3,
        'Fair': 2,
        'Poor': 1
    }
    return rating_to_score.get(rating, None)

def normalize_subject_name(name):
    """Normalize subject name by removing extra spaces and converting to uppercase"""
    return ' '.join(name.strip().upper().split())

def get_sorted_unique_values(df, column):
    """Get sorted unique values from a column, handling NaN values"""
    # Drop NA values and convert to list
    unique_values = df[column].dropna().unique().tolist()
    # Sort the values if they're not empty
    if unique_values:
        return sorted(unique_values)
    return []

def calculate_average_scores(df):
    average_scores = {}
    subject_scores = {}
    accumulated_scores = {}

    # First, identify all subject columns and normalize their names
    subject_columns = {}
    for column in df.columns:
        if (('Subjects [' in column or 'Subject [' in column) and ']' in column):
            # Extract and normalize the subject name
            start_idx = column.find('[') + 1
            end_idx = column.find(']')
            if start_idx > 0 and end_idx > start_idx:
                subject_name = normalize_subject_name(column[start_idx:end_idx])
                
                # Convert ratings to scores for this column
                scores = df[column].apply(convert_rating_to_score)
                valid_scores = scores.dropna().tolist()
                
                if valid_scores:  # Only process if we have valid scores
                    if subject_name not in accumulated_scores:
                        accumulated_scores[subject_name] = []
                    accumulated_scores[subject_name].extend(valid_scores)

    # Calculate average scores and store individual scores
    for subject_name, scores in accumulated_scores.items():
        if scores:
            average_scores[subject_name] = sum(scores) / len(scores)
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
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        
        # Sidebar filters
        st.sidebar.header("Filters")
        
        # Date input for filtering
        st.sidebar.subheader("Filter by Date")
        min_date = df['Timestamp'].min().date()
        max_date = df['Timestamp'].max().date()
        from_date = st.sidebar.date_input("From Date", value=min_date)
        to_date = st.sidebar.date_input("To Date", value=max_date)

        # Convert dates to datetime for comparison
        from_date = pd.to_datetime(from_date)
        to_date = pd.to_datetime(to_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        
        # Year and Semester filter
        st.sidebar.subheader("Filter by Year and Semester")
        year_semester_options = get_sorted_unique_values(df, 'Choose your Current/Last Academic Year and Semester')
        selected_year_semesters = st.sidebar.multiselect(
            "Select Year and Semester", 
            options=year_semester_options, 
            default=year_semester_options
        )
        
        # Gender filter
        st.sidebar.subheader("Filter by Gender")
        gender_options = get_sorted_unique_values(df, 'Gender')
        selected_genders = st.sidebar.multiselect("Select Gender", options=gender_options, default=gender_options)
        
        # Branch filter
        st.sidebar.subheader("Filter by Branch")
        branch_options = get_sorted_unique_values(df, 'Select Branch/Discipline')
        selected_branches = st.sidebar.multiselect("Select Branch/Discipline", options=branch_options, default=branch_options)
        
        # Section Type filter
        st.sidebar.subheader("Filter by Section Type")
        section_type_options = get_sorted_unique_values(df, 'Section Type')
        selected_section_types = st.sidebar.multiselect("Select Section Type", options=section_type_options, default=section_type_options)
        
        # Filter the DataFrame
        mask = (
            (df['Timestamp'] >= from_date) &
            (df['Timestamp'] <= to_date) &
            (df['Choose your Current/Last Academic Year and Semester'].isin(selected_year_semesters)) &
            (df['Gender'].isin(selected_genders)) &
            (df['Select Branch/Discipline'].isin(selected_branches)) &
            (df['Section Type'].isin(selected_section_types))
        )
        filtered_df = df.loc[mask]
        
        # Calculate scores
        average_scores, subject_scores = calculate_average_scores(filtered_df)
        
        # Display response statistics
        st.header("Response Statistics")
        total_responses = len(filtered_df)
        st.write(f"Total number of responses after filtering: {total_responses}")
        
        # Create DataFrame for scores
        if average_scores:
            scores_data = []
            for subject, avg_score in average_scores.items():
                num_responses = len(subject_scores[subject])
                scores_data.append({
                    'Subject': subject,
                    'Average Score': round(avg_score, 2),
                    'Number of Responses': num_responses,
                    'Response Rate (%)': round((num_responses / total_responses) * 100, 1)
                })
            
            scores_df = pd.DataFrame(scores_data)
            scores_df = scores_df.sort_values('Average Score', ascending=False)
            
            # Display average scores
            st.header("Average Scores for Each Subject")
            st.dataframe(scores_df, hide_index=True)
            
            # Create and display score distribution
            st.header("Score Distribution by Subject")
            for subject in scores_df['Subject']:
                st.subheader(subject)
                scores = subject_scores[subject]
                score_dist = pd.Series(scores).value_counts().sort_index()
                
                # Calculate percentages
                total = sum(score_dist.values)
                score_percentages = (score_dist / total * 100).round(1)
                
                # Create a DataFrame for the distribution
                dist_df = pd.DataFrame({
                    'Score': score_dist.index,
                    'Count': score_dist.values,
                    'Percentage': score_percentages.values
                })
                dist_df = dist_df.sort_values('Score')
                
                # Display as a bar chart
                fig = px.bar(dist_df, x='Score', y='Count', text='Percentage',
                           labels={'Count': 'Number of Responses', 'Score': 'Rating Score'},
                           title=f'Score Distribution for {subject}')
                fig.update_traces(texttemplate='%{text}%', textposition='outside')
                st.plotly_chart(fig)
                
                # Display numerical breakdown
                st.write("Detailed Score Distribution:")
                st.dataframe(dist_df, hide_index=True)
        else:
            st.write("No subjects with scores found after filtering.")
                
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.exception(e)  # This will show the full error traceback