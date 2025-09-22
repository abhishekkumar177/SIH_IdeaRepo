import pandas as pd
import numpy as np
from datetime import date, timedelta
from faker import Faker

# Initialize Faker for generating realistic names
fake = Faker('en_IN') # Using Indian locale for relevant names

# --- Configuration ---
NUM_STUDENTS = 1000
NUM_MENTORS = 50
DAYS_OF_ATTENDANCE = 90
NUM_ASSESSMENTS_PER_SUBJECT = 3 # 3 tests per subject
SUBJECTS = ['Mathematics-I', 'Physics', 'Programming']
BRANCHES = ['Computer Science', 'Electrical', 'Mechanical', 'Civil', 'Electronics']

# --- 1. Mentors Data ---
mentor_ids = [1000 + i for i in range(NUM_MENTORS)]
mentor_data = {
    'mentor_id': mentor_ids,
    'login_id': [f'mentor{i}' for i in range(NUM_MENTORS)],
    'password': ['password123'] * NUM_MENTORS,
    'name': [fake.name() for _ in range(NUM_MENTORS)]
}
mentors_df = pd.DataFrame(mentor_data)
mentors_df.to_csv('mentors.csv', index=False)
print("Generated mentors.csv")

# --- 2. Students Data ---
student_ids = [2000 + i for i in range(NUM_STUDENTS)]
student_assignment = np.repeat(mentor_ids, NUM_STUDENTS // NUM_MENTORS)
np.random.shuffle(student_assignment)

students_data = {
    'student_id': student_ids,
    'name': [fake.name() for _ in range(NUM_STUDENTS)],
    'branch': np.random.choice(BRANCHES, NUM_STUDENTS),
    'guardian_contact': [f'987654{i:04d}' for i in range(NUM_STUDENTS)],
    'mentor_id': student_assignment
}
students_df = pd.DataFrame(students_data)
students_df.to_csv('students.csv', index=False)
print("Generated students.csv")

# --- 3. Attendance Data ---
attendance_records = []
dates = [date.today() - timedelta(days=i) for i in range(DAYS_OF_ATTENDANCE)]
for student_id in student_ids:
    # Simulate a few students (10%) with attendance issues
    if np.random.rand() < 0.1:
        statuses = np.random.choice(['Present', 'Absent', 'Late'], p=[0.75, 0.2, 0.05], size=DAYS_OF_ATTENDANCE)
    else:
        statuses = np.random.choice(['Present', 'Absent', 'Late'], p=[0.95, 0.04, 0.01], size=DAYS_OF_ATTENDANCE)

    for i, d in enumerate(dates):
        attendance_records.append([student_id, d, statuses[i]])

attendance_df = pd.DataFrame(attendance_records, columns=['student_id', 'date', 'status'])
attendance_df.to_csv('attendance.csv', index=False)
print("Generated attendance.csv")

# --- 4. Assessments Data ---
assessments_records = []
for student_id in student_ids:
    for subject in SUBJECTS:
        # 10% of students have poor performance
        if np.random.rand() < 0.1:
            scores = np.random.uniform(20, 50, NUM_ASSESSMENTS_PER_SUBJECT)
        # 5% of students have declining scores
        elif np.random.rand() < 0.05:
            scores = np.random.uniform(70, 90, 1).tolist() + np.random.uniform(55, 75, 1).tolist() + np.random.uniform(30, 50, 1).tolist()
        else:
            scores = np.random.uniform(60, 95, NUM_ASSESSMENTS_PER_SUBJECT)

        for i in range(NUM_ASSESSMENTS_PER_SUBJECT):
            assessments_records.append([
                student_id,
                f'{subject.split("-")[0].strip()}_{i+1}',
                date.today() - timedelta(days=np.random.randint(1, 90)),
                subject,
                round(scores[i], 2),
                100,
                i+1
            ])

assessments_df = pd.DataFrame(assessments_records, columns=['student_id', 'assessment_id', 'date', 'subject', 'score', 'max_score', 'attempts'])
assessments_df.to_csv('assessments.csv', index=False)
print("Generated assessments.csv")

# --- 5. Fees Data ---
fees_records = []
for student_id in student_ids:
    amount_due = 150000 # Example annual fee
    status = 'Paid'
    amount_paid = amount_due
    due_date = date.today() - timedelta(days=np.random.randint(1, 60))
    last_payment_date = due_date

    # Simulate 7% of students with overdue fees
    if np.random.rand() < 0.07:
        status = np.random.choice(['Overdue', 'Partial'])
        amount_paid = np.random.randint(10000, amount_due - 10000) if status == 'Partial' else 0
        due_date = date.today() - timedelta(days=np.random.randint(31, 180))
        last_payment_date = pd.NaT

    fees_records.append([student_id, due_date, amount_due, amount_paid, status, last_payment_date])

fees_df = pd.DataFrame(fees_records, columns=['student_id', 'due_date', 'amount_due', 'amount_paid', 'status', 'last_payment_date'])
fees_df.to_csv('fees.csv', index=False)
print("Generated fees.csv")

# --- 6. Create Student Ledger (Derived) ---
# Start with students data
student_ledger_df = students_df.copy()

# Add a derived attendance percentage
attendance_summary = attendance_df.groupby('student_id')['status'].apply(
    lambda x: (x == 'Present').sum() / len(x) * 100 if len(x) > 0 else 0
).reset_index(name='rolling_attendance_90d')
student_ledger_df = student_ledger_df.merge(attendance_summary, on='student_id', how='left')

# Add derived test score averages and attempts per subject
assessments_summary = assessments_df.groupby(['student_id', 'subject']).agg(
    avg_subject_score=('score', 'mean'),
    attempts=('attempts', 'max')
).reset_index()

# Pivot to have subjects as columns
assessments_summary_pivot = assessments_summary.pivot(index='student_id', columns='subject', values='avg_subject_score').reset_index()
assessments_summary_pivot.columns = [f'avg_score_{col}' for col in assessments_summary_pivot.columns]
assessments_summary_pivot = assessments_summary_pivot.rename(columns={'avg_score_student_id': 'student_id'})
student_ledger_df = student_ledger_df.merge(assessments_summary_pivot, on='student_id', how='left')

# Calculate overall average test score
overall_avg_scores = assessments_df.groupby('student_id')['score'].mean().reset_index(name='overall_avg_score')
student_ledger_df = student_ledger_df.merge(overall_avg_scores, on='student_id', how='left')

# Add fee status info
# Fix 1: Convert 'due_date' column to datetime objects
fees_df['due_date'] = pd.to_datetime(fees_df['due_date'])
# Fix 2: Convert date.today() to a Pandas Timestamp object for calculation
current_date = pd.to_datetime(date.today())

fees_df['overdue_days'] = (current_date - fees_df['due_date']).dt.days.fillna(0).astype(int)
fees_summary = fees_df[['student_id', 'amount_due', 'amount_paid', 'status', 'overdue_days']]
student_ledger_df = student_ledger_df.merge(fees_summary, on='student_id', how='left')

# Save the final ledger
student_ledger_df.to_csv('student_ledger.csv', index=False)
print("Generated student_ledger.csv")