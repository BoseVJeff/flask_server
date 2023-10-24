from flask import Flask, render_template, request, redirect, url_for
import sqlite3, os
from werkzeug.utils import secure_filename

import db_utils

app = Flask(__name__, static_url_path="/static", static_folder="static")

# Database for user info.
DATABASE_PATH = "users.db"

# DONE: Remove this after transition to `db_obj` is complete
# DATABASE = DATABASE_PATH

# Database object
db_obj = db_utils.Db(DATABASE_PATH, db_utils.DbType.SQLITE)
# db_obj = db_utils.Db(DATABASE_PATH, db_utils.DbType.MYSQL)


def init() -> None:
    """Handles init for the server.

    Expect this to run on startup only.
    """
    db_obj.dbInit()
    return


# Initialise the server.
init()

# Add table for posts with cols post_id, message (prob md), likes, poster_id

# Replaced with `db_obj.is<Username/Email>Taken()`.
# def is_username_taken(username):
#     conn = sqlite3.connect(DATABASE)
#     cursor = conn.cursor()
#     cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
#     user = cursor.fetchone()
#     conn.close()
#     return user is not None


# def is_email_taken(email):
#     conn = sqlite3.connect(DATABASE)
#     cursor = conn.cursor()
#     cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
#     user = cursor.fetchone()
#     conn.close()
#     return user is not None


@app.route("/")
def index():
    return render_template("login.html", username="")


# Route exists to be able to debug issues related to data sent/recieved.
# Feel free to point any api to this endpoint for testing
@app.route("/echo")
def echo():
    return render_template("echo.html", method=request.method)


@app.route("/home/<username>", methods=["GET", "POST"])
def home(username):
    # conn = sqlite3.connect(DATABASE)
    # cursor = conn.cursor()
    # cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    # user = cursor.fetchone()
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
        # TODO: add error.html file
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
        # if profile_picture:
        #     profile_picture_filename = secure_filename(profile_picture.filename)
        #     if not os.path.exists("static/profile_pictures"):
        #         os.mkdir("static/profile_pictures")
        #     profile_picture_path = os.path.join(
        #         "static/profile_pictures", profile_picture_filename
        #     )
        #     profile_picture.save(profile_picture_path)
        # else:
        #     profile_picture_filename = None

        # conn = sqlite3.connect(DATABASE)
        # cursor = conn.cursor()
        # cursor.execute(
        #     "INSERT INTO users (username, email, password, profile_picture) VALUES (?, ?, ?, ?)",
        #     (username, email, password, profile_picture_filename),
        # )
        # conn.commit()
        # conn.close()
        # db_obj.createUser(
        #     username=username,
        #     password=password,
        #     profile_picture=profile_picture,
        #     email=email,
        # )

        return redirect(url_for("home", username=username))
    elif request.method == "GET":
        return render_template("signup.html", username="")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = db_obj.validateUser(userName=username, password=password)

        if user is not None:
            return redirect(url_for("home", username=user["username"]))
        else:
            error_message = "Invalid username or password"
            return render_template("login.html", error_message=error_message)

    return render_template("login.html", username="")


@app.route("/logout")
def logout():
    return redirect(url_for("login"))


@app.route("/account/<username>")
def account(username):
    # conn = sqlite3.connect(DATABASE)
    # cursor = conn.cursor()
    # cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    # user = cursor.fetchone()
    # conn.close()
    res = db_obj.getUser(username=username)

    if res is not None:
        # user[1] is the username, user[2] is the email, user[4] is the profile_picture TODO: Abstraact this into a function
        return render_template(
            "account.html",
            username=res["username"],
            email=res["email"],
            profile_picture=res["profile_picture"],
        )
    else:
        # Handle user not found
        error_message = "User not found"
        return render_template("error.html", error_message=error_message, username="")


@app.route("/change_password/<username>")
def change_password_page(username):
    return render_template("change_password.html", username=username)


@app.route("/change_password/<username>", methods=["POST"])
def change_password(username):
    old_password = request.form["old_password"]
    new_password = request.form["new_password"]

    # conn = sqlite3.connect(DATABASE)
    # cursor = conn.cursor()
    # cursor.execute(
    #     "SELECT * FROM users WHERE username = ? AND password = ?",
    #     (username, old_password),
    # )
    # user = cursor.fetchone()
    res = db_obj.updatePassword(
        username=username, oldPassword=old_password, newPassword=new_password
    )
    res1 = db_obj.getUser(username)

    if res is not None:
        # cursor.execute(
        #     "UPDATE users SET password = ? WHERE username = ?", (new_password, username)
        # )
        # conn.commit()
        # conn.close()
        success_message = "Password changed successfully"
        return render_template(
            "account.html",
            username=res1["username"],
            email=res1["email"],
            profile_picture=res1["profile_picture"],
            success_message=success_message,
        )
    else:
        # conn.close()
        error_message = "Incorrect old password"
        return render_template(
            "account.html",
            username=res1["username"],
            email=res1["email"],
            profile_picture=res1["profile_picture"],
            error_message=error_message,
        )


@app.route("/upload_profile_picture/<username>")
def upload_profile_picture_page(username):
    return render_template("upload_profile_picture.html", username=username)


@app.route("/upload_profile_picture/<username>", methods=["POST"])
def upload_profile_picture(username):
    profile_picture = request.files["profile_picture"]

    db_obj.updatePicture(username=username, new_profile_picture=profile_picture)
    # if profile_picture:
    #     profile_picture_filename = secure_filename(profile_picture.filename)
    #     profile_picture_path = os.path.join(
    #         "static/profile_pictures", profile_picture_filename
    #     )
    #     profile_picture.save(profile_picture_path)

    #     conn = sqlite3.connect(DATABASE)
    #     cursor = conn.cursor()
    #     cursor.execute(
    #         "UPDATE users SET profile_picture = ? WHERE username = ?",
    #         (profile_picture_filename, username),
    #     )
    #     conn.commit()
    #     conn.close()

    return redirect(url_for("account", username=username))


@app.route("/delete_account/<username>")
def delete_account(username):
    # conn = sqlite3.connect(DATABASE)
    # cursor = conn.cursor()
    # cursor.execute("DELETE FROM users WHERE username = ?", (username,))
    # conn.commit()
    # conn.close()
    db_obj.deleteUser(username=username)

    # Redirect to a page indicating successful account deletion
    return redirect(url_for("account_deleted"))


@app.route("/account_deleted")
def account_deleted():
    return "Your account has been deleted successfully."


@app.route("/users-data-all")
def get_dict():
    # conn = sqlite3.connect("users.db")
    # curror = conn.cursor()
    # curror.execute("SELECT * FROM users")
    # data = curror.fetchall()
    res = db_obj.dumpUsers()
    return render_template("list.html", data=res, username="")


if __name__ == "__main__":
    app.run(debug=True)
