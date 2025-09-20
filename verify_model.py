import pandas as pd
import numpy as np
import joblib
from datetime import date, timedelta


def verify_student_risk():
    """
    A command-line tool to manually verify a student's risk band using the trained model.
    """
    try:
        # Load the saved model
        model = joblib.load('risk_model.joblib')
        print("Model loaded successfully.")
    except FileNotFoundError:
        print("Error: Required file 'risk_model.joblib' not found.")
        print("Please run 'main.py' first to generate this file.")
        return

    # Create a mapping from numerical labels back to risk bands
    risk_band_map = {0: 'Green', 1: 'Amber', 2: 'Red'}

    print("\n--- Model Verification Tool ---")
    print("Enter student data to see the predicted risk band.")
    print("---------------------------------")

    while True:
        try:
            print("\nEnter student data to predict risk (or 'q' to quit):")

            attendance = float(input("Rolling Attendance % (e.g., 72.5): "))
            avg_score = float(input("Average Test Score % (e.g., 55.0): "))

            # Simplified manual input for complex rules
            attempts_points = float(input("Attempts Points (0, 15, or 35): "))
            overdue_points = float(input("Overdue Fee Points (0, 10, 25, or 40): "))
            trend_bonus = float(input("Downward Trend Bonus (0 or 15): "))

            if attendance == 'q':
                break

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

            # Create a DataFrame for the prediction
            new_data = pd.DataFrame([[attendance, avg_score, risk_score]],
                                    columns=['rolling_attendance_4w', 'avg_test_score_overall', 'risk_score'])

            # Make the prediction
            predicted_risk = model.predict(new_data)[0]
            predicted_band = risk_band_map[predicted_risk]

            print("\n--- Analysis & Prediction ---")
            print(f"Total Calculated Risk Score: {risk_score}")
            print(f"Risk Reasons: {', '.join(risk_reasons) if risk_reasons else 'No Risk'}")
            print(f"\nModel Prediction: The student is at a {predicted_band} risk.")

        except ValueError:
            print("Invalid input. Please enter a number for each field.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    verify_student_risk()
