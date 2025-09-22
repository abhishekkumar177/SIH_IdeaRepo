import dash
from dash import dcc, html, Input, Output, State, dash_table
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sys
from datetime import date, timedelta

# --- Configuration and Helper Functions (Data Processing) ---
NUM_ASSESSMENTS_PER_SUBJECT = 3
PASSING_ATTEMPTS_LIMIT = 3
SUBJECTS = ['Mathematics-I', 'Physics', 'Programming']
LOGIN_PASSWORD = 'password123'


def calculate_risk(student):
    """
    Calculates the risk score, band, and reasons for a single student.
    """
    risk_score = 0
    risk_reasons = []

    # 1. Attendance points
    attendance = student['rolling_attendance_90d']
    if pd.notna(attendance):
        if 70 <= attendance < 85:
            risk_score += 10
            risk_reasons.append(f"Attendance {attendance:.2f}% (70-85)")
        elif 50 <= attendance < 70:
            risk_score += 25
            risk_reasons.append(f"Attendance {attendance:.2f}% (50-70)")
        elif attendance < 50:
            risk_score += 50
            risk_reasons.append(f"Attendance {attendance:.2f}% (<50%)")

    # 2. Score trends and low score points (Overall)
    overall_avg_score = student['overall_avg_score']
    if pd.notna(overall_avg_score):
        if 50 <= overall_avg_score < 60:
            risk_score += 10
            risk_reasons.append(f"Overall Avg Score {overall_avg_score:.2f}% (50-60%)")
        elif 35 <= overall_avg_score < 50:
            risk_score += 25
            risk_reasons.append(f"Overall Avg Score {overall_avg_score:.2f}% (35-50%)")
        elif overall_avg_score < 35:
            risk_score += 50
            risk_reasons.append(f"Overall Avg Score {overall_avg_score:.2f}% (<35%)")

    # 3. Exhausted attempts (per subject)
    if student.get('max_attempts_overall', 0) >= (PASSING_ATTEMPTS_LIMIT - 1):
        risk_score += 15
        risk_reasons.append("Exhausted attempts for at least one subject")
    if student.get('max_attempts_overall', 0) >= PASSING_ATTEMPTS_LIMIT:
        risk_score += 35
        risk_reasons.append("Attempts limit reached for at least one subject")

    # 4. Fee overdue
    overdue_days = student['overdue_days']
    if pd.notna(overdue_days):
        if 1 <= overdue_days <= 30:
            risk_score += 10
            risk_reasons.append(f"Overdue fees (1-30 days)")
        elif 31 <= overdue_days <= 90:
            risk_score += 25
            risk_reasons.append(f"Overdue fees (31-90 days)")
        elif overdue_days > 90:
            risk_score += 40
            risk_reasons.append(f"Overdue fees (>90 days)")

    return risk_score, risk_reasons

def map_risk_band(score):
    if score >= 100:
        return 'Red (High)'
    elif score >= 40:
        return 'Amber (Medium)'
    else:
        return 'Green (Low)'

def run_data_pipeline():
    """Reads raw data, processes it, calculates risk, and returns the ledger."""
    try:
        students_df = pd.read_csv('students.csv')
        attendance_df = pd.read_csv('attendance.csv')
        assessments_df = pd.read_csv('assessments.csv')
        fees_df = pd.read_csv('fees.csv')
    except FileNotFoundError:
        print("Error: Required CSV files not found. Please run university_data_generator.py first.")
        sys.exit(1)

    # --- FUSE DATA & CALCULATE RISK ---
    student_ledger = students_df.copy()

    # Attendance
    attendance_summary = attendance_df.groupby('student_id')['status'].apply(
        lambda x: (x == 'Present').sum() / len(x) * 100 if len(x) > 0 else 0
    ).reset_index(name='rolling_attendance_90d')
    student_ledger = student_ledger.merge(attendance_summary, on='student_id', how='left')

    # Assessments
    assessments_df['date'] = pd.to_datetime(assessments_df['date'])
    assessments_summary = assessments_df.groupby('student_id').agg(
        overall_avg_score=('score', 'mean'),
        max_attempts_overall=('attempts', 'max')
    ).reset_index()
    student_ledger = student_ledger.merge(assessments_summary, on='student_id', how='left')

    # Per-subject scores
    assessments_summary_pivot = assessments_df.groupby(['student_id', 'subject'])[
        'score'].mean().unstack().reset_index()
    assessments_summary_pivot.columns = ['student_id'] + [f'avg_score_{col}' for col in
                                                          assessments_summary_pivot.columns[1:]]
    student_ledger = student_ledger.merge(assessments_summary_pivot, on='student_id', how='left')

    # Fees
    fees_df['due_date'] = pd.to_datetime(fees_df['due_date'])
    current_date = pd.to_datetime(date.today())
    fees_df['overdue_days'] = (current_date - fees_df['due_date']).dt.days.fillna(0).astype(int)
    fees_summary = fees_df[['student_id', 'amount_due', 'amount_paid', 'status', 'overdue_days']]
    student_ledger = student_ledger.merge(fees_summary, on='student_id', how='left')

    # Apply risk calculation
    student_ledger[['risk_score', 'risk_reasons']] = student_ledger.apply(
        lambda row: pd.Series(calculate_risk(row)), axis=1
    )
    student_ledger['risk_band'] = student_ledger['risk_score'].apply(map_risk_band)
    student_ledger['risk_reasons'] = student_ledger['risk_reasons'].apply(
        lambda x: ', '.join(x) if x else 'No risk factors')

    return student_ledger


# --- Dash App Layout and Callbacks ---
app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'])

