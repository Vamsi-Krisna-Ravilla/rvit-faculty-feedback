import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io
import base64
from fpdf import FPDF
import plotly.io as pio

# Set page config
st.set_page_config(
    page_title="Faculty Rating Analysis",
    page_icon="📊",
    layout="wide"
)

# Custom CSS for improved UI
st.markdown("""
    <style>
    .main { padding: 1rem; }
    .stButton>button { width: 100%; }
    .css-1d391kg { padding-top: 1rem; }
    .sidebar .sidebar-content { width: 300px; }
    .download-btn { margin-top: 1rem; }
    .header-title { font-size: 28px; font-weight: bold; text-align: center; color: #1a5276; }
    .header-logo { display: flex; justify-content: center; align-items: center; }
    .header-logo img { width: 80px; margin-right: 15px; }
    .header-college-name { font-size: 24px; font-weight: bold; color: #1a5276; }
    .header-subtitle { font-size: 18px; color: #154360; }
    </style>
""", unsafe_allow_html=True)

def convert_rating_to_score(rating):
    if pd.isna(rating):
        return None
    return {
        'Excellent': 5,
        'Very Good': 4,
        'Good': 3,
        'Fair': 2,
        'Poor': 1
    }.get(rating, None)

def normalize_subject_name(name):
    if pd.isna(name):
        return None
    return ' '.join(str(name).strip().upper().split())

def get_sorted_unique_values(df, column):
    unique_values = df[column].dropna().unique().tolist()
    unique_values.append("nan")  # Include nan option
    return sorted(unique_values)

def calculate_average_scores(df):
    average_scores, subject_scores, accumulated_scores = {}, {}, {}

    for column in df.columns:
        if 'Subjects [' in column or 'Subject [' in column:
            start_idx = column.find('[') + 1
            end_idx = column.find(']')
            if start_idx > 0 and end_idx > start_idx:
                subject_name = normalize_subject_name(column[start_idx:end_idx])
                if subject_name:
                    scores = df[column].apply(convert_rating_to_score)
                    valid_scores = scores.dropna().tolist()
                    if valid_scores:
                        accumulated_scores.setdefault(subject_name, []).extend(valid_scores)

    for subject_name, scores in accumulated_scores.items():
        if scores:
            average_scores[subject_name] = sum(scores) / len(scores)
            subject_scores[subject_name] = scores

    return average_scores, subject_scores

def create_pdf_report(scores_df, subject_scores, selected_subjects, filters, generation_date):
    pdf = FPDF()
    pdf.add_page()

    # College Header with Logo
    pdf.set_font("Arial", "B", 12)
    pdf.image("rvitlogo_f.png", 10, 8, 30)
    pdf.cell(40)
    pdf.cell(0, 10, 'RV Institute of Technology', 0, 1, 'L')
    pdf.cell(40)
    pdf.cell(0, 10, 'UGC-Autonomous', 0, 1, 'L')
    pdf.ln(15)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, 'Faculty Rating Analysis Report', 0, 1, 'C')
    pdf.ln(5)

    # Report Generation Details
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 10, f"Report Generation Date: {generation_date}", 0, 1)
    pdf.cell(0, 10, f"Filters Applied:", 0, 1)
    for filter_name, filter_value in filters.items():
        pdf.cell(0, 10, f"{filter_name}: {', '.join(filter_value)}", 0, 1)
    pdf.ln(10)

    # Overall scores table
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, 'Overall Subject Performance', 0, 1, 'L')
    pdf.set_font("Arial", "", 10)
    
    # Table headers
    cols = ['Subject', 'Average Score', 'Number of Responses', 'Response Rate (%)']
    col_widths = [80, 30, 40, 40]
    for i, col in enumerate(cols):
        pdf.cell(col_widths[i], 10, col, 1)
    pdf.ln()
    
    # Table data
    for _, row in scores_df.iterrows():
        pdf.cell(80, 10, str(row['Subject'])[:40], 1)
        pdf.cell(30, 10, str(row['Average Score']), 1)
        pdf.cell(40, 10, str(row['Number of Responses']), 1)
        pdf.cell(40, 10, str(row['Response Rate (%)']), 1)
        pdf.ln()

    # Detailed breakdown for selected subjects
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, 'Detailed Score Distribution', 0, 1, 'L')
    
    for subject in selected_subjects:
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 10, f'\n{subject}', 0, 1, 'L')
        pdf.set_font("Arial", "", 10)
        
        scores = subject_scores[subject]
        score_dist = pd.Series(scores).value_counts().sort_index()
        total = sum(score_dist.values)
        score_percentages = (score_dist / total * 100).round(1)
        
        # Distribution table
        pdf.cell(30, 10, 'Score', 1)
        pdf.cell(30, 10, 'Count', 1)
        pdf.cell(30, 10, 'Percentage', 1)
        pdf.ln()
        
        for score, count in score_dist.items():
            pdf.cell(30, 10, str(score), 1)
            pdf.cell(30, 10, str(count), 1)
            pdf.cell(30, 10, f"{score_percentages[score]}%", 1)
            pdf.ln()
        pdf.ln(5)
    
    return pdf

