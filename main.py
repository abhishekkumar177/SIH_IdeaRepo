import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, accuracy_score, precision_score, recall_score, f1_score, roc_curve, auc
from sklearn.preprocessing import label_binarize
from itertools import cycle
from datetime import date, timedelta
from faker import Faker
import random

# Set up Faker for realistic data
fake = Faker()

# Configuration
NUM_STUDENTS = 1000
START_DATE = date(2025, 8, 1)
END_DATE = date(2025, 9, 15)
PASSING_ATTEMPTS_LIMIT = 3

# --- Generate Raw Data ---
# This part is included here to make the script self-contained.
print("Generating raw data tables...")
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

attendance = []
date_range = [START_DATE + timedelta(days=x) for x in range((END_DATE - START_DATE).days + 1)]
for student_id in range(1, NUM_STUDENTS + 1):
    for d in date_range:
        status = random.choices(['Present', 'Absent', 'Late'], weights=[0.95, 0.03, 0.02], k=1)[0]
        if student_id % 10 == 0:
            status = random.choices(['Present', 'Absent', 'Late'], weights=[0.7, 0.2, 0.1], k=1)[0]
        attendance.append({
            'student_id': student_id,
            'date': d,
            'status': status
        })
attendance_df = pd.DataFrame(attendance)

assessments = []
assessment_id = 1
for student_id in range(1, NUM_STUDENTS + 1):
    for subject in ['Math', 'Science', 'English']:
        num_assessments = random.randint(3, 5)
        for i in range(num_assessments):
            score = np.random.normal(loc=80, scale=15)
            if student_id % 7 == 0:
                score -= i * 5
            score = max(0, min(100, int(score)))
            if student_id % 5 == 0:
                score = np.random.normal(loc=50, scale=10)
            score = max(0, min(100, int(score)))
            attempts = random.randint(1, 4)
            if score < 60:
                attempts = random.randint(2, 5)
            assessments.append({
                'student_id': student_id,
                'assessment_id': assessment_id,
                'date': fake.date_between(start_date=START_DATE, end_date=END_DATE),
                'subject': subject,
                'score': score,
                'max_score': 100,
                'attempts': min(attempts, 6),
                'passing_attempts_limit': PASSING_ATTEMPTS_LIMIT
            })
            assessment_id += 1
assessments_df = pd.DataFrame(assessments)

fees = []
for student_id in range(1, NUM_STUDENTS + 1):
    status = random.choices(['Paid', 'Partial', 'Overdue'], weights=[0.85, 0.1, 0.05], k=1)[0]
    last_payment_date = None
    if status == 'Paid':
        start_date_range = date.today() - timedelta(days=90)
        end_date_range = date.today() - timedelta(days=7)
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
print("Data generation complete.")

# --- Data Merging & Derivations ---
student_ledger = students_df.copy()
student_ledger['risk_score'] = 0
student_ledger['risk_reasons'] = [[] for _ in range(len(student_ledger))]

# 2. Process Attendance Data
attendance_df['date'] = pd.to_datetime(attendance_df['date'])
attendance_summary = attendance_df.groupby('student_id').apply(
    lambda x: 100 * (1 - (x['status'] == 'Absent').mean())
).reset_index(name='rolling_attendance_4w')
student_ledger = pd.merge(student_ledger, attendance_summary, on='student_id', how='left')


def apply_attendance_points(row):
    points = 0
    reasons = []
    if 70 <= row['rolling_attendance_4w'] < 85:
        points = 10
        reasons.append(f"Attendance {row['rolling_attendance_4w']:.0f}% (70-85% band)")
    elif 50 <= row['rolling_attendance_4w'] < 70:
        points = 25
        reasons.append(f"Attendance {row['rolling_attendance_4w']:.0f}% (50-70% band)")
    elif row['rolling_attendance_4w'] < 50:
        points = 50
        reasons.append(f"Attendance {row['rolling_attendance_4w']:.0f}% (<50% band)")
    return points, reasons


