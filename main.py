#  docker-compose up
#   (cd to annie_server)
#  docker build . -t annie_img
#  docker run --rm -v $PWD/winddata:/winddata -p 80:8000/tcp -e SERVER_URL=http://192.168.68.113 -v roosterpict:/rooster  annie_img
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
import shutil

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pytz import timezone

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.mime.text import MIMEText
from fastapi.staticfiles import StaticFiles

from starlette.responses import FileResponse 
from datetime import datetime, timedelta
from typing import Optional
import paho.mqtt.publish as publish


class AutoPhoto:
    def __init__(self):
        self._prev_direction = 0
        self._prev_avg_wind = 0
        self._prev_gusts = 0
        self._prev_lull = 0
        self.last_photo_time = datetime.now()
        self.photo_count = 0

    def should_capture_photo(self, direction, avg_wind, gusts, lull):
        now = datetime.now()
        hour = now.hour

        if not os.path.exists('autopict'):
            return False
        
        if now - self.last_photo_time < timedelta(minutes=30):
            return False

        # reset the count at midnight
        if hour < 1:
            self.photo_count = 0
        # In the morning, if the wind is above 14 mph for two samples, take a photo
        elif 9 <= hour < 13 and self.photo_count < 1:
            if avg_wind > 12 and self.prev_avg_wind > 12:
                return True
        # In the afternoon
        elif 13 <= hour < 18 and self.photo_count < 2:  
            if avg_wind > 10 and self.prev_avg_wind > 10:
                return True
            # if self.prev_avg_wind > 12 and (wind_change < 6 or direction_change > 120):
            #     return True

        return False

    def capture_photo(self, direction, avg_wind, gusts, lull):
        if self.should_capture_photo(direction, avg_wind, gusts, lull):
            # Capture the photo
            publish.single(TOPIC_COMMAND, "p5", hostname=MQTT_HOST)
            self.last_photo_time = datetime.now()
            self.prev_avg_wind = avg_wind
            self.photo_count += 1





# MQTT 
MQTT_HOST = 'broker.hivemq.com'
TOPIC_ALL = 'zimbuktu/#'
TOPIC_WIND = 'zimbuktu/wind'
TOPIC_COMMAND = 'zimbuktu/cmd'
TOPIC_JPG_START = 'zimbuktu/jpgStart'
TOPIC_JPG_END = 'zimbuktu/jpgEnd'
TOPIC_JPG_DATA = 'zimbuktu/jpgData'

#Paths to static html related files, copied when server starts
INDEX_HTML_PATH = 'web_assets/index.html'
ROOSTERCAM_HTML_PATH = 'web_assets/roostercam.html'

#Paths to non-voliatile data, they exist outside of docker container
DATABASE = "/winddata/test.db" 
TMPJPGFILE = "/winddata/temp.jpg"
IMAGE_PATH = "/winddata/images"
ROOSTERJPGFILE = "/rooster/camera0.jpg"

last_image_date = 'No Images'
auto_photo = AutoPhoto()

image_size = 0
rest_image_size = 0  # used to indicate how many bytes hasn't received yet for one image
num_bytes_received = 0
num_bytes_in_image = 1
last_percentage_printed = 0

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

app.mount("/web_assets", StaticFiles(directory="web_assets"), name="web_assets")
app.mount("/images", StaticFiles(directory=IMAGE_PATH), name="images")
app.mount("/rooster", StaticFiles(directory='/rooster'), name="rooster")

@app.get("/list_images")
def list_files():
    files = sorted(os.listdir(IMAGE_PATH),reverse=True)
    return {"files": files}

@app.get("/take_image")
def take_image(size: str):
    topic = TOPIC_COMMAND
    if size == 'small':
        publish.single(topic, "p2", hostname=MQTT_HOST)
    elif size == 'medium':
        publish.single(topic, "p4", hostname=MQTT_HOST)
    elif size == 'large':
        publish.single(topic, "p5", hostname=MQTT_HOST)
    else:
        return {"error": "Invalid size parameter"}

    return {"message": "Image capture command sent"}


@app.get("/delete_image")
def delete_image(filename: str):
    os.remove(IMAGE_PATH + '/' + filename)
    return {"deleted": filename}

@app.get("/roostercam.php")
def roostercamphp():
    return FileResponse(ROOSTERCAM_HTML_PATH)

@app.get("/roostercam")
def roostercam():
    if os.path.exists(ROOSTERJPGFILE):
        return FileResponse(ROOSTERJPGFILE)
    return FileResponse('web_assets/404.jpg')


@app.get("/wind")
def root(day: Optional[str] = None):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if day is not None:
        # Select only rows from the specified day
        windy = cursor.execute("SELECT * FROM wind WHERE date(time) = ?", (day,))
    else:
        # If no day is specified, select all rows
        windy = cursor.execute("SELECT * FROM wind")

    ti=[]
    di=[]
    av=[]
    gu=[]
    ll=[]

    for row in windy:
        ti.append(hours_minutes(row[0]))
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

