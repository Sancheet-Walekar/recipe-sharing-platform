# Recipe Sharing Platform

**RecipeShare** is a beginner-friendly recipe sharing website built with
Python (Flask), SQLite and plain HTML, CSS and JavaScript.
It runs completely on your own computer (localhost) and needs no internet
connection or external services once the dependencies are installed.

---

## Project Description

RecipeShare lets people create an account, share their own recipes (with a
photo), browse and search recipes from other users, save favourites, and
leave star ratings and reviews.

Everything is stored locally:

- user accounts, recipes, favourites, reviews and ratings live in a **SQLite**
  database file (`database.db`)
- recipe photos are saved in the `static/uploads/recipes/` folder

The code is intentionally simple (normal Flask routes, Jinja2 templates, no
frameworks) and full of comments so that beginners can read and learn from it.

---

## Features

**Accounts**
- Register with name, email and password (validated on the server)
- Duplicate emails are rejected; passwords must be at least 6 characters
- Passwords are stored as secure hashes (never as plain text)
- Log in / log out using Flask sessions
- The navigation bar changes depending on whether you are logged in

**Recipes**
- Create recipes with title, description, ingredients, instructions,
  category, difficulty, preparation time, cooking time, servings and an
  optional photo
- View all recipes as cards (image, title, category, difficulty, total time,
  average rating, short description, author)
- Recipe details page with numbered steps and an ingredient list
- Edit and delete **your own** recipes only (checked on the server, not just
  hidden buttons), with a confirmation before deleting

**Images**
- Photos are uploaded and stored locally in `static/uploads/recipes/`
- Only JPG, JPEG, PNG and WEBP files up to 2 MB are accepted
- The file content is checked, and every file gets a random safe name
- Recipes without a photo show a placeholder image

**Finding recipes**
- Search by title, description, category or ingredient
- Filter by category and by difficulty
- Search and filters can be combined (e.g. "pasta" + Italian + Easy)

**Community**
- Add and remove favourites (no duplicates) and see them on a Favourites page
- Rate recipes from 1 to 5 stars and write a review
- Average rating shown on recipe cards and the details page
- Update or delete your own review; you cannot review your own recipe

**Profile**
- Your name, email and "member since" date
- Counts of your recipes, favourites and reviews
- A list of all recipes you have shared

**Other**
- Responsive design (phones, tablets and desktops) with a mobile menu
- Friendly flash messages for success and errors
- Custom 404 page, plus friendly handling of too-large uploads and wrong URLs

---

## Technology Stack

| Part            | Technology                       |
|-----------------|----------------------------------|
| Structure       | HTML5                            |
| Styling         | CSS3 (Flexbox + Grid, no frameworks) |
| Interactivity   | Vanilla JavaScript               |
| Backend         | Python + Flask                   |
| Templates       | Jinja2 (comes with Flask)        |
| Database        | SQLite (built into Python)       |
| Version control | Git / GitHub                     |

The only package you need to install is **Flask** (it brings Werkzeug and
Jinja2 with it).

---

## Project Structure

```
recipe/
├── app.py                  # Flask app: settings, helpers and all routes
├── database.py             # SQLite connection + table definitions
├── init_db.py              # Run once to create the database tables
├── requirements.txt        # Python packages to install (just Flask)
├── README.md               # This file
├── .gitignore              # Files Git should NOT save (venv, database, ...)
│
├── templates/              # Jinja2 HTML templates
│   ├── base.html           # Main layout: navbar, flash messages, footer
│   ├── index.html          # Home page
│   ├── login.html
│   ├── register.html
│   ├── recipes.html        # Recipe list + search + filters
│   ├── recipe_details.html # One recipe + reviews
│   ├── add_recipe.html
│   ├── edit_recipe.html
│   ├── favorites.html
│   ├── profile.html
│   ├── 404.html            # Error page
│   ├── _recipe_card.html        # Reusable recipe card
│   ├── _recipe_form_fields.html # Form fields shared by add + edit
│   └── _stars.html              # Reusable star display
│
├── static/
│   ├── css/style.css       # All styles
│   ├── js/script.js        # Small interface helpers
│   ├── images/             # Logo and placeholder image
│   └── uploads/recipes/    # Uploaded recipe photos (not saved in Git)
│
└── database.db             # Created by init_db.py (not saved in Git)
```

Files starting with `_` are small pieces included by other templates so the
same HTML is not copied into several files.

---

## Requirements

- **Python 3.9 or newer** (tested with Python 3.10 and 3.14).
  Check with `python --version` (on Linux/macOS: `python3 --version`).
  Download from <https://www.python.org/downloads/>.
  **Windows:** tick **"Add python.exe to PATH"** during installation.
- **Git** (to clone the project and use version control).
  Check with `git --version`. Download from <https://git-scm.com/downloads>.
  On Windows this also installs **Git Bash**.