# Global variable to store the processed data
student_ledger_df = pd.DataFrame()

# App layout (Login page first)
app.layout = html.Div(id='page-content', children=[
    html.Div(id='login-container', children=[
        html.H1("Student Dashboard Login", style={'textAlign': 'center'}),
        html.Div([
            html.Label("Student ID"),
            dcc.Input(id='student-id-input', type='text', placeholder='Enter Student ID', style={'width': '100%'}),
        ], style={'marginBottom': '10px'}),
        html.Div([
            html.Label("Password"),
            dcc.Input(id='password-input', type='password', placeholder='Enter Password', style={'width': '100%'}),
        ], style={'marginBottom': '20px'}),
        html.Button('Login', id='login-button', n_clicks=0, style={'width': '100%'}),
        html.Div(id='login-status', style={'textAlign': 'center', 'marginTop': '10px'}),
    ], style={'width': '300px', 'margin': '50px auto', 'padding': '20px', 'border': '1px solid #ccc', 'borderRadius': '5px'})
])


@app.callback(
    Output('page-content', 'children'),
    Output('login-status', 'children'),
    Input('login-button', 'n_clicks'),
    State('student-id-input', 'value'),
    State('password-input', 'value')
)
def update_page(n_clicks, student_id_input, password):
    if n_clicks > 0:
        if password == LOGIN_PASSWORD:
            try:
                student_id = int(student_id_input)
                student_data = student_ledger_df[student_ledger_df['student_id'] == student_id]
                if not student_data.empty:
                    student_data = student_data.iloc[0]

                    gauge_fig = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=student_data['risk_score'],
                        gauge={'axis': {'range': [0, 150]},
                               'steps': [
                                   {'range': [0, 39], 'color': "lightgreen"},
                                   {'range': [40, 99], 'color': "yellow"},
                                   {'range': [100, 150], 'color': "lightcoral"}
                               ]},
                        domain={'x': [0, 1], 'y': [0, 1]}
                    ))
                    gauge_fig.update_layout(title_text="Risk Score", height=200, margin=dict(t=0, b=0, l=20, r=20))

                    dashboard_layout = html.Div(style={'padding': '20px', 'max-width': '960px', 'margin': 'auto'}, children=[
                        html.H1(f"Welcome, {student_data['name']}", style={'textAlign': 'center'}),
                        html.H3(f"Student Dashboard", style={'textAlign': 'center'}),
                        html.Hr(),
                        html.Div(style={'display': 'flex', 'flex-wrap': 'wrap', 'justify-content': 'space-around'}, children=[
                            html.Div(style={'flex-basis': '45%', 'min-width': '250px', 'max-height': '200px', 'overflow-y': 'auto', 'padding': '10px', 'border': '1px solid #ccc', 'borderRadius': '5px', 'margin': '10px'}, children=[
                                html.H4("Key Information"),
                                html.P(f"ID: {student_data['student_id']}"),
                                html.P(f"Branch: {student_data['branch']}"),
                                html.P(f"Guardian Contact: {student_data['guardian_contact']}"),
                                html.P(f"Assigned Mentor ID: {student_data['mentor_id']}")
                            ]),
                            html.Div(style={'flex-basis': '45%', 'min-width': '250px', 'max-height': '200px', 'overflow-y': 'auto', 'padding': '10px', 'border': '1px solid #ccc', 'borderRadius': '5px', 'margin': '10px'}, children=[
                                html.H4("Risk Status"),
                                dcc.Graph(figure=gauge_fig),
                                html.P(f"Risk Band: {student_data['risk_band']}"),
                                html.P(f"Reasons: {student_data['risk_reasons']}", style={'white-space': 'pre-line'})
                            ]),
                            html.Div(style={'flex-basis': '95%', 'min-width': '250px', 'max-height': '200px', 'overflow-y': 'auto', 'padding': '10px', 'border': '1px solid #ccc', 'borderRadius': '5px', 'margin': '10px'}, children=[
                                html.H4("Academic & Financials"),
                                html.P(f"Overall Avg Score: {student_data.get('overall_avg_score', 'N/A'):.2f}%"),
                                html.P(f"Attendance (90d): {student_data.get('rolling_attendance_90d', 'N/A'):.2f}%"),
                                html.P(f"Fees Status: {student_data.get('status', 'N/A')}"),
                                html.P(f"Overdue Days: {student_data.get('overdue_days', 'N/A')}")
                            ])
                        ]),
                        html.Hr(),
                        html.H4("Subject-wise Performance"),
                        dash_table.DataTable(
                            id='subject-table',
                            columns=[
                                {"name": "Subject", "id": "Subject"},
                                {"name": "Avg Score", "id": "Avg Score"}
                            ],
                            data=[
                                {'Subject': 'Mathematics-I', 'Avg Score': student_data.get('avg_score_Mathematics-I', 'N/A')},
                                {'Subject': 'Physics', 'Avg Score': student_data.get('avg_score_Physics', 'N/A')},
                                {'Subject': 'Programming', 'Avg Score': student_data.get('avg_score_Programming', 'N/A')}
                            ],
                            style_cell={'textAlign': 'left'},
                            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                        )
                    ])
                    return dashboard_layout, ''
                else:
                    return dash.no_update, '❌ Invalid Student ID.'
            except (ValueError, KeyError):
                return dash.no_update, '❌ Invalid Student ID or data format.'
        else:
            return dash.no_update, '❌ Invalid password.'
    return dash.no_update, ''


if __name__ == '__main__':
    print("Running data pipeline...")
    student_ledger_df = run_data_pipeline()
    print("Data pipeline complete. Starting Dash server...")
    app.run(debug=True)