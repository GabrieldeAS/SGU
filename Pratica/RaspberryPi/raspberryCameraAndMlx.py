# import the necessary packages
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.models import load_model
from imutils.video import VideoStream
import numpy as np
import imutils
import time
import cv2
import os
from datetime import datetime
import requests

import smbus
from time import sleep

# Variables
# <<<<<<< main
# ServerURL = 'http://0.0.0.0:5000/data_from_sgu'
=======
# replace here with your server ip
ServerURL = 'http://192.168.0.14:5000/data_from_sgu'
# >>>>>>> main

# Identification of this particular SGU
SGUid = "001"

class MXL90614():
    # Based on the following source-code
    # github.com/sightsdev/PyMLX90614/blob/master/mlx90614.py
    #
    # More details on MLX90614 datasheet on section 8.4 (SMBus)

    BUS = 1         # /dev/i2c-1 is bus=1
    ADDRESS = 0x5a    # MXL90614 slave address is 0x5a

    ############# MLX90614 ADDRESS #################
    Tamb = 0x06
    Tobj1 = 0x07
    Tobj2 = 0x08

    comm_retries = 5
    comm_sleep_amount = 0.1

    def __init__(self):
        self.bus = smbus.SMBus(self.BUS)
        self.t_amb = 0
        self.t_obj1 = 0
        self.t_obj2 = 0

    def read(self):
        err = None
        for i in range(self.comm_retries):
            try:
                self.t_amb = self.bus.read_word_data(self.ADDRESS, self.Tamb)
                self.t_obj1 = self.bus.read_word_data(self.ADDRESS, self.Tobj1)
                self.t_obj2 = self.bus.read_word_data(self.ADDRESS, self.Tobj2)
            except IOError as e:
                err = e
                sleep(self.comm_sleep_amount)
        #raise err

    def celsius(self, data):
        return (data * 0.02) - 273.15


def detect_face(frame, faceNet):
    # grab the dimensions of the frame and then construct a blob
    # from it
    (h, w) = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 1.0, (224, 224),
        (104.0, 177.0, 123.0))

    # pass the blob through the network and obtain the face detections
    faceNet.setInput(blob)
    detections = faceNet.forward()
    print(detections.shape)

    # initialize our list of faces, their corresponding locations,
    # and the list of predictions from our face mask network
    faces = []
    locs = []

    # loop over the detections
    for i in range(0, detections.shape[2]):
        # extract the confidence (i.e., probability) associated with
        # the detection
        confidence = detections[0, 0, i, 2]

        # filter out weak detections by ensuring the confidence is
        # greater than the minimum confidence
        if confidence > 0.5:
            # compute the (x, y)-coordinates of the bounding box for
            # the object
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")

            # ensure the bounding boxes fall within the dimensions of
            # the frame
            (startX, startY) = (max(0, startX), max(0, startY))
            (endX, endY) = (min(w - 1, endX), min(h - 1, endY))

            # extract the face ROI, convert it from BGR to RGB channel
            # ordering, resize it to 224x224, and preprocess it
            face = frame[startY:endY, startX:endX]
            face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
            face = cv2.resize(face, (224, 224))
            face = img_to_array(face)
            face = preprocess_input(face)

            # add the face and bounding boxes to their respective
            # lists
            faces.append(face)
            locs.append((startX, startY, endX, endY))

    # return a 2-tuple of the face locations and their corresponding
    # locations
    return (locs, faces)


def predict_mask(faces, maskNet):
    preds = []

    # only make a predictions if at least one face was detected
    if len(faces) > 0:
        # for faster inference we'll make batch predictions on *all*
        # faces at the same time rather than one-by-one predictions
        # in the above `for` loop
        faces = np.array(faces, dtype="float32")
        preds = maskNet.predict(faces, batch_size=32)

    # return a 2-tuple of the face locations and their corresponding
    # locations
    return preds


# load our serialized face detector model from disk
prototxtPath = r"./face_detector/deploy.prototxt"
weightsPath = r"./face_detector/res10_300x300_ssd_iter_140000.caffemodel"
faceNet = cv2.dnn.readNet(prototxtPath, weightsPath)

# load the face mask detector model from disk
maskNet = load_model("mask_detector.model")

# initialize the video stream
print("[INFO] starting video stream...")
vs = VideoStream(src=0).start()

# valores para a caixa (BOX Start/End X/Y)
BSX = 150
BSY = 50
BEX = 250
BEY = 200

# Cores em BGR (RGB)
blue = (255, 0, 0)
green = (0, 255, 0)
red = (0, 0, 255)

