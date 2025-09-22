import dash
from dash import dcc, html, Input, Output, State
import pandas as pd
import plotly.express as px
import sys

# Load pre-processed data
try:
    student_ledger_df = pd.read_csv('student_ledger.csv')
    mentors_df = pd.read_csv('mentors.csv')
except FileNotFoundError:
    print("Error: 'student_ledger.csv' or 'mentors.csv' not found. Please run process_data.py first.")
    sys.exit(1)

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'])
server = app.server  # This is needed for deployment

# App layout (Login page first)
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


# Callback for login authentication
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

            # Create the main dashboard layout
            dashboard_layout = html.Div(children=[
                html.H1(f"Mentor Dashboard", style={'textAlign': 'center'}),
                html.P(f"Showing students for Mentor ID: {mentor_id}"),
                html.Div([
                    html.H3("Assigned Students"),
                    # Use a Dash DataTable to display student info
                    dash.dash_table.DataTable(
                        id='table',
                        columns=[{"name": i, "id": i} for i in assigned_students[
                            ['name', 'branch', 'risk_band', 'risk_score', 'overall_avg_score']].columns],
                        data=assigned_students.to_dict('records'),
                        sort_action="native",
                        style_cell={'textAlign': 'left'},
                        style_header={
                            'backgroundColor': 'rgb(230, 230, 230)',
                            'fontWeight': 'bold'
                        },
                    ),
                ], style={'padding': '20px'}),
                html.Div(id='student-details-container',
                         style={'padding': '20px', 'borderTop': '1px solid #ccc', 'marginTop': '20px'})
            ])
            return dashboard_layout, ''
        else:
            return dash.no_update, '❌ Invalid login credentials.'
    return dash.no_update, ''


if __name__ == '__main__':
    app.run(debug=True)