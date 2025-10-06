import dash
from dash import dcc, html, Input, Output, State, dash_table
import pandas as pd
import sys
import plotly.graph_objects as go
from datetime import date
import json

# --- Custom Styles & Colors ---
COLOR_GREEN = '#2E7D32'  # Darker Green
COLOR_AMBER = '#FFB300'  # Darker Amber
COLOR_RED = '#C62828'  # Darker Red
COLOR_PRIMARY = '#1976D2'  # Blue (Main Accent)
COLOR_BG_LIGHT = '#F5F5F5'  # Light Background
COLOR_BG_DARK = '#212121'  # Header/Footer
CARD_STYLE = {
    'backgroundColor': 'white',
    'borderRadius': '12px',
    'boxShadow': '0 4px 12px rgba(0,0,0,0.15)',
    'padding': '20px',
    'transition': 'all 0.3s ease-in-out',
}


# --- Data Processing and Risk Calculation Functions (Kept for self-sufficiency) ---
def calculate_risk(student):
    risk_score = 0
    risk_reasons = []
    attendance = student.get('rolling_attendance_90d')
    if pd.notna(attendance):
        if 70 <= attendance < 85:
            risk_score += 10; risk_reasons.append(f"Attendance {attendance:.2f}% (70-85)")
        elif 50 <= attendance < 70:
            risk_score += 25; risk_reasons.append(f"Attendance {attendance:.2f}% (50-70)")
        elif attendance < 50:
            risk_score += 50; risk_reasons.append(f"Attendance {attendance:.2f}% (<50%)")
    overall_avg_score = student.get('overall_avg_score')
    if pd.notna(overall_avg_score):
        if 50 <= overall_avg_score < 60:
            risk_score += 10; risk_reasons.append(f"Overall Avg Score {overall_avg_score:.2f}% (50-60%)")
        elif 35 <= overall_avg_score < 50:
            risk_score += 25; risk_reasons.append(f"Overall Avg Score {overall_avg_score:.2f}% (35-50%)")
        elif overall_avg_score < 35:
            risk_score += 50; risk_reasons.append(f"Overall Avg Score {overall_avg_score:.2f}% (<35%)")
    overdue_days = student.get('overdue_days', 0)
    if pd.notna(overdue_days):
        if 1 <= overdue_days <= 30:
            risk_score += 10; risk_reasons.append(f"Overdue fees (1-30 days)")
        elif 31 <= overdue_days <= 90:
            risk_score += 25; risk_reasons.append(f"Overdue fees (31-90 days)")
        elif overdue_days > 90:
            risk_score += 40; risk_reasons.append(f"Overdue fees (>90 days)")
    if student.get('max_attempts_overall', 0) >= 2: risk_score += 15; risk_reasons.append(
        "Exhausted attempts for at least one subject")
    if student.get('max_attempts_overall', 0) >= 3: risk_score += 35; risk_reasons.append(
        "Attempts limit reached for at least one subject")
    return risk_score, risk_reasons


def map_risk_band(score):
    if score >= 100:
        return 'Red'
    elif score >= 40:
        return 'Amber'
    else:
        return 'Green'


def run_data_pipeline():
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
    attendance_summary = attendance_df.groupby('student_id')['status'].apply(
        lambda x: (x == 'Present').sum() / len(x) * 100 if len(x) > 0 else 0
    ).reset_index(name='rolling_attendance_90d')
    student_ledger = student_ledger.merge(attendance_summary, on='student_id', how='left')

    assessments_df['date'] = pd.to_datetime(assessments_df['date'])
    assessments_summary = assessments_df.groupby('student_id').agg(
        overall_avg_score=('score', 'mean'),
        max_attempts_overall=('attempts', 'max')
    ).reset_index()
    student_ledger = student_ledger.merge(assessments_summary, on='student_id', how='left')

    assessments_summary_pivot = assessments_df.groupby(['student_id', 'subject'])[
        'score'].mean().unstack().reset_index()
    assessments_summary_pivot.columns = ['student_id'] + [f'avg_score_{col}' for col in
                                                          assessments_summary_pivot.columns[1:]]
    student_ledger = student_ledger.merge(assessments_summary_pivot, on='student_id', how='left')

    fees_df['due_date'] = pd.to_datetime(fees_df['due_date'])
    current_date = pd.to_datetime(date.today())
    fees_df['overdue_days'] = (current_date - fees_df['due_date']).dt.days.fillna(0).astype(int)
    fees_summary = fees_df[['student_id', 'amount_due', 'amount_paid', 'status', 'overdue_days']]
    student_ledger = student_ledger.merge(fees_summary, on='student_id', how='left')

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


