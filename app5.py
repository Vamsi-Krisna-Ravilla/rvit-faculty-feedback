import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Set page config
st.set_page_config(
    page_title="Faculty Rating Analysis",
    page_icon="📊",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 1rem;
    }
    .stButton>button {
        width: 100%;
    }
    .css-1d391kg {
        padding-top: 1rem;
    }
    .sidebar .sidebar-content {
        width: 300px;
    }
    </style>
""", unsafe_allow_html=True)

def convert_rating_to_score(rating):
    return {
        'Excellent': 5,
        'Very Good': 4,
        'Good': 3,
        'Fair': 2,
        'Poor': 1
    }.get(rating, None)

def normalize_subject_name(name):
    return ' '.join(name.strip().upper().split())

def get_sorted_unique_values(df, column):
    unique_values = df[column].dropna().unique().tolist()
    return sorted(unique_values) if unique_values else []

def calculate_average_scores(df):
    average_scores = {}
    subject_scores = {}
    accumulated_scores = {}

    for column in df.columns:
        if 'Subjects [' in column or 'Subject [' in column:
            start_idx = column.find('[') + 1
            end_idx = column.find(']')
            if start_idx > 0 and end_idx > start_idx:
                subject_name = normalize_subject_name(column[start_idx:end_idx])
                scores = df[column].apply(convert_rating_to_score)
                valid_scores = scores.dropna().tolist()
                
                if valid_scores:
                    if subject_name not in accumulated_scores:
                        accumulated_scores[subject_name] = []
                    accumulated_scores[subject_name].extend(valid_scores)

    for subject_name, scores in accumulated_scores.items():
        if scores:
            average_scores[subject_name] = sum(scores) / len(scores)
            subject_scores[subject_name] = scores

    return average_scores, subject_scores

# Main app
def main():
    st.title("📊 Subject Faculty Rating Analysis")
    
    # File upload section
    with st.container():
        st.markdown("### 📁 Upload Data")
        uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])

            # Create two columns for date filters
            col1, col2 = st.columns(2)
            min_date = df['Timestamp'].min().date()
            max_date = df['Timestamp'].max().date()
            
            with col1:
                from_date = st.date_input("From Date", value=min_date)
            with col2:
                to_date = st.date_input("To Date", value=max_date)

            # Convert dates
            from_date = pd.to_datetime(from_date)
            to_date = pd.to_datetime(to_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

            # Create expander for filters
            with st.expander("📌 Additional Filters", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    year_semester_options = get_sorted_unique_values(df, 'Choose your Current/Last Academic Year and Semester')
                    selected_year_semesters = st.multiselect(
                        "Year and Semester",
                        options=year_semester_options,
                        default=year_semester_options
                    )

                    gender_options = get_sorted_unique_values(df, 'Gender')
                    selected_genders = st.multiselect(
                        "Gender",
                        options=gender_options,
                        default=gender_options
                    )

                with col2:
                    branch_options = get_sorted_unique_values(df, 'Select Branch/Discipline')
                    selected_branches = st.multiselect(
                        "Branch/Discipline",
                        options=branch_options,
                        default=branch_options
                    )

                    section_type_options = get_sorted_unique_values(df, 'Section Type')
                    selected_section_types = st.multiselect(
                        "Section Type",
                        options=section_type_options,
                        default=section_type_options
                    )

            # Apply filters
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

            # Display statistics in a metric container
            total_responses = len(filtered_df)
            st.metric("Total Responses", total_responses)

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

                # Display scores in a clean table
                st.markdown("### 📊 Subject Performance Overview")
                st.dataframe(
                    scores_df.style.background_gradient(subset=['Average Score'], cmap='RdYlGn'),
                    hide_index=True,
                    use_container_width=True
                )

                # Create tabs for different visualizations
                tab1, tab2 = st.tabs(["📈 Score Distribution", "📋 Detailed Breakdown"])

                with tab1:
                    for subject in scores_df['Subject']:
                        scores = subject_scores[subject]
                        score_dist = pd.Series(scores).value_counts().sort_index()
                        total = sum(score_dist.values)
                        score_percentages = (score_dist / total * 100).round(1)

                        dist_df = pd.DataFrame({
                            'Score': score_dist.index,
                            'Count': score_dist.values,
                            'Percentage': score_percentages.values
                        })
                        dist_df = dist_df.sort_values('Score')

                        fig = px.bar(
                            dist_df,
                            x='Score',
                            y='Count',
                            text='Percentage',
                            labels={'Count': 'Number of Responses', 'Score': 'Rating Score'},
                            title=f'{subject} - Score Distribution',
                            color='Score',
                            color_continuous_scale='RdYlBu'
                        )
                        fig.update_traces(texttemplate='%{text}%', textposition='outside')
                        fig.update_layout(
                            showlegend=False,
                            height=400,
                            margin=dict(l=20, r=20, t=40, b=20)
                        )
                        st.plotly_chart(fig, use_container_width=True)

                with tab2:
                    for subject in scores_df['Subject']:
                        st.subheader(subject)
                        scores = subject_scores[subject]
                        score_dist = pd.Series(scores).value_counts().sort_index()
                        total = sum(score_dist.values)
                        score_percentages = (score_dist / total * 100).round(1)

                        dist_df = pd.DataFrame({
                            'Score': score_dist.index,
                            'Count': score_dist.values,
                            'Percentage': score_percentages.values
                        })
                        st.dataframe(
                            dist_df.sort_values('Score'),
                            hide_index=True,
                            use_container_width=True
                        )
            else:
                st.warning("No subjects with scores found after filtering.")

        except Exception as e:
            st.error("An error occurred while processing the data.")
            st.exception(e)

if __name__ == "__main__":
    main()