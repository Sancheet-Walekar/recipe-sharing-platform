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
# Routes
# ------------------------------------------------------------------
@app.route("/")
def index():
    """Home page."""
    return render_template("index.html")


# ------------------------------------------------------------------
# Start the development server
# ------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