# --- Component Layouts ---

def get_navbar(mentor_id, notification_count):
    """Generates the navigation bar for the dashboard."""
    COLOR_RED = '#C62828'
    COLOR_PRIMARY = '#1976D2'
    COLOR_BG_DARK = '#212121'

    notification_color = COLOR_RED if notification_count > 0 else COLOR_PRIMARY

    return html.Div([
        # Header Bar
        html.Div(style={'backgroundColor': COLOR_BG_DARK, 'color': 'white', 'padding': '15px 30px', 'display': 'flex',
                        'justifyContent': 'space-between', 'alignItems': 'center'}, children=[
            html.H2("Student Risk Analyzer: Mentor Dashboard 🛡️", style={'margin': '0', 'fontSize': '24px'}),
            html.P(f"Mentor ID: {mentor_id}", style={'margin': '0', 'opacity': '0.8'})
        ]),

        # Navigation Tabs
        html.Div(style={'backgroundColor': 'white', 'padding': '10px 30px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.05)',
                        'display': 'flex', 'gap': '30px', 'alignItems': 'center'}, children=[
            dcc.Link(html.Button('📊 Overview Dashboard', id='nav-overview', className='nav-button',
                                 style={'padding': '10px 15px', 'backgroundColor': 'transparent', 'border': 'none',
                                        'color': COLOR_BG_DARK, 'fontWeight': 'bold', 'cursor': 'pointer'}),
                     href='/overview'),
            dcc.Link(html.Button('📋 All Students List', id='nav-all-students', className='nav-button',
                                 style={'padding': '10px 15px', 'backgroundColor': 'transparent', 'border': 'none',
                                        'color': COLOR_BG_DARK, 'fontWeight': 'bold', 'cursor': 'pointer'}),
                     href='/all-students'),

            # Notification Button (used as a simple Input for the modal callback)
            html.Button(
                f'🔔 ({notification_count})',
                id='notification-button',
                title='Red Zone Students',
                n_clicks=0,  # Added n_clicks for stability
                style={
                    'marginLeft': 'auto',
                    'fontSize': '18px',
                    'cursor': 'pointer',
                    'backgroundColor': notification_color,
                    'color': 'white',
                    'border': 'none',
                    'borderRadius': '6px',
                    'padding': '8px 15px',
                    'fontWeight': 'bold',
                    'boxShadow': '0 2px 5px rgba(0,0,0,0.2)'
                }
            ),
        ])
    ])


