from flask import *
import os
from flask import Flask, flash, request, redirect, render_template
from werkzeug.utils import secure_filename
import cv2 
import face_recognition
import numpy as np
import smtplib
import datetime
from flask_pymongo import PyMongo
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


app = Flask(__name__)

app.secret_key = "AbCdfc"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

app.config["MONGO_URI"] = "mongodb://localhost:27017/TechD"
mongo = PyMongo(app)

path = os.getcwd()
path = os.path.join(path, 'upload')
if not os.path.isdir(path):
    os.mkdir(path)

if not os.path.isdir(os.path.join(path, 'detected')):
    os.mkdir(os.path.join(path, 'detected'))

images_path = os.path.join(path, 'images')
if not os.path.isdir(images_path):
    os.mkdir(images_path)

if not os.path.isdir(os.path.join(path, 'videos')):
    os.mkdir(os.path.join(path, 'videos'))

app.config['UPLOAD_FOLDER'] = path

# Allowed extension you can set your own
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

names = []
embeddings = []

for filename in os.listdir(images_path):
    img = face_recognition.load_image_file(os.path.join(images_path, filename))
    embedding = face_recognition.face_encodings(img)[0]
    embeddings.append(embedding)
    names.append(filename.split('.')[0])

print(names)
'''
collection = mongo.db.missing_list
for doc in collection.find():
    names.append(doc['person_name'])
    embeddings.append(doc['embedding'])
print(names)
'''
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_mail(name,loc):
    user = mongo.db.missing_list.find_one({"name":name})

    if not user:
        print("missing user data")
        return

    person_name = user['name']
    person_age = user['age']
    person_phno = user['phno']
    person_email = user['email']
    person_address = user['address']

    sender_email = "y.aaryan12@gmail.com"
    password = "mpzdqyodltffozck"
    rec_email = "y.aaryan12@gmail.com"
    #message = "Detected " + name +' at ' + loc

    now = datetime.datetime.now()
    current_time = now.strftime("%H:%M:%S")

    subject = "ALERT!!!"
    text = """
A missing person has been detected via closed circuit cameras.
    Name : """ + person_name.title() + """
    Location : """ + loc.title() + """
    Date : """ + str(datetime.date.today()) + """
    Time : """ + str(current_time) + """ 

Personal Details:
    Name : """ + person_name.title() + """
    Age : """ + person_age + """
    Phone Number : """ + person_phno + """
    Email ID : """ + person_email + """
    Address : """ + person_address.title()

    #message = 'Subject: {}\n\n{}'.format(subject, text)

    msg = MIMEMultipart()
    msg['Subject'] = 'ALERT!!!'
    msg['From'] = "Tech Detectives"
    msg['To'] = rec_email

    text = MIMEText(text)
    msg.attach(text)

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender_email, password)
    server.sendmail(sender_email, rec_email, msg.as_string())
    print("Email Sent")

def encoding_file(img_name, person_name):
    img = face_recognition.load_image_file(os.path.join('upload', 'images', img_name))
    embedding = face_recognition.face_encodings(img)[0]
    embeddings.append(embedding)
    names.append(person_name)
    return embedding
    #print(names,embeddings)

def vid_detection(search_video):
    cap = cv2.VideoCapture(os.path.join('upload', 'videos', search_video))
    #cap = cv2.VideoCapture(0)

    if (cap.isOpened()== False): 
        print("Error opening video  file")

    while(cap.isOpened()):

        ret, frame = cap.read()
        if ret == True:
            frame = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)

            try:
                face_loc = face_recognition.face_locations(frame)[0]
                #print('face_loc : ',face_loc)
                if face_loc:
                    y1,x2,y2,x1 = face_loc

                    ht,wt = int(abs(y1-y2)/4),int(abs(x1-x2)/4)
                    y1 = max(y1-ht,0)
                    y2 = min(y2+ht,len(frame))
                    x1 = max(x1-wt,0)
                    x2 = min(x2+wt,len(frame[0]))

                    img_new = frame[y1:y2,x1:x2]

                    encodeTest = face_recognition.face_encodings(img_new)[0]

                    results = face_recognition.compare_faces(embeddings, encodeTest)
                    faceDis = face_recognition.face_distance(embeddings, encodeTest)
                    #print(results,faceDis)

                    match_index = np.argmin(faceDis)

                    img_new = cv2.cvtColor(img_new,cv2.COLOR_RGB2BGR)

                    if results[match_index]:
                        name_found = names[match_index]
                        cv2.imwrite(os.path.join(app.config['UPLOAD_FOLDER'],'detected', (name_found + '.jpg')), img_new)
                        return name_found

                    cv2.rectangle(frame,(x1,y1),(x2,y2),(0,255,0),2)

                    
            except IndexError as e:
                pass
            
            frame =cv2.cvtColor(frame,cv2.COLOR_RGB2BGR)
            cv2.imshow('Frame', frame)

            if cv2.waitKey(25) & 0xFF == ord('q'):
                break

        else: 
            break

    cap.release()
    cv2.destroyAllWindows()

    return None

@app.route("/", methods=["GET", "POST"])
def file():
    return render_template('file.html')


@app.route("/subm", methods=["GET", "POST"])
def subm():
    return render_template('upload.html')


@app.route("/multifile", methods=["GET", "POST"])
def multifile():
    files = request.files.getlist('files[]')

    dicti = request.form.to_dict()
    person_name = dicti['person_name']
    person_age = dicti['person_age']
    person_phno = dicti['person_phno']
    person_email = dicti['person_email']
    person_address = dicti['person_address']

    i=1
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(person_name)
            filename += '.' + file.filename.rsplit('.', 1)[1].lower()
            file.save(os.path.join(app.config['UPLOAD_FOLDER'],'images', filename))
            i+=1

            embd = encoding_file(filename,person_name)

    mongo.db.missing_list.insert_one({"name":person_name, "age":person_age, "phno":person_phno, "email":person_email, "address":person_address})
    print("Added new person's data.")

    flash('File(s) successfully uploaded')
    return redirect('/subm')


@app.route("/vinput", methods=["GET", "POST"])
def vinput():
    return render_template('videoupload.html')


@app.route("/videocheck", methods=["GET", "POST"])
def videocheck():
    dicti2 = request.form.to_dict()
    locations = dicti2['location']

    search_video = request.files.get('search_video') #to_dict()
    #print(search_video)
    search_video.save(os.path.join(app.config['UPLOAD_FOLDER'],'videos', (search_video.filename)))
    name_found = vid_detection((search_video.filename))
    #print('Found:',name_found)
    if not name_found:
        print("Found not")
        flash('No missing person recognized. Thank you.')
    else:
        print("Found : " + name_found)
        send_mail(name_found,locations)
        flash('A missing person was recognized. Thank you.')

    return redirect('/vinput')

if __name__ == "__main__":
    app.run(debug=True, threaded=True)