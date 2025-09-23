# Student Risk Analyzer

## Project Overview

The **Student Risk Analyzer** is a comprehensive, spreadsheet-first, low-cost early-warning system designed to help students and mentors proactively manage academic and financial risks. The platform automates the entire process, from data ingestion to risk analysis and interactive visualization, with a strong focus on transparency and user-friendly interfaces.

## Documentation ### Technical Approach: Student Risk Analyzer

The technical approach for the **Student Risk Analyzer** is built on a modular, Python-based architecture designed for efficiency, transparency, and ease of maintenance. The system is composed of several key components that work together to deliver a comprehensive early-warning solution.

***

### Data Pipeline and Processing
The core of the system is a robust data pipeline implemented using the **Pandas** library. It follows a "spreadsheet-first" philosophy, ingesting data from multiple CSV files. These disparate data sources are then processed and merged into a single, comprehensive `student_ledger` DataFrame. This approach ensures a single source of truth for all student data, simplifying subsequent analysis. The pipeline is designed to be run as a separate process, separating data-heavy operations from the user-facing application for improved performance.

***

### Rule-Based Risk Engine
The risk analysis is driven by a **transparent, rule-based scoring engine**. This engine applies a series of conditional logic checks (`if/elif/else`) on key performance indicators (KPIs) such as attendance percentage, average test scores, and overdue fee days. For each rule violation, a student is assigned points, which are summed to produce a final risk score. This score is then mapped to a clear risk band (Green, Amber, or Red), and the specific reasons for the risk are captured. This approach ensures that the risk assessment is easily understood and trusted by educators and students.

***

### Web Application and Interface
The user interface is developed using the **Dash** framework, which is built on top of Flask and Plotly. This allows for the creation of interactive, analytical web dashboards entirely in Python, eliminating the need for separate front-end development in JavaScript or HTML. The application features a secure login system for both students and mentors, with dynamic content rendering based on user credentials. Key features like the notification bell for at-risk students and the counseling chatbot are integrated as `html` components and managed through Dash callbacks, providing a responsive and modern user experience. 

## Key Features

  * **Consolidated Dashboard**: The platform features a single, consolidated dashboard for each student, presenting all key information in one place. This includes personal details, academic performance, financial status, and risk analysis.
  * **Automated Data Pipeline**: The system processes raw data from CSV files (students, attendance, assessments, and fees) and fuses it into a single, comprehensive student ledger.
  * **Transparent & Rule-Based Risk Scoring**: A sophisticated scoring engine calculates a risk score and assigns a risk band (Green/Amber/Red) based on configurable rules. The specific reasons for each student's risk level are clearly articulated, helping mentors and students understand the root causes.
  * **Interactive Web Dashboards**:
      * **Student Dashboard (`app_student.py`)**: A web-based application where students can securely log in to view their personalized dashboard. This includes their average scores, attendance percentage, fees status, and risk profile.
      * **Mentor Dashboard (`app_mentor.py`)**: A web-based application for mentors to access a dashboard of all their assigned students. This dashboard provides a consolidated view of student data and an alerting system.
  * **Notification and Alert System**: The mentor dashboard includes a notification bell that alerts mentors to students in the "Red Zone." Clicking the bell opens a pop-up modal with a list of at-risk students, ensuring no student's critical status is missed.
  * **Integrated Counseling Chatbot**: The student dashboard features a floating chatbot button in the bottom-right corner. Clicking this button takes the student to an AI counseling service for immediate support, promoting a proactive approach to student well-being.

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

# Resolving issues with this project, here's a step-by-step guide to troubleshooting the **Student Risk Analyzer** platform.

### 1\. File Not Found Errors

**Symptom:** You see a `FileNotFoundError` when running a script like `app_mentor.py` or `app_student.py`. This typically occurs with `student_ledger.csv`, `mentors.csv`, or other data files.
**Solution:** The data files are generated by `university_data_generator.py`. You'll need to run this script at least once before you try to run any other part of the application.

```bash
python university_data_generator.py
```

This command will create all the necessary CSV files in your project directory.

-----

### 2\. Module Not Found Errors

**Symptom:** Your code editor or terminal displays `No module named 'dash'` or `No module named 'pandas'`.
**Solution:** This indicates that you haven't installed the required Python libraries. You need to install all of them using `pip`.

```bash
pip install pandas numpy dash plotly Flask psutil Faker
```

-----

### 3\. Server-Related Errors

**Symptom:** The error `app.run_server has been replaced by app.run` or `OSError: [WinError 10038]` appears.
**Solution:** These are common issues with older versions of Dash or conflicts with how processes are managed.

  * **For `app.run_server`:** This method is deprecated. Replace `app.run_server(debug=True)` with the new method, `app.run(debug=True)`.
  * **For `OSError`:** This error often occurs when trying to terminate a process that no longer exists. Ensure you have the `psutil` library installed (`pip install psutil`) and use the `app_manager.py` script to safely start and stop applications. The `app_manager.py` script is designed to handle these errors and provides a more robust way to control your programs.

-----

### 4\. Layout and Display Issues

**Symptom:** The web dashboard layout is broken, with columns expanding infinitely or content overflowing the page boundaries.
**Solution:** This is a CSS issue with how the Flexbox container handles long strings of text. The fix involves explicitly setting CSS properties to control wrapping and prevent overflow. The provided `app_mentor.py` and `app_student.py` scripts have been updated to include these fixes by using `overflow-wrap: break-word` and ensuring appropriate `max-width` and `min-width` properties on the containers.

-----

### 5\. Running the Correct Application

**Symptom:** You're trying to log in as a student, but the web page shows "Mentor Dashboard Login" and rejects your credentials.
**Solution:** You are running the wrong script. The login page title is a clear indicator of which application is active. Stop the current server (press `Ctrl + C` in the terminal) and run the correct script.

  * To run the **Mentor** dashboard, use: `python app_mentor.py`
  * To run the **Student** dashboard, use: `python app_student.py`
  * The `app_manager.py` script is the best way to handle this, as it gives you clear buttons for each application.

By following these troubleshooting steps, you should be able to resolve any issues and get the **Student Risk Analyzer** platform running smoothly.

<img width="1586" height="814" alt="image" src="https://github.com/user-attachments/assets/367a8c65-864e-4e31-9ebf-82fdb59fac99" />

