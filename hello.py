from http import server
from flask import Flask, flash, render_template, request, redirect, url_for, session
import sqlite3, os
from werkzeug.utils import secure_filename
import subprocess

import db_utils

app = Flask(__name__, static_url_path="/static", static_folder="static")
app.secret_key = b'_5#yswq2L"F4Q8z\n\xec]/'

# Database for user info.
DATABASE_PATH = "users.db"

# Database object
db_obj = db_utils.Db(DATABASE_PATH, db_utils.DbType.SQLITE)  #   SQLite
# db_obj = db_utils.Db(DATABASE_PATH, db_utils.DbType.MYSQL) #  MySQL


def init() -> None:
    """Handles init for the server.

    Expect this to run on startup only.
    """
    db_obj.dbInit()
    return


# Initialise the server.
init()

# Add table for posts with cols post_id, message (prob md), likes, poster_id


@app.route("/")
def index():
    print(session.keys())
    if ("userid" in session) or ("username" in session):
        return redirect(f'/home/{session["username"]}')
    return redirect("/login")


# Route exists to be able to debug issues related to data sent/recieved.
# Feel free to point any api to this endpoint for testing
@app.route("/echo")
def echo():
    return render_template("echo.html", method=request.method)


@app.route("/home/<username>", methods=["GET", "POST"])
def home(username):
    print(session.keys())
    if ("userid" not in session) or ("username" not in session):
        # Not logged in
        return redirect("/login")
    else:
        if session["username"] != username:
            # logged in as a different user
            return redirect("/login")
    user = db_obj.getUser(username)

    if user is not None:
        return render_template(
            "home.html",
            username=user["username"],
            profile_picture=user["profile_picture"],
        )
    else:
        # Handle user not found
        error_message = "User not found"
        return render_template("error.html", error_message=error_message)


