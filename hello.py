from flask import Flask, flash, render_template, request, redirect, url_for, session
import sqlite3, os
from werkzeug.utils import secure_filename
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
    # print(session)
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
            "account.html",
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
        success_message = "Password changed successfully"
        return render_template(
            "account.html",
            username=res1["username"],
            email=res1["email"],
            profile_picture=res1["profile_picture"],
            success_message=success_message,
        )
    else:
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
    session.pop("userid", None)
    session.pop("username", None)
    # print(session.keys())
    # print(session.items())
    flash("You have deleted your acount successfully ", "success")
    # return "Your account has been deleted successfully."
    return redirect("/")

# NOTE change back create user
@app.route("/post" , methods = ["POST","GET"])
def create_post():
    users = db_obj.dumpUsers()
    res = []
    content = request.form.get("content")
    creater = request.form.get("users")
    root_id = str(request.form.get('root_id')) # post cration
    getRepiesFor= str(request.form.get("reply")) # view post
    # print(content)
    # print(user)
    if not (creater is None or content is None):
        if root_id.lower() != "none":
            db_obj.createPost(user_id=int(creater),content= content,root_id= int(root_id))
        else:
            db_obj.createPost(int(creater),content)

    res = db_obj.getAllPost([0,10])
    allReplies = []
    if getRepiesFor.lower() != "none":
        allReplies = db_obj.getAllRepies(int(getRepiesFor), [0,10])
    print(272 , root_id,getRepiesFor , allReplies)

    return render_template("test.html",users = users,posts = res , replies = allReplies)

@app.route("/users-data-all")
def get_dict():
    res = db_obj.dumpUsers()
    return render_template("list.html", data=res, username="")

if __name__ == "__main__":
    app.run(debug=True)
