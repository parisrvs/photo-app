import sys
import os
import requests
import boto3
from flask import Flask, render_template, request, session, redirect
from flask_session import Session
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
import util
#from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
import random
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET")

#app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


class PhotoForm(FlaskForm):
    photo = FileField('image', validators=[FileRequired()])


@app.route("/login", methods=["POST", "GET"])
def login():
    session.clear()
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username")
    password = request.form.get("password")
    if not username or not password:
        return render_template("login.html", error_message = "enter username and password")
    
    users = db.execute("SELECT * FROM users WHERE username = :username", {'username': username}).fetchall()
    if len(users) == 0:
        return render_template("login.html", error_message = "username does not exist")
    user = users[0]
    if check_password_hash(user.password, password):
        session["username"] = username
        return redirect("/")
    else:
        return render_template("login.html", error_message = "incorrect password")
   


@app.route("/register", methods=["POST", "GET"])
def register():
    session.clear()
    if request.method == "GET":        
        return render_template("register.html")
    username = request.form.get("username")
    password = request.form.get("password")
    password1 = request.form.get("password1")
    email = request.form.get("email")
    if not username or not password or not password1 or not email:
        return render_template("register.html", error_message = "enter all details")
    if password != password1:
        return render_template("register.html", error_message = "passwords don't match")

    if not util.validate_email(email):
        return render_template("register.html", error_message = "enter a valid email address")
    if not util.validate_password(password):
        return render_template("register.html", error_message = "enter an alpha-numeric password of minimum 6 character")
    if not util.validate_username(username):
        return render_template("register.html", error_message = "only a-z, 0-9, '_' and '.' characters without spaces allowed in username")

    username.strip()
    email.strip()

    Email = db.execute("SELECT email FROM users WHERE username = :username", {'username': username}).fetchone()
    if Email is not None:
        if Email.email == email:
            return render_template("register.html", error_message = "This account already exists. Reset your password.")
        else:
            return render_template("register.html", error_message = "username already exists, please select a different username")
    
    User = db.execute("SELECT username FROM users WHERE email = :email", {'email': email}).fetchone()
    if User is not None:
        return render_template("register.html", error_message = "this email is associated with another account, please enter a different email")

    
    Password = generate_password_hash(password)    
    session["username"] = username
    session["password"] = Password
    session["email"] = email

    code = random.randint(100000, 999999)
    session["code"] = code
    code = str(code)
    util.sendEmail(session["email"], "confirm email address", code)    
    return redirect("/confirmEmail")

@app.route("/confirmEmail", methods=["POST", "GET"])
def confirmEmail():
    if session.get("code") == None or session.get("username") == None or session.get("email") == None:        
        return redirect("/login")
    if request.method == "GET":
        return render_template("confirmEmail.html", email=session["email"])
    code = request.form.get("code")
    if not code:
        return render_template("confirmEmail.html", email=session["email"], error_message ="enter confirmation code")
    
    try:
        code = int(code)
    except ValueError:
        return render_template("confirmEmail.html", email=session["email"], error_message ="incorrect code")

    if code != session["code"]:
        return render_template("confirmEmail.html", email=session["email"], error_message ="incorrect code")

    time = util.get_date_time()
    db.execute("INSERT INTO users (username, email, password, day, date, time) VALUES (:username, :email, :password, :day, :date, :time)", {'username': session["username"], 'email': session["email"], 'password': session["password"], 'day': time["day"], 'date': time["date"], 'time': time["time"]})
    db.commit()
    util.sendEmail(session["email"], "Registration Successful!", "You are now registered with paris-photos.")
    util.sendEmail(os.getenv("EMAIL"), "New Registration for paris-photos", session["email"])
    session.clear()
    return redirect("/login")

@app.route("/resend_confirmation_code")
def resend_confirmation_code():
    if session.get("code") == None or session.get("username") == None or session.get("email") == None:        
        return redirect("/login")
    code = random.randint(100000, 999999)
    session["code"] = code
    code = str(code)
    util.sendEmail(session["email"], "confirm email address", code)    
    return redirect("/confirmEmail")


@app.route("/forgotpassword", methods =["POST", "GET"])
def forgotpassword():
    session.clear()
    if request.method == "GET":
        return render_template("forgotpassword.html")

    username = request.form.get("username")
    if not username:
        return render_template("forgotpassword.html", error_message = "enter username")
    username = username.strip()
    user = db.execute("SELECT * FROM users WHERE username = :username", {'username': username}).fetchone()
    if user == None:
        return render_template("forgotpassword.html", error_message = "Invelid Username!")
    else:
        session["email"] = user.email
        session["temp_username"] = username
        code = random.randint(100000, 999999)
        session["code"] = code
        code = str(code)
        util.sendEmail(user.email, "confirmation code", code)
    return redirect("/forgot_password")

@app.route("/resendconfirmationcode")
def resendconfirmationcode():
    if session.get("code") == None or session.get("email") == None or session.get("temp_username") == None:
        session.clear()
        return redirect("/login")
    code = random.randint(100000, 999999)
    session["code"] = code
    code = str(code)
    util.sendEmail(session["email"], "confirm email address", code)    
    return redirect("/forgot_password")