@app.get("/first_date")
def get_first_date():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Execute the query
    cursor.execute('SELECT date(time) FROM wind ORDER BY time ASC LIMIT 1')

    # Fetch the result
    result = cursor.fetchone()

    # Close the connection
    conn.close()

    # Return the result
    if result is not None:
        return {"first_date": result[0]}
    else:
        return {"error": "No data found"}
    
@app.get("/get_image")
async def get_image():
    print("hello get image")
    if os.path.exists(TMPJPGFILE):
        return FileResponse(TMPJPGFILE)
    return FileResponse('web_assets/404.jpg')

@app.get("/image_date")
async def get_image_date():
    global last_image_date
    return {"first_date": last_image_date}

@app.get("/")
async def read_index():
    return FileResponse(INDEX_HTML_PATH)



def hours_minutes(time_str):
    datetime_obj = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
    if (datetime_obj.strftime("%M") == '00'):
        return datetime_obj.strftime("%-I:%M%p")
    else:
        return datetime_obj.strftime("%-I:%M")
        

def pst_to_utc(pst_time):
    pst_tz = pytz.timezone('America/Los_Angeles')
    utc_tz = pytz.timezone('UTC')
    pst_time_naive = datetime.strptime(pst_time, "%Y-%m-%d %H:%M")
    pst_time = pst_tz.localize(pst_time_naive)
    utc_time = pst_time.astimezone(utc_tz)
    return utc_time.strftime("%Y-%m-%d %H:%M")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print('Connected'+str(client._client_id))
        client.subscribe(TOPIC_ALL)
    else:
        print('Connection refused')





def on_message(client, userdata, message):
    """
        on received packet: the whole payload is python3 byte object
    """
    #print('topic:', message.topic)
    # print('payload:', message.payload)
    global num_bytes_in_image
    global num_bytes_received
    global last_percentage_printed 

    if (message.topic == TOPIC_WIND):
        jd = json.loads(message.payload)
        print("json: " + jd["t"] + " " + str(jd["d"]) + " " + str(jd["a"]) + " " + str(jd["g"]) + " " + str(jd["l"]))


        val = (jd["t"], jd["d"], jd["a"], jd["g"], jd["l"])
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        val = (jd["t"], jd["d"], jd["a"], jd["g"], jd["l"])
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        # Convert the time to the desired format and adjust the timezone from UTC to PST
        time_obj = datetime.strptime(jd["t"], "%m/%d/%y %H:%M")
        pst_tz = pytz.timezone('America/Los_Angeles')
        time_obj = time_obj.replace(tzinfo=pytz.utc).astimezone(pst_tz)
        time_str = time_obj.strftime("%Y-%m-%d %H:%M")

        cursor.execute('''INSERT INTO wind (time, dir, avg, gust, lull) VALUES (?, ?, ?, ?, ?)
                        ''', (time_str, jd["d"], jd["a"], jd["g"], jd["l"]))
        conn.commit()
        cursor.close()
        conn.close()

        auto_photo.capture_photo(jd["a"], jd["g"], 0, 0)
            

    elif (message.topic == TOPIC_JPG_START):
        
        num_bytes_received = 0
        last_percentage_printed = 0 
        num_bytes_in_image = int(message.payload.decode('utf-8'))
        print(f'Start Image, bytes: {num_bytes_in_image}')
        if os.path.exists(TMPJPGFILE):
            os.remove(TMPJPGFILE)

    elif (message.topic == TOPIC_JPG_END):
        global last_image_date
        print('\nEnd image')
        last_image_date = datetime.now(timezone('US/Pacific')).strftime("%m/%d %I:%M%p")
        filename = IMAGE_PATH + '/' + datetime.now(timezone('US/Pacific')).strftime("%m_%d_%H_%M") + ".jpg"
        # Copy TMPJPGFILE to filename
        shutil.copy2(TMPJPGFILE, filename)

    elif (message.topic == TOPIC_JPG_DATA):
        num_bytes_received += len(message.payload)
        percentage_received = (num_bytes_received / num_bytes_in_image) * 100
        if percentage_received - last_percentage_printed >= 10:
            print(f'{int(percentage_received)}% received')
            last_percentage_printed = percentage_received 

        image_file = open(TMPJPGFILE, 'ab')
        image_file.write(message.payload)
        image_file.close()
        print('.', end='', flush=True)
    else:
        print(message.payload)
            




def has_correct_checksum(byte_array):
    # Calculate the checksum from the byte array (excluding the last two bytes)
    calculated_checksum = sum(byte_array[:-3]) % 0x10000

    # Extract the checksum from the second and third to last bytes of the byte array
    stored_checksum = int.from_bytes(byte_array[-3:-1], byteorder='little')

    # Extract the count from the last byte of the byte array
    count = int.from_bytes(byte_array[-1:], byteorder='little')

    # If the checksums are different, print them in hex
    if calculated_checksum != stored_checksum:
        print(f'Calculated checksum: {calculated_checksum:02x}, Stored checksum: {stored_checksum:02x}, count: {count} ')


    # Return True if the calculated checksum matches the stored checksum, False otherwise
    return calculated_checksum == stored_checksum

def mqtt_client_init(client):
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host=MQTT_HOST, port=1883)
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
# print(windy)
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
    # print(row)

cursor.close()
conn.close()

client = mqtt.Client()
mqtt_client_init(client)