def main():
    # College Header
    st.markdown("""
        <div class="header-logo">
            <img src="rvitlogo_f.png" alt="RVIT Logo">
            <div>
                <div class="header-college-name">RV Institute of Technology</div>
                <div class="header-subtitle">UGC-Autonomous</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.title("📊 Subject Faculty Rating Analysis")
    
    # File upload section
    with st.container():
        st.markdown("### 📁 Upload Data")
        uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])

            # Date Filters
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

            # Additional Filters with `nan` options
            with st.expander("📌 Additional Filters", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    year_semester_options = get_sorted_unique_values(df, 'Choose your Current/Last Academic Year and Semester')
                    selected_year_semesters = st.multiselect("Year and Semester", options=year_semester_options)

                    gender_options = get_sorted_unique_values(df, 'Gender')
                    selected_genders = st.multiselect("Gender", options=gender_options)

                with col2:
                    branch_options = get_sorted_unique_values(df, 'Select Branch/Discipline')
                    selected_branches = st.multiselect("Branch/Discipline", options=branch_options)

                    section_type_options = get_sorted_unique_values(df, 'Section Type')
                    selected_section_types = st.multiselect("Section Type", options=section_type_options)

            # Apply filters
            mask = (
                (df['Timestamp'] >= from_date) &
                (df['Timestamp'] <= to_date) &
                (df['Choose your Current/Last Academic Year and Semester'].fillna("nan").isin(selected_year_semesters)) &
                (df['Gender'].fillna("nan").isin(selected_genders)) &
                (df['Select Branch/Discipline'].fillna("nan").isin(selected_branches)) &
                (df['Section Type'].fillna("nan").isin(selected_section_types))
            )
            filtered_df = df.loc[mask]

            # Calculate scores
            average_scores, subject_scores = calculate_average_scores(filtered_df)

            # Display metrics
            total_responses = len(filtered_df)
            st.metric("Total Responses", total_responses)

            # Subject Performance Overview
            if average_scores:
                scores_data = [
                    {
                        'Subject': subject,
                        'Average Score': round(avg_score, 2),
                        'Number of Responses': len(subject_scores[subject]),
                        'Response Rate (%)': round((len(subject_scores[subject]) / total_responses) * 100, 1)
                    }
                    for subject, avg_score in average_scores.items()
                ]

                scores_df = pd.DataFrame(scores_data).sort_values('Average Score', ascending=False)
                st.markdown("### 📊 Subject Performance Overview")
                st.dataframe(
                    scores_df.style.background_gradient(subset=['Average Score'], cmap='RdYlGn'),
                    hide_index=True,
                    use_container_width=True
                )

                # Tabs for visualizations
                tab1, tab2 = st.tabs(["📈 Score Distribution", "📋 Detailed Breakdown"])

                with tab1:
                    selected_subjects = st.multiselect(
                        "Select Subjects to Display",
                        options=scores_df['Subject'].tolist(),
                        default=scores_df['Subject'].iloc[0]
                    )
                    for subject in selected_subjects:
                        scores = subject_scores[subject]
                        score_dist = pd.Series(scores).value_counts().sort_index()
                        total = sum(score_dist.values)
                        score_percentages = (score_dist / total * 100).round(1)

                        dist_df = pd.DataFrame({
                            'Score': score_dist.index,
                            'Count': score_dist.values,
                            'Percentage': score_percentages.values
                        })
                        fig = px.bar(
                            dist_df, x='Score', y='Count', text='Percentage',
                            labels={'Count': 'Number of Responses', 'Score': 'Rating Score'},
                            title=f'{subject} - Score Distribution',
                            color='Score', color_continuous_scale='RdYlBu'
                        )
                        fig.update_traces(texttemplate='%{text}%', textposition='outside')
                        fig.update_layout(showlegend=False, height=400, margin=dict(l=20, r=20, t=40, b=20))
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
                        st.dataframe(dist_df.sort_values('Score'), hide_index=True, use_container_width=True)

                # Report generation section
                st.markdown("### 📑 Generate Report")
                report_subjects = st.multiselect(
                    "Select Subjects for Detailed Report",
                    options=scores_df['Subject'].tolist(),
                    default=scores_df['Subject'].tolist()[:5]
                )
                filters = {
                    "Year and Semester": selected_year_semesters,
                    "Gender": selected_genders,
                    "Branch/Discipline": selected_branches,
                    "Section Type": selected_section_types
                }
                generation_date = datetime.now().strftime("%Y-%m-%d")

                if st.button("Generate PDF Report", key="generate_report"):
                    pdf = create_pdf_report(scores_df, subject_scores, report_subjects, filters, generation_date)
                    
                    # Save PDF to bytes
                    pdf_bytes = pdf.output(dest='S').encode('latin1')
                    
                    # Create download button
                    b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                    href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="faculty_rating_report.pdf" class="download-btn"><button style="padding: 0.5rem 1rem; background-color: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer;">Download PDF Report</button></a>'
                    st.markdown(href, unsafe_allow_html=True)

            else:
                st.warning("No subjects with scores found after filtering.")

        except Exception as e:
            st.error("An error occurred while processing the data.")
            st.exception(e)

if __name__ == "__main__":
    main()