def get_overview_page(assigned_students, notification_count, amber_count, green_count):
    """Generates the main Overview Dashboard layout with charts and KPIs."""
    COLOR_RED = '#C62828'
    COLOR_AMBER = '#FFB300'
    COLOR_GREEN = '#2E7D32'
    COLOR_PRIMARY = '#1976D2'
    COLOR_BG_DARK = '#212121'
    CARD_STYLE = {
        'backgroundColor': 'white',
        'borderRadius': '12px',
        'boxShadow': '0 4px 12px rgba(0,0,0,0.15)',
        'padding': '20px',
        'transition': 'all 0.3s ease-in-out',
    }

    risk_counts = assigned_students['risk_band'].value_counts()

    risk_fig = go.Figure(data=[go.Pie(
        labels=risk_counts.index,
        values=risk_counts.values,
        hole=.3,
        marker_colors=[COLOR_RED, COLOR_AMBER, COLOR_GREEN],
        hoverinfo='label+percent',
        textinfo='value',
        pull=[0.05 if label == 'Red' else 0 for label in risk_counts.index]
    )])
    risk_fig.update_layout(
        title_text="Risk Distribution",
        title_x=0.5,
        margin=dict(t=30, b=0, l=0, r=0),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        height=350,
        paper_bgcolor='white'
    )

    return html.Div(style={'padding': '30px', 'maxWidth': '1400px', 'margin': 'auto'}, children=[
        # Row 1: KPI Cards
        html.Div(
            style={'display': 'grid', 'gridTemplateColumns': 'repeat(4, 1fr)', 'gap': '20px', 'marginBottom': '30px'},
            children=[
                html.Div(style={**CARD_STYLE, 'borderBottom': f'5px solid {COLOR_PRIMARY}', 'textAlign': 'center',
                                'backgroundColor': COLOR_PRIMARY, 'color': 'white'}, children=[
                    html.P("Total Students 👨‍🎓", style={'fontSize': '1.0em', 'opacity': '0.9', 'marginBottom': '5px'}),
                    html.P(f"{len(assigned_students)}", style={'fontSize': '2.8em', 'fontWeight': '900', 'margin': '0'})
                ]),
                html.Div(style={**CARD_STYLE, 'borderBottom': f'5px solid {COLOR_RED}', 'textAlign': 'center',
                                'backgroundColor': COLOR_RED, 'color': 'white'}, children=[
                    html.P("High Risk (Red Zone) 🚨",
                           style={'fontSize': '1.0em', 'opacity': '0.9', 'marginBottom': '5px'}),
                    html.P(f"{notification_count}", style={'fontSize': '2.8em', 'fontWeight': '900', 'margin': '0'})
                ]),
                html.Div(style={**CARD_STYLE, 'borderBottom': f'5px solid {COLOR_AMBER}', 'textAlign': 'center',
                                'backgroundColor': COLOR_AMBER, 'color': COLOR_BG_DARK}, children=[
                    html.P("Medium Risk (Amber) ⚠️",
                           style={'fontSize': '1.0em', 'opacity': '0.9', 'marginBottom': '5px'}),
                    html.P(f"{amber_count}", style={'fontSize': '2.8em', 'fontWeight': '900', 'margin': '0'})
                ]),
                html.Div(style={**CARD_STYLE, 'borderBottom': f'5px solid {COLOR_GREEN}', 'textAlign': 'center',
                                'backgroundColor': COLOR_GREEN, 'color': 'white'}, children=[
                    html.P("Low Risk (Green) ✅", style={'fontSize': '1.0em', 'opacity': '0.9', 'marginBottom': '5px'}),
                    html.P(f"{green_count}", style={'fontSize': '2.8em', 'fontWeight': '900', 'margin': '0'})
                ]),
            ]),

        # Row 2: Chart and Filters/Table
        html.Div(style={'display': 'grid', 'gridTemplateColumns': '4fr 6fr', 'gap': '20px', 'marginBottom': '30px'},
                 children=[
                     # Chart Card
                     html.Div(style={**CARD_STYLE, 'padding': '15px'}, children=[
                         dcc.Graph(id='risk-pie-chart', figure=risk_fig, config={'displayModeBar': False}),
                     ]),

                     # Filters and Table Preview Card
                     html.Div(style={**CARD_STYLE, 'padding': '30px 20px 20px 20px', 'display': 'flex',
                                     'flexDirection': 'column'}, children=[
                         html.H3("Filtered Student Data",
                                 style={'color': COLOR_BG_DARK, 'marginBottom': '20px', 'marginTop': '0'}),

                         # Filters
                         html.Div(style={'display': 'flex', 'gap': '20px', 'marginBottom': '20px'}, children=[
                             # Branch Filter
                             html.Div(style={'flexGrow': '1'}, children=[
                                 html.Label("Filter by Branch:",
                                            style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '5px'}),
                                 dcc.Dropdown(
                                     id='branch-filter-overview',
                                     options=[{'label': i, 'value': i} for i in assigned_students['branch'].unique()],
                                     placeholder="Select Branch(es)",
                                     multi=True,
                                     style={'borderRadius': '4px'}
                                 )
                             ]),
                             # Risk Band Filter
                             html.Div(style={'flexGrow': '1'}, children=[
                                 html.Label("Filter by Risk Band:",
                                            style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '5px'}),
                                 dcc.Dropdown(
                                     id='risk-band-filter-overview',
                                     options=[
                                         {'label': 'Red (High)', 'value': 'Red'},
                                         {'label': 'Amber (Medium)', 'value': 'Amber'},
                                         {'label': 'Green (Low)', 'value': 'Green'}
                                     ],
                                     placeholder="Select Risk Band(s)",
                                     multi=True,
                                     style={'borderRadius': '4px'}
                                 )
                             ]),
                         ]),

                         # Filtered Table Content (Preview)
                         html.Div(id='filtered-table-container')
                     ]),
                 ]),
    ])