points_reasons = student_ledger.apply(apply_attendance_points, axis=1)
student_ledger['risk_score'] += points_reasons.apply(lambda x: x[0])
for idx, reasons in points_reasons.apply(lambda x: x[1]).items():
    student_ledger.at[idx, 'risk_reasons'].extend(reasons)

# 3. Process Assessments Data
assessments_df['date'] = pd.to_datetime(assessments_df['date'])
assessments_df['passing_attempts_limit'] = 3


def apply_assessment_rules(student_group):
    risk_score_points = 0
    reasons = []
    avg_score = student_group['score'].mean()

    if 50 <= avg_score < 60:
        risk_score_points += 10
        reasons.append(f"Avg Score {avg_score:.0f}% (50-60% band)")
    elif 35 <= avg_score < 50:
        risk_score_points += 25
        reasons.append(f"Avg Score {avg_score:.0f}% (35-50% band)")
    elif avg_score < 35:
        risk_score_points += 50
        reasons.append(f"Avg Score {avg_score:.0f}% (<35% band)")

    exhausted_subjects = student_group[student_group['attempts'] >= student_group['passing_attempts_limit']]
    if not exhausted_subjects.empty:
        risk_score_points += 35
        for subj in exhausted_subjects['subject'].unique():
            reasons.append(f"Attempts exhausted for {subj}")

    student_group = student_group.sort_values(by='date', ascending=False)
    if len(student_group) >= 3:
        latest_scores = student_group.iloc[0:3]['score']
        score_decline = latest_scores.iloc[2] - latest_scores.iloc[0]
        if score_decline > 10:
            risk_score_points += 15
            reasons.append("Significant downward trend in scores")

    return pd.Series(
        {'assessment_score': risk_score_points, 'assessment_reasons': reasons, 'avg_test_score_overall': avg_score})


assessment_summary = assessments_df.groupby('student_id').apply(apply_assessment_rules).reset_index()
student_ledger = pd.merge(student_ledger, assessment_summary, on='student_id', how='left')

student_ledger['risk_score'] += student_ledger['assessment_score'].fillna(0)
for idx, reasons in student_ledger['assessment_reasons'].fillna('').items():
    student_ledger.at[idx, 'risk_reasons'].extend(reasons)

# 4. Process Fees Data
fees_df['due_date'] = pd.to_datetime(fees_df['due_date'])
fees_df['overdue_days'] = (pd.to_datetime('today') - fees_df['due_date']).dt.days
fees_df['overdue_days'] = fees_df['overdue_days'].apply(lambda x: x if x > 0 else 0)
student_ledger = pd.merge(student_ledger, fees_df[['student_id', 'status', 'overdue_days']], on='student_id',
                          how='left')
student_ledger.rename(columns={'status': 'fee_status'}, inplace=True)


def apply_fee_points(row):
    points = 0
    reasons = []
    if row['fee_status'] == 'Overdue':
        if 1 <= row['overdue_days'] <= 30:
            points = 10
            reasons.append(f"Fees overdue (1-30 days)")
        elif 31 <= row['overdue_days'] <= 90:
            points = 25
            reasons.append(f"Fees overdue (31-90 days)")
        elif row['overdue_days'] > 90:
            points = 40
            reasons.append(f"Fees overdue (>90 days)")
    return points, reasons


points_reasons = student_ledger.apply(apply_fee_points, axis=1)
student_ledger['risk_score'] += points_reasons.apply(lambda x: x[0])
for idx, reasons in points_reasons.apply(lambda x: x[1]).items():
    student_ledger.at[idx, 'risk_reasons'].extend(reasons)

# 5. Finalize Risk Bands and Reasons
student_ledger['risk_band'] = pd.cut(student_ledger['risk_score'],
                                     bins=[-1, 19, 49, student_ledger['risk_score'].max()],
                                     labels=['Green', 'Amber', 'Red'],
                                     right=True)
student_ledger.loc[student_ledger['risk_band'].isnull(), 'risk_band'] = 'Green'
student_ledger['risk_band'] = student_ledger['risk_band'].astype('category')
student_ledger['risk_reasons'] = student_ledger['risk_reasons'].apply(lambda x: "; ".join(x) if x else "No Risk")

