# AI Hackathon Website (School Students)

A simple, working website for a school AI Hackathon under the theme **"Meri Samasya, Mera Samadhan" (My Problem, My Solution)**.

Students solve a real problem from their own home, school, or village. Judges reward thinking about the problem over technical polish.

## Features

- **Public pages**
  - Home page with theme, tracks/example problems, and judging parameters
  - Student registration (solo or group) with a unique auto-generated **registration number**
- **Admin login**
  - Dashboard with registration stats
  - View all registrations (team details, members, problem/solution)
  - View evaluation results (average total and per-parameter scores across judges)
  - Manage/create judge accounts
- **Judge panel login**
  - View assigned/available registrations and evaluation status
  - Evaluate each registration on **five parameters** (1–10 each) with optional comments
  - Submit or update evaluations

## Tracks included

- Safe and healthy communities
- Farming and local livelihoods
- Climate and environment
- Better learning at school
- Inclusion and girls’ safety
- AI for good (optional, Class 8-9)

## Judging parameters (5)

Each parameter is scored from **1 to 10** (max total 50 per judge):

1. **Problem Understanding** – clarity and depth of understanding of the real-life problem (Meri Samasya)
2. **Solution Relevance & Impact** – how well the solution addresses the problem and benefits the community (Mera Samadhan)
3. **Creativity & Innovation** – originality and thoughtful approach
4. **Feasibility & Implementation** – practicality and realistic implementation/demonstration
5. **Presentation & Explanation** – clarity of communication and ability to discuss limitations or improvements

## Registration rules (as implemented)

- **Type:** Solo or Group
- **Group size:** **any number** of members (group registrations must include at least one additional member besides the leader; there is no upper limit)
- **Registration number:** auto-generated unique number on successful submission (format: `AIH-<year>-<sequence>`, e.g. `AIH-2026-0001`)
- Captures track, project/solution title and description, school, leader/student details, and optional group member details/contact info

## Tech stack

- Python 3 + Flask
- SQLite database (`instance/hackathon.db`, auto-created on first run)
- HTML/CSS (Jinja templates)

## Setup and run (Windows / PowerShell)

1. **Install dependencies** (from the project folder):

   ```powershell
   python -m pip install -r requirements.txt
   ```

2. **Run the app**:

   ```powershell
   python app.py
   ```

3. Open in your browser: **http://localhost:5000**

The database and default accounts are created automatically on first run.

## Default demo accounts

> **Change these credentials before using in a real event.**

- **Admin**
  - Username: `admin`
  - Password: `admin123`
- **Judge (demo)**
  - Username: `judge`
  - Password: `judge123`

Admins can create additional judge accounts from **Admin Dashboard → Manage Judges**.

## Project structure

- `app.py` – Flask application, routes, database initialization, and configuration
- `requirements.txt` – Python dependencies
- `templates/` – HTML templates (home, registration, admin, judge, evaluation)
- `static/style.css` – styles
- `instance/hackathon.db` – SQLite database (created at runtime)

## Notes / customization

- Judging parameters and theme/track text are defined as constants near the top of `app.py` for easy customization. Group size is unlimited (solo or group with any number of members).
- Set a secure `SECRET_KEY` environment variable for production-like use.
- For a real deployment, use a production WSGI server and secure credential management.
