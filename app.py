import pandas as pd
import joblib
from flask import Flask, render_template, request, jsonify
from sklearn.preprocessing import label_binarize
import numpy as np

app = Flask(__name__)

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


@app.route('/')
def index():
    """
    Main dashboard route.
    Renders a template showing the student data table.
    """
    # Convert DataFrame to a list of dictionaries for easier handling in the template
    students = student_ledger.to_dict('records')
    return render_template('index.html', students=students)


@app.route('/predict', methods=['POST'])
def predict():
    """
    API endpoint to handle risk prediction from the front-end form.
    """
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
            reasons.append(f"Attendance {attendance:.0f}% (50-70% band)")
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