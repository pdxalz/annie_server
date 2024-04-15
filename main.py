#  docker-compose up
#   (cd to Desktop/annie_api/)
#  docker build . -t anniem
#  docker run --rm --volume $PWD/winddata:/winddata -p 8000:8000/tcp anniem:latest
#  docker run --rm --volume $PWD/winddata:/winddata -p 8000:8000/tcp -e SERVER_URL=http://192.168.68.113:8000 anniem
#  docker ps -a
#   docker system prune -a      (wipe out all data)
#   sudo find / -name test.db   (find the location of the database)


import sqlite3
import json
import datetime
import paho.mqtt.client as mqtt
import os
import pathlib
import pytz

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.mime.text import MIMEText
from fastapi.staticfiles import StaticFiles

from starlette.responses import FileResponse 
from datetime import datetime








TOPIC_ALL = 'zimbuktu/#'
TOPIC_WIND = 'zimbuktu/wind'
TOPIC_JPG_START = 'zimbuktu/jpgStart'
TOPIC_JPG_END = 'zimbuktu/jpgEnd'
TOPIC_JPG_DATA = 'zimbuktu/jpgData'
INDEX_HTML_PATH = 'web_assets/index.html'

DATABASE = "/winddata/test.db" 
TMPJPGFILE = "/winddata/temp.jpg"

app = FastAPI()

origins = [
    'null',
    # "http://192.168.68.114:8000",
    # "http://192.168.68.114",
    # "http://localhost",
    # "http://localhost:8000",
]

# needed for CORS, gives error when accessing from server hosting the api
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex='.*',
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/wind")
def root():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    windy = cursor.execute("SELECT * FROM wind")

    ti=[]
    di=[]
    av=[]
    gu=[]
    ll=[]

    for row in windy:
        ti.append(utc_to_pst(row[0]))
        di.append(row[1])
        av.append(row[2])
        gu.append(row[3])
        ll.append(row[4])

    dict = {'time':ti,
     'dir':di,
      'avg':av,
       'gust':gu,
        'lull': ll}

    cursor.close()
    conn.close()

    return json.dumps(dict)

@app.get("/get_image")
async def get_image():
    if os.path.exists(TMPJPGFILE):
        return FileResponse(TMPJPGFILE)
    return FileResponse('web_assets/404.jpg')

@app.get("/")
async def read_index():
    return FileResponse(INDEX_HTML_PATH)



def utc_to_pst(utc_time):
    utc_tz = pytz.timezone('UTC')
    pst_tz = pytz.timezone('America/Los_Angeles')
    utc_time_naive = datetime.strptime(utc_time, "%m/%d/%y %H:%M")
    utc_time = utc_tz.localize(utc_time_naive)
    pst_time = utc_time.astimezone(pst_tz)
    return pst_time.strftime("%I:%M%p")


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print('Connected'+str(client._client_id))
        client.subscribe(TOPIC_ALL)
    else:
        print('Connection refused')

image_size = 0
rest_image_size = 0  # used to indicate how many bytes hasn't received yet for one image
def on_message(client, userdata, message):
    """
        on received packet: the whole payload is python3 byte object
    """
    #print('topic:', message.topic)
    # print('payload:', message.payload)

    if (message.topic == TOPIC_WIND):
        jd = json.loads(message.payload)
        print("json: " + jd["t"] + " " + str(jd["d"]) + " " + str(jd["a"]) + " " + str(jd["g"]) + " " + str(jd["l"]))


        val = (jd["t"], jd["d"], jd["a"], jd["g"], jd["l"])
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute('''INSERT INTO wind (time, dir, avg, gust, lull) VALUES (?, ?, ?, ?, ?)
                        ''', val)
        conn.commit()
        cursor.close()
        conn.close()
    elif (message.topic == TOPIC_JPG_START):
        print('Start Image')
        if os.path.exists(TMPJPGFILE):
            os.remove(TMPJPGFILE)
    elif (message.topic == TOPIC_JPG_END):
        print('\nEnd image')
        # sender_email = "pdxalz@gmail.com"
        # sender_password = "xuoq euxb lnzt qomz "
        # receiver_email = "pdxalz@gmail.com"
        # subject = "Email with attachment"
        # body = "Please find the attached file."
        # attachment_path = TMPJPGFILE
        # print('Send mail')
        # send_email(sender_email, sender_password, receiver_email, subject, body, attachment_path)
    elif (message.topic == TOPIC_JPG_DATA):
        image_file = open(TMPJPGFILE, 'ab')
        image_file.write(message.payload)
        image_file.close()
        print('.', end='', flush=True)
    else:
        print(message.payload)
            






def mqtt_client_init(client):
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host='broker.hivemq.com', port=1883)
    client.loop_start()



def send_email(sender_email, sender_password, receiver_email, subject, body, attachment_path):
    # Create a multipart message object
    message = MIMEMultipart()
    message["From"] = 'pdxalz@gmail.com'
    message["To"] = 'pdxalz@gmail.com'
    message["Subject"] = 'test image'

    # Add body to the email
    message.attach(MIMEText(body, "plain"))

    # Open the file in bynary
    with open(attachment_path, "rb") as attachment:
        # Add file as application/octet-stream
        # Email client can usually download this automatically as attachment
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())

    # Encode file in ASCII characters to send by email    
    encoders.encode_base64(part)

    # Add header as key/value pair to attachment part
    part.add_header(
        "Content-Disposition",
        f"attachment; filename= {attachment_path}",
    )

    # Add attachment to message and convert message to string
    message.attach(part)
    text = message.as_string()

    # Create a secure connection with the SMTP server
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        # Login to the sender's email account
        server.login(sender_email, sender_password)

        # Send the email
        server.sendmail(sender_email, receiver_email, text)

# Usage example
# sender_email = "pdxalz@gmail.com"
# sender_password = "xuoq euxb lnzt qomz "
# receiver_email = "pdxalz@gmail.com"
# subject = "Email with attachment"
# body = "Please find the attached file."
# attachment_path = "src/temp.jpg"

# send_email(sender_email, sender_password, receiver_email, subject, body, attachment_path)









conn = sqlite3.connect(DATABASE)

cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS wind
               (time STR, dir INT, avg INT, gust INT, lull INT)''')
# wind_data = [
#     ("1/12/24 7:00",120, 8,14,7),
#     ("1/12/24 7:10",140, 10,25,6),
#     ("1/12/24 7:20",130, 6,24,4),
#     ("1/12/24 7:30",110, 8,15,7),
#     ("1/12/24 7:40",120, 9,17,8),
#     ("1/12/24 7:50",180, 16,18,6)
# ]
# cursor.executemany('''INSERT INTO wind (time, dir, avg, gust, lull) VALUES (?, ?, ?, ?, ?)
#                    ''', wind_data)

# conn.commit()

windy = cursor.execute("SELECT * FROM wind")
print(windy)
ti=[]
di=[]
av=[]
gu=[]
ll=[]

for row in windy:
    ti.append(row[0])
    di.append(row[1])
    av.append(row[2])
    gu.append(row[3])
    ll.append(row[4])
    print(row)

cursor.close()
conn.close()

client = mqtt.Client()
mqtt_client_init(client)



