#!/usr/bin/env python3
import cgi
import cgitb
import json
import sys
import os

cgitb.enable()

# ── session store (file-based since CGI is stateless) ─────────────────────────
SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".gs_session.json")

def load_session():
    try:
        with open(SESSION_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def save_session(data):
    with open(SESSION_FILE, "w") as f:
        json.dump(data, f)

def clear_session():
    try:
        os.remove(SESSION_FILE)
    except Exception:
        pass

# ── helpers ───────────────────────────────────────────────────────────────────
def is_numeric(v):
    if v is None: return False
    try: float(v); return True
    except (ValueError, TypeError): return False

def letter_grade(pct):
    if pct is None: return "N/A"
    if pct >= 93: return "A"
    if pct >= 90: return "A-"
    if pct >= 87: return "B+"
    if pct >= 83: return "B"
    if pct >= 80: return "B-"
    if pct >= 77: return "C+"
    if pct >= 73: return "C"
    if pct >= 70: return "C-"
    if pct >= 67: return "D+"
    if pct >= 63: return "D"
    if pct >= 60: return "D-"
    return "F"

def semester_sort_key(sem):
    order = {"Spring": 0, "Summer": 1, "Fall": 2, "Winter": 3}
    parts = sem.split()
    if len(parts) == 2:
        try: return (int(parts[1]), order.get(parts[0], 99))
        except ValueError: pass
    return (9999, 99)

def get_grades(connection, course_id):
    try:
        assignments = connection.account.get_assignments(course_id) or []
        total_earned = total_possible = 0.0
        graded_count = 0
        for a in assignments:
            raw_grade = getattr(a, "grade",     None)
            raw_max   = getattr(a, "max_grade", None)
            if is_numeric(raw_grade) and is_numeric(raw_max):
                grade     = float(raw_grade)
                max_grade = float(raw_max)
                total_earned += grade
                if max_grade > 0:
                    total_possible += max_grade
                    graded_count   += 1
        if graded_count == 0:
            return None
        pct = (total_earned / total_possible) * 100
        return {
            "earned":   round(total_earned, 2),
            "possible": round(total_possible, 2),
            "pct":      round(pct, 2),
            "letter":   letter_grade(pct),
            "count":    graded_count,
        }
    except Exception:
        return None

# ── CGI handler ───────────────────────────────────────────────────────────────
print("Content-Type: application/json\n")

form   = cgi.FieldStorage()
action = form.getvalue("action", "")

if action == "login":
    email    = form.getvalue("email",    "")
    password = form.getvalue("password", "")
    try:
        from gradescopeapi.classes.connection import GSConnection
        conn    = GSConnection()
        conn.login(email, password)
        courses = conn.account.get_courses()

        # Build course list with grades
        result  = {}
        all_courses = []
        for role in ("student", "instructor"):
            for cid, c_obj in courses.get(role, {}).items():
                name      = getattr(c_obj, "name",      None) or cid
                full_name = getattr(c_obj, "full_name", None) or name
                semester  = getattr(c_obj, "semester",  None) or "Unknown"
                year      = getattr(c_obj, "year",      None) or ""
                display   = f"{full_name} ({name})" if full_name.strip() != name.strip() else name
                all_courses.append({
                    "id":      cid,
                    "display": display,
                    "sem":     f"{semester} {year}".strip(),
                })

        # Fetch grades for every course
        grades = {}
        for c in all_courses:
            grades[c["id"]] = get_grades(conn, c["id"])

        # Save credentials for subsequent requests
        save_session({"email": email, "password": password})

        print(json.dumps({
            "ok":      True,
            "courses": all_courses,
            "grades":  grades,
        }))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))

elif action == "add_manual":
    session = load_session()
    try:
        course_id = form.getvalue("course_id", "")
        name      = form.getvalue("name",      "")
        earned    = float(form.getvalue("earned",   0))
        possible  = float(form.getvalue("possible", 100))

        manual = session.get("manual", {})
        if course_id not in manual:
            manual[course_id] = []
        manual[course_id].append({"name": name, "earned": earned, "possible": possible})
        session["manual"] = manual
        save_session(session)
        print(json.dumps({"ok": True, "manual": manual.get(course_id, [])}))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))

elif action == "remove_manual":
    session = load_session()
    try:
        course_id = form.getvalue("course_id", "")
        idx       = int(form.getvalue("idx", -1))
        manual    = session.get("manual", {})
        if course_id in manual and 0 <= idx < len(manual[course_id]):
            manual[course_id].pop(idx)
        session["manual"] = manual
        save_session(session)
        print(json.dumps({"ok": True, "manual": manual.get(course_id, [])}))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))

elif action == "logout":
    clear_session()
    print(json.dumps({"ok": True}))

else:
    print(json.dumps({"ok": False, "error": "Unknown action"}))