- A web browser (Chrome, Firefox, Edge, ...).
- Internet is only needed once, to download Flask with `pip`.

---

## Installation

Follow the steps for your system. Every command is typed in a terminal.

### 1. Clone (or download) the project

```bash
git clone https://github.com/Sancheet-Walekar/recipe-sharing-platform.git
```

No Git? On the GitHub page click **Code → Download ZIP** and unzip it.

> The repository is private. You need to be added as a collaborator and be
> logged in to GitHub (for example with `gh auth login`) to clone it.

### 2. Open the project folder

```bash
cd recipe-sharing-platform
```

(If you downloaded the ZIP, `cd` into the unzipped folder instead.)
You are in the right place when you can see `app.py` with `ls` (or `dir` on
Windows Command Prompt).

### 3. Create a virtual environment

A virtual environment (`venv`) is a private folder of Python packages just for
this project.

| System | Command |
|--------|---------|
| Windows (Git Bash / PowerShell / CMD) | `python -m venv venv` |
| Linux / macOS | `python3 -m venv venv` |

> Linux (Ubuntu/Debian): if you get *"ensurepip is not available"*, run
> `sudo apt install python3-venv` and try again.

### 4. Activate the virtual environment

| System | Command |
|--------|---------|
| Windows **Git Bash** | `source venv/Scripts/activate` |
| Windows **PowerShell** | `venv\Scripts\Activate.ps1` |
| Windows **Command Prompt (CMD)** | `venv\Scripts\activate.bat` |
| Linux / macOS | `source venv/bin/activate` |

When it works, your prompt starts with `(venv)`.
After activation, `python` and `pip` refer to the venv on every system.

> PowerShell error *"running scripts is disabled on this system"*? Run this
> once, then activate again:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

### 5. Install the dependencies

```bash
python -m pip install -r requirements.txt
```

### 6. Initialize the database

```bash
python init_db.py
```

This creates `database.db` with all tables. It is safe to run again later -
existing data is never deleted.

### 7. Run the application

```bash
python app.py
```

### Quick copy-paste: Windows Git Bash

```bash
git clone https://github.com/Sancheet-Walekar/recipe-sharing-platform.git
cd recipe-sharing-platform
python -m venv venv
source venv/Scripts/activate
python -m pip install -r requirements.txt
python init_db.py
python app.py
```

### Quick copy-paste: Linux / macOS

```bash
git clone https://github.com/Sancheet-Walekar/recipe-sharing-platform.git
cd recipe-sharing-platform
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python init_db.py
python app.py
```

**Next time** you only need to open the folder, activate the venv (step 4) and
run `python app.py`.

---

## Running the Application

```bash
python app.py
```

You will see something like:

```
 * Running on http://127.0.0.1:5000
 * Debugger is active!
```

Open your browser at **<http://127.0.0.1:5000>**.

Stop the server with **Ctrl + C** in the terminal.

The app runs in **debug mode**: the server restarts automatically when you
save a Python file, and errors show a detailed page. Debug mode is meant for
learning on your own computer only.

### The secret key (SECRET_KEY)

Flask signs the login session cookie with a secret key. `app.py` reads it
from an environment variable:

```python
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")
```

- If `SECRET_KEY` is **not** set, the fallback `"dev-only-change-me"` is used.
  That is fine for learning on localhost.
- If you ever put the app on a real server, set your own random key and never
  commit it to Git. Generate one with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Then set it **before** `python app.py` (in the same terminal):

| System | Command |
|--------|---------|
| Git Bash / Linux / macOS | `export SECRET_KEY="paste-your-key-here"` |
| PowerShell | `$env:SECRET_KEY="paste-your-key-here"` |
| Command Prompt (CMD) | `set SECRET_KEY=paste-your-key-here` |

---

## Database

The app uses **SQLite**, a database stored in a single file
(`database.db`). It is built into Python, so there is no database server to
install. The file is ignored by Git, so every developer has their own local
data.

`init_db.py` (and `app.py` on start-up) run `CREATE TABLE IF NOT EXISTS ...`
for every table, so running them again never deletes data.

| Table | Purpose | Important columns / rules |
|-------|---------|---------------------------|
| `users` | Accounts | `id`, `name`, `email` (**unique**), `password` (a **hash**), `created_at` |
| `recipes` | Recipes | `id`, `user_id` → users, `title`, `description`, `ingredients`, `instructions`, `category`, `difficulty` (Easy/Medium/Hard), `prep_time`, `cook_time`, `servings`, `image` (file name only), `created_at`, `updated_at` |
| `favorites` | Saved recipes | `user_id` → users, `recipe_id` → recipes, **unique (user_id, recipe_id)** so no duplicates |
| `reviews` | Comments | `user_id`, `recipe_id`, `comment`, `created_at`, one review per user per recipe |
| `ratings` | Stars | `user_id`, `recipe_id`, `rating` (**CHECK 1-5**), `created_at`, one rating per user per recipe |

