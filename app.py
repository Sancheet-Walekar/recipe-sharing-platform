"""
RecipeShare - main Flask application.

Run it with:
    python app.py
Then open http://127.0.0.1:5000 in your browser.
"""

import os

from flask import Flask, render_template

# ------------------------------------------------------------------
# App setup
# ------------------------------------------------------------------
app = Flask(__name__)

# The secret key signs the session cookie. In real deployments set the
# SECRET_KEY environment variable; the fallback is only for local development.
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")

# ------------------------------------------------------------------
# Settings used across the app
# ------------------------------------------------------------------
CATEGORIES = [
    "Indian", "Italian", "Mexican", "Chinese", "American", "Healthy",
    "Dessert", "Breakfast", "Lunch", "Dinner", "Other",
]
DIFFICULTIES = ["Easy", "Medium", "Hard"]


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
