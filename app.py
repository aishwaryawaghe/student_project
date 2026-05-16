from flask import Flask, render_template, request, redirect, session
import pandas as pd
import pickle
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns

app = Flask(__name__)
app.secret_key = "studentproject"

# ---------------- LOAD MODEL ----------------

with open("model.pkl", "rb") as f:
    model = pickle.load(f)

# ---------------- DATABASE ----------------

def init_db():

    conn = sqlite3.connect('students.db')
    c = conn.cursor()

    # USERS TABLE

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT
        )
    ''')

    # PREDICTIONS TABLE

    c.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            attendance REAL,
            study REAL,
            internal_marks REAL,
            assignment_marks REAL,
            sleep_hours REAL,
            predicted_marks REAL
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# ---------------- HOME PAGE ----------------

@app.route('/')
def home():
    return render_template('index.html')

# ---------------- REGISTER ----------------

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('students.db')
        c = conn.cursor()

        c.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password)
        )

        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('register.html')

# ---------------- LOGIN ----------------

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('students.db')
        c = conn.cursor()

        c.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )

        user = c.fetchone()

        conn.close()

        if user:
            session['username'] = username
            return redirect('/dashboard')

        else:
            return render_template(
                'login.html',
                error="Invalid Username or Password"
            )

    return render_template('login.html')

# ---------------- DASHBOARD ----------------

@app.route('/dashboard')
def dashboard():

    if 'username' in session:

        return render_template(
            'dashboard.html',
            username=session['username']
        )

    return redirect('/login')

# ---------------- LOGOUT ----------------

@app.route('/logout')
def logout():

    session.pop('username', None)

    return redirect('/')

# ---------------- PREDICTION ----------------

@app.route('/predict', methods=['POST'])
def predict():

    try:

        attendance = float(request.form['attendance'])
        study = float(request.form['study'])
        internal = float(request.form['internal'])
        assignment = float(request.form['assignment'])
        sleep = float(request.form['sleep'])

        # ---------------- VALIDATION ----------------

        if attendance < 0 or attendance > 100:
            return render_template(
                'dashboard.html',
                username=session['username'],
                prediction_text="Invalid Attendance"
            )

        if study < 0 or study > 12:
            return render_template(
                'dashboard.html',
                username=session['username'],
                prediction_text="Invalid Study Hours"
            )

        if sleep < 0 or sleep > 12:
            return render_template(
                'dashboard.html',
                username=session['username'],
                prediction_text="Invalid Sleep Hours"
            )

        # ---------------- INPUT DATAFRAME ----------------

        input_data = pd.DataFrame(
            [[attendance, study, internal, assignment, sleep]],
            columns=[
                'Attendance',
                'Study_Hours',
                'Internal_Marks',
                'Assignments',
                'Sleep_Hours'
            ]
        )

        # ---------------- MACHINE LEARNING PREDICTION ----------------

        prediction = model.predict(input_data)

        predicted_marks = round(prediction[0], 2)

        # ---------------- SMART AI PERFORMANCE LOGIC ----------------

        if internal <= 5 and assignment <= 5:
            predicted_marks = predicted_marks - 40

        elif attendance >= 90 and study <= 2:
            predicted_marks = predicted_marks - 25

        elif internal <= 10:
            predicted_marks = predicted_marks - 20

        elif assignment <= 5:
            predicted_marks = predicted_marks - 15

        elif study >= 8 and internal >= 20 and assignment >= 15:
            predicted_marks = predicted_marks + 10

        elif attendance < 50:
            predicted_marks = predicted_marks - 20

        elif sleep >= 9 and study <= 2:
            predicted_marks = predicted_marks - 10

        elif attendance >= 80 and study >= 5 and internal >= 15:
            predicted_marks = predicted_marks + 5

        # ---------------- LIMIT RANGE ----------------

        if predicted_marks > 100:
            predicted_marks = 100

        if predicted_marks < 0:
            predicted_marks = 0

        # ---------------- RECOMMENDATION SYSTEM ----------------

        recommendation = ""

        if predicted_marks >= 85:
            recommendation = "✅ Excellent Performance"

        elif predicted_marks >= 70:
            recommendation = "👍 Good Performance"

        elif predicted_marks >= 50:
            recommendation = "⚠ Average Performance. Improve study hours and assignments"

        else:
            recommendation = "❌ Low Performance. Improve attendance, study hours, internal marks and assignments"

        # ---------------- SAVE INTO DATABASE ----------------

        conn = sqlite3.connect('students.db')
        c = conn.cursor()

        c.execute('''
            INSERT INTO predictions (
                username,
                attendance,
                study,
                internal_marks,
                assignment_marks,
                sleep_hours,
                predicted_marks
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            session['username'],
            attendance,
            study,
            internal,
            assignment,
            sleep,
            predicted_marks
        ))

        conn.commit()
        conn.close()

        return render_template(
            'dashboard.html',
            username=session['username'],
            prediction_text=f"Predicted Marks: {predicted_marks}",
            recommendation=recommendation
        )

    except Exception as e:
        return str(e)

# ---------------- HISTORY ----------------

@app.route('/history')
def history():

    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect('students.db')

    c = conn.cursor()

    c.execute('''
        SELECT id,
               attendance,
               study,
               internal_marks,
               assignment_marks,
               sleep_hours,
               predicted_marks
        FROM predictions
        WHERE username=?
    ''', (session['username'],))

    data = c.fetchall()

    conn.close()

    return render_template('history.html', data=data)

# ---------------- DELETE HISTORY ----------------

@app.route('/delete/<int:id>')
def delete(id):

    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect('students.db')
    c = conn.cursor()

    c.execute(
        "DELETE FROM predictions WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect('/history')

# ---------------- ANALYTICS ----------------

@app.route('/analytics')
def analytics():

    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect('students.db')

    query = """
        SELECT attendance, predicted_marks
        FROM predictions
        WHERE username=?
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=(session['username'],)
    )

    conn.close()

    # CREATE GRAPH

    plt.figure(figsize=(6,4))

    sns.scatterplot(
        x=df['attendance'],
        y=df['predicted_marks']
    )

    plt.title("Attendance vs Predicted Marks")

    graph_path = "static/graphs/graph.png"

    plt.savefig(graph_path)

    plt.close()

    return render_template(
        'analytics.html',
        graph=graph_path
    )

# ---------------- STUDENT REPORT ----------------

@app.route('/report')
def report():

    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect('students.db')
    c = conn.cursor()

    c.execute('''
        SELECT attendance,
               study,
               internal_marks,
               assignment_marks,
               sleep_hours,
               predicted_marks
        FROM predictions
        WHERE username=?
        ORDER BY id DESC
        LIMIT 1
    ''', (session['username'],))

    data = c.fetchone()

    conn.close()

    if data:

        attendance = data[0]
        study = data[1]
        internal = data[2]
        assignment = data[3]
        sleep = data[4]
        marks = data[5]

        # PERFORMANCE STATUS

        if marks >= 85:
            status = "Excellent"

        elif marks >= 70:
            status = "Good"

        elif marks >= 50:
            status = "Average"

        else:
            status = "Low"

        return render_template(
            'report.html',
            attendance=attendance,
            study=study,
            internal=internal,
            assignment=assignment,
            sleep=sleep,
            marks=marks,
            status=status
        )

    return redirect('/dashboard')

# ---------------- RUN APP ----------------

if __name__ == "__main__":
    app.run(debug=True)