@app.route("/forgot_password", methods=["POST", "GET"])
def forgot_password():
    if session.get("code") == None or session.get("email") == None or session.get("temp_username") == None:
        session.clear()
        return redirect("/login")
    email = session["email"]
    email = email.split("@")
    l = len(email[0])
    email_1 = ""
    for c in range(1,l-1):
        email_1 = email_1 + "*"
    Email = email[0][0] + email_1 + "@" + email[1]

    if request.method == "GET":        
        return render_template("forgot_password.html", email=Email)

    code = request.form.get("code")
    if not code:
        return render_template("forgot_password.html", email=Email, error_message ="enter code")

    try:
        code = int(code)
    except ValueError:
        return render_template("forgot_password.html", email=Email, error_message ="incorrect code")
    
    if code != session["code"]:
        return render_template("forgot_password.html", email=Email, error_message ="incorrect code")
    
    return redirect("/changepassword")

@app.route("/changepassword", methods=["POST", "GET"])
def changepassword():
    if session.get("code") == None or session.get("email") == None or session.get("temp_username") == None:
        session.clear()
        return redirect("/login")
    if request.method == "GET":
        return render_template("changepassword.html")
    password1 = request.form.get("password1")
    password2 = request.form.get("password2")
    if not password1 or not password2:
        return render_template("changepassword.html", error_message="enter password and confirm password")    
    if password1 != password2:
        return render_template("changepassword.html", error_message="passwords don't match")
    if not util.validate_password(password1):
        return render_template("changepassword.html", error_message="enter an alpha-numeric password of minimum 6 character")
    
    user = db.execute("SELECT * FROM users WHERE username = :username AND email = :email", {'username': session["temp_username"], 'email': session["email"]}).fetchone()
    if user == None:
        session.clear()
        return redirect("/login")
    Password = generate_password_hash(password1)

    db.execute("UPDATE users SET password = :password WHERE username = :username AND email = :email", {"password": Password, "username": session["temp_username"], "email": session["email"]})
    
    message = "Your password has been changed."
    util.sendEmail(session["email"], "password change", message)
    db.commit()
    session.clear()
    return redirect("/login")


@app.route("/", methods=["POST", "GET"])
def home():
    if session.get("username") == None:
        return redirect("/login")
    if session.get("message") == None:
        session["message"] = {}
        photos = db.execute("SELECT * FROM photos WHERE username = :username", {"username": session["username"]}).fetchall()
        for photo in photos:
            Date_Time = {"weekday": photo.weekday, "date": photo.date, "month": photo.month, "year": photo.year, "time": photo.time}            
            Image_key = photo.key
            session["message"][Image_key] = [photo.title, photo.memo, Date_Time]

        
    s3_client = boto3.client('s3')
    prefix = session["username"] + "/"
    if session.get("photos") == None:
        session["photos"] = {}
        response = s3_client.list_objects(Bucket=os.getenv("PHOTOS_BUCKET"), Prefix=prefix)
        if 'Contents' in response and response['Contents']:
            for content in response['Contents']:
                image_key = content['Key']       
                image_key = image_key.split("/")
                image_key = image_key[1].split(".")
                image_key = image_key[0]
                session["photos"][image_key] = s3_client.generate_presigned_url('get_object', Params={'Bucket': os.getenv("PHOTOS_BUCKET"), 'Key': content['Key']}, ExpiresIn=36000)

    form = PhotoForm()
    url = None
    if request.method == "POST":
        person = request.form.get("person")
        message = request.form.get("message")
        if not person or not message:
            return render_template("home.html", form=form, url=url, photos=session["photos"], error_message = "pick a photo type and enter a message")
        if form.validate_on_submit():
            image_bytes = util.resize_image(form.photo.data, (500, 500))
            if image_bytes:
                k = util.random_hex_bytes(8)
                key = prefix + k + '.png'
                s3_client.put_object(Bucket=os.getenv("PHOTOS_BUCKET"),Key=key,Body=image_bytes,ContentType='image/png')
                url = s3_client.generate_presigned_url('get_object',Params={'Bucket': os.getenv("PHOTOS_BUCKET"), 'Key': key}, ExpiresIn=36000)
                TIME = util.get_time()
                db.execute("INSERT INTO photos (key, title, memo, date, month, year, weekday, time, username) VALUES (:key, :title, :memo, :date, :month, :year, :weekday, :time, :username)", {"key": k, "title": person, "memo": message, "date": TIME["date"], "month": TIME["month"], "year": TIME["year"], "weekday": TIME["weekday"], "time": TIME["time"], "username": session["username"]})
                session["photos"][k] = url                
                session["message"][k] = [person, message, TIME]
                db.commit()


    return render_template("home.html", form=form, url=url, photos=session["photos"], username = session["username"])


@app.route("/delete_image/<key>")
def delete_image(key):
    if session.get("username") == None:
        return redirect("/login")
    if key not in session["photos"]:
        return redirect("/")
    if key not in session["message"]:
        return redirect("/")
    Key = session["username"] + "/" + key + '.png'
    s3_client = boto3.client('s3')
    s3_client.delete_object(Bucket=os.getenv("PHOTOS_BUCKET"), Key=Key)
    db.execute("DELETE FROM photos WHERE key=:key AND username=:username", {"key": key, "username": session["username"]})
    db.commit()
    del session["photos"][key]
    del session["message"][key]
    return redirect("/")
    

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/view_image/<key>")
def view_image(key):
    if session.get("username") == None:
        return redirect("/login")
    if key not in session["photos"]:
        return redirect("/")
    if key not in session["message"]:
        return redirect("/")
    return render_template("image.html", url=session["photos"][key], info=session["message"][key], key=key, username = session["username"])