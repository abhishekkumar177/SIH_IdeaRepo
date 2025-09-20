# Student Risk Analyzer

<img width="1901" height="935" alt="image" src="https://github.com/user-attachments/assets/30a5c151-ee7e-425e-aa2e-175540e01796" />

<img width="1901" height="935" alt="Screenshot 2025-09-20 140114" src="https://github.com/user-attachments/assets/3d866328-c1e0-4e90-a994-d3170077b56e" />

Student Risk Analyzer

This project is a prototype for a Student Risk Analysis system. It uses a data-driven approach to identify students who may be at risk of academic or financial issues, allowing mentors and administrators to provide timely, targeted support.

The system is built on a simple machine learning model that analyzes key student data points to generate a risk score and a corresponding risk band (Green, Amber, or Red). The project includes a data generation pipeline, a machine learning model, and a Flask-based web dashboard for data visualization and manual risk prediction.

Features

Automated Risk Scoring: A rule-based system calculates a numerical risk score for each student by analyzing their attendance, test scores, exhausted attempts, and fee payment status.

Risk Band Classification: The system categorizes students into three risk bands—Green (Low), Amber (Medium), and Red (High)—based on their calculated risk score.

Data Generation Pipeline: A Python script generates a large, realistic dummy dataset that mimics real-world student records from multiple sources (attendance, assessments, fees, etc.).

Machine Learning Model: A Logistic Regression model is trained on the generated data to predict the risk band of a student.

Interactive Web Dashboard: A Flask-based web application provides a user-friendly interface to view the student risk ledger and manually predict a student's risk band using an input form.

Model Performance Visualization: The project generates key plots like a Confusion Matrix and ROC Curve to demonstrate the model's viability and performance.

Prerequisites

To run this project, you will need to have Python and a few libraries installed.

Python: Versions 3.7 or higher.

Pip: The Python package installer.

Use the following command to install all the required libraries:

pip install pandas numpy scikit-learn matplotlib seaborn Flask joblib Faker


Getting Started

Follow these steps to set up and run the project locally.

1. Project Structure

Ensure your project directory is organized as follows:

/Your_Project_Folder
|-- app.py
|-- main.py
|-- /templates
|   |-- index.html


2. Run the Data & Model Pipeline

First, you need to generate the data and train the model. This script will create the necessary .csv and .joblib files.

python main.py


This will generate the following files in your project folder:

students.csv

attendance.csv

assessments.csv

fees.csv

student_ledger.csv

risk_model.joblib

It will also display several performance plots in separate windows and print analysis reports in the terminal.

3. Run the Flask Web Application

Once the data and model files are ready, start the Flask server to launch the web dashboard.

python app.py


After the server starts, open your web browser and navigate to the local address provided (usually http://127.0.0.1:5000).

How to Use the Dashboard

The web dashboard is split into two main sections:

Student Risk Ledger: A table showing the calculated risk score, risk band, and risk reasons for each student in the dataset.

Manual Risk Prediction: An interactive form that allows you to enter hypothetical student data. After entering the values, click the "Predict Risk" button to see the model's real-time prediction and the reasons for its output.

Code Overview

main.py: This is the core data processing and machine learning pipeline. It generates the raw data, merges it, applies the risk scoring rules, trains the model, and saves the final outputs.

app.py: This file defines the Flask web server. It handles loading the pre-trained model and data, rendering the main dashboard, and providing an API endpoint for the prediction form.

templates/index.html: The front-end of the application, built with HTML and Tailwind CSS. It displays the data in a table and provides the interactive form for manual predictions.

Future Improvements

Enhanced Prediction: Migrate the prediction logic to be fully handled by the machine learning model instead of relying on the rule-based risk score as a feature.

Real-time Data Integration: Connect the system to a live database or an API to fetch and process real-time student data.

Notification System: Implement automated email or SMS notifications for mentors and guardians when a student is flagged as a high risk.

Multi-User Authentication: Add a user login system to provide secure, role-based access for different users (e.g., mentors, administrators).
