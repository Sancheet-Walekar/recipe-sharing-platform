"""
RecipeShare - main Flask application.

Run it with:
    python app.py
Then open http://127.0.0.1:5000 in your browser.
"""

import os
import re
from functools import wraps

from flask import (
    Flask, flash, g, redirect, render_template, request, session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

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
        "current_user": g.get("user"),
    }


# ------------------------------------------------------------------
# Logged-in user helpers
# ------------------------------------------------------------------
@app.before_request
def load_logged_in_user():
    """
    Runs before every request. If the session contains a user id, load that
    user from the database and keep it in g.user (None for guests).
    """
    user_id = session.get("user_id")
    g.user = None
    if user_id is not None:
        g.user = get_db().execute(
            "SELECT id, name, email, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()


def login_required(view):
    """
    Decorator for pages that need a logged-in user.
    Usage:
        @app.route("/secret")
        @login_required
        def secret(): ...
    """
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            flash("Please log in to continue.", "info")
            # Remember where the user wanted to go, so we can send them back
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped_view


def is_safe_next_url(target):
    """Only allow redirects to pages on our own site (e.g. "/recipes/3")."""
    return bool(target) and target.startswith("/") and not target.startswith("//")


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
    if g.user:
        return redirect(url_for("index"))

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
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# ------------------------------------------------------------------
# Authentication: login and logout
# ------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    """Show the login form (GET) and log the user in (POST)."""
    if g.user:
        return redirect(url_for("index"))

    next_url = request.args.get("next", "")

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        next_url = request.form.get("next", "")

        if not email or not password:
            flash("Please enter both your email and password.", "error")
            return render_template("login.html", email=email, next_url=next_url)

        user = get_db().execute(
            "SELECT id, name, password FROM users WHERE email = ?", (email,)
        ).fetchone()

        # Same message for "unknown email" and "wrong password" so attackers
        # cannot find out which emails are registered.
        if user is None or not check_password_hash(user["password"], password):
            flash("Incorrect email or password.", "error")
            return render_template("login.html", email=email, next_url=next_url)

        # Start a fresh session that remembers who is logged in
        session.clear()
        session["user_id"] = user["id"]
        flash(f"Welcome back, {user['name']}!", "success")

        if is_safe_next_url(next_url):
            return redirect(next_url)
        return redirect(url_for("index"))

    return render_template("login.html", next_url=next_url)


@app.route("/logout", methods=["POST"])
def logout():
    """Log out by forgetting everything stored in the session."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


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
