# Student Risk Analyzer

## Project Overview

The **Student Risk Analyzer** is a comprehensive, spreadsheet-first, low-cost early-warning system designed to help students and mentors proactively manage academic and financial risks. The platform automates the entire process, from data ingestion to risk analysis and interactive visualization, with a strong focus on transparency and user-friendly interfaces.

## Key Features

  * **Consolidated Dashboard**: The platform features a single, consolidated dashboard for each student, presenting all key information in one place. This includes personal details, academic performance, financial status, and risk analysis.
  * **Automated Data Pipeline**: The system processes raw data from CSV files (students, attendance, assessments, and fees) and fuses it into a single, comprehensive student ledger.
  * **Transparent & Rule-Based Risk Scoring**: A sophisticated scoring engine calculates a risk score and assigns a risk band (Green/Amber/Red) based on configurable rules. The specific reasons for each student's risk level are clearly articulated, helping mentors and students understand the root causes.
  * **Interactive Web Dashboards**:
      * **Student Dashboard (`app_student.py`)**: A web-based application where students can securely log in to view their personalized dashboard. This includes their average scores, attendance percentage, fees status, and risk profile.
      * **Mentor Dashboard (`app_mentor.py`)**: A web-based application for mentors to access a dashboard of all their assigned students. This dashboard provides a consolidated view of student data and an alerting system.
  * **Notification and Alert System**: The mentor dashboard includes a notification bell that alerts mentors to students in the "Red Zone." Clicking the bell opens a pop-up modal with a list of at-risk students, ensuring no student's critical status is missed.
  * **Integrated Counseling Chatbot**: The student dashboard features a floating chatbot button in the bottom-right corner. Clicking this button takes the student to an AI counseling service for immediate support, promoting a proactive approach to student well-being.
  * **Centralized Management**: The `app_manager.py` script provides a simple web interface to run and terminate the dashboard applications, simplifying the process of starting and stopping the various components of the platform.

## Data Model

The system uses the following CSV files as data sources:

  * `students.csv`: Contains unique student IDs, names, branches, guardian contacts, and assigned mentor IDs.
  * `attendance.csv`: Records daily attendance status.
  * `assessments.csv`: Stores test scores and attempts for different subjects.
  * `fees.csv`: Tracks fee payment status.
  * `mentors.csv`: Stores login credentials and names for mentors.

## How to Run

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/abhishekkumar177/sih_idearepo.git
    cd sih_idearepo
    ```
2.  **Install Dependencies**: Make sure you have Python installed. Then, install all necessary libraries:
    ```bash
    pip install pandas numpy dash plotly Flask psutil Faker
    ```
3.  **Generate Data**: First, run the `university_data_generator.py` script to create the necessary raw data files.
    ```bash
    python university_data_generator.py
    ```
4.  **Manage Applications**: To run the web dashboards, use the `app_manager.py` script.
    ```bash
    python app_manager.py
    ```
    Open your browser and navigate to `http://127.0.0.1:5000` to access the manager dashboard. From there, you can start `app_mentor.py` or `app_student.py`.

## Login Credentials

  * **Students**:
      * **Username**: `student_id` (e.g., `2000`, `2001`, etc.)
      * **Password**: `password123`
  * **Mentors**:
      * **Username**: `login_id` (e.g., `mentor0`, `mentor1`, etc.)
      * **Password**: `password123`
