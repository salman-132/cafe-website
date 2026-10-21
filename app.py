import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = "practice-only-change-me"  # needed for login sessions and flash messages
DB_PATH = os.path.join(os.path.dirname(__file__), "cafe.db")
OWNER_PASSWORD = "1234"  # practice project only

# Display order and labels (English, Arabic)
CATEGORY_ORDER = ["coffee", "tea", "dessert"]
CATEGORY_LABELS = {
    "coffee": ("Coffee", "قهوة"),
    "tea": ("Tea", "شاي"),
    "dessert": ("Desserts", "حلويات"),
}

# Button name -> status saved in the database
STATUS_ACTIONS = {"accept": "accepted", "reject": "rejected"}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.template_filter("bhd")
def format_bhd(price):
    return f"{price:.3f} BHD"


@app.template_filter("num")
def format_number(value):
    return f"{value:g}"


def check_required(form, fields):
    """Return an error message for every empty field. fields = {name: label}"""
    errors = []
    for name, label in fields.items():
        if not form.get(name, "").strip():
            errors.append(f"{label} is required.")
    return errors


def positive_number(value, number_type):
    """Convert value to int/float. Return None if it is not a positive number."""
    try:
        number = number_type(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def get_study_tables():
    conn = get_db()
    tables = conn.execute(
        "SELECT id, table_number, seats, booking_fee FROM cafe_tables "
        "WHERE type = 'study' ORDER BY table_number"
    ).fetchall()
    conn.close()
    return tables


def calculate_bill(study):
    """Penalty only if the goal was NOT completed AND actual hours > planned hours."""
    penalty = 0.0
    if not study["goal_completed"] and study["actual_hours"] > study["planned_hours"]:
        extra_hours = study["actual_hours"] - study["planned_hours"]
        penalty = extra_hours * study["penalty_per_hour"]
    total = study["booking_fee"] + penalty
    return penalty, total


def is_owner():
    return session.get("is_owner") is True


# ---------- Menu ----------

@app.route("/")
def menu():
    conn = get_db()
    items = conn.execute(
        "SELECT name, category, price, description FROM menu_items ORDER BY name"
    ).fetchall()
    conn.close()

    groups = {}
    for item in items:
        key = item["category"].strip().lower()
        groups.setdefault(key, []).append(item)

    keys = [k for k in CATEGORY_ORDER if k in groups]
    keys += [k for k in groups if k not in CATEGORY_ORDER]

    sections = []
    for key in keys:
        en, ar = CATEGORY_LABELS.get(key, (key.title(), ""))
        sections.append({"en": en, "ar": ar, "items": groups[key]})

    return render_template("menu.html", sections=sections)


# ---------- Normal table reservation ----------

@app.route("/reserve", methods=["GET", "POST"])
def reserve():
    form = request.form
    errors = []

    if request.method == "POST":
        errors = check_required(form, {
            "customer_name": "Name",
            "phone": "Phone",
            "date": "Date",
            "time": "Time",
        })
        people = positive_number(form.get("people_count"), int)
        if people is None:
            errors.append("Number of people must be 1 or more.")

        if not errors:
            conn = get_db()
            conn.execute(
                "INSERT INTO reservations "
                "(customer_name, phone, date, time, people_count, notes) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    form["customer_name"].strip(),
                    form["phone"].strip(),
                    form["date"],
                    form["time"],
                    people,
                    form.get("notes", "").strip() or None,
                ),
            )
            conn.commit()
            conn.close()
            return redirect(url_for("confirmed", kind="reservation"))

    return render_template("reserve.html", form=form, errors=errors)


# ---------- Study table booking ----------

@app.route("/study", methods=["GET", "POST"])
def study():
    form = request.form
    errors = []
    tables = get_study_tables()

    if request.method == "POST":
        errors = check_required(form, {
            "customer_name": "Name",
            "phone": "Phone",
            "date": "Date",
            "start_time": "Start time",
            "goal": "Goal",
        })

        study_table_ids = {str(t["id"]) for t in tables}
        if form.get("table_id") not in study_table_ids:
            errors.append("Choose one of the study tables.")

        hours = positive_number(form.get("planned_hours"), float)
        if hours is None:
            errors.append("Planned hours must be more than 0.")

        if not errors:
            conn = get_db()
            conn.execute(
                "INSERT INTO study_sessions "
                "(table_id, customer_name, phone, date, start_time, goal, planned_hours) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    int(form["table_id"]),
                    form["customer_name"].strip(),
                    form["phone"].strip(),
                    form["date"],
                    form["start_time"],
                    form["goal"].strip(),
                    hours,
                ),
            )
            conn.commit()
            conn.close()
            return redirect(url_for("confirmed", kind="study"))

    return render_template("study.html", form=form, errors=errors, tables=tables)


