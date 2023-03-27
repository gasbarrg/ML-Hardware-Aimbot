import time
import torch
import cv2
import mss.tools
import numpy as np
import math
import keyboard
import serial
import win32api
import win32con
import win32gui
import win32ui
import winsound
from win32api import GetSystemMetrics

ESP_ENABLE = 1                  #Enable ESP for mouse movement       
FIRE_ENABLE = 0                 #Enable ESP for mouse clicking / shooting     
DETECTION_RANGE = 1080          #Detection Box size in px
ACTIVATION_RANGE = 125          #Lock on range box size in px 
COLVAR = 8                      #Maximum variation in Red, Green, and Blue
AIM = "head"                    #Aim location. "head" or "center"
SENS   = 3                      #Bot sens. WIP. 
INGAMESENS = .188 
#ML Variables: 
CONFIDENCE_THRESHOLD = 0.6      #Minimum confidence for detection
NMS_THRESHOLD = 0.7             #Box Supression for overlapping detections 
MAX_DET = 5                     #Maximum Number of detections 
#Screen Variables 
MID_X = DETECTION_RANGE / 2
MID_Y = DETECTION_RANGE / 2
# Globals: 
monitor = centerX = centerY = lower = upper = esp = lastAvg = None
#Init arrays 
imageTime = colorTime = distTime = totTime = []
#Screen Objects 
dc = win32gui.GetDC(0)
dcObj = win32ui.CreateDCFromHandle(dc) 


#---------------------------Functions----------------------------


def grab_screen(region=None):
    """Returns an array of pixels in the defined region """

    hwin = win32gui.GetDesktopWindow()

    if region:
        left, top, x2, y2 = region
        widthScr = x2 - left + 1
        heightScr = y2 - top + 1

    else:
        widthScr = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
        heightScr = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
        left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
        top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)     

    hwindc = win32gui.GetWindowDC(hwin)
    srcdc = win32ui.CreateDCFromHandle(hwindc)
    memdc = srcdc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(srcdc, widthScr, heightScr)
    memdc.SelectObject(bmp)
    memdc.BitBlt((0, 0), (widthScr, heightScr), srcdc, (left, top), win32con.SRCCOPY)
 
    signedIntsArray = bmp.GetBitmapBits(True)
    img = np.frombuffer(signedIntsArray, dtype='uint8')
    img.shape = (heightScr, widthScr, 4)
 
    srcdc.DeleteDC()
    memdc.DeleteDC()
    win32gui.ReleaseDC(hwin, hwindc)
    win32gui.DeleteObject(bmp.GetHandle())


    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)    