- **Foreign keys** connect the tables. Deleting a recipe automatically
  deletes its favourites, reviews and ratings (`ON DELETE CASCADE`).
- All queries use **parameters** (`?`) instead of gluing user input into
  SQL, which protects against SQL injection.

**Start with an empty database:** stop the app, delete `database.db`, then
run `python init_db.py` again. (Uploaded photos stay in
`static/uploads/recipes/`; delete them by hand if you like.)

---

## User Flow

```
Register → Login → Add Recipe → Browse Recipes → Favorite → Review → Profile
```

1. **Register** - click *Register*, enter name, email and password.
2. **Login** - log in with your email and password.
3. **Add Recipe** - click *Add Recipe*, fill in the form, optionally upload a
   photo, and publish.
4. **Browse Recipes** - open *Recipes*, search (e.g. "pasta") and filter by
   category and difficulty. Click a card to open the recipe.
5. **Favorite** - on a recipe page click *Add to favorites*; see all saved
   recipes on the *Favorites* page.
6. **Review** - on someone else's recipe choose 1-5 stars, write a comment
   and submit. Submit again to update it.
7. **Profile** - see your details, statistics and your own recipes. From a
   recipe you own you can *Edit* or *Delete* it.

Tip: register two accounts (e.g. in a normal and a private browser window)
to try favourites and reviews on each other's recipes.

---

## Security Basics

- Passwords are hashed with Werkzeug's `generate_password_hash()` and checked
  with `check_password_hash()`.
- Every SQL query uses `?` parameters (no string concatenation).
- Edit/delete routes check on the **server** that you own the recipe.
- All forms are validated on the server (JavaScript checks are only extra
  help for the user).
- Uploaded files: allowed extensions only, content check, `secure_filename()`,
  random file names, 2 MB limit.
- Actions that change data (logout, delete, favourite, review) use POST forms.
- The secret key can come from an environment variable; no passwords or keys
  are stored in the code or in Git.

---

## Git Workflow

Basic commands for saving your work:

```bash
git status                     # what changed?
git add .                      # stage all changes
git commit -m "Describe what you changed"
git push                       # upload commits to GitHub
```

Other useful commands:

```bash
git log --oneline              # history of commits
git pull                       # download changes from GitHub
git diff                       # see exact line changes before committing
```

`.gitignore` makes sure these are **never** committed: `venv/`,
`__pycache__/`, `*.pyc`, `*.db` (the database), `.env`, `.vscode/` and
uploaded photos.

---

## Troubleshooting

**`pip` not found / `pip is not recognized`**
Use `python -m pip ...` instead of `pip ...`. If `python` itself is not found
on Windows, reinstall Python and tick *"Add python.exe to PATH"*, or try
`py -m venv venv`. On Linux/macOS use `python3`.

**`ModuleNotFoundError: No module named 'flask'`**
The virtual environment is not active or Flask is not installed in it.
Activate it (step 4 - your prompt should show `(venv)`) and run
`python -m pip install -r requirements.txt`.

**Port already in use (`Address already in use` / port 5000 is busy)**
Another program (or another copy of the app) is using port 5000. Stop the
other terminal with Ctrl + C, or run on another port:
`flask --app app run --debug --port 5001` and open
<http://127.0.0.1:5001>. On macOS, *AirPlay Receiver* may use port 5000 -
turn it off in System Settings or use another port.

**Database not initialized / `no such table`**
Run `python init_db.py` from the project folder (the folder that contains
`app.py`). The app also creates missing tables when it starts.

**`jinja2.exceptions.TemplateNotFound`**
You are probably running the app from the wrong folder, or a template was
renamed/moved. `cd` into the folder that contains `app.py` and the
`templates/` folder, then run `python app.py`.

**Static files (CSS/JS/images) not loading - the page looks unstyled**
Make sure the `static/` folder is next to `app.py`, then do a hard refresh in
the browser (**Ctrl + F5**, or **Cmd + Shift + R** on macOS) to clear cached
files.

**"That image is too large"**
Photos must be 2 MB or smaller. Resize or compress the image and try again.

**Logged out after restarting the app**
This can happen if `SECRET_KEY` changed between runs. Just log in again.

**PowerShell will not activate the venv**
See the tip under step 4 (`Set-ExecutionPolicy ...`).

---

## Future Improvements

Ideas that are **not** implemented yet:

- CSRF protection for forms (e.g. with Flask-WTF)
- Pagination for long recipe lists
- Password reset by email and editable user profiles
- Public author pages ("all recipes by this user")
- Sorting recipes by rating, newest or cooking time
- Image resizing/thumbnails (e.g. with Pillow)
- Recipe tags, printable recipes and shopping lists
- Automated tests with `pytest`
- Deployment to a real server with a production WSGI server (e.g. Waitress
  or Gunicorn) and debug mode turned off
