import requests
import os

from flask import redirect, render_template, session, request
from functools import wraps
import logging
import werkzeug
from werkzeug.utils import secure_filename

from pylinac import FieldProfileAnalysis
from pylinac.core.profile import ProfileMetric
import matplotlib.pyplot as plt

from datetime import datetime
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from io import BytesIO
import base64


ALLOWED_EXTENSIONS = {"dcm"}
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def allowed_file(filename: str) -> bool:
    return "." in filename and \
        filename.rsplit("." , 1)[1].lower() in ALLOWED_EXTENSIONS


def get_data_for_positions(filename: str) -> dict:

    logging.info("Inside helpers.py get_position")
    logging.info(f"{filename=}")


    class CenterMetric(ProfileMetric):
        """Plugin to get the beam center, as required by pylinac."""
        name = "Center Index"


        def calculate(self) -> float:
            """Return the index of the center of the profile."""
            return self.profile.center_idx


        def plot(self, axis: plt.Axes) -> None:
            "Plot the center index."
            axis.plot(
                self.profile.center_idx,
                self.profile.y_at_x(self.profile.center_idx),
                "o",
                color="red",
                markersize=10,
                label=self.name,
            )

    fa = FieldProfileAnalysis(filename)
    fa.analyze(
        x_width = 0.02,
        y_width = 0.02,
        metrics=[CenterMetric()])

    # Distance from beam center to panel center in X and Y (mm)
    x = (fa.image.center.x - fa.results_data().x_metrics.get("Center Index"))/fa.image.dpmm
    y = (fa.image.center.y - fa.results_data().y_metrics.get("Center Index"))/fa.image.dpmm

    # Date
    date_created = fa.image.date_created(format=DATETIME_FORMAT)

    # Source to image plane distance and gantry angle
    sid = float(fa.image.metadata['RTImageSID'].value)
    gantry_angle = float(fa.image.metadata['GantryAngle'].value)

    return {
        "Date": date_created,
        "SID": sid,
        "Gantry": gantry_angle,
        "X": round(x, 5),
        "Y": round(y, 5),
        }


def check_extensions_and_save_to_db(
        files: list,
        upload_folder: str,
        db,
        ):
    """
    Check if the uploaded files have correct extensions, calculate results
    and save them to the database.
    """

    logging.info(f"Inside check_extension_and_save function")
    logging.info(f"The uploaded files are {files}")
    logging.info(f"First item is of the type: {type(files[0])}")

    for file in files:
        if  file and allowed_file(file.filename):
            filename = secure_filename(file.filename)

            path_to_file = os.path.join(upload_folder, filename)
            file.save(path_to_file)

            # Get data from the file (panel position, date, etc.)
            data = get_data_for_positions(path_to_file)
            logging.info("Geting data for positions")
            logging.info(data)

            # If database is empty, use the given files as reference
            rows = db.execute(
                """
                SELECT *
                FROM positions
                LIMIT 1
                """
            )
            if len(rows) != 0:
                reference = 0
            else:
                reference = 1

            # Save to database
            db.execute(
                """
                INSERT INTO positions
                (date, sid, gantry_angle, panel_position_x, panel_position_y, reference)
                VALUES
                (?, ?, ?, ?, ?, ?)
                """,
                data.get("Date"), data.get("SID"), data.get("Gantry"), data.get("X"), data.get("Y"), reference
            )


def create_epid_position_figure(plot_type: str, user: int, db):
    """Creates a figure to show epid positions reproducibility"""

    if plot_type == "reference":

        data = db.execute(
            """
            SELECT * FROM positions
            WHERE gantry_angle = 0.0
            AND sid = 1000.0
            AND user_id = ?
            """,
            user
        )

        reference = db.execute(
            """
            SELECT * FROM positions
            WHERE reference = 1
            AND user_id = ?
            """,
            user
        )

        ref_x = reference[0].get("panel_position_x")
        ref_y = reference[0].get("panel_position_y")

        dx = []
        dy = []
        date = []

        for row in data:
            diff_x = row.get("panel_position_x") - ref_x
            diff_y = row.get("panel_position_y") - ref_y
            dx.append(diff_x)
            dy.append(diff_y)
            date.append(
                datetime.strptime(row.get("date"), DATETIME_FORMAT)
                )

        fig = Figure(figsize=(5,3), layout = 'constrained')
        ax = fig.subplots()
        ax.plot(date, dx, marker="o", color="blue", label="x")
        ax.plot(date, dy, marker="o", color="green", label="y")
        #ax.set_title("Reference position reproducibility")
        # Change date format
        ax.xaxis.set_major_formatter(
            mdates.ConciseDateFormatter(ax.xaxis.get_major_locator())
            )
        ax.axhline(2, linestyle = "--", linewidth = 3, color = "g", alpha = 0.7)
        ax.axhline(-2, linestyle = "--", linewidth = 3, color = "g", alpha = 0.7)
        ax.grid(which="both")
        ax.set_ylim(bottom = -5, top = 5)
        ax.legend(loc = 'upper right')
        ax.set_ylabel("Variation [mm]")
        # Save it to a temporary buffer.
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=100)
        # Embed the result in the html output.
        buf_fig = base64.b64encode(buf.getbuffer()).decode("ascii")


    elif plot_type == "sid":

        # Find the last date
        dates_list = db.execute(
            """
            SELECT date FROM positions
            WHERE gantry_angle = 0.0
            AND sid = 1000.0
            AND user_id = ?
            """,
            user
        )

        dates = []
        for item in dates_list:
            dates.append(
                datetime.strptime(item.get("date"), DATETIME_FORMAT)
            )

        dates.sort(reverse=True)
        last_date = dates[0].strftime("%Y-%m-%d")
        last_date_query = last_date + "%"

        # Get last day positions
        data_last_date = db.execute(
            """
            SELECT * FROM positions
            WHERE date LIKE ?
            AND user_id = ?
            """,
            last_date_query,
            user
        )

        # Get last day positions for reference position
        reference_data = db.execute(
            """
            SELECT * FROM positions
            WHERE date LIKE ?
            AND user_id = ?
            AND sid = (
                SELECT sid FROM positions
                WHERE reference = 1
                AND user_id = ?
                )
            """,
            last_date_query,
            user,
            user,
        )

        x_ref = reference_data[0].get("panel_position_x")
        y_ref = reference_data[0].get("panel_position_y")

        dx = []
        dy = []
        sid = []

        for item in data_last_date:
            dx.append(item.get("panel_position_x") - x_ref)
            dy.append(item.get("panel_position_y") - y_ref)
            sid.append(item.get("sid"))

        fig = Figure(figsize=(5,3), layout = 'constrained')
        ax = fig.subplots()
        ax.plot(sid, dx, marker="o", color="blue", label="x")
        ax.plot(sid, dy, marker="o", color="green", label="y")
        ax.set_title(f"Date {last_date}")
        ax.set_xlabel("Source to image plane distance [mm]")
        # Change date format

        ax.axhline(2, linestyle = "--", linewidth = 3, color = "g", alpha = 0.7)
        ax.axhline(-2, linestyle = "--", linewidth = 3, color = "g", alpha = 0.7)
        ax.grid(which="both")
        ax.set_ylim(bottom = -5, top = 5)
        ax.legend(loc = 'upper right')
        ax.set_ylabel("Variation [mm]")
        # Save it to a temporary buffer.
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=100)
        # Embed the result in the html output.
        buf_fig = base64.b64encode(buf.getbuffer()).decode("ascii")

    elif plot_type == "g_rotation":
        buf_fig = None


    return buf_fig
