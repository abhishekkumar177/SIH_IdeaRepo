import dash
from dash import dcc, html, Input, Output, State
import pandas as pd
import sys


# --- Data Processing and Risk Calculation Functions ---
# (You should have these functions from our previous conversations)
# Make sure to copy them here or import them from a separate file.
def calculate_risk(student):
    risk_score = 0
    risk_reasons = []

    # Attendance points
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

    # Score trends and low score points (Overall)
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

    # Fee overdue
    overdue_days = student.get('overdue_days', 0)
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

    # Assuming 'max_attempts_overall' exists
    if student.get('max_attempts_overall', 0) >= 2:
        risk_score += 15
        risk_reasons.append("Exhausted attempts for at least one subject")
    if student.get('max_attempts_overall', 0) >= 3:
        risk_score += 35
        risk_reasons.append("Attempts limit reached for at least one subject")

    return risk_score, risk_reasons


def map_risk_band(score):
    if score >= 100:
        return 'Red'
    elif score >= 40:
        return 'Amber'
    else:
        return 'Green'


def run_data_pipeline():
    # Placeholder for data pipeline logic
    try:
        students_df = pd.read_csv('students.csv')
        attendance_df = pd.read_csv('attendance.csv')
        assessments_df = pd.read_csv('assessments.csv')
        fees_df = pd.read_csv('fees.csv')
        mentors_df = pd.read_csv('mentors.csv')
    except FileNotFoundError:
        print("Error: Required CSV files not found. Please run university_data_generator.py first.")
        sys.exit(1)

    # FUSE DATA & CALCULATE RISK
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
    from datetime import date
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
        lambda x: ', '.join(x) if isinstance(x, list) else str(x))

    return student_ledger, mentors_df


# Load and process data at startup
student_ledger_df, mentors_df = run_data_pipeline()

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'])
server = app.server

# --- App Layout (Login Page) ---
app.layout = html.Div(id='page-content', children=[
    html.Div(id='login-container', children=[
        html.H1("Mentor Dashboard Login", style={'textAlign': 'center'}),
        html.Div([
            html.Label("Login ID"),
            dcc.Input(id='login-input', type='text', placeholder='Enter Login ID', style={'width': '100%'}),
        ], style={'marginBottom': '10px'}),
        html.Div([
            html.Label("Password"),
            dcc.Input(id='password-input', type='password', placeholder='Enter Password', style={'width': '100%'}),
        ], style={'marginBottom': '20px'}),
        html.Button('Login', id='login-button', n_clicks=0, style={'width': '100%'}),
        html.Div(id='login-status', style={'textAlign': 'center', 'marginTop': '10px'}),
    ], style={'width': '300px', 'margin': '50px auto', 'padding': '20px', 'border': '1px solid #ccc',
              'borderRadius': '5px'})
])


# --- Callbacks ---

@app.callback(
    Output('page-content', 'children'),
    Output('login-status', 'children'),
    Input('login-button', 'n_clicks'),
    State('login-input', 'value'),
    State('password-input', 'value')
)
def update_page(n_clicks, login_id, password):
    if n_clicks > 0:
        mentor_data = mentors_df[(mentors_df['login_id'] == login_id) & (mentors_df['password'] == password)]
        if not mentor_data.empty:
            mentor_id = mentor_data.iloc[0]['mentor_id']
            assigned_students = student_ledger_df[student_ledger_df['mentor_id'] == mentor_id]

            if assigned_students.empty:
                return html.Div([
                    html.H1("Welcome to the Mentor Dashboard", style={'textAlign': 'center'}),
                    html.P("You have no students assigned to you.")
                ]), ''

            red_zone_students = assigned_students[assigned_students['risk_band'].str.contains('Red')]

            dashboard_layout = html.Div(children=[
                html.Button(
                    f'🔔 ({len(red_zone_students)})',
                    id='notification-button',
                    style={
                        'position': 'fixed',
                        'top': '20px',
                        'right': '20px',
                        'fontSize': '20px',
                        'cursor': 'pointer',
                        'backgroundColor': 'white',
                        'border': '1px solid #ccc',
                        'borderRadius': '5px',
                        'padding': '5px 10px',
                        'zIndex': '1000'
                    }
                ),
                html.Div(id='notification-modal', style={
                    'display': 'none',
                    'position': 'fixed', 'zIndex': '1001', 'left': '0', 'top': '0',
                    'width': '100%', 'height': '100%', 'overflow': 'auto',
                    'backgroundColor': 'rgba(0,0,0,0.4)'
                }, children=[
                    html.Div(style={
                        'backgroundColor': '#fefefe', 'margin': '15% auto', 'padding': '20px',
                        'border': '1px solid #888', 'width': '80%',
                        'boxShadow': '0 4px 8px 0 rgba(0,0,0,0.2), 0 6px 20px 0 rgba(0,0,0,0.19)'
                    }, children=[
                        html.Span('✖️', id='close-modal',
                                  style={'float': 'right', 'fontSize': '24px', 'cursor': 'pointer'}),
                        html.H3('Red Zone Student Notifications'),
                        dash.dash_table.DataTable(
                            id='red-zone-table',
                            columns=[
                                {"name": "Student Name", "id": "name"},
                                {"name": "Branch", "id": "branch"},
                                {"name": "Risk Score", "id": "risk_score"},
                                {"name": "Reasons", "id": "risk_reasons"}
                            ],
                            data=red_zone_students.to_dict('records'),
                            style_cell={'textAlign': 'left', 'whiteSpace': 'normal', 'minWidth': '120px',
                                        'width': '120px', 'maxWidth': '250px'},
                            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                        )
                    ])
                ]),
                html.H1("Mentor Dashboard", style={'textAlign': 'center'}),
                html.P(f"Showing students for Mentor ID: {mentor_id}"),
                html.Div([
                    html.H3("Assigned Students"),
                    dash.dash_table.DataTable(
                        id='table',
                        columns=[
                            {"name": "Name", "id": "name"},
                            {"name": "Branch", "id": "branch"},
                            {"name": "Risk Band", "id": "risk_band"},
                            {"name": "Risk Score", "id": "risk_score"},
                            {"name": "Avg Score", "id": "overall_avg_score"}
                        ],
                        data=assigned_students.to_dict('records'),
                        sort_action="native",
                        style_cell={'textAlign': 'left'},
                        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                    ),
                ], style={'padding': '20px'}),
            ])
            return dashboard_layout, ''
        else:
            return dash.no_update, '❌ Invalid login credentials.'
    return dash.no_update, ''


@app.callback(
    Output('notification-modal', 'style'),
    [Input('notification-button', 'n_clicks'),
     Input('close-modal', 'n_clicks')],
    [State('notification-modal', 'style')],
    prevent_initial_call=True
)
def toggle_modal(open_clicks, close_clicks, current_style):
    ctx = dash.callback_context
    if not ctx.triggered:
        return current_style

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'notification-button':
        current_style['display'] = 'block'
    elif button_id == 'close-modal':
        current_style['display'] = 'none'

    return current_style


if __name__ == '__main__':
    print("Running data pipeline...")
    student_ledger_df, mentors_df = run_data_pipeline()
    print("Data pipeline complete. Starting Dash server...")
    app.run(debug=True)