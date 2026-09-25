"""
RecipeShare - main Flask application.

Run it with:
    python app.py
Then open http://127.0.0.1:5000 in your browser.
"""

import os
import re
import uuid
from datetime import datetime
from functools import wraps

from flask import (
    Flask, abort, flash, g, redirect, render_template, request, session, url_for,
)
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

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

# Reviews and ratings
MIN_RATING = 1
MAX_RATING = 5
MAX_COMMENT_LENGTH = 1000

LATEST_RECIPES_ON_HOME = 6

# Image uploads are stored on this computer, inside static/uploads/recipes/
UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads", "recipes")
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_UPLOAD_MB = 2
# Flask rejects any request bigger than this (error 413, handled below)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


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
# Image upload helpers
# ------------------------------------------------------------------
def get_file_extension(filename):
    """'My Photo.JPG' -> 'jpg'. secure_filename() first removes dangerous
    characters such as '../' so nothing outside our folder can be targeted."""
    safe_name = secure_filename(filename or "")
    if "." not in safe_name:
        return ""
    return safe_name.rsplit(".", 1)[1].lower()


def file_looks_like_image(file_storage):
    """
    Check the first bytes of the file ("magic numbers"). This stops someone
    from renaming e.g. a .exe file to .jpg and uploading it.
    """
    header = file_storage.stream.read(12)
    file_storage.stream.seek(0)  # rewind so the file can still be saved
    is_jpeg = header.startswith(b"\xff\xd8\xff")
    is_png = header.startswith(b"\x89PNG\r\n\x1a\n")
    is_webp = header[:4] == b"RIFF" and header[8:12] == b"WEBP"
    return is_jpeg or is_png or is_webp


def check_image_upload(file_storage):
    """Return an error message if the uploaded file is not allowed, otherwise None.
    No file at all is fine - the image is optional."""
    if file_storage is None or file_storage.filename == "":
        return None
    if get_file_extension(file_storage.filename) not in ALLOWED_IMAGE_EXTENSIONS:
        return "Image must be a JPG, JPEG, PNG or WEBP file."
    if not file_looks_like_image(file_storage):
        return "The uploaded file is not a valid image."
    return None


def save_recipe_image(file_storage):
    """
    Save an uploaded image and return its new file name (or None if no file).
    We invent a random name (e.g. '3f2a...9c.jpg') so that users can never
    overwrite each other's files or choose a dangerous file name.
    """
    if file_storage is None or file_storage.filename == "":
        return None
    extension = get_file_extension(file_storage.filename)
    new_filename = f"{uuid.uuid4().hex}.{extension}"
    file_storage.save(os.path.join(UPLOAD_FOLDER, new_filename))
    return new_filename


def delete_recipe_image(filename):
    """Remove an image file from the uploads folder (if it exists)."""
    if not filename:
        return
    # basename() keeps only the file name part, so paths like '../x' are ignored
    file_path = os.path.join(UPLOAD_FOLDER, os.path.basename(filename))
    if os.path.isfile(file_path):
        os.remove(file_path)


# ------------------------------------------------------------------
# Database query helpers for recipes
# ------------------------------------------------------------------
# Every recipe list needs the same columns: the recipe itself, the author's
# name and the rating summary. Keeping the SQL in one place avoids copy-pasting.
# The two small sub-queries calculate the average rating and number of ratings.
RECIPE_LIST_SQL = """
    SELECT recipes.*,
           users.name AS author_name,
           (SELECT ROUND(AVG(rating), 1) FROM ratings
             WHERE ratings.recipe_id = recipes.id) AS avg_rating,
           (SELECT COUNT(*) FROM ratings
             WHERE ratings.recipe_id = recipes.id) AS rating_count
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


def user_owns_recipe(recipe):
    """True only if someone is logged in AND they created this recipe."""
    return g.user is not None and g.user["id"] == recipe["user_id"]


def is_favorite(recipe_id):
    """True if the logged-in user has saved this recipe to their favorites."""
    if g.user is None:
        return False
    row = get_db().execute(
        "SELECT 1 FROM favorites WHERE user_id = ? AND recipe_id = ?",
        (g.user["id"], recipe_id),
    ).fetchone()
    return row is not None


def get_reviews(recipe_id):
    """All reviews of a recipe, newest first, with the reviewer's name and star rating."""
    return get_db().execute(
        """
        SELECT reviews.id, reviews.user_id, reviews.comment, reviews.created_at,
               users.name AS reviewer_name,
               ratings.rating
        FROM reviews
        JOIN users ON users.id = reviews.user_id
        LEFT JOIN ratings ON ratings.user_id = reviews.user_id
                         AND ratings.recipe_id = reviews.recipe_id
        WHERE reviews.recipe_id = ?
        ORDER BY reviews.created_at DESC, reviews.id DESC
        """,
        (recipe_id,),
    ).fetchall()


