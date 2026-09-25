"""
RecipeShare - main Flask application.

Run it with:
    python app.py
Then open http://127.0.0.1:5000 in your browser.
"""

import os
import re
from datetime import datetime
from functools import wraps

from flask import (
    Flask, abort, flash, g, redirect, render_template, request, session, url_for,
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

# Limits for the recipe form
MAX_TITLE_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 500
MAX_LONG_TEXT_LENGTH = 5000      # ingredients and instructions
MAX_MINUTES = 1440               # 24 hours
MAX_SERVINGS = 100

LATEST_RECIPES_ON_HOME = 6


def recipe_image_url(image_filename):
    """Return the URL of a recipe photo, or of the placeholder if there is none."""
    if image_filename:
        return url_for("static", filename=f"uploads/recipes/{image_filename}")
    return url_for("static", filename="images/placeholder.svg")


@app.context_processor
def inject_globals():
    """Make these values available in every template automatically."""
    return {
        "categories": CATEGORIES,
        "difficulties": DIFFICULTIES,
        "current_user": g.get("user"),
        "recipe_image_url": recipe_image_url,
    }


@app.template_filter("nice_date")
def nice_date(value):
    """Jinja filter: turn '2026-09-25 06:38:04' into '25 Sep 2026'."""
    if not value:
        return ""
    try:
        return datetime.strptime(str(value)[:19], "%Y-%m-%d %H:%M:%S").strftime("%d %b %Y")
    except ValueError:
        return value


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
# Recipe form validation (used by both "add" and "edit")
# ------------------------------------------------------------------
def parse_whole_number(value, label, minimum, maximum, errors):
    """
    Turn text like "15" into the number 15.
    Adds a message to "errors" and returns None if the value is not valid.
    """
    try:
        number = int(value)
    except (TypeError, ValueError):
        errors.append(f"{label} must be a whole number.")
        return None
    if number < minimum or number > maximum:
        errors.append(f"{label} must be between {minimum} and {maximum}.")
        return None
    return number


def validate_recipe_form(form):
    """
    Check every recipe field sent by the browser.
    Returns (recipe_data, errors). If "errors" is empty the data is safe to save.
    """
    errors = []
    recipe_data = {
        "title": form.get("title", "").strip(),
        "description": form.get("description", "").strip(),
        "ingredients": form.get("ingredients", "").strip(),
        "instructions": form.get("instructions", "").strip(),
        "category": form.get("category", ""),
        "difficulty": form.get("difficulty", ""),
        "prep_time": form.get("prep_time", "").strip(),
        "cook_time": form.get("cook_time", "").strip(),
        "servings": form.get("servings", "").strip(),
    }

    # Required text fields with a maximum length
    text_rules = [
        ("title", "Title", MAX_TITLE_LENGTH),
        ("description", "Description", MAX_DESCRIPTION_LENGTH),
        ("ingredients", "Ingredients", MAX_LONG_TEXT_LENGTH),
        ("instructions", "Instructions", MAX_LONG_TEXT_LENGTH),
    ]
    for field, label, max_length in text_rules:
        if not recipe_data[field]:
            errors.append(f"{label} is required.")
        elif len(recipe_data[field]) > max_length:
            errors.append(f"{label} must be at most {max_length} characters.")

    # Drop-downs must contain one of our allowed values
    if recipe_data["category"] not in CATEGORIES:
        errors.append("Please choose a valid category.")
    if recipe_data["difficulty"] not in DIFFICULTIES:
        errors.append("Please choose a valid difficulty.")

    # Numbers: keep the typed text if invalid so the form can show it again
    number_rules = [
        ("prep_time", "Preparation time", 0, MAX_MINUTES),
        ("cook_time", "Cooking time", 0, MAX_MINUTES),
        ("servings", "Servings", 1, MAX_SERVINGS),
    ]
    for field, label, minimum, maximum in number_rules:
        number = parse_whole_number(recipe_data[field], label, minimum, maximum, errors)
        if number is not None:
            recipe_data[field] = number

    return recipe_data, errors


# ------------------------------------------------------------------
# Database query helpers for recipes
# ------------------------------------------------------------------
# Every recipe list needs the same columns: the recipe itself plus the
# author's name. Keeping the SQL in one place avoids copy-pasting it.
RECIPE_LIST_SQL = """
    SELECT recipes.*,
           users.name AS author_name
    FROM recipes
    JOIN users ON users.id = recipes.user_id
"""


def fetch_recipes(conditions=None, params=(), limit=None):
    """
    Return a list of recipes (newest first).

    conditions: list of SQL snippets written by US, e.g. ["recipes.category = ?"]
    params:     the user-provided values that replace each "?" safely
    limit:      maximum number of recipes to return (None = all)

    User input is NEVER pasted into the SQL text - it only goes into "params".
    """
    sql = RECIPE_LIST_SQL
    params = list(params)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY recipes.created_at DESC, recipes.id DESC"
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    return get_db().execute(sql, params).fetchall()


def get_recipe_or_404(recipe_id):
    """Load one recipe (with author name) or show the 404 page if it does not exist."""
    recipe = get_db().execute(
        RECIPE_LIST_SQL + " WHERE recipes.id = ?", (recipe_id,)
    ).fetchone()
    if recipe is None:
        abort(404)
    return recipe


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------
@app.route("/")
def index():
    """Home page with the newest recipes."""
    latest_recipes = fetch_recipes(limit=LATEST_RECIPES_ON_HOME)
    return render_template("index.html", latest_recipes=latest_recipes)


@app.route("/recipes")
def recipes():
    """List of all recipes from the database."""
    return render_template("recipes.html", recipes=fetch_recipes())


@app.route("/recipes/<int:recipe_id>")
def recipe_details(recipe_id):
    """Full page for a single recipe."""
    recipe = get_recipe_or_404(recipe_id)
    is_owner = g.user is not None and g.user["id"] == recipe["user_id"]
    return render_template("recipe_details.html", recipe=recipe, is_owner=is_owner)


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
# Recipes: create
# ------------------------------------------------------------------
@app.route("/recipes/add", methods=["GET", "POST"])
@login_required
def add_recipe():
    """Show the empty recipe form (GET) and save a new recipe (POST)."""
    if request.method == "POST":
        recipe_data, errors = validate_recipe_form(request.form)

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("add_recipe.html", form=recipe_data)

        db = get_db()
        cursor = db.execute(
            """
            INSERT INTO recipes (user_id, title, description, ingredients, instructions,
                                 category, difficulty, prep_time, cook_time, servings)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                g.user["id"], recipe_data["title"], recipe_data["description"],
                recipe_data["ingredients"], recipe_data["instructions"],
                recipe_data["category"], recipe_data["difficulty"],
                recipe_data["prep_time"], recipe_data["cook_time"], recipe_data["servings"],
            ),
        )
        db.commit()
        flash("Recipe added successfully!", "success")
        # cursor.lastrowid is the id SQLite gave to the new recipe
        return redirect(url_for("recipe_details", recipe_id=cursor.lastrowid))

    return render_template("add_recipe.html", form={})


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
