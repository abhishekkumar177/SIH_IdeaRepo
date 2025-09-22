import pandas as pd
import joblib
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from sklearn.preprocessing import label_binarize
import numpy as np

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a unique, strong key

# Load the data and model once when the app starts
try:
    student_ledger = pd.read_csv('student_ledger.csv')
    model = joblib.load('risk_model.joblib')
    print("Model and student data loaded successfully.")
except FileNotFoundError:
    print("Error: Required files not found. Please run 'main.py' first.")
    exit()

# Define the risk band mapping
risk_band_map = {0: 'Green', 1: 'Amber', 2: 'Red'}


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Mentor login route.
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # Use a simple hardcoded check. For a real application, use a database.
        if username == 'mentor' and password == 'password123':
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')


@app.route('/logout')
def logout():
    """
    Log out the user by clearing the session.
    """
    session.pop('logged_in', None)
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    """
    Main dashboard route.
    Only accessible after a successful login.
    """
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    # Filter for at-risk students (Amber or Red)
    at_risk_students = student_ledger[
        (student_ledger['risk_band'] == 'Amber') | (student_ledger['risk_band'] == 'Red')
        ]

    # Convert filtered DataFrame to a list of dictionaries for the template
    students = at_risk_students.to_dict('records')
    return render_template('index.html', students=students)


@app.route('/predict', methods=['POST'])
def predict():
    """
    API endpoint to handle risk prediction from the front-end form.
    This route can be accessed by the logged-in mentor.
    """
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.json

        # Extract features from the request
        attendance = float(data.get('attendance'))
        avg_score = float(data.get('avg_score'))
        attempts_points = float(data.get('attempts_points'))
        overdue_points = float(data.get('overdue_points'))
        trend_bonus = float(data.get('trend_bonus'))

        # --- Apply Scoring Rules (mirrors main.py) ---
        risk_score = 0
        risk_reasons = []

        if 70 <= attendance < 85:
            risk_score += 10
            risk_reasons.append(f"Attendance {attendance:.0f}% (70-85% band)")
        elif 50 <= attendance < 70:
            risk_score += 25
            risk_reasons.append(f"Attendance {attendance:.0f}% (50-70% band)")
        elif attendance < 50:
            risk_score += 50
            risk_reasons.append(f"Attendance {attendance:.0f}% (<50% band)")

        if 50 <= avg_score < 60:
            risk_score += 10
            risk_reasons.append(f"Avg Score {avg_score:.0f}% (50-60% band)")
        elif 35 <= avg_score < 50:
            risk_score += 25
            risk_reasons.append(f"Avg Score {avg_score:.0f}% (35-50% band)")
        elif avg_score < 35:
            risk_score += 50
            risk_reasons.append(f"Avg Score {avg_score:.0f}% (<35% band)")

        if attempts_points == 15:
            risk_score += 15
            risk_reasons.append("Attempts exhausted (n-1 limit)")
        elif attempts_points == 35:
            risk_score += 35
            risk_reasons.append("Attempts exhausted (at limit)")

        if overdue_points == 10:
            risk_score += 10
            risk_reasons.append("Fees overdue (1-30 days)")
        elif overdue_points == 25:
            risk_score += 25
            risk_reasons.append("Fees overdue (31-90 days)")
        elif overdue_points == 40:
            risk_score += 40
            risk_reasons.append("Fees overdue (>90 days)")

        if trend_bonus > 0:
            risk_score += trend_bonus
            risk_reasons.append("Significant downward trend in scores")

        # Create DataFrame for prediction
        features = pd.DataFrame([[attendance, avg_score, risk_score]],
                                columns=['rolling_attendance_4w', 'avg_test_score_overall', 'risk_score'])

        # Predict the risk band
        predicted_risk = model.predict(features)[0]
        predicted_band = risk_band_map[predicted_risk]

        # Prepare the response
        response = {
            'predicted_band': predicted_band,
            'risk_score': risk_score,
            'risk_reasons': '; '.join(risk_reasons) if risk_reasons else 'No Risk'
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': str(e)}), 400


if __name__ == '__main__':
    # You must create a 'templates' folder in your project directory
    # and place 'index.html' inside it.
    app.run(debug=True)