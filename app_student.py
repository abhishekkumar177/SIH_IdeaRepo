import dash
from dash import dcc, html, Input, Output, State, dash_table
import pandas as pd
import plotly.graph_objects as go
import sys
from datetime import date

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
        # Assuming these files are present in the execution environment
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
# Using the provided simple external stylesheet
app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'])

# Global variable to store the processed data
student_ledger_df = pd.DataFrame()

# App layout (Login page first)
app.layout = html.Div(id='page-content', children=[
    html.Div(id='login-container', children=[
        html.H1("Student Dashboard Login", style={'textAlign': 'center', 'color': '#343a40'}),
        html.Div([
            html.Label("Student ID", style={'fontWeight': 'bold'}),
            dcc.Input(id='student-id-input', type='text', placeholder='Enter Student ID',
                      style={'width': '100%', 'padding': '10px', 'marginBottom': '10px', 'border': '1px solid #ccc',
                             'borderRadius': '5px'}),
        ], style={'marginBottom': '10px'}),
        html.Div([
            html.Label("Password", style={'fontWeight': 'bold'}),
            dcc.Input(id='password-input', type='password', placeholder='Enter Password',
                      style={'width': '100%', 'padding': '10px', 'marginBottom': '10px', 'border': '1px solid #ccc',
                             'borderRadius': '5px'}),
        ], style={'marginBottom': '20px'}),
        html.Button('Login', id='login-button', n_clicks=0,
                    style={'width': '100%', 'padding': '10px', 'backgroundColor': '#007bff', 'color': 'white',
                           'border': 'none', 'borderRadius': '5px', 'cursor': 'pointer'}),
        html.Div(id='login-status', style={'textAlign': 'center', 'marginTop': '15px', 'color': '#dc3545'}),
    ], style={'width': '350px', 'margin': '100px auto', 'padding': '30px', 'borderRadius': '8px',
              'boxShadow': '0 4px 12px 0 rgba(0, 0, 0, 0.1)', 'backgroundColor': 'white'})
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

                    # --- Risk Status Color Coding ---
                    risk_band = student_data['risk_band']
                    if 'Red' in risk_band:
                        risk_color = '#dc3545'  # Red
                        risk_bg_color = '#f8d7da'
                    elif 'Amber' in risk_band:
                        risk_color = '#ffc107'  # Yellow/Orange
                        risk_bg_color = '#fff3cd'
                    else:
                        risk_color = '#28a745'  # Green
                        risk_bg_color = '#d4edda'

                    # General Card Style - Enhanced shadow for a "lifted" feel (like LinkedIn posts)
                    card_style = {
                        'flex-basis': '48%',
                        'min-width': '300px',
                        'padding': '20px',
                        'borderRadius': '10px',
                        'boxShadow': '0 6px 16px 0 rgba(0, 0, 0, 0.1), 0 0 0 1px rgba(0, 0, 0, 0.05)',
                        # Enhanced shadow
                        'margin': '10px 0',
                        'backgroundColor': 'white',
                        'height': 'auto',
                        'overflowY': 'hidden',
                        'display': 'flex',
                        'flexDirection': 'column',
                        'transition': 'box-shadow 0.3s ease-in-out',
                    }

                    # Gauge Figure
                    gauge_fig = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=student_data['risk_score'],
                        gauge={'axis': {'range': [0, 150]},
                               'steps': [
                                   {'range': [0, 39], 'color': "lightgreen"},
                                   {'range': [40, 99], 'color': "gold"},
                                   {'range': [100, 150], 'color': "lightcoral"}
                               ]},
                        domain={'x': [0, 1], 'y': [0, 1]}
                    ))
                    gauge_fig.update_layout(title_text="Risk Score", height=150, margin=dict(t=0, b=0, l=0, r=0),
                                            font={'size': 12})
                    # --------------------------------

                    dashboard_layout = html.Div(style={'padding': '20px', 'max-width': '1200px', 'margin': '20px auto',
                                                       'backgroundColor': '#f2f5f7', 'borderRadius': '12px'},
                                                children=[  # Light blue-grey background
                                                    html.H1(f"Welcome, {student_data['name']} 👋",
                                                            style={'textAlign': 'center', 'color': '#343a40',
                                                                   'marginBottom': '5px', 'paddingTop': '10px'}),
                                                    html.H3(f"Student Performance Dashboard",
                                                            style={'textAlign': 'center', 'color': '#6c757d',
                                                                   'marginBottom': '20px'}),
                                                    html.Hr(style={'borderColor': '#ccc'}),

                                                    # Main Row: Key Info + Risk Status
                                                    html.Div(style={'display': 'flex', 'flex-wrap': 'wrap',
                                                                    'justify-content': 'space-between', 'gap': '20px'},
                                                             children=[
                                                                 # 1. Key Information Card
                                                                 html.Div(style={**card_style, 'maxHeight': '300px',
                                                                                 'overflowY': 'auto'}, children=[
                                                                     html.H4("Key Information ℹ️",
                                                                             style={'borderBottom': '2px solid #007bff',
                                                                                    'paddingBottom': '10px',
                                                                                    'marginBottom': '15px',
                                                                                    'color': '#007bff'}),

                                                                     # FIX APPLIED HERE: Wrap children in a list
                                                                     html.P([html.B("ID: "),
                                                                             f"{student_data['student_id']}"],
                                                                            style={'margin': '5px 0'}),
                                                                     html.P([html.B("Branch: "),
                                                                             f"{student_data['branch']}"],
                                                                            style={'margin': '5px 0'}),
                                                                     html.P([html.B("Guardian Contact: "),
                                                                             f"{student_data['guardian_contact']}"],
                                                                            style={'margin': '5px 0'}),
                                                                     html.P([html.B("Assigned Mentor ID: "),
                                                                             f"{student_data['mentor_id']}"],
                                                                            style={'margin': '5px 0'})
                                                                 ]),

                                                                 # 2. Risk Status Card (Color-coded)
                                                                 html.Div(style={
                                                                     **card_style,
                                                                     'maxHeight': '300px',
                                                                     'backgroundColor': risk_bg_color,
                                                                     'border': f'1px solid {risk_color}'
                                                                 }, children=[
                                                                     html.H4("Risk Status 🚨",
                                                                             style={'color': risk_color,
                                                                                    'borderBottom': f'2px solid {risk_color}',
                                                                                    'paddingBottom': '10px',
                                                                                    'marginBottom': '15px'}),
                                                                     html.Div(style={'display': 'flex',
                                                                                     'alignItems': 'flex-start',
                                                                                     'justifyContent': 'space-between',
                                                                                     'flexWrap': 'wrap'}, children=[
                                                                         html.Div(style={'flexGrow': '1',
                                                                                         'minWidth': '150px'},
                                                                                  children=[
                                                                                      html.P([html.B("Risk Band: "),
                                                                                              html.Span(student_data[
                                                                                                            'risk_band'],
                                                                                                        style={
                                                                                                            'fontWeight': 'bold',
                                                                                                            'color': risk_color,
                                                                                                            'fontSize': '1.1em'})]),
                                                                                      html.P(html.B("Reasons: ")),
                                                                                      html.Div(
                                                                                          student_data['risk_reasons'],
                                                                                          style={
                                                                                              'white-space': 'pre-line',
                                                                                              'fontSize': '0.9em',
                                                                                              'maxHeight': '80px',
                                                                                              'overflowY': 'auto',
                                                                                              'padding': '5px',
                                                                                              'borderLeft': f'3px solid {risk_color}'})
                                                                                  ]),
                                                                         dcc.Graph(figure=gauge_fig,
                                                                                   style={'width': '150px',
                                                                                          'height': '150px'})
                                                                     ])
                                                                 ])
                                                             ]),  # End Main Row

                                                    # Academic & Financials Summary Row - Presented as a horizontal "stat bar"
                                                    html.H4("Academic & Financials Summary 📊",
                                                            style={'marginTop': '30px',
                                                                   'borderBottom': '2px solid #17a2b8',
                                                                   'paddingBottom': '10px', 'marginBottom': '20px',
                                                                   'color': '#17a2b8'}),
                                                    html.Div(style={
                                                        'display': 'flex',
                                                        'justifyContent': 'space-around',
                                                        'flexWrap': 'wrap',
                                                        'backgroundColor': 'white',
                                                        'padding': '15px 10px',
                                                        'borderRadius': '10px',
                                                        'boxShadow': '0 2px 8px 0 rgba(0, 0, 0, 0.05)',
                                                    }, children=[
                                                        html.Div(style={'textAlign': 'center', 'margin': '10px',
                                                                        'padding': '10px',
                                                                        'borderRight': '1px solid #eee'}, children=[
                                                            html.B("Overall Avg Score: "),
                                                            html.P(
                                                                f"{student_data.get('overall_avg_score', 'N/A'):.2f}%",
                                                                style={'fontSize': '1.2em', 'color': '#333',
                                                                       'fontWeight': 'bold', 'marginTop': '5px'})
                                                        ]),
                                                        html.Div(style={'textAlign': 'center', 'margin': '10px',
                                                                        'padding': '10px',
                                                                        'borderRight': '1px solid #eee'}, children=[
                                                            html.B("Attendance (90d): "),
                                                            html.P(
                                                                f"{student_data.get('rolling_attendance_90d', 'N/A'):.2f}%",
                                                                style={'fontSize': '1.2em', 'color': '#333',
                                                                       'fontWeight': 'bold', 'marginTop': '5px'})
                                                        ]),
                                                        html.Div(style={'textAlign': 'center', 'margin': '10px',
                                                                        'padding': '10px',
                                                                        'borderRight': '1px solid #eee'}, children=[
                                                            html.B("Fees Status: "),
                                                            html.P(f"{student_data.get('status', 'N/A')}",
                                                                   style={'fontSize': '1.2em', 'color': '#333',
                                                                          'fontWeight': 'bold', 'marginTop': '5px'})
                                                        ]),
                                                        html.Div(style={'textAlign': 'center', 'margin': '10px',
                                                                        'padding': '10px'}, children=[
                                                            html.B("Overdue Days: "),
                                                            html.P(f"{student_data.get('overdue_days', 'N/A')}",
                                                                   style={'fontSize': '1.2em', 'color': '#333',
                                                                          'fontWeight': 'bold', 'marginTop': '5px'})
                                                        ])
                                                    ]),

                                                    html.Hr(style={'borderColor': '#ccc', 'marginTop': '30px'}),

                                                    # Subject-wise Performance Table
                                                    html.H4("Subject-wise Performance 📚",
                                                            style={'marginBottom': '15px', 'color': '#343a40'}),
                                                    dash_table.DataTable(
                                                        id='subject-table',
                                                        columns=[
                                                            {"name": "Subject", "id": "Subject"},
                                                            {"name": "Avg Score", "id": "Avg Score"}
                                                        ],
                                                        data=[
                                                            {'Subject': 'Mathematics-I',
                                                             'Avg Score': f"{student_data.get('avg_score_Mathematics-I', 'N/A')}"},
                                                            {'Subject': 'Physics',
                                                             'Avg Score': f"{student_data.get('avg_score_Physics', 'N/A')}"},
                                                            {'Subject': 'Programming',
                                                             'Avg Score': f"{student_data.get('avg_score_Programming', 'N/A')}"}
                                                        ],
                                                        style_cell={
                                                            'textAlign': 'center',
                                                            'padding': '12px',
                                                            'border': 'none',
                                                            'fontSize': '1.0em'
                                                        },
                                                        style_header={
                                                            'backgroundColor': '#007bff',
                                                            'color': 'white',
                                                            'fontWeight': 'bold',
                                                            'fontSize': '1.1em',
                                                            'border': 'none',
                                                            'padding': '15px'
                                                        },
                                                        style_data_conditional=[
                                                            {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}
                                                        ],
                                                        style_table={'borderRadius': '8px', 'overflow': 'hidden',
                                                                     'boxShadow': '0 2px 8px 0 rgba(0, 0, 0, 0.1)'}
                                                    ),

                                                    # Chat AI Button (Stays fixed at the bottom right)
                                                    html.A(
                                                        html.Button('Chat AI 🤖', style={
                                                            'background-color': '#20c997',
                                                            'color': 'white',
                                                            'border': 'none',
                                                            'padding': '15px 25px',
                                                            'text-align': 'center',
                                                            'text-decoration': 'none',
                                                            'display': 'inline-block',
                                                            'font-size': '16px',
                                                            'cursor': 'pointer',
                                                            'borderRadius': '50px',
                                                            'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.2)'
                                                        }),
                                                        href="https://ai-counseling-chatbot.onrender.com/",
                                                        target="_blank",
                                                        style={'position': 'fixed', 'bottom': '30px', 'right': '30px',
                                                               'z-index': '1000'}
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
    try:
        student_ledger_df = run_data_pipeline()
        print("Data pipeline complete. Starting Dash server...")
        app.run(debug=True)
    except SystemExit:
        print("Could not start server due to missing data files.")