student_ledger.to_csv('student_ledger.csv', index=False)
print("\nFinal student ledger saved to student_ledger.csv")
print("\nFinal Student Ledger (First 5 rows):")
print(student_ledger.head())

# --- Model Training & Evaluation ---
# FIX: Fill NaN values with 0 to prevent KeyErrors
X = student_ledger[['rolling_attendance_4w', 'avg_test_score_overall', 'risk_score']].fillna(0)
y = student_ledger['risk_band']
y = y.map({'Green': 0, 'Amber': 1, 'Red': 2})
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

model = LogisticRegression(max_iter=1000)
model.fit(X_train, y_train)

joblib.dump(model, 'risk_model.joblib')
print("\nTrained model saved as 'risk_model.joblib'")

y_pred = model.predict(X_test)
y_pred_proba = model.predict_proba(X_test)

print("\nModel Evaluation Metrics:")
print(f"Accuracy: {accuracy_score(y_test, y_pred):.2f}")
print(f"Precision: {precision_score(y_test, y_pred, average='weighted'):.2f}")
print(f"Recall: {recall_score(y_test, y_pred, average='weighted'):.2f}")
print(f"F1-Score: {f1_score(y_test, y_pred, average='weighted'):.2f}")

# --- Visualizing Model Viability ---
cm = confusion_matrix(y_test, y_pred)
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=['Green', 'Amber', 'Red'],
            yticklabels=['Green', 'Amber', 'Red'])
plt.title('Confusion Matrix')
plt.xlabel('Predicted Label')
plt.ylabel('True Label')
plt.show()

y_test_bin = label_binarize(y_test, classes=[0, 1, 2])
n_classes = y_test_bin.shape[1]
fpr = dict()
tpr = dict()
roc_auc = dict()
for i in range(n_classes):
    fpr[i], tpr[i], _ = roc_curve(y_test_bin[:, i], y_pred_proba[:, i])
    roc_auc[i] = auc(fpr[i], tpr[i])
plt.figure(figsize=(10, 8))
colors = cycle(['blue', 'red', 'green'])
for i, color in zip(range(n_classes), colors):
    plt.plot(fpr[i], tpr[i], color=color, lw=2,
             label=f'ROC curve of class {i} (area = {roc_auc[i]:.2f})')
plt.plot([0, 1], [0, 1], 'k--', lw=2)
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('Receiver Operating Characteristic (ROC) Curves')
plt.legend(loc="lower right")
plt.show()

# --- Analysis & Progress Graphs ---
student_ledger['mentor_id'] = student_ledger['mentor_id'].astype(int)
class_analysis = student_ledger.groupby('class').agg(
    avg_attendance=('rolling_attendance_4w', 'mean'),
    avg_score=('avg_test_score_overall', 'mean'),
    at_risk_count=('risk_band', lambda x: (x == 'Red').sum())
).reset_index().sort_values(by='avg_score', ascending=False)
mentor_analysis = student_ledger.groupby('mentor_id').agg(
    avg_attendance=('rolling_attendance_4w', 'mean'),
    avg_score=('avg_test_score_overall', 'mean'),
    at_risk_count=('risk_band', lambda x: (x == 'Red').sum())
).reset_index().sort_values(by='avg_score', ascending=False)

plt.figure(figsize=(10, 6))
sns.barplot(x='class', y='at_risk_count', data=class_analysis, color='steelblue')
plt.title('Number of At-Risk Students by Class')
plt.xlabel('Class')
plt.ylabel('Number of At-Risk Students (Red Band)')
plt.show()

plt.figure(figsize=(12, 7))
sns.barplot(x='mentor_id', y='at_risk_count', data=mentor_analysis, color='coral')
plt.title('Number of At-Risk Students by Mentor')
plt.xlabel('Mentor ID')
plt.ylabel('Number of At-Risk Students (Red Band)')
plt.show()