@app.route("/signup", methods=["POST", "GET"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        profile_picture = request.files["profile_picture"]
        print(type(profile_picture))
        db_obj.createUser(
            username=username,
            password=password,
            email=email,
            profile_picture=profile_picture,
        )
        return redirect(url_for("home", username=username))
    elif request.method == "GET":
        return render_template("signup.html", username="")
    else:
        return render_template("signup.html", username="")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = db_obj.validateUser(userName=username, password=password)

        if user is not None:
            session["userid"] = user["id"]
            session["username"] = user["username"]
            # print(session.keys())
            # print(session.items())
            return redirect(url_for("home", username=user["username"]))
        else:
            error_message = "Invalid username or password"
            flash(error_message, "error")
            print("Flashing message...")
            return redirect("/login")

    return render_template("login.html", username="")


@app.route("/logout")
def logout():
    session.pop("userid", None)
    session.pop("username", None)
    # print(session.keys())
    # print(session.items())
    flash("You have been successfully logged out!", "success")
    return redirect(url_for("login"))


@app.route("/account/<username>")
def account(username):
    if ("userid" not in session) or ("username" not in session):
        # Not logged in
        return redirect("/login")
    else:
        if session["username"] != username:
            # logged in as a different user
            return redirect("/login")
    res = db_obj.getUser(username=username)

    if res is not None:
        return render_template(
            "account_new.html",
            username=res["username"],
            email=res["email"],
            profile_picture=res["profile_picture"],
        )
    else:
        error_message = "User not found"
        return render_template("error.html", error_message=error_message, username="")


@app.route("/change_password/<username>")
def change_password_page(username):
    if ("userid" not in session) or ("username" not in session):
        # Not logged in
        return redirect("/login")
    else:
        if session["username"] != username:
            # logged in as a different user
            return redirect("/login")
    return render_template("change_password.html", username=username)


@app.route("/change_password/<username>", methods=["POST"])
def change_password(username):
    old_password = request.form["old_password"]
    new_password = request.form["new_password"]
    if ("userid" not in session) or ("username" not in session):
        # Not logged in
        return redirect("/login")
    else:
        if session["username"] != username:
            # logged in as a different user
            return redirect("/login")
    res = db_obj.updatePassword(
        username=username, oldPassword=old_password, newPassword=new_password
    )
    res1 = db_obj.getUser(username)

    if res1 is None:
        return redirect("/")

    if res is not None:
        # success_message = "Password changed successfully"
        flash("Password changed successfully!", "success")
        return render_template(
            "account_new.html",
            username=res1["username"],
            email=res1["email"],
            profile_picture=res1["profile_picture"],
            # success_message=success_message,
        )
    else:
        # error_message = "Incorrect old password"
        flash("Incorrect old password!", "error")
        return render_template(
            "account_new.html",
            username=res1["username"],
            email=res1["email"],
            profile_picture=res1["profile_picture"],
            # error_message=error_message,
        )


@app.route("/upload_profile_picture/<username>")
def upload_profile_picture_page(username):
    if ("userid" not in session) or ("username" not in session):
        # Not logged in
        return redirect("/login")
    else:
        if session["username"] != username:
            # logged in as a different user
            return redirect("/login")
    return render_template("upload_profile_picture.html", username=username)


@app.route("/upload_profile_picture/<username>", methods=["POST"])
def upload_profile_picture(username):
    if ("userid" not in session) or ("username" not in session):
        # Not logged in
        return redirect("/login")
    else:
        if session["username"] != username:
            # logged in as a different user
            return redirect("/login")
    profile_picture = request.files["profile_picture"]

    db_obj.updatePicture(username=username, new_profile_picture=profile_picture)
    return redirect(url_for("account", username=username))


@app.route("/delete_account/<username>")
def delete_account(username):
    if ("userid" not in session) or ("username" not in session):
        # Not logged in
        return redirect("/login")
    else:
        if session["username"] != username:
            # logged in as a different user
            return redirect("/login")
    db_obj.deleteUser(username=username)

    # Redirect to a page indicating successful account deletion
    return redirect(url_for("account_deleted"))


@app.route("/account_deleted")
def account_deleted():
    # return "Your account has been deleted successfully."
    flash("Your account has been deleted successfully!", "success")
    return redirect("/")


@app.route("/post")
def create_post():
    return render_template("test.html")


@app.route("/users-data-all")
def get_dict():
    res = db_obj.dumpUsers()
    return render_template("list.html", data=res, username="")


@app.errorhandler(404)
def page_not_found(err):
    return render_template("404.html"), 404


ex_name = "Leslie Alexander"
ex_pic = "https://images.unsplash.com/photo-1494790108377-be9c29b29330?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80"
ex_email = "leslie.alexander@example.com"


@app.route("/design/<page>")
def serve_design_template(page: str) -> str:
    # Adding a few flashes for testing purposes
    # flash("This an error message that should be flashed!", category="error")
    # flash("This a warning message that should be flashed!", category="warning")
    # flash("This an informational message that should be flashed!", category="info")
    # flash("This a success message that should be flashed!", category="success")
    # flash("This a miscellaneous message that should be flashed!", category="")
    return render_template(
        page, poll=page, username=ex_name, profile_picture=ex_pic, email=ex_email
    )


cnt_map: dict[str, bytes] = {}

base_layout_path = os.path.join(os.getcwd(), "templates", "layout.html")

base_layout_new_path = os.path.join(os.getcwd(), "templates", "layout_new.html")

css_path = os.path.join(os.getcwd(), "static", "css", "output.css")

server_path = os.path.join(os.getcwd(), "hello.py")


@app.route("/design/poll_page/<page>")
def is_page_modified(page: str):
    # Returns `'true'` if the page has been modified since the last time it was polled
    path = os.path.join(os.getcwd(), "templates", page)
    file_bytes: bytes
    is_changed = False
    with open(path, "rb") as f:
        file_bytes = f.read()
        if path not in cnt_map:
            cnt_map[path] = file_bytes
            # is_changed = False
        else:
            if cnt_map[path] != file_bytes:
                is_changed = True
                cnt_map[path] = file_bytes
        f.close()
    path = base_layout_path
    with open(path, "rb") as f:
        file_bytes = f.read()
        if path not in cnt_map:
            cnt_map[path] = file_bytes
            # is_changed = False
        else:
            if cnt_map[path] != file_bytes:
                is_changed = True
                cnt_map[path] = file_bytes
        f.close()
    path = base_layout_new_path
    with open(path, "rb") as f:
        file_bytes = f.read()
        if path not in cnt_map:
            cnt_map[path] = file_bytes
            # is_changed = False
        else:
            if cnt_map[path] != file_bytes:
                is_changed = True
                cnt_map[path] = file_bytes
        f.close()
    path = server_path
    with open(path, "rb") as f:
        file_bytes = f.read()
        if path not in cnt_map:
            cnt_map[path] = file_bytes
            is_changed = True
        else:
            if cnt_map[path] != file_bytes:
                is_changed = True
                cnt_map[path] = file_bytes
        f.close()
    # HACK: This part is very inefficient. Proper approach would be to monitor relevant directories and do it accordingly.
    # A better approach that could exist in a seperate thread is outlined in https://stackoverflow.com/a/28319191
    subprocess.call(
        [
            "tailwindcss.exe",
            "-i",
            "static/css/input.css",
            "-o",
            "static/css/output.css",
        ],
    )
    path = css_path
    with open(path, "rb") as f:
        file_bytes = f.read()
        if path not in cnt_map:
            cnt_map[path] = file_bytes
            is_changed = True
        else:
            if cnt_map[path] != file_bytes:
                is_changed = True
                cnt_map[path] = file_bytes
        f.close()
    return str(1) if is_changed else str(0)


if __name__ == "__main__":
    app.run(debug=True)
