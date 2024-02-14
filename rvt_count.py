import cv2
from PIL import  Image
import numpy as np
import datetime
import time
import ast
import os
import subprocess
from utily import get_limits
from pyModbusTCP.client import ModbusClient

# Define the Modbus server address and port
SERVER_HOST = "192.168.8.2"  # PLC IP address
SERVER_PORT = 502           # Default Modbus TCP port is 502

client = ModbusClient(host=SERVER_HOST, port=SERVER_PORT)

# Connect to the Modbus server
if not client.is_open:
    if client.open():
        print("Connected to the Modbus server")
    else:
        print("Failed to connect to the Modbus server")

#Color range define
gold = [0, 0, 0] #BGR

silver_lower= np.array([0,0,254]) #hsv
silver_upper= np.array([180,10,255])

#Camera Selection
devices_output = subprocess.check_output(['v4l2-ctl', '--list-devices']).decode('utf-8').split('\n')

for line in devices_output:
	if 'HD camera' in line:
		index= devices_output.index(line)
		camid= index +1
		camcall = devices_output[camid]
		busw= camcall.split()[:1]
		camval = busw[0]

#Camera setup
cap = cv2.VideoCapture(camval)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

rvt_count=0
not_rvt_count=0
done = 0
done_neg = 0

#Create and Read txt File
today = str(datetime.date.today())

file_name = today + ".txt"
def save(values,filename):
    with open("data/"+filename,'w') as f:
        f.write(values)
       
def load(filename):
    with open("data/"+filename,'r') as f:
        read=f.read()
    return read

try:
    values = ast.literal_eval(load(file_name))
    print('loaded riveted : ',values['rvt'])
    print('loaded Not riveted : ',values['nrvt'])

except:
    print('Creating...')
    values={'rvt': '0', 'nrvt': '0'}

while True:
    ret, frame = cap.read()
    lable = 0

    #Count Display Setting
    frame[0:70,0:640]=[0,0,255]
    cv2.putText(frame,"Riveted = ",(10,50),cv2.FONT_HERSHEY_PLAIN,2,(255,255,255),2)
    cv2.putText(frame,"Not riveted = ",(300,50),cv2.FONT_HERSHEY_PLAIN,2,(255,255,255),2)

    width,height,dim = frame.shape
    left, top = 270,235
    right,bottom =400,360

    crop = frame[top:bottom,left:right,:]
    hsvImage = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsvImage,silver_lower,silver_upper)
    mask_ = Image.fromarray(mask)
    bbox = mask_.getbbox()

    if bbox is not None: #Socket detected
        x,y,w,h = bbox
        if  x<1 | w>125 | h>122  :
            crop = cv2.rectangle(crop, (x,y),(w,h),(0,0,255),2)
            lowerlimit, upperlimit = get_limits(color=gold)
            mask1 = cv2.inRange(hsvImage, lowerlimit, upperlimit)
            mask1_ = Image.fromarray(mask1)
            bbox2 = mask1_.getbbox()
            lable=1
            

            if bbox2 is not None: #Rivet detected
                x2,y2,w2,h2 = bbox2
                if w2>90 :
                    if w2<120 | h2>100:
                        crop = cv2.rectangle(crop, (x2,y2),(w2,h2),(0,255,0),2)
                        lable=2

    #Same socket frame counting - Since a separate sensor is not used to identify the socket, this step is used to identify the socket separately.
    if lable == 1: 
        not_rvt_count = not_rvt_count + 1

    elif lable == 2: 
        rvt_count = rvt_count + 1

    #Socket counting
    else:
        if rvt_count >= 10:
            rvt_count = 0
            not_rvt_count = 0
            values['rvt'] = int(values['rvt']) + 1
            save(str(values),file_name)


        elif not_rvt_count >=10:
            rvt_count = 0
            not_rvt_count = 0
            
            client.write_single_coil(10, True)
            time.sleep(0.2)
            client.write_single_coil(10, False)
            values['nrvt'] = int(values['nrvt']) + 1
            save(str(values),file_name)       

    cv2.putText(frame,str(values['rvt']),(200,50),cv2.FONT_HERSHEY_PLAIN,2,(255,255,255),2)
    cv2.putText(frame,str(values['nrvt']),(580,50),cv2.FONT_HERSHEY_PLAIN,2,(255,255,255),2)
    
    cv2.imshow('Capture', frame)

    if cv2.waitKey(20) & 0xFF == ord('q'):
        break

#client.close()
cv2.waitKey(0)
cv2.destroyAllWindows()