def get_all_students_page(assigned_students):
    """Generates the dedicated page showing a comprehensive list of all students."""
    COLOR_RED = '#C62828'
    COLOR_AMBER = '#FFB300'
    COLOR_GREEN = '#2E7D32'
    COLOR_PRIMARY = '#1976D2'
    CARD_STYLE = {
        'backgroundColor': 'white',
        'borderRadius': '12px',
        'boxShadow': '0 4px 12px rgba(0,0,0,0.15)',
        'padding': '20px',
        'transition': 'all 0.3s ease-in-out',
    }

    style_data_conditional = [
        {'if': {'column_id': 'risk_band', 'filter_query': '{risk_band} contains "Red"'},
         'backgroundColor': 'rgba(198, 40, 40, 0.1)', 'color': COLOR_RED, 'fontWeight': 'bold'},
        {'if': {'column_id': 'risk_band', 'filter_query': '{risk_band} contains "Amber"'},
         'backgroundColor': 'rgba(255, 179, 0, 0.1)', 'color': COLOR_AMBER, 'fontWeight': 'bold'},
        {'if': {'column_id': 'risk_band', 'filter_query': '{risk_band} contains "Green"'},
         'backgroundColor': 'rgba(46, 125, 50, 0.1)', 'color': COLOR_GREEN, 'fontWeight': 'bold'}
    ]

    return html.Div(style={'padding': '30px', 'maxWidth': '1400px', 'margin': 'auto'}, children=[
        html.H3("Comprehensive List of Assigned Students",
                style={'color': COLOR_PRIMARY, 'marginBottom': '20px', 'borderBottom': '1px solid #e0e0e0',
                       'paddingBottom': '10px'}),
        html.Div(style={**CARD_STYLE, 'padding': '30px'}, children=[
            dash_table.DataTable(
                id='full-students-table',
                columns=[
                    {"name": "Name", "id": "name"},
                    {"name": "Student ID", "id": "student_id"},
                    {"name": "Branch", "id": "branch"},
                    {"name": "Risk Band", "id": "risk_band"},
                    {"name": "Risk Score", "id": "risk_score", "type": "numeric"},
                    {"name": "Avg Score", "id": "overall_avg_score", "type": "numeric",
                     'format': dash_table.Format.Format(precision=2, scheme=dash_table.Format.Scheme.fixed)},
                    {"name": "Attendance %", "id": "rolling_attendance_90d", "type": "numeric",
                     'format': dash_table.Format.Format(precision=2, scheme=dash_table.Format.Scheme.fixed)},
                    {"name": "Fee Status", "id": "status"},
                    {"name": "Overdue Days", "id": "overdue_days", "type": "numeric"},
                    {"name": "Risk Reasons", "id": "risk_reasons", "presentation": "markdown"}
                ],
                data=assigned_students.to_dict('records'),
                sort_action="native",
                filter_action="native",
                page_action="native",
                page_current=0,
                page_size=15,
                style_cell={'textAlign': 'left', 'padding': '12px', 'fontSize': '14px',
                            'borderBottom': '1px solid #e0e0e0', 'whiteSpace': 'normal'},
                style_header={'backgroundColor': COLOR_PRIMARY, 'color': 'white', 'fontWeight': 'bold',
                              'border': 'none', 'padding': '12px', 'borderRadius': '4px 4px 0 0'},
                style_data_conditional=style_data_conditional,
                style_table={'overflowX': 'auto', 'border': '1px solid #e0e0e0', 'borderRadius': '8px'}
            )
        ])
    ])


