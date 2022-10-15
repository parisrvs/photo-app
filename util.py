import os
from io import BytesIO
from PIL import Image, ExifTags
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from datetime import datetime, timezone, tzinfo
import calendar


EXIF_ORIENTATION = 274  # Magic numbers from http://www.exiv2.org/tags.html

def random_hex_bytes(n_bytes):
    """Create a hex encoded string of random bytes"""
    return os.urandom(n_bytes).hex()

def resize_image(file_p, size):
    """Resize an image to fit within the size, and save to the path directory"""
    dest_ratio = size[0] / float(size[1])
    try:
        image = Image.open(file_p)
    except IOError:
        print("Error: Unable to open image")
        return None

    try:
        exif = dict(image._getexif().items())
        if exif[EXIF_ORIENTATION] == 3:
            image = image.rotate(180, expand=True)
        elif exif[EXIF_ORIENTATION] == 6:
            image = image.rotate(270, expand=True)
        elif exif[EXIF_ORIENTATION] == 8:
            image = image.rotate(90, expand=True)
    except:
        print("No exif data")

    source_ratio = image.size[0] / float(image.size[1])

    # the image is smaller than the destination on both axis
    # don't scale it
    if image.size < size:
        new_width, new_height = image.size
    elif dest_ratio > source_ratio:
        new_width = int(image.size[0] * size[1]/float(image.size[1]))
        new_height = size[1]
    else:
        new_width = size[0]
        new_height = int(image.size[1] * size[0]/float(image.size[0]))
    image = image.resize((new_width, new_height), resample=Image.LANCZOS)

    final_image = Image.new("RGBA", size)
    topleft = (int((size[0]-new_width) / float(2)),
               int((size[1]-new_height) / float(2)))
    final_image.paste(image, topleft)
    bytes_stream = BytesIO()
    final_image.save(bytes_stream, 'PNG')
    return bytes_stream.getvalue()


def validate_username(username):
    for c in username:
        if not c.isalnum():
            if c != '.' and c != '_':
                return 0
    return 1

def validate_password(password):
    for c in password:
        if c == " ":
            return 0
    if len(password) < 6:
        return 0
    if password.isalpha():
        return 0
    if password.isnumeric():
        return 0
    return 1



def validate_email(email):
    pos_AT = 0
    count_AT = 0
    count_DT = 0
    if email[0] == '@' or email[-1] == '@':
        return 0
    if email[0] == '.' or email[-1] == '.':
        return 0
    for c in range(len(email)):
        if email[c] == '@':
            pos_AT = c
            count_AT = count_AT + 1
    if count_AT != 1:
        return 0
        
    username = email[0:pos_AT]
    #print(username)
    if not username[0].isalnum() or not username[-1].isalnum():
        return 0
    for d in range(len(email)):
        if email[d] == '.':
            if d == (pos_AT+1):
                return 0
            if d > pos_AT:
                word = email[(pos_AT+1):d]
                #print(word)
                if not word.isalnum():
                    return 0
                pos_AT = d
                count_DT = count_DT + 1
    #print(count_DT)
    if count_DT < 1 or count_DT > 2:
        return 0
        
    return 1

def get_date_time():
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    time = datetime.now(datetime.now(timezone.utc).astimezone().tzinfo)
    date_time = {}

    time = str(time)
    Time = time.split()
    date = Time[0]
    time = Time[1].split(".")
    time = time[0]
    
    date_time["date"] = date
    date_time["time"] = time

    date = date.split("-")
    day = days[calendar.weekday(int(date[0]),  int(date[1]), int(date[2]))]    
    date_time["day"] = day
    return date_time


def sendEmail(email, subject, message):
    msg = MIMEMultipart("alternative")
    msg["From"] = os.getenv("TEST_EMAIL")
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(message, 'html'))
    server = smtplib.SMTP("smtp-mail.outlook.com", 587)
    server.starttls()
    server.login(os.getenv("TEST_EMAIL"), os.getenv("TEST_PASSWORD"))
    server.sendmail(os.getenv("TEST_EMAIL"), email, msg.as_string())
    server.quit()

def get_time():
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    months = ["NULL", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    time = datetime.now(datetime.now(timezone.utc).astimezone().tzinfo)
    date_time = {}

    time = str(time)
    Time = time.split()
    date = Time[0]
    time = Time[1].split(".")
    time = time[0]

    date = date.split("-")    
    date_time["date"] = int(date[2])
    month = int(date[1])
    date_time["month"] = months[month]
    date_time["year"] = int(date[0])
    date_time["time"] = time

    day = days[calendar.weekday(int(date[0]),  int(date[1]), int(date[2]))]
    date_time["weekday"] = day

    return date_time

