import pandas as pd
import numpy as np

# --- Load Raw Data ---
try:
    students_df = pd.read_csv('students.csv')
    attendance_df = pd.read_csv('attendance.csv')
    assessments_df = pd.read_csv('assessments.csv')
    fees_df = pd.read_csv('fees.csv')
    print("All data tables loaded successfully.")
except FileNotFoundError:
    print("Error: One or more data files not found. Please run 'generate_data.py' first.")
    exit()

# --- Data Merging & Derivations ---
# 1. Start with the students table as the base
student_ledger = students_df.copy()

# 2. Merge Attendance Data
attendance_df['date'] = pd.to_datetime(attendance_df['date'])
attendance_df['is_absent'] = (attendance_df['status'] == 'Absent').astype(int)
attendance_summary = attendance_df.groupby('student_id')['is_absent'].mean().reset_index()
attendance_summary['rolling_attendance_4w'] = 100 * (1 - attendance_summary['is_absent'])
student_ledger = pd.merge(student_ledger, attendance_summary[['student_id', 'rolling_attendance_4w']], on='student_id', how='left')

# 3. Merge Assessments Data
assessments_summary = assessments_df.groupby('student_id')['score'].mean().reset_index()
assessments_summary.rename(columns={'score': 'avg_test_score_overall'}, inplace=True)
student_ledger = pd.merge(student_ledger, assessments_summary, on='student_id', how='left')

# 4. Merge Fees Data
fees_df['due_date'] = pd.to_datetime(fees_df['due_date'])
fees_df['overdue_fee_days'] = (pd.to_datetime('today') - fees_df['due_date']).dt.days
fees_df['overdue_fee_days'] = fees_df['overdue_fee_days'].apply(lambda x: x if x > 0 else 0)
student_ledger = pd.merge(student_ledger, fees_df[['student_id', 'status', 'overdue_fee_days']], on='student_id', how='left')
student_ledger.rename(columns={'status': 'fee_status'}, inplace=True)

# 5. Compute Risk Score & Band
student_ledger['risk_score'] = 0
student_ledger['risk_reasons'] = ""

# Define risk factors (logic can be refined)
student_ledger.loc[student_ledger['rolling_attendance_4w'] < 75, 'risk_score'] += 30
student_ledger.loc[student_ledger['avg_test_score_overall'] < 50, 'risk_score'] += 40
student_ledger.loc[student_ledger['fee_status'] == 'Overdue', 'risk_score'] += 30

# Define risk reasons
student_ledger.loc[student_ledger['rolling_attendance_4w'] < 75, 'risk_reasons'] = student_ledger['risk_reasons'] + " Low_Attendance"
student_ledger.loc[student_ledger['avg_test_score_overall'] < 50, 'risk_reasons'] = student_ledger['risk_reasons'] + " Low_Test_Scores"
student_ledger.loc[student_ledger['fee_status'] == 'Overdue', 'risk_reasons'] = student_ledger['risk_reasons'] + " Overdue_Fees"

# Clean up risk reasons string
student_ledger['risk_reasons'] = student_ledger['risk_reasons'].str.strip()
student_ledger.loc[student_ledger['risk_reasons'] == '', 'risk_reasons'] = 'No Risk'

# Assign risk band based on score
student_ledger['risk_band'] = pd.cut(student_ledger['risk_score'],
                                    bins=[-1, 20, 70, 101],
                                    labels=['Green', 'Amber', 'Red'],
                                    right=False)

# --- Final Output ---
print("\nFinal Student Ledger (First 5 rows):")
print(student_ledger.head())

# Save the final merged ledger to a new CSV file
student_ledger.to_csv('student_ledger.csv', index=False)
print("\nFinal student ledger saved to student_ledger.csv")