def get_login_layout(status_message=""):
    """Helper function to return the login page layout."""
    COLOR_PRIMARY = '#1976D2'
    COLOR_BG_DARK = '#212121'
    COLOR_RED = '#C62828'
    return html.Div(id='login-container', children=[
        html.H1("Mentor Dashboard Login 🔑",
                style={'textAlign': 'center', 'color': COLOR_PRIMARY, 'marginBottom': '25px'}),
        html.Div([
            html.Label("Login ID", style={'fontWeight': 'bold', 'color': COLOR_BG_DARK}),
            dcc.Input(id='login-input', type='text', placeholder='Enter Login ID (e.g., mentor0)',
                      style={'width': '100%', 'padding': '12px', 'border': '1px solid #ced4da', 'borderRadius': '6px'}),
        ], style={'marginBottom': '15px'}),
        html.Div([
            html.Label("Password", style={'fontWeight': 'bold', 'color': COLOR_BG_DARK}),
            dcc.Input(id='password-input', type='password', placeholder='Enter Password (password123)',
                      style={'width': '100%', 'padding': '12px', 'border': '1px solid #ced4da', 'borderRadius': '6px'}),
        ], style={'marginBottom': '30px'}),
        html.Button('Login to Dashboard', id='login-button', n_clicks=0,
                    style={'width': '100%', 'padding': '14px', 'backgroundColor': COLOR_PRIMARY, 'color': 'white',
                           'border': 'none', 'borderRadius': '6px', 'cursor': 'pointer', 'fontWeight': 'bold',
                           'fontSize': '1.1em'}),
        html.Div(id='login-status', children=status_message,
                 style={'textAlign': 'center', 'marginTop': '20px', 'color': COLOR_RED, 'fontWeight': 'bold'}),
    ], style={'width': '380px', 'margin': '100px auto', 'padding': '40px', 'border': '1px solid #e0e0e0',
              'borderRadius': '12px', 'boxShadow': '0 10px 25px rgba(0,0,0,0.15)', 'backgroundColor': 'white'})


# --- App Layout (Initial) ---
app.layout = html.Div(children=[
    # Persistent Stores
    dcc.Store(id='mentor-data-store', data=json.dumps({})),
    dcc.Store(id='login-id-store', data=None),
    dcc.Location(id='url', refresh=False),

    # Hidden components for modal logic
    html.Button(id='close-modal', n_clicks=0, style={'display': 'none'}),
    html.Div(id='notification-modal', style={'display': 'none'}),  # Will be updated by toggle_modal

    # Main content wrapper (holds login page or dashboard)
    html.Div(id='page-content-wrapper', style={'backgroundColor': '#F5F5F5', 'minHeight': '100vh'})
])


# --- Callbacks ---

@app.callback(
    # Only updates data stores and URL on successful login
    Output('mentor-data-store', 'data'),
    Output('login-id-store', 'data'),
    Output('url', 'pathname', allow_duplicate=True),
    Output('login-status', 'children'),
    Input('login-button', 'n_clicks'),
    State('login-input', 'value'),
    State('password-input', 'value'),
    State('url', 'pathname'),  # New state to prevent unnecessary redirect if already logged in
    prevent_initial_call=True
)
def login_callback(n_clicks, login_id, password, current_pathname):
    if n_clicks is None or n_clicks == 0:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    mentor_data = mentors_df[(mentors_df['login_id'] == login_id) & (mentors_df['password'] == password)]

    if not mentor_data.empty:
        mentor_id = mentor_data.iloc[0]['mentor_id']
        assigned_students = student_ledger_df[student_ledger_df['mentor_id'] == mentor_id]

        # Prepare data for JSON storage
        df_for_json = assigned_students.copy()
        df_for_json['risk_reasons'] = df_for_json['risk_reasons'].astype(str)
        student_data_json = df_for_json.to_json(date_format='iso', orient='split')

        # Success: Update stores, and redirect ONLY if not already on the overview page
        target_pathname = '/overview' if current_pathname not in ['/overview', '/all-students'] else dash.no_update

        return student_data_json, mentor_id, target_pathname, ''
    else:
        # Failure: No update to stores/URL, just update the status message
        return dash.no_update, dash.no_update, dash.no_update, '❌ Invalid login credentials.'


