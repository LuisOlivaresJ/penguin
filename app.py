from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import os, shutil


from helpers import (apology, login_required, check_extensions_and_save_to_db,
    DATETIME_FORMAT, create_epid_position_figure)
import logging

UPLOAD_FOLDER = "./uploads"

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 6 * 1000 * 1000

Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///penguin.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
#@login_required
def index():
    """Show EPID positioning tendency."""

    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        username = request.form.get("username")
        if not username:
            return apology("Must provide a username")

        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        # Check that password and confirmation are given
        if not all([password, confirmation]):
            return apology("Must provide a password and confirm it.")
        # Check if both passwords are equal
        if password != confirmation:
            return apology("Passwords are not the same")

        # Create a hash from password
        hashed_password = generate_password_hash(password)

        try:
            db.execute(
                "INSERT INTO users (username, hash) VALUES (?, ?)",
                username,
                hashed_password
            )

        except:
            return apology("The given user aldready exists")

        return redirect("/epid")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/epid")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/epid", methods=["GET", "POST"])
@login_required
def epid():
    """Show history of EPID QA measurements."""

    # User reached route via GET (as by submitting a form via GET)
    if request.args.get("plot_type"):

        buf_fig = create_epid_position_figure(
            request.args.get("plot_type"),
            session["user_id"],
            db
            )
    else:
        # Show reference position
        buf_fig = _get_default_plot()


    return render_template("epid.html", buf_fig = buf_fig)


@app.route("/epid_input_img", methods=["POST"])
@login_required
def epid_input_img():
    """Show reference position reproducibility."""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        logging.info("Entrando a la función epid_input_img con método POST")

        # Check if the POST request has the file part
        if not request.files:
            logging.info("The post request must have a file part.")
            return apology("Must provide a file")

        # Identify which form has activated the POST.
        files = request.files.getlist("positioning_input_files")

        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if files[0].filename == '':
            flash('No selected file')
            return redirect("/epid")

        # Check for allowed files extensions and save them.
        check_extensions_and_save_to_db(files, app.config["UPLOAD_FOLDER"], db)

        # Delete the uploaded files
        for filename in os.listdir(app.config["UPLOAD_FOLDER"]):
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))

        return redirect("/epid")


@app.route("/vmat", methods=["GET", "POST"])
@login_required
def vmat():
    """Get stock quote."""
    return apology("TODO")


@app.route("/ct", methods=["GET", "POST"])
@login_required
def ct():
    """Sell shares of stock"""
    return apology("TODO")


def _get_default_plot():
    # Check if there is data on the database
    rows = db.execute(
        """
        SELECT * FROM positions
        WHERE user_id = ?
        LIMIT 1
        """,
        session["user_id"]
        )

    if len(rows) == 0:
        return None

    else:
        return create_epid_position_figure("reference", session["user_id"], db)
