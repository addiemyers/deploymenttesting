#!/usr/bin/env python3
import cgi
import cgitb
import json
import os

cgitb.enable()
print("Content-Type: text/plain\n")

SESSION_FILE = "/tmp/gs2_session.json"
WEIGHTS_DIR  = "/tmp/gs2_weights"

os.makedirs(WEIGHTS_DIR, exist_ok=True)

def load_session():
    try:
        with open(SESSION_FILE) as f: return json.load(f)
    except: return {}

def save_session(data):
    with open(SESSION_FILE, "w") as f: json.dump(data, f)

def clear_session():
    try: os.remove(SESSION_FILE)
    except: pass

def weights_file(email, course_id):
    safe = email.replace("@","_").replace(".","_")
    return os.path.join(WEIGHTS_DIR, f"{safe}_{course_id}.json")

def load_weights(email, course_id):
    try:
        with open(weights_file(email, course_id)) as f: return json.load(f)
    except: return {"categories": [], "assignments": {}, "manual": []}

def save_weights(email, course_id, data):
    with open(weights_file(email, course_id), "w") as f: json.dump(data, f)

def is_numeric(v):
    if v is None: return False
    try: float(v); return True
    except: return False

def letter_grade(pct):
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

def get_grades_summary(conn, course_id):
    try:
        assignments = conn.account.get_assignments(course_id) or []
        total_earned = total_possible = 0.0
        graded_count = 0
        for a in assignments:
            rg = getattr(a, "grade", None)
            rm = getattr(a, "max_grade", None)
            if is_numeric(rg) and is_numeric(rm):
                g = float(rg); m = float(rm)
                total_earned += g
                if m > 0: total_possible += m; graded_count += 1
        if graded_count == 0: return None
        pct = (total_earned / total_possible) * 100
        return {"earned": round(total_earned,2), "possible": round(total_possible,2),
                "pct": round(pct,2), "letter": letter_grade(pct), "count": graded_count}
    except: return None

def get_all_assignments(conn, course_id):
    try:
        assignments = conn.account.get_assignments(course_id) or []
        result = []
        for a in assignments:
            rg = getattr(a, "grade", None)
            rm = getattr(a, "max_grade", None)
            if is_numeric(rg) and is_numeric(rm) and float(rm) > 0:
                result.append({"name": getattr(a,"name","Unnamed"),
                               "earned": float(rg), "possible": float(rm)})
        return result
    except: return []

# ── router ────────────────────────────────────────────────────────────────────
form   = cgi.FieldStorage()
action = form.getvalue("action", "")

if action == "login":
    email    = form.getvalue("email", "")
    password = form.getvalue("password", "")
    try:
        from gradescopeapi.classes.connection import GSConnection
        conn    = GSConnection()
        conn.login(email, password)
        courses = conn.account.get_courses()
        all_courses = []
        for role in ("student", "instructor"):
            for cid, c_obj in courses.get(role, {}).items():
                name      = getattr(c_obj, "name",      None) or cid
                full_name = getattr(c_obj, "full_name", None) or name
                semester  = getattr(c_obj, "semester",  None) or "Unknown"
                year      = getattr(c_obj, "year",      None) or ""
                display   = (full_name + " (" + name + ")") if full_name.strip() != name.strip() else name
                all_courses.append({"id": cid, "display": display,
                                    "sem": (semester + " " + year).strip()})
        grades = {c["id"]: get_grades_summary(conn, c["id"]) for c in all_courses}
        save_session({"email": email, "password": password})
        print(json.dumps({"ok": True, "courses": all_courses, "grades": grades}))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))

elif action == "course_data":
    course_id = form.getvalue("course_id", "")
    session   = load_session()
    try:
        from gradescopeapi.classes.connection import GSConnection
        conn = GSConnection()
        conn.login(session["email"], session["password"])
        assignments = get_all_assignments(conn, course_id)
        weights     = load_weights(session["email"], course_id)
        summary     = get_grades_summary(conn, course_id)
        print(json.dumps({"ok": True, "assignments": assignments,
                          "weights": weights, "summary": summary}))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))

elif action == "save_weights":
    course_id = form.getvalue("course_id", "")
    session   = load_session()
    try:
        data = json.loads(form.getvalue("data", "{}"))
        save_weights(session["email"], course_id, data)
        print(json.dumps({"ok": True}))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))

elif action == "logout":
    clear_session()
    print(json.dumps({"ok": True}))

else:
    print(json.dumps({"ok": False, "error": "Unknown action"}))
