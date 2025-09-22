import pandas as pd
import numpy as np
import sys
from datetime import date, timedelta
from faker import Faker

# --- Configuration for Risk Scoring ---
NUM_ASSESSMENTS_PER_SUBJECT = 3
PASSING_ATTEMPTS_LIMIT = 3  # This is a new variable based on your rule. Assuming passing attempts limit is same as total attempts.
SUBJECTS = ['Mathematics-I', 'Physics', 'Programming']
BRANCHES = ['Computer Science', 'Electrical', 'Mechanical', 'Civil', 'Electronics']


# --- Helper Functions (copied from risk_calculator.py) ---
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
    # This assumes a column 'max_attempts_overall' exists in the ledger.
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

    # Downward trend bonus is not implemented here as it requires a different data structure.

    return risk_score, risk_reasons


def map_risk_band(score):
    if score >= 100:
        return 'Red (High)'
    elif score >= 40:
        return 'Amber (Medium)'
    else:
        return 'Green (Low)'


# --- Main Application Functions ---
def authenticate_mentor(login_id, password, mentors_df):
    """Authenticates the mentor using their login ID and password."""
    mentor_data = mentors_df[(mentors_df['login_id'] == login_id) & (mentors_df['password'] == password)]
    if not mentor_data.empty:
        return mentor_data.iloc[0]['mentor_id']
    return None


def display_mentor_dashboard(mentor_id, students_df):
    """Displays the list of students and their details for the logged-in mentor."""
    assigned_students = students_df[students_df['mentor_id'] == mentor_id]

    if assigned_students.empty:
        print("\n😔 You have no students assigned to you.")
        return

    print(f"\n✅ Logged in as Mentor with ID: {mentor_id}. Here are your assigned students:")
    print("-" * 50)

    for index, student in assigned_students.iterrows():
        print(f"👤 **Student Name**: {student['name']} (ID: {student['student_id']})")
        print(f"   - **Branch**: {student['branch']}")
        print(f"   - **Guardian Contact**: {student['guardian_contact']}")

        # Display academic and financial data
        print(f"   - **Overall Avg Score**: {student.get('overall_avg_score', 'N/A'):.2f}%")
        print(f"   - **Attendance (90d)**: {student.get('rolling_attendance_90d', 'N/A'):.2f}%")

        # Display subject-specific scores
        for subject in SUBJECTS:
            score_col = f'avg_score_{subject}'
            score = student.get(score_col)
            if pd.notna(score):
                print(f"   - **{subject} Avg Score**: {score:.2f}%")
            else:
                print(f"   - **{subject} Avg Score**: N/A")

        # Display fees and risk data
        print(f"   - **Fees Status**: {student.get('status', 'N/A')}")
        print(f"   - **Overdue Days**: {student.get('overdue_days', 'N/A')}")

        if pd.notna(student.get('risk_band')):
            print(f"   - **Risk Band**: {student['risk_band']}")
            print(f"   - **Risk Score**: {student['risk_score']:.2f}")
            print(f"   - **Risk Reasons**: {student['risk_reasons']}")
        else:
            print("   - **Risk Data**: Not yet calculated. This should not happen.")

        print("-" * 50)


def main():
    """Main function to run the console-based dashboard."""
    try:
        # Load raw data from CSV files
        mentors_df = pd.read_csv('mentors.csv')
        students_df = pd.read_csv('students.csv')
        attendance_df = pd.read_csv('attendance.csv')
        assessments_df = pd.read_csv('assessments.csv')
        fees_df = pd.read_csv('fees.csv')
    except FileNotFoundError:
        print("Error: Required CSV files not found. Please run university_data_generator.py first.")
        sys.exit(1)

    print("=== Student Risk Dashboard (Console) ===")
    print("Step 1: Processing raw data and calculating risk scores...")

    # --- Step 2: FUSE DATA & CALCULATE RISK (from risk_calculator.py) ---
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
    print("Please log in with your mentor credentials.")

    login_attempts = 3
    while login_attempts > 0:
        login_id = input("Enter your Login ID (e.g., 'mentor0'): ").strip()
        password = input("Enter your Password: ").strip()

        mentor_id = authenticate_mentor(login_id, password, mentors_df)

        if mentor_id is not None:
            display_mentor_dashboard(mentor_id, student_ledger)
            break
        else:
            login_attempts -= 1
            print(f"❌ Invalid login credentials. You have {login_attempts} attempts left.")
            if login_attempts == 0:
                print("🔒 Maximum login attempts reached. Exiting.")
                sys.exit(1)


if __name__ == "__main__":
    main()