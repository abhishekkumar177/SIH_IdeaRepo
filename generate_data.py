import pandas as pd
import numpy as np
import random
from faker import Faker
from datetime import date, timedelta

# Set up Faker for realistic data
fake = Faker()

# Configuration
NUM_STUDENTS = 1000
START_DATE = date(2025, 8, 1)
END_DATE = date(2025, 9, 15)

# --- Students Table ---
students = []
for i in range(1, NUM_STUDENTS + 1):
    students.append({
        'student_id': i,
        'name': fake.name(),
        'class': random.choice(['10A', '10B', '11A', '11B']),
        'guardian_contact': fake.email(),
        'mentor_id': random.randint(101, 120)
    })
students_df = pd.DataFrame(students)
students_df.to_csv('students.csv', index=False)
print("Generated students.csv")

# --- Attendance Table ---
attendance = []
date_range = [START_DATE + timedelta(days=x) for x in range((END_DATE - START_DATE).days + 1)]
for student_id in range(1, NUM_STUDENTS + 1):
    for d in date_range:
        status = random.choices(['Present', 'Absent', 'Late'], weights=[0.95, 0.03, 0.02], k=1)[0]
        if student_id % 10 == 0:  # Simulate a few at-risk students with low attendance
            status = random.choices(['Present', 'Absent', 'Late'], weights=[0.7, 0.2, 0.1], k=1)[0]
        attendance.append({
            'student_id': student_id,
            'date': d,
            'status': status
        })
attendance_df = pd.DataFrame(attendance)
attendance_df.to_csv('attendance.csv', index=False)
print("Generated attendance.csv")

# --- Assessments Table ---
assessments = []
assessment_id = 1
for student_id in range(1, NUM_STUDENTS + 1):
    for subject in ['Math', 'Science', 'English']:
        for _ in range(random.randint(1, 3)):  # 1-3 assessments per student per subject
            score = np.random.normal(loc=80, scale=15)
            if student_id % 5 == 0:  # Simulate a few students with low scores
                score = np.random.normal(loc=50, scale=10)
            score = max(0, min(100, int(score)))  # Clamp score between 0 and 100
            assessments.append({
                'student_id': student_id,
                'assessment_id': assessment_id,
                'date': fake.date_between(start_date=START_DATE, end_date=END_DATE),
                'subject': subject,
                'score': score,
                'max_score': 100,
                'attempts': random.randint(1, 2)
            })
            assessment_id += 1
assessments_df = pd.DataFrame(assessments)
assessments_df.to_csv('assessments.csv', index=False)
print("Generated assessments.csv")

# --- Fees Table ---
fees = []
for student_id in range(1, NUM_STUDENTS + 1):
    status = random.choices(['Paid', 'Partial', 'Overdue'], weights=[0.85, 0.1, 0.05], k=1)[0]
    last_payment_date = None
    if status == 'Paid':
        # FIX: Explicitly define the date range to avoid the ValueError
        start_date_range = date.today() - timedelta(days=90)  # ~3 months ago
        end_date_range = date.today() - timedelta(days=7)    # ~1 week ago
        last_payment_date = fake.date_between(start_date=start_date_range, end_date=end_date_range)
    elif status == 'Partial':
        start_date_range = date.today() - timedelta(days=90)
        end_date_range = date.today() - timedelta(days=7)
        last_payment_date = fake.date_between(start_date=start_date_range, end_date=end_date_range)

    fees.append({
        'student_id': student_id,
        'due_date': fake.date_between(start_date='-6m', end_date='-1m'),
        'amount_due': 50000,
        'amount_paid': 50000 if status == 'Paid' else (30000 if status == 'Partial' else 0),
        'status': status,
        'last_payment_date': last_payment_date
    })
fees_df = pd.DataFrame(fees)
fees_df.to_csv('fees.csv', index=False)
print("Generated fees.csv")