@app.callback(
    # Handles routing logic and renders the full page content
    Output('page-content-wrapper', 'children'),
    Output('url', 'pathname', allow_duplicate=True),
    Input('url', 'pathname'),
    State('login-id-store', 'data'),
    State('mentor-data-store', 'data'),
    # FIX: Change to 'initial_duplicate' to satisfy Dash's rule for allow_duplicate output
    prevent_initial_call='initial_duplicate'
)
def route_callback(pathname, mentor_id, student_data_json):
    # 1. AUTHENTICATION & INITIAL CHECK
    if not mentor_id or student_data_json == json.dumps({}) or student_data_json is None:
        # If user is trying to access a restricted page, redirect to login
        if pathname not in ['/', '/login']:
            return get_login_layout(), '/'
        return get_login_layout(), dash.no_update

    # 2. DATA LOAD
    try:
        assigned_students = pd.read_json(student_data_json, orient='split')
        if assigned_students.empty:
            return get_login_layout(f"Welcome Mentor {mentor_id}, but you have no students assigned."), dash.no_update
    except Exception:
        # If JSON parsing fails (e.g., bad session data) -> force logout/login
        return get_login_layout('Session data corrupted. Please log in again.'), '/'

    # 3. KPI CALCULATIONS
    red_zone_students = assigned_students[assigned_students['risk_band'].str.contains('Red')]
    amber_zone_students = assigned_students[assigned_students['risk_band'].str.contains('Amber')]
    green_zone_students = assigned_students[assigned_students['risk_band'].str.contains('Green')]
    notification_count = len(red_zone_students)

    navbar = get_navbar(mentor_id, notification_count)

    # 4. PAGE SELECTION
    if pathname == '/overview' or pathname == '/':
        content = get_overview_page(assigned_students, notification_count, len(amber_zone_students),
                                    len(green_zone_students))
    elif pathname == '/all-students':
        content = get_all_students_page(assigned_students)
    else:
        # Redirect to overview if an invalid path is hit while logged in
        return html.Div(), '/overview'

    # 5. FINAL LAYOUT COMPOSITION
    return html.Div([
        navbar,
        content
    ], style={'padding': '0', 'backgroundColor': COLOR_BG_LIGHT, 'minHeight': '100vh'}), dash.no_update


@app.callback(
    # Modal logic must be handled separately for stability
    Output('notification-modal', 'children'),
    Output('notification-modal', 'style'),
    Input('notification-button', 'n_clicks'),
    Input('close-modal', 'n_clicks'),
    State('mentor-data-store', 'data'),
    prevent_initial_call=True
)
def toggle_modal(open_clicks, close_clicks, student_data_json):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # Default style is hidden
    style_copy = {
        'display': 'none',
        'position': 'fixed', 'zIndex': '1001', 'left': '0', 'top': '0',
        'width': '100%', 'height': '100%', 'overflow': 'auto',
        'backgroundColor': 'rgba(0,0,0,0.5)'
    }

    # 1. Determine visibility
    if button_id == 'notification-button':
        style_copy['display'] = 'block'
    elif button_id == 'close-modal':
        style_copy['display'] = 'none'

    # 2. Generate content (must be generated regardless of visibility change)
    if student_data_json and student_data_json != json.dumps({}):
        try:
            assigned_students = pd.read_json(student_data_json, orient='split')
            red_zone_students = assigned_students[assigned_students['risk_band'].str.contains('Red')]
        except Exception:
            red_zone_students = pd.DataFrame()
    else:
        red_zone_students = pd.DataFrame()

    modal_content = html.Div(style={
        'backgroundColor': 'white', 'margin': '10% auto', 'padding': '30px', 'borderRadius': '8px', 'width': '80%',
        'max-width': '1000px', 'boxShadow': '0 10px 30px rgba(0,0,0,0.3)'
    }, children=[
        html.Span('✖️', id='close-modal', n_clicks=0,
                  style={'float': 'right', 'fontSize': '28px', 'cursor': 'pointer', 'color': COLOR_BG_DARK}),
        html.H3('🚨 Red Zone Student Alerts',
                style={'color': COLOR_RED, 'borderBottom': f'2px solid #e0e0e0', 'paddingBottom': '10px',
                       'marginBottom': '20px'}),
        dash_table.DataTable(
            id='red-zone-table',
            columns=[
                {"name": "Student Name", "id": "name"},
                {"name": "Branch", "id": "branch"},
                {"name": "Risk Score", "id": "risk_score"},
                {"name": "Reasons", "id": "risk_reasons"}
            ],
            data=red_zone_students.to_dict('records'),
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': COLOR_BG_LIGHT}],
            style_header={'backgroundColor': COLOR_RED, 'color': 'white', 'fontWeight': 'bold'},
            style_cell={'textAlign': 'left', 'whiteSpace': 'normal', 'minWidth': '120px', 'width': '120px',
                        'maxWidth': '300px'},
        )
    ])

    return modal_content, style_copy


