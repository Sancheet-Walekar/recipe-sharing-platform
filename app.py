"""
RecipeShare - main Flask application.

Run it with:
    python app.py
Then open http://127.0.0.1:5000 in your browser.
"""

import os
import re

from flask import Flask, flash, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from database import close_db, create_tables, get_db

# ------------------------------------------------------------------
# App setup
# ------------------------------------------------------------------
app = Flask(__name__)

# The secret key signs the session cookie. In real deployments set the
# SECRET_KEY environment variable; the fallback is only for local development.
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")

# Close the database connection automatically after every request.
app.teardown_appcontext(close_db)

# Make sure all tables exist, even if "python init_db.py" was forgotten.
create_tables()

# ------------------------------------------------------------------
# Settings used across the app
# ------------------------------------------------------------------
CATEGORIES = [
    "Indian", "Italian", "Mexican", "Chinese", "American", "Healthy",
    "Dessert", "Breakfast", "Lunch", "Dinner", "Other",
]
DIFFICULTIES = ["Easy", "Medium", "Hard"]

MIN_PASSWORD_LENGTH = 6
MAX_NAME_LENGTH = 60
# A simple (not perfect) email check: something@something.something
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@app.context_processor
def inject_globals():
    """Make these values available in every template automatically."""
    return {
        "categories": CATEGORIES,
        "difficulties": DIFFICULTIES,
    }


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------
@app.route("/")
def index():
    """Home page."""
    return render_template("index.html", latest_recipes=[])


@app.route("/recipes")
def recipes():
    """List of all recipes (connected to the database in a later stage)."""
    return render_template("recipes.html", recipes=[])


# ------------------------------------------------------------------
# Authentication: register
# ------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    """Show the sign-up form (GET) and create a new account (POST)."""
    if request.method == "POST":
        # .strip() removes spaces the user may have typed by accident
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Collect every problem so the user can fix them all at once
        errors = []
        if not name:
            errors.append("Name is required.")
        elif len(name) > MAX_NAME_LENGTH:
            errors.append(f"Name must be at most {MAX_NAME_LENGTH} characters.")
        if not email:
            errors.append("Email is required.")
        elif not EMAIL_PATTERN.match(email):
            errors.append("Please enter a valid email address.")
        if not password:
            errors.append("Password is required.")
        elif len(password) < MIN_PASSWORD_LENGTH:
            errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
        elif password != confirm_password:
            errors.append("Passwords do not match.")

        db = get_db()
        if not errors:
            existing_user = db.execute(
                "SELECT id FROM users WHERE email = ?", (email,)
            ).fetchone()
            if existing_user:
                errors.append("An account with this email already exists.")

        if errors:
            for error in errors:
                flash(error, "error")
            # Show the form again, keeping what the user typed (except passwords)
            return render_template("register.html", name=name, email=email)

        # Never store the real password - only its secure hash
        db.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        db.commit()
        flash("Account created successfully! Welcome to RecipeShare.", "success")
        return redirect(url_for("index"))

    return render_template("register.html")


# ------------------------------------------------------------------
# Error pages
# ------------------------------------------------------------------
@app.errorhandler(404)
def page_not_found(error):
    """Show a friendly page when a URL does not exist."""
    return render_template("404.html"), 404


# ------------------------------------------------------------------
# Start the development server
# ------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