# ---------- Confirmation ----------

@app.route("/confirmed/<kind>")
def confirmed(kind):
    return render_template("confirmed.html", kind=kind)


# ---------- Owner: login / logout ----------

@app.route("/owner/login", methods=["GET", "POST"])
def owner_login():
    if is_owner():
        return redirect(url_for("owner"))

    errors = []
    if request.method == "POST":
        if request.form.get("password") == OWNER_PASSWORD:
            session["is_owner"] = True
            return redirect(url_for("owner"))
        errors.append("Wrong password. Try again.")

    return render_template("owner_login.html", errors=errors)


@app.route("/owner/logout")
def owner_logout():
    session.pop("is_owner", None)
    return redirect(url_for("owner_login"))


# ---------- Owner: dashboard ----------

@app.route("/owner")
def owner():
    if not is_owner():
        return redirect(url_for("owner_login"))

    conn = get_db()
    reservations = conn.execute(
        "SELECT * FROM reservations ORDER BY created_at DESC, id DESC"
    ).fetchall()
    study_rows = conn.execute(
        "SELECT s.*, t.table_number, t.booking_fee "
        "FROM study_sessions s JOIN cafe_tables t ON t.id = s.table_id "
        "ORDER BY s.created_at DESC, s.id DESC"
    ).fetchall()
    conn.close()

    # Add penalty and total to finished sessions
    study_sessions = []
    for row in study_rows:
        study = dict(row)
        if study["status"] == "finished":
            study["penalty"], study["total"] = calculate_bill(study)
        study_sessions.append(study)

    return render_template(
        "owner.html", reservations=reservations, study_sessions=study_sessions
    )


# ---------- Owner: accept / reject ----------

@app.route("/owner/reservations/<int:res_id>/<action>", methods=["POST"])
def update_reservation(res_id, action):
    if not is_owner():
        return redirect(url_for("owner_login"))

    new_status = STATUS_ACTIONS.get(action)
    if new_status:
        conn = get_db()
        conn.execute(
            "UPDATE reservations SET status = ? WHERE id = ? AND status = 'pending'",
            (new_status, res_id),
        )
        conn.commit()
        conn.close()
        flash(f"Reservation #{res_id} {new_status}.", "success")

    return redirect(url_for("owner"))


@app.route("/owner/study/<int:study_id>/<action>", methods=["POST"])
def update_study(study_id, action):
    if not is_owner():
        return redirect(url_for("owner_login"))

    new_status = STATUS_ACTIONS.get(action)
    if new_status:
        conn = get_db()
        conn.execute(
            "UPDATE study_sessions SET status = ? WHERE id = ? AND status = 'pending'",
            (new_status, study_id),
        )
        conn.commit()
        conn.close()
        flash(f"Study session #{study_id} {new_status}.", "success")

    return redirect(url_for("owner"))


# ---------- Owner: end a study session ----------

@app.route("/owner/study/<int:study_id>/finish", methods=["POST"])
def finish_study(study_id):
    if not is_owner():
        return redirect(url_for("owner_login"))

    actual_hours = positive_number(request.form.get("actual_hours"), float)
    if actual_hours is None:
        flash(f"Study session #{study_id}: actual hours must be more than 0.", "error")
        return redirect(url_for("owner"))

    goal_completed = 1 if request.form.get("goal_completed") else 0

    conn = get_db()
    conn.execute(
        "UPDATE study_sessions "
        "SET actual_hours = ?, goal_completed = ?, status = 'finished' "
        "WHERE id = ? AND status = 'accepted'",
        (actual_hours, goal_completed, study_id),
    )
    conn.commit()
    conn.close()
    flash(f"Study session #{study_id} finished.", "success")

    return redirect(url_for("owner"))


if __name__ == "__main__":
    app.run(debug=True)