def redirect_back(default_url):
    """Go back to the page named in the hidden "next" form field, if it is safe."""
    next_url = request.form.get("next", "")
    if is_safe_next_url(next_url):
        return redirect(next_url)
    return redirect(default_url)


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
    """
    List recipes, optionally filtered. Examples:
        /recipes?q=pasta
        /recipes?q=pasta&category=Italian&difficulty=Easy
    """
    search_text = request.args.get("q", "").strip()
    category = request.args.get("category", "")
    difficulty = request.args.get("difficulty", "")

    conditions = []
    params = []

    if search_text:
        # "%pasta%" means: "pasta" anywhere in the text. The value goes into
        # params (never into the SQL string), so it is safe from SQL injection.
        like_pattern = f"%{search_text}%"
        conditions.append(
            "(recipes.title LIKE ? OR recipes.description LIKE ?"
            " OR recipes.category LIKE ? OR recipes.ingredients LIKE ?)"
        )
        params.extend([like_pattern] * 4)

    # Unknown values (e.g. ?category=abc) are simply ignored
    if category in CATEGORIES:
        conditions.append("recipes.category = ?")
        params.append(category)
    else:
        category = ""

    if difficulty in DIFFICULTIES:
        conditions.append("recipes.difficulty = ?")
        params.append(difficulty)
    else:
        difficulty = ""

    return render_template(
        "recipes.html",
        recipes=fetch_recipes(conditions, params),
        search_text=search_text,
        selected_category=category,
        selected_difficulty=difficulty,
        filters_active=bool(search_text or category or difficulty),
    )


