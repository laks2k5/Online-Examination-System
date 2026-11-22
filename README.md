# Online Examination System

A web-based application that lets students take exams online instead of on paper.
Questions, users and results are stored in a **MySQL** database, the backend logic is
written in **Python (Flask)**, and the frontend uses **HTML, CSS and JavaScript**.

## Features
- User authentication (register / login / logout, hashed passwords)
- Question management (admin can create exams, add and delete questions - CRUD)
- Online quiz with countdown timer and auto-submit
- Automatic result evaluation with pass/fail and answer review
- Result history for every student

## Technologies
| Technology | Purpose |
|------------|---------|
| HTML | Webpage structure |
| CSS | Styling and layout |
| JavaScript | Exam countdown timer |
| Python (Flask) | Application logic |
| MySQL | Stores users, questions, answers, results |

## How It Works
1. **Login** - student enters username and password.
2. **Question display** - exam questions are shown.
3. **Answer selection** - student selects options.
4. **Submission** - answers are sent to the backend.
5. **Result evaluation** - answers are compared with correct options and the score is displayed.

## Database Design
`users` -> `results` <- `exams` -> `questions`; `answers` links each result to each question.
See `database/online_exam.sql` for the complete schema, sample data, a `leaderboard` view and sample queries.

## Setup
```bash
git clone https://github.com/<your-username>/Online-Examination-System.git
cd Online-Examination-System

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create the database
mysql -u root -p < database/online_exam.sql

# Configure DB password (or edit DB_CONFIG in app.py)
export DB_PASSWORD=your_mysql_password   # Windows: set DB_PASSWORD=your_mysql_password

python app.py
```
Open http://127.0.0.1:5000

### Create an admin
Register a user, then run in MySQL:
```sql
USE online_exam;
UPDATE users SET role='admin' WHERE username='your_username';
```

## Project Structure
```
Online-Examination-System/
├── app.py
├── requirements.txt
├── templates/   (login, register, dashboard, exam, result, admin)
├── static/      (css, js, images)
├── database/    (online_exam.sql)
└── screenshots/
```

## Screenshots
| Login | Dashboard |
|-------|-----------|
| ![Login](screenshots/login.png) | ![Dashboard](screenshots/dashboard.png) |

| Exam | Result |
|------|--------|
| ![Exam](screenshots/exam.png) | ![Result](screenshots/result.png) |

## Future Improvements
- Randomized questions, question bank by difficulty
- Email verification and password reset
- Export results to PDF/Excel