# Função para plotar uma caixa para referencial do usuário
def plot_box(onBox):
    color_box = blue
    label = "Encaixe seu rosto"
    if onBox:
        color_box = green
        label = "Rosto Encaixado"
    cv2.rectangle(frame, (BSX, BSY), (BEX, BEY), color_box, 2)
    cv2.putText(frame, label, (BSX, BSY - 10),cv2.FONT_HERSHEY_SIMPLEX, 0.45, color_box, 2)

# Verifica se o usuário está com o rosto enquadrado corretamente
def is_on_box(locs):
    (locsSX, locsSY, locsEX, locsEY) = locs[0]
    if (locsSX >= BSX and locsEX <= BEX and locsSY >= BSY and locsEY <= BEY):
        return True
    else:
        return False


def get_size_of_box(box):
    return box[2]-box[0]

def get_max_face(locs):
    max_face = locs[0]
    size = get_size_of_box(max_face)
    for box in locs:
        if(get_size_of_box(box) > size):
           max_face = box
    return [max_face]
    
# Contador para o número de frames consecutivos com rosto na caixa
onBoxCounter = -1
face_on_box = False
preds = [[0, 1]]
    
sensor = MXL90614()

import base64
# loop over the frames from the video stream
while True:
    # grab the frame from the threaded video stream and resize it
    # to have a maximum width of 400 pixels
    frame = vs.read()
    frame64 = base64.b64encode(frame)
    frame = imutils.resize(frame, width=400)
    # Espelha a imagem
    frame = cv2.flip(frame,1)

    # detect faces in the frame and determine if they are wearing a
    # face mask or not
    #(locs, preds) = detect_and_predict_mask(frame, faceNet, maskNet)
    
    (locs, faces) = detect_face(frame, faceNet)
    #preds = predict_mask(faces, maskNet)
    
    if locs != []:
        face_on_box = is_on_box(locs)
        # remover outras pessoas do calculo
        #locs = get_max_face(locs)
    
    if face_on_box:
        onBoxCounter = onBoxCounter + 1
    else:
        onBoxCounter = -1
        preds = [[0, 1]]
    
    
    # loop detecting person on box and sending json to server with data: {time, temp, mask, img}
    if (onBoxCounter % 50 == 0) and (face_on_box):
        
        #get the time
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        
        # Aferir temperatura
        # temp = getTemperature()
        sensor.read()
        temp = str(sensor.celsius(sensor.t_obj1))
        temp = str(temp)[0:5]
        print(temp)
        
        # get information about the mask
        preds = predict_mask(faces, maskNet)
        (mask, withoutMask) = preds[0]
        label_mask = "sim" if mask > withoutMask else "nao"
        
        # get the persons img
# <<<<<<< main
#         #personsImg = "newImg"
#         #import base64
#         _, JPEG = cv2.imencode('.jpeg', frame)
#         personsImg = base64.b64encode(JPEG).decode('utf-8')
                
# =======
        personsImg = "newImg"
        cv2.imwrite("lastImg.jpg", frame)
        image = open('lastImg.jpg', 'rb') #open binary file in read mode
        image_read = image.read()
        image_64_encode = str(base64.encodestring(image_read).decode('utf-8'))
        personsImg = image_64_encode
        
# >>>>>>> main
        # Envia um json para um servidor
        payload = {
           "time": current_time,
           "temp": temp,
           "mascara": label_mask,
           "img": personsImg,
           "SGUid": SGUid
        }
        r = requests.post(ServerURL, json=payload)
        print(r)
    
    # loop over the detected face locations and their corresponding
    # locations
    for (box, pred) in zip(locs, preds):
        # unpack the bounding box and predictions
        (startX, startY, endX, endY) = box
        (mask, withoutMask) = pred

        # determine the class label and color we'll use to draw
        # the bounding box and text
        label = "Mask" if mask > withoutMask else "No Mask"
        color = (0, 255, 0) if label == "Mask" else (0, 0, 255)

        # include the probability in the label
        label = "{}: {:.2f}%".format(label, max(mask, withoutMask) * 100)

        # display the label and bounding box rectangle on the output
        # frame
        cv2.putText(frame, label, (startX, startY - 10),cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)
        plot_box(face_on_box)
        cv2.rectangle(frame, (startX, startY), (endX, endY), color, 2)
        print(onBoxCounter)

    
    # show the output frame
    cv2.imshow("Frame", frame)
    key = cv2.waitKey(1) & 0xFF

    # if the `q` key was pressed, break from the loop
    if key == ord("q"):
        break

# do a bit of cleanup
cv2.destroyAllWindows()
vs.stop()