@app.route("/recipes/<int:recipe_id>")
def recipe_details(recipe_id):
    """Full page for a single recipe."""
    recipe = get_recipe_or_404(recipe_id)
    reviews = get_reviews(recipe_id)

    # If the logged-in user already reviewed this recipe, pre-fill the form
    my_review = None
    if g.user:
        my_review = next((r for r in reviews if r["user_id"] == g.user["id"]), None)

    return render_template(
        "recipe_details.html",
        recipe=recipe,
        reviews=reviews,
        my_review=my_review,
        is_owner=user_owns_recipe(recipe),
        is_favorite=is_favorite(recipe_id),
    )


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

        image_file = request.files.get("image")
        image_error = check_image_upload(image_file)
        if image_error:
            errors.append(image_error)

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("add_recipe.html", form=recipe_data)

        # Only save the image once we know the whole form is valid
        image_filename = save_recipe_image(image_file)

        db = get_db()
        cursor = db.execute(
            """
            INSERT INTO recipes (user_id, title, description, ingredients, instructions,
                                 category, difficulty, prep_time, cook_time, servings, image)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                g.user["id"], recipe_data["title"], recipe_data["description"],
                recipe_data["ingredients"], recipe_data["instructions"],
                recipe_data["category"], recipe_data["difficulty"],
                recipe_data["prep_time"], recipe_data["cook_time"], recipe_data["servings"],
                image_filename,
            ),
        )
        db.commit()
        flash("Recipe added successfully!", "success")
        # cursor.lastrowid is the id SQLite gave to the new recipe
        return redirect(url_for("recipe_details", recipe_id=cursor.lastrowid))

    return render_template("add_recipe.html", form={})


# ------------------------------------------------------------------
# Recipes: edit and delete (only the owner is allowed)
# ------------------------------------------------------------------
@app.route("/recipes/<int:recipe_id>/edit", methods=["GET", "POST"])
@login_required
def edit_recipe(recipe_id):
    """Show the filled-in form (GET) and save the changes (POST)."""
    recipe = get_recipe_or_404(recipe_id)

    # Security: hiding the Edit button is not enough - check on the server too
    if not user_owns_recipe(recipe):
        flash("You can only edit your own recipes.", "error")
        return redirect(url_for("recipe_details", recipe_id=recipe_id))

    if request.method == "POST":
        recipe_data, errors = validate_recipe_form(request.form)

        image_file = request.files.get("image")
        image_error = check_image_upload(image_file)
        if image_error:
            errors.append(image_error)

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("edit_recipe.html", recipe=recipe, form=recipe_data)

        # Work out which image the recipe should have after saving
        old_image = recipe["image"]
        new_image = old_image
        uploaded_image = save_recipe_image(image_file)
        if uploaded_image:
            new_image = uploaded_image                 # a new photo replaces the old one
        elif request.form.get("remove_image") == "yes":
            new_image = None                           # user ticked "Remove current image"

        db = get_db()
        db.execute(
            """
            UPDATE recipes
            SET title = ?, description = ?, ingredients = ?, instructions = ?,
                category = ?, difficulty = ?, prep_time = ?, cook_time = ?, servings = ?,
                image = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (
                recipe_data["title"], recipe_data["description"],
                recipe_data["ingredients"], recipe_data["instructions"],
                recipe_data["category"], recipe_data["difficulty"],
                recipe_data["prep_time"], recipe_data["cook_time"], recipe_data["servings"],
                new_image, recipe_id, g.user["id"],
            ),
        )
        db.commit()

        # Delete the old file from disk if it is no longer used
        if old_image and old_image != new_image:
            delete_recipe_image(old_image)

        flash("Recipe updated successfully!", "success")
        return redirect(url_for("recipe_details", recipe_id=recipe_id))

    # dict(recipe) turns the database row into a normal dictionary for the form
    return render_template("edit_recipe.html", recipe=recipe, form=dict(recipe))


@app.route("/recipes/<int:recipe_id>/delete", methods=["POST"])
@login_required
def delete_recipe(recipe_id):
    """Delete a recipe. Its favorites, reviews and ratings are removed automatically
    by the database because of ON DELETE CASCADE."""
    recipe = get_recipe_or_404(recipe_id)

    if not user_owns_recipe(recipe):
        flash("You can only delete your own recipes.", "error")
        return redirect(url_for("recipe_details", recipe_id=recipe_id))

    db = get_db()
    db.execute("DELETE FROM recipes WHERE id = ? AND user_id = ?", (recipe_id, g.user["id"]))
    db.commit()
    delete_recipe_image(recipe["image"])
    flash(f'Recipe "{recipe["title"]}" was deleted.', "success")
    return redirect(url_for("recipes"))


# ------------------------------------------------------------------
# Favorites
# ------------------------------------------------------------------
@app.route("/recipes/<int:recipe_id>/favorite", methods=["POST"])
@login_required
def add_favorite(recipe_id):
    """Save a recipe to the logged-in user's favorites."""
    get_recipe_or_404(recipe_id)
    db = get_db()
    # "OR IGNORE" + the UNIQUE(user_id, recipe_id) rule = no duplicate favorites
    cursor = db.execute(
        "INSERT OR IGNORE INTO favorites (user_id, recipe_id) VALUES (?, ?)",
        (g.user["id"], recipe_id),
    )
    db.commit()

    if cursor.rowcount == 0:
        flash("This recipe is already in your favorites.", "info")
    else:
        flash("Added to your favorites.", "success")
    return redirect_back(url_for("recipe_details", recipe_id=recipe_id))


@app.route("/recipes/<int:recipe_id>/unfavorite", methods=["POST"])
@login_required
def remove_favorite(recipe_id):
    """Remove a recipe from the logged-in user's favorites."""
    db = get_db()
    db.execute(
        "DELETE FROM favorites WHERE user_id = ? AND recipe_id = ?",
        (g.user["id"], recipe_id),
    )
    db.commit()
    flash("Removed from your favorites.", "info")
    return redirect_back(url_for("recipe_details", recipe_id=recipe_id))