def displayVision(bbox, i, lbl):
    """Opens an Additional window to display machine learning output

    Draws squares around each detection and labels their respective confidence. Labels each detections class. 
    Draws a line to the closest detection aim point. 
    """
    #Draw Rectangle around Enemies:
    for box in bbox: 
        cv2.rectangle(img, (box[0], box[1]), (box[2], box[3]), (0, 0, 255), 2)
        cv2.putText(img, str(box[6]), (box[0], box[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cv2.putText(img, str(lbl), (box[0], box[1] + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
    cv2.line(img, (int(bbox[i][4]), int(bbox[i][5])), (int(DETECTION_RANGE / 2), int(DETECTION_RANGE / 2)),
        (255, 0, 0), 1, cv2.LINE_AA)
    #resize = cv2.resize(img, (340, 340))
    cv2.imshow("Detection", img)
    cv2.waitKey(1)
    
     
def espInit(): 
    """Initialize ESP using serial library and clear in/out buffers"""
    global esp
    esp = serial.Serial('COM5', 115200, timeout=None)   #Will wait for data on read 
    #esp = serial.Serial('COM5', 115200, timeout=0   )   #No wait for data on read 
    esp.reset_output_buffer()
    esp.reset_input_buffer()


def getScreenRes(): 
    """Get monitor width and height, get center of screen"""
    global monitor, centerX, centerY, sct
    with mss.mss() as sct:
        Wd, Hd = sct.monitors[1]["width"], sct.monitors[1]["height"]
        monitor = (int(Wd / 2 - DETECTION_RANGE / 2),
                int(Hd / 2 - DETECTION_RANGE / 2),
                int(Wd / 2 + DETECTION_RANGE / 2),
                int(Hd / 2 + DETECTION_RANGE / 2))
        
        #Center of Screen
        centerX = int(Wd/2)
        centerY = int(Hd/2)


#-------------------------------------------------
# avgList(): returns average value of an entire 
#   list
#-------------------------------------------------
def avgList(lst): 
    if(len(lst) > 0):
        return sum(lst) / len(lst)
    else:
        return 0 

#-------------------------------------------------
# printTimes(t): Prints calculation times for 
#   important functions every second. Must be called 
#   repeadedly to add times to array 
#-------------------------------------------------
def printTimes(t):
    global lastAvg, imageTime, colorTime, distTime, totTime
    
    #Add times to list over a second 
    if ((time.time() - lastAvg) < 1):
        imageTime.append(t[1] - t[0])
        colorTime.append(t[3] - t[2])
        distTime.append( t[5] - t[4])
        totTime.append(time.time() - t[0])
        
    
    #Else, take averages and print
    else:
        avgImageTime = round(avgList(imageTime)* 1000, 2) 
        avgColorTime = round(avgList(colorTime)* 1000, 2) 
        avgDistTime  = round(avgList(distTime) * 1000, 2) 
        avgTotTime   = round(avgList(totTime)  * 1000, 2)
        print("---------------------------------")
        print("Average image capture time: ", avgImageTime, "ms")
        print("Average color calc time:    ", avgColorTime, "ms")
        print("Average dist calc time:     ", avgDistTime,  "ms")
        print("Average Total Cycle Time:   ", avgTotTime,   "ms") 
        #Clear Lists
        imageTime = []; colorTime = []; distTime = []
        lastAvg = time.time()


#==========================MAIN===============================
if __name__ == "__main__": 
    if ESP_ENABLE: 
        #Open connection
        espInit()

    #Get monitor width and height, Get center of screen:
    getScreenRes()

    #Record Time
    start = time.time()
    lastAvg = time.time()
    lastCycle = time.time()
    lastshot = time.time()


    #model = torch.hub.load('yolov5', 'custom', path=r"C:\Users\Gabe\Documents\PersonalFiles\AimLabs-BotTEST\yolov5\runs\train\AL-Nano300Epoch\weights\best.pt",\
    #                       source='local')
    #model = torch.hub.load('yolov5', 'custom', path=r"C:\Users\Gabe\Documents\PersonalFiles\AimLabs-BotTEST\yolov5\runs\train\VAL-Nano70Epoch\weights\best.pt",\
    #                    source='local')
    # model = torch.hub.load('yolov5', 'custom', path=r"C:\Users\Gabe\Documents\PersonalFiles\AimLabs-BotTEST\yolov5\runs\train\CS-Nano1Epoch\weights\best.pt",\
    #                     source='local')
    model = torch.hub.load('yolov5', 'custom', path=r"C:\Users\Gabe\Documents\PersonalFiles\AimLabs-BotTEST\yolov5\runs\train\CS-Nano300Epoch\weights\best.pt",\
                        source='local')

    #Assign model variables 
    model.conf = CONFIDENCE_THRESHOLD
    model.iou  = NMS_THRESHOLD
    model.max_det = MAX_DET

    #Wait for user 
    print("Press M4 to start")
    while not (win32api.GetKeyState(0x05) == -127 or win32api.GetKeyState(0x05) == -128):
        time.sleep(.02)
    print("Starting...")
    time.sleep(1)
    print("GO!")


    toggle = 1
    loop = True
    while loop:
        #Check Toggle: 
        if (not toggle and win32api.GetKeyState(0x05) == -127 or win32api.GetKeyState(0x05) == -128): 
            toggle = 1
            winsound.Beep(700, 200)
            time.sleep(.4)
        elif(toggle and win32api.GetKeyState(0x05) == -127 or win32api.GetKeyState(0x05) == -128): 
            toggle = 0
            time.sleep(.4)
            winsound.Beep(500, 200)
        
        #Exit condition
        if keyboard.is_pressed(']'):
            cv2.destroyAllWindows()
            sct.close()
            esp.close()
            loop = False
            break
        

        if(toggle): 
            #Get image array 
            getImg1 = time.time()
            img = grab_screen(region=monitor)
            frame = np.array(img)
            getImg2 = time.time()


            modelt1 = time.time()
            results = model(frame)
            box = results.xyxyn[0].detach().cpu().clone().numpy()
            modelt2 = time.time()
            enemyNum = len(box)

            #Ensure Target
            if enemyNum == 0:
                pass

        
            #Clar Vals 
            distances = []
            closest = 10000
            closestObject = None
            closestX = None
            closestY = None
            conf = None
            bbox = []

            dist1 = time.time()
            for i in range(len(box)): 
                x1 = int(box[i][0] * DETECTION_RANGE)
                y1 = int(box[i][1] * DETECTION_RANGE)
                x2 = int(box[i][2] * DETECTION_RANGE)
                y2 = int(box[i][3] * DETECTION_RANGE)
                width = x2-x1           #Box width  
                height = y2-y1          #Box height 
                #Calculate aim width 
                centerX = x1 + (width / 2)
                #Calculate aim height 
                if AIM == "center":
                    centerY = y1 + (height / 2)  
                elif AIM == "head":
                    centerY = y1 + (height / 6) 
                #Assign Confidence 
                conf = round((box[i][4]) * 100, 2)
                #Assign Classes 
                if box[i][5]:
                    lbl = 'T'
                else:
                    lbl = 'CT'

                #Calculate distance to middle of screen 
                distance = int(math.sqrt(((centerX - DETECTION_RANGE / 2) ** 2) + ((centerY - DETECTION_RANGE / 2) ** 2)))
                distances.append(distance)

                #Save each box 
                bbox.append([x1, y1, x2, y2, centerX, centerY, conf, lbl])

                #Find closest box 
                if distances[i] < closest:
                    closest = distances[i]
                    closestObject = i
                    closestX = centerX - MID_X
                    closestY = centerY - MID_Y
            dist2 = time.time() 
                

            if closestObject is not None: 
                movX = int(closestX * SENS)
                movY = int(closestY * SENS)
                #Turn into string for ESP 
                data = str(movX) + ':' + str(movY) + '\n' 

                dispt1 = time.time()
                displayVision(bbox, closestObject, lbl)
                dispt2 = time.time()    

                #Ensure target within attack radius 
                minmove = abs(closestX) > 2 or abs(closestY) > 2
                maxmove = abs(closestX) < ACTIVATION_RANGE and abs(closestY) < ACTIVATION_RANGE

                writet1 = time.time()
                if(minmove and maxmove and ESP_ENABLE): 
                    #Wait for confirmation from last execution 
                    resp = esp.readline()
                    while b"complete" not in resp:
                        resp = esp.readline()
                    esp.write(data.encode()) 
                
                    #Fire and wait for reply 
                    if FIRE_ENABLE:             
                        if ((time.time() - lastshot) > .1):
                            hit = str("hit\n")
                            esp.write(hit.encode())
                            resp = esp.readline()
                            lastshot = time.time()
                        while b"complete" not in resp:
                            resp = esp.readline()        
                writet2 = time.time()


                ##Prints: 
                print("-----------------------")
                print("Model time:   ", round((modelt2 - modelt1)* 1000, 2), "ms")
                print("Display Time: ", round((dispt2 - dispt1)* 1000, 2), "ms")
                print("Distance Time:", round((dist2 - dist1)* 1000, 2), "ms")
                print("Write Time:   ", round((writet2 - writet1)* 1000, 2), "ms")
                print("Total Time:   ", round((writet2 - getImg1)* 1000, 2), "ms")



#==========================GUI===============================