@app.callback(
    # Filter callback is now much simpler and robust
    Output('filtered-table-container', 'children'),
    Input('branch-filter-overview', 'value'),
    Input('risk-band-filter-overview', 'value'),
    State('mentor-data-store', 'data'),
    prevent_initial_call=False
)
def update_table(selected_branches, selected_risk_bands, student_data_json):
    # CRASH FIX: Check for empty/default data
    if student_data_json is None or student_data_json == json.dumps({}):
        # Returns an empty container element instead of crashing
        return html.Div(id='empty-table-container', children=[
            html.P("Log in to view student data.", style={'color': COLOR_RED})
        ])

    try:
        assigned_students = pd.read_json(student_data_json, orient='split')
        df_filtered = assigned_students.copy()
    except Exception:
        return html.P("Error loading student data.", style={'color': COLOR_RED})

    # Apply filters
    if selected_branches:
        df_filtered = df_filtered[df_filtered['branch'].isin(selected_branches)]

    if selected_risk_bands:
        df_filtered = df_filtered[df_filtered['risk_band'].isin(selected_risk_bands)]

    # Conditional Formatting
    style_data_conditional = [
        {'if': {'column_id': 'risk_band', 'filter_query': '{risk_band} contains "Red"'},
         'backgroundColor': 'rgba(198, 40, 40, 0.1)', 'color': COLOR_RED, 'fontWeight': 'bold'},
        {'if': {'column_id': 'risk_band', 'filter_query': '{risk_band} contains "Amber"'},
         'backgroundColor': 'rgba(255, 179, 0, 0.1)', 'color': COLOR_AMBER, 'fontWeight': 'bold'},
        {'if': {'column_id': 'risk_band', 'filter_query': '{risk_band} contains "Green"'},
         'backgroundColor': 'rgba(46, 125, 50, 0.1)', 'color': COLOR_GREEN, 'fontWeight': 'bold'}
    ]

    return dash_table.DataTable(
        id='table-preview',
        columns=[
            {"name": "Name", "id": "name"},
            {"name": "Branch", "id": "branch"},
            {"name": "Risk Band", "id": "risk_band"},
            {"name": "Risk Score", "id": "risk_score", "type": "numeric"}
        ],
        data=df_filtered.head(5).to_dict('records'),
        sort_action="native",
        page_action="none",
        style_cell={'textAlign': 'left', 'padding': '8px', 'fontSize': '12px'},
        style_header={'backgroundColor': COLOR_PRIMARY, 'color': 'white', 'fontWeight': 'bold'},
        style_data_conditional=style_data_conditional,
        style_table={'overflowX': 'auto', 'border': '1px solid #e0e0e0', 'borderRadius': '4px'}
    )


if __name__ == '__main__':
    print("Running data pipeline...")
    student_ledger_df, mentors_df = run_data_pipeline()
    print("Data pipeline complete. Starting Dash server...")
    app.run(debug=True)