@app.route("/recipes/<int:recipe_id>/review", methods=["POST"])
@login_required
def add_review(recipe_id):
    """
    Save the user's star rating + comment for a recipe.
    Each user has at most one review and one rating per recipe;
    submitting again simply updates them.
    """
    recipe = get_recipe_or_404(recipe_id)
    details_url = url_for("recipe_details", recipe_id=recipe_id) + "#reviews"

    if user_owns_recipe(recipe):
        flash("You cannot review your own recipe.", "error")
        return redirect(details_url)

    comment = request.form.get("comment", "").strip()
    rating_text = request.form.get("rating", "")
    errors = []

    rating = None
    if not rating_text:
        errors.append("Please choose a star rating.")
    else:
        rating = parse_whole_number(rating_text, "Rating", MIN_RATING, MAX_RATING, errors)

    if not comment:
        errors.append("Please write a comment.")
    elif len(comment) > MAX_COMMENT_LENGTH:
        errors.append(f"Comments must be at most {MAX_COMMENT_LENGTH} characters.")

    if errors:
        for error in errors:
            flash(error, "error")
        return redirect(details_url)

    db = get_db()
    already_reviewed = db.execute(
        "SELECT 1 FROM reviews WHERE user_id = ? AND recipe_id = ?",
        (g.user["id"], recipe_id),
    ).fetchone()

    # "ON CONFLICT ... DO UPDATE" = insert a new row, or update the existing one
    # if this user already reviewed/rated this recipe (an "upsert").
    db.execute(
        """
        INSERT INTO ratings (user_id, recipe_id, rating) VALUES (?, ?, ?)
        ON CONFLICT (user_id, recipe_id)
        DO UPDATE SET rating = excluded.rating, created_at = CURRENT_TIMESTAMP
        """,
        (g.user["id"], recipe_id, rating),
    )
    db.execute(
        """
        INSERT INTO reviews (user_id, recipe_id, comment) VALUES (?, ?, ?)
        ON CONFLICT (user_id, recipe_id)
        DO UPDATE SET comment = excluded.comment, created_at = CURRENT_TIMESTAMP
        """,
        (g.user["id"], recipe_id, comment),
    )
    db.commit()

    if already_reviewed:
        flash("Your review was updated.", "success")
    else:
        flash("Thanks for your review!", "success")
    return redirect(details_url)


@app.route("/recipes/<int:recipe_id>/review/delete", methods=["POST"])
@login_required
def delete_review(recipe_id):
    """Delete the logged-in user's own review and rating for a recipe."""
    db = get_db()
    db.execute("DELETE FROM reviews WHERE user_id = ? AND recipe_id = ?", (g.user["id"], recipe_id))
    db.execute("DELETE FROM ratings WHERE user_id = ? AND recipe_id = ?", (g.user["id"], recipe_id))
    db.commit()
    flash("Your review was deleted.", "info")
    return redirect(url_for("recipe_details", recipe_id=recipe_id) + "#reviews")


@app.route("/favorites")
@login_required
def favorites():
    """Page listing every recipe the logged-in user has saved."""
    favorite_recipes = fetch_recipes(
        ["recipes.id IN (SELECT recipe_id FROM favorites WHERE user_id = ?)"],
        [g.user["id"]],
    )
    return render_template("favorites.html", recipes=favorite_recipes)


# ------------------------------------------------------------------
# Error pages
# ------------------------------------------------------------------
@app.errorhandler(404)
def page_not_found(error):
    """Show a friendly page when a URL does not exist."""
    return render_template("404.html"), 404


@app.errorhandler(RequestEntityTooLarge)
def file_too_large(error):
    """Runs when an upload is bigger than MAX_CONTENT_LENGTH (error 413)."""
    flash(f"That image is too large. The maximum size is {MAX_UPLOAD_MB} MB.", "error")
    return redirect(request.url)


# ------------------------------------------------------------------
# Start the development server
# ------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
