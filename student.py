import pandas as pd
import numpy as np
import sys
from datetime import date, timedelta

# --- Configuration for Risk Scoring ---
NUM_ASSESSMENTS_PER_SUBJECT = 3
PASSING_ATTEMPTS_LIMIT = 3
SUBJECTS = ['Mathematics-I', 'Physics', 'Programming']


# --- Helper Functions (Risk Calculation) ---
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


# --- Main Application Functions ---
def authenticate_student(student_id_input, password, students_df):
    """Authenticates the student using their ID and password."""
    # The password for all students is 'password123'
    if password == 'password123':
        try:
            student_id = int(student_id_input)
            student_data = students_df[students_df['student_id'] == student_id]
            if not student_data.empty:
                return student_id
        except ValueError:
            return None
    return None


def display_student_dashboard(student_id, students_df):
    """Displays the details for the logged-in student."""
    student_data = students_df[students_df['student_id'] == student_id].iloc[0]

    print(f"\n✅ Logged in as: {student_data['name']}. Here is your dashboard:")
    print("-" * 50)

    # Display student's personal information
    print(f"👤 **Your Name**: {student_data['name']} (ID: {student_data['student_id']})")
    print(f"   - **Branch**: {student_data['branch']}")
    print(f"   - **Guardian Contact**: {student_data['guardian_contact']}")

    # Display academic and financial data
    print(f"   - **Overall Avg Score**: {student_data.get('overall_avg_score', 'N/A'):.2f}%")
    print(f"   - **Attendance (90d)**: {student_data.get('rolling_attendance_90d', 'N/A'):.2f}%")

    # Display subject-specific scores
    for subject in SUBJECTS:
        score_col = f'avg_score_{subject}'
        score = student_data.get(score_col)
        if pd.notna(score):
            print(f"   - **{subject} Avg Score**: {score:.2f}%")
        else:
            print(f"   - **{subject} Avg Score**: N/A")

    # Display fees and risk data
    print(f"   - **Fees Status**: {student_data.get('status', 'N/A')}")
    print(f"   - **Overdue Days**: {student_data.get('overdue_days', 'N/A')}")

    if pd.notna(student_data.get('risk_band')):
        print(f"   - **Risk Band**: {student_data['risk_band']}")
        print(f"   - **Risk Score**: {student_data['risk_score']:.2f}")
        print(f"   - **Risk Reasons**: {student_data['risk_reasons']}")
    else:
        print("   - **Risk Data**: Not yet calculated. This should not happen.")

    print("-" * 50)


def main():
    """Main function to run the console-based dashboard."""
    try:
        # Load raw data from CSV files
        students_df = pd.read_csv('students.csv')
        attendance_df = pd.read_csv('attendance.csv')
        assessments_df = pd.read_csv('assessments.csv')
        fees_df = pd.read_csv('fees.csv')
    except FileNotFoundError:
        print("Error: Required CSV files not found. Please run university_data_generator.py first.")
        sys.exit(1)

    print("=== Student Risk Dashboard (Console) ===")
    print("Step 1: Processing raw data and calculating risk scores...")

    # --- Step 2: FUSE DATA & CALCULATE RISK ---
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

    # --- Step 3: START DASHBOARD ---
    print("Processing complete. Ready to serve the dashboard.")
    print("Please log in with your student credentials.")

    login_attempts = 3
    while login_attempts > 0:
        student_id_input = input("Enter your Student ID (e.g., '2000'): ").strip()
        password = input("Enter your Password: ").strip()

        student_id = authenticate_student(student_id_input, password, student_ledger)

        if student_id is not None:
            display_student_dashboard(student_id, student_ledger)
            break
        else:
            login_attempts -= 1
            print(f"❌ Invalid login credentials. You have {login_attempts} attempts left.")
            if login_attempts == 0:
                print("🔒 Maximum login attempts reached. Exiting.")
                sys.exit(1)


if __name__ == "__main__":
    main()