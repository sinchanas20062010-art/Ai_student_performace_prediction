import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import os
from datetime import datetime

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="AI Student Performance Prediction",
    page_icon="🎓",
    layout="wide"
)

# Upload directory setup
os.makedirs("uploaded_videos", exist_ok=True)

# ==========================================
# DATABASE SETUP
# ==========================================
conn = sqlite3.connect("student_performance.db", check_same_thread=False)
cursor = conn.cursor()

# 1. Students Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT UNIQUE,
    name TEXT,
    course TEXT,
    username TEXT UNIQUE,
    password TEXT,
    marks REAL,
    attendance REAL,
    internal_marks REAL,
    activities REAL,
    video_path TEXT
)
""")

# 2. History Table (Tracks progress over time)
cursor.execute("""
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT,
    marks REAL,
    attendance REAL,
    internal_marks REAL,
    activities REAL,
    predicted_score REAL,
    date TEXT
)
""")
conn.commit()

# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = ""
if "student_id" not in st.session_state:
    st.session_state.student_id = ""

# ==========================================
# AI PREDICTION ALGORITHM
# ==========================================
def predict_performance(marks, attendance, internal, activities):
    # Weighted calculation
    score = (marks * 0.40) + (attendance * 0.20) + (internal * 0.25) + (activities * 0.15)
    
    if score >= 90:
        result = "Excellent"
        suggestion = "Student is performing exceptionally well. Encourage advanced project work."
    elif score >= 80:
        result = "Good"
        suggestion = "Consistent performance. Focus on improving weaker internal test areas."
    elif score >= 60:
        result = "Average"
        suggestion = "Student needs more focus on attendance and daily activity submissions."
    else:
        result = "Needs Improvement / At Risk"
        suggestion = "Immediate academic mentoring and remedial sessions required."
        
    return round(score, 2), result, suggestion

def logout():
    st.session_state.logged_in = False
    st.session_state.role = ""
    st.session_state.student_id = ""
    st.rerun()

# ==========================================
# AUTHENTICATION / LOGIN VIEW
# ==========================================
if not st.session_state.logged_in:
    st.title("🎓 AI Student Performance Monitoring System")
    st.caption("Predictive Analytics & Student Academic Progress Dashboard")
    st.divider()

    st.subheader("🔐 Login")
    login_type = st.selectbox("Select Role", ["Teacher / Admin", "Student"],key="login_role_select")
    username = st.text_input("Username",key="login_username")
    password = st.text_input("Password", type="password",key="login_password")

    if st.button("Login", use_container_width=True,key="student_login_btn"):
        if login_type == "Teacher / Admin":
            # Default Teacher / Admin credentials
            if username == "Teacher" and password == "Teacher123":
                st.session_state.logged_in = True
                st.session_state.role = "admin"
                st.rerun()
            else:
                st.error("Invalid Teacher/Admin credentials.")
        else:
            student = cursor.execute(
                "SELECT student_id FROM students WHERE username = ? AND password = ?",
                (username, password)
            ).fetchone()
            if student:
                st.session_state.logged_in = True
                st.session_state.role = "student"
                st.session_state.student_id = student[0]
                st.rerun()
            else:
                st.error("Invalid Student username or password.")

# ==========================================
# TEACHER / ADMIN DASHBOARD
# ==========================================
elif st.session_state.role == "admin":
    st.sidebar.title("👨‍🏫 Teacher Dashboard")
    if st.sidebar.button("Logout"):
        logout()

    menu = st.sidebar.radio(
        "Navigation",
        [
            "📊 Dashboard Overview",
            "📝 Add / Edit Student (Manual)",
            "📁 Excel Upload",
            "🎥 Upload Presentation Video",
            "👥 All Students Performance",
            "🔍 Individual Student Analysis"
        ]
    )

    # 1. Dashboard Overview
    if menu == "📊 Dashboard Overview":
        st.header("Overview")
        total = cursor.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Enrolled Students", total)
        c2.metric("AI System", "Active")
        c3.metric("Database", "Connected")
        st.info("Use the navigation menu on the left to add records, view student performance, or inspect individual analytics.")

    # 2. Add / Edit Student Manually
    elif menu == "📝 Add / Edit Student (Manual)":
        st.header("Add or Edit Student Record")
        action = st.radio("Action", ["Add New Student", "Edit Existing Student"], horizontal=True)

        if action == "Add New Student":
            with st.form("add_student_form"):
                sid = st.text_input("Student ID (e.g. BCA001)")
                name = st.text_input("Full Name")
                course = st.text_input("Course", value="BCA")
                usr = st.text_input("Set Username")
                pwd = st.text_input("Set Password", type="password")
                marks = st.number_input("Semester Marks (%)", 0.0, 100.0, 75.0)
                att = st.number_input("Attendance (%)", 0.0, 100.0, 80.0)
                internal = st.number_input("Internal Marks (%)", 0.0, 100.0, 70.0)
                activities = st.number_input("Activity Score (%)", 0.0, 100.0, 65.0)
                
                submitted = st.form_submit_button("Save Student Record")
                if submitted:
                    if not (sid and name and usr and pwd):
                        st.warning("Please fill all required identification fields.")
                    else:
                        try:
                            cursor.execute("""
                            INSERT INTO students (student_id, name, course, username, password, marks, attendance, internal_marks, activities)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (sid, name, course, usr, pwd, marks, att, internal, activities))
                            
                            score, _, _ = predict_performance(marks, att, internal, activities)
                            cursor.execute("""
                            INSERT INTO history (student_id, marks, attendance, internal_marks, activities, predicted_score, date)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (sid, marks, att, internal, activities, score, datetime.now().strftime("%Y-%m-%d %H:%M")))
                            
                            conn.commit()
                            st.success(f"Student {name} ({sid}) added successfully!")
                        except sqlite3.IntegrityError:
                            st.error("Student ID or Username already exists.")

        else:
            student_list = [r[0] for r in cursor.execute("SELECT student_id FROM students").fetchall()]
            if not student_list:
                st.warning("No students available to edit.")
            else:
                sel_sid = st.selectbox("Select Student ID to Edit", student_list)
                data = cursor.execute("SELECT name, course, marks, attendance, internal_marks, activities FROM students WHERE student_id=?", (sel_sid,)).fetchone()
                
                with st.form("edit_student_form"):
                    name = st.text_input("Full Name", value=data[0])
                    course = st.text_input("Course", value=data[1])
                    marks = st.number_input("Semester Marks (%)", 0.0, 100.0, float(data[2] or 0.0))
                    att = st.number_input("Attendance (%)", 0.0, 100.0, float(data[3] or 0.0))
                    internal = st.number_input("Internal Marks (%)", 0.0, 100.0, float(data[4] or 0.0))
                    activities = st.number_input("Activity Score (%)", 0.0, 100.0, float(data[5] or 0.0))
                    
                    update_submitted = st.form_submit_button("Update Record & Save to History")
                    if update_submitted:
                        cursor.execute("""
                        UPDATE students 
                        SET name=?, course=?, marks=?, attendance=?, internal_marks=?, activities=?
                        WHERE student_id=?
                        """, (name, course, marks, att, internal, activities, sel_sid))
                        
                        score, _, _ = predict_performance(marks, att, internal, activities)
                        cursor.execute("""
                        INSERT INTO history (student_id, marks, attendance, internal_marks, activities, predicted_score, date)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (sel_sid, marks, att, internal, activities, score, datetime.now().strftime("%Y-%m-%d %H:%M")))
                        
                        conn.commit()
                        st.success(f"Updated record for {sel_sid} and logged history entry.")

    # 3. Excel Upload
    elif menu == "📁 Excel Upload":
        st.header("Batch Upload Via Excel / CSV")
        st.caption("Columns required: student_id, name, course, username, password, marks, attendance, internal_marks, activities")
        uploaded_file = st.file_uploader("Upload File", type=["xlsx", "csv"])
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith(".csv"):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)

                st.dataframe(df.head())

                if st.button("Import Data to Database"):

                    for _, row in df.iterrows():

                        # Save student data
                        cursor.execute("""
                            INSERT OR REPLACE INTO students
                            (student_id, name, course, username, password,
                            marks, attendance, internal_marks, activities)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            row["student_id"],
                            row["name"],
                            row["course"],
                            row["username"],
                            str(row["password"]),
                            row["marks"],
                            row["attendance"],
                            row["internal_marks"],
                            row["activities"]
                        ))

                        # AI prediction
                        score, result, suggestion = predict_performance(
                            row["marks"],
                            row["attendance"],
                            row["internal_marks"],
                            row["activities"]
                        )

                        # Save performance history
                        cursor.execute("""
                            INSERT INTO history
                            (student_id, marks, attendance, internal_marks,
                            activities, predicted_score, date)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            row["student_id"],
                            row["marks"],
                            row["attendance"],
                            row["internal_marks"],
                            row["activities"],
                            score,
                            datetime.now().strftime("%Y-%m-%d %H:%M")
                        ))

                    conn.commit()

                    st.success(
                        "All student records imported successfully with performance history."
                    )

            except Exception as e:
                st.error(f"Error parsing file: {e}")
    # 4. Presentation Video Upload
    elif menu == "🎥 Upload Presentation Video":
        st.header("Upload Student Presentation Video")
        student_list = [r[0] for r in cursor.execute("SELECT student_id FROM students").fetchall()]
        if not student_list:
            st.warning("Please add student profiles first.")
        else:
            sel_sid = st.selectbox("Assign Video to Student ID", student_list)
            video_file = st.file_uploader("Select Video", type=["mp4", "mov", "avi"])
            if video_file and st.button("Save Video"):
                save_path = os.path.join("uploaded_videos", f"{sel_sid}_{video_file.name}")
                with open(save_path, "wb") as f:
                    f.write(video_file.getbuffer())
                cursor.execute("UPDATE students SET video_path=? WHERE student_id=?", (save_path, sel_sid))
                conn.commit()
                st.success(f"Video uploaded and mapped to {sel_sid}.")

    # 5. All Students Performance View
    elif menu == "👥 All Students Performance":

        st.header("📊 All Students AI Performance Overview")

        df = pd.read_sql_query(
        "SELECT student_id, name, marks, attendance, internal_marks, activities FROM students",
        conn
    )

        if df.empty:
            st.info("No student records to display.")

        else:
            scores = []
        results = []
        tips = []

        for _, row in df.iterrows():

            score, result, tip = predict_performance(
                row["marks"] or 0,
                row["attendance"] or 0,
                row["internal_marks"] or 0,
                row["activities"] or 0
            )

            scores.append(round(score, 2))
            results.append(result)
            tips.append(tip)

        df["AI Score (%)"] = scores
        df["Predicted Performance"] = results
        df["AI Recommendation"] = tips

        # Summary
        total_students = len(df)
        average_score = round(df["AI Score (%)"].mean(), 2)
        excellent = (df["Predicted Performance"] == "Excellent").sum()
        attention = (~df["Predicted Performance"].isin(
            ["Excellent", "Good"]
        )).sum()

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("👨‍🎓 Total Students", total_students)

        with col2:
            st.metric("🤖 Average AI Score", f"{average_score}%")

        with col3:
            st.metric("🟢 Excellent", excellent)

        with col4:
            st.metric("⚠️ Need Attention", attention)

        st.divider()

        # AI Prediction Table
        st.subheader("🤖 AI Performance Prediction")

        st.dataframe(
            df[
                [
                    "student_id",
                    "name",
                    "marks",
                    "attendance",
                    "internal_marks",
                    "activities",
                    "AI Score (%)",
                    "Predicted Performance"
                ]
            ],
            width="stretch",
            hide_index=True
        )

        st.divider()



    # 6. Individual Student Analysis (Graphs, History, AI Prediction)
    elif menu == "🔍 Individual Student Analysis":
        st.header("Individual Student Deep Dive")
        student_list = [r[0] for r in cursor.execute("SELECT student_id FROM students").fetchall()]
        if not student_list:
            st.warning("No records found.")
        else:
            sel_sid = st.selectbox("Select Student", student_list)
            std = cursor.execute("SELECT name, course, marks, attendance, internal_marks, activities, video_path FROM students WHERE student_id=?", (sel_sid,)).fetchone()
            
            st.subheader(f"Profile: {std[0]} ({sel_sid}) - {std[1]}")
        
            # Prediction Card
            score, result, suggestion = predict_performance(std[2] or 0, std[3] or 0, std[4] or 0, std[5] or 0)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric("Predicted Score", f"{score}%")
                st.markdown(f"*Classification:* {result}")
                st.info(f"💡 *AI Recommendation:*\n{suggestion}")
            
            with col2:
                # Metric breakdown chart
                metrics_df = pd.DataFrame({
                    "Parameter": ["Marks", "Attendance", "Internals", "Activities"],
                    "Value (%)": [std[2] or 0, std[3] or 0, std[4] or 0, std[5] or 0]
                }).set_index("Parameter")
                st.bar_chart(metrics_df)

            # Historical Progress Chart
            st.subheader("📈 Performance History & Progress")
            hist_df = pd.read_sql_query("SELECT date, predicted_score FROM history WHERE student_id=? ORDER BY id ASC", conn, params=(sel_sid,))
            if not hist_df.empty:
                st.line_chart(hist_df.set_index("date"))
            else:
                st.caption("No historical updates logged yet.")

            # Video player
            if std[6] and os.path.exists(std[6]):
                st.subheader("🎥 Student Presentation Video")
                st.video(std[6])
            else:
                st.info("No presentation video uploaded by your instructor yet.")
            
            

# ==========================================
# STUDENT DASHBOARD
# ==========================================
elif st.session_state.role == "student":
    sid = st.session_state.student_id
    st.sidebar.title("🎓 Student Portal")
    if st.sidebar.button("Logout"):
        logout()

    std = cursor.execute("SELECT name, course, marks, attendance, internal_marks, activities, video_path FROM students WHERE student_id=?", (sid,)).fetchone()

    st.header(f"Welcome, {std[0]}")
    st.caption(f"Student ID: {sid} | Course: {std[1]}")
    st.divider()

    # Metrics Summary
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Semester Marks", f"{std[2]}%")
    c2.metric("Attendance", f"{std[3]}%")
    c3.metric("Internal Marks", f"{std[4]}%")
    c4.metric("Activity Score", f"{std[5]}%")

    st.divider()

    # AI Future Prediction Section
    st.subheader("🤖 AI Future Prediction & Assessment")
    score, result, suggestion = predict_performance(std[2] or 0, std[3] or 0, std[4] or 0, std[5] or 0)
    
    p1, p2 = st.columns([1, 1])
    with p1:
        st.metric("Estimated Performance Score", f"{score}%")
        st.markdown(f"*Predicted Rating:* {result}")
        st.info(f"💡 *Actionable…Feedback:*\n{suggestion}")
    
    with p2:
        radar_df = pd.DataFrame({
            "Category": ["Marks", "Attendance", "Internals", "Activities"],
            "Score": [std[2] or 0, std[3] or 0, std[4] or 0, std[5] or 0]
        }).set_index("Category")
        st.bar_chart(radar_df)

    # Previous History Graph
    
    st.subheader("📈 Performance History & Progress")
    hist_df = pd.read_sql_query("SELECT date, predicted_score FROM history WHERE student_id=? ORDER BY id ASC", conn, params=(sid,))
    if not hist_df.empty:
                st.line_chart(hist_df.set_index("date"))
    else:
                st.caption("No historical updates logged yet.")

    # Presentation Video
    st.subheader("🎥 Assigned Presentation Video")
    if std[6] and os.path.exists(std[6]):
        st.video(std[6])
    else:
        st.info("No presentation video uploaded by your instructor yet.")
