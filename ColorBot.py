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

ACTIVATION_RANGE = 1080         #Detection Box size in px
MID_X = ACTIVATION_RANGE / 2    
MID_Y = ACTIVATION_RANGE / 2
COLVAR = 8                      #Maximum Variation in R,G,B 
HIT_REGION = 2                  #Acceptable error in aim 
ESP_ENABLE = 1                  #Enable Mouse Movement via external ESP432 

#Colors: 
#COLOR='#FFFF38'    #Yellow PROP  
COLOR = '#33AEBC'   #Teal 
COLOR2 = '#1BECEA'  
COLOR3 = '#21FFFF'
INGAMESENS = .188 
SENS   = 3


# Globals: 
monitor = centerX = centerY = lower = upper = esp = lastAvg = None
#init arrays 
imageTime = colorTime = distTime = totTime = []


dc = win32gui.GetDC(0)
dcObj = win32ui.CreateDCFromHandle(dc) 

def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def grab_screen(region=None):
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
    #return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

def drawRect(bbox, i, lbl):
    #Draw Rectangle around Enemies:
    for box in bbox: 
        cv2.rectangle(img, (box[0], box[1]), (box[2], box[3]), (0, 0, 255), 2)
        cv2.putText(img, str(box[6]), (box[0], box[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cv2.putText(img, str(lbl), (box[0], box[1] + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
    cv2.line(img, (int(bbox[i][4]), int(bbox[i][5])), (int(ACTIVATION_RANGE / 2), int(ACTIVATION_RANGE / 2)),
        (255, 0, 0), 1, cv2.LINE_AA)
    #resize = cv2.resize(img, (340, 340))
    cv2.imshow("Detection", img)
    cv2.waitKey(1)
    
     


#-------------------------------------------------
# espInit(): Initialize ESP using serial library
#   and clear in/out buffers 
#-------------------------------------------------
def espInit(): 
    global esp
    esp = serial.Serial('COM5', 115200, timeout=None)   #Will wait for data on read 
    #esp = serial.Serial('COM5', 115200, timeout=0   )   #No wait for data on read 
    esp.reset_output_buffer()
    esp.reset_input_buffer()

#-------------------------------------------------
# getScreenRed(): Get monitor width and height,
#   Get center of screen:v
#-------------------------------------------------
def getScreenRes(): 
    global monitor, centerX, centerY, sct
    with mss.mss() as sct:
        Wd, Hd = sct.monitors[1]["width"], sct.monitors[1]["height"]
        monitor = (int(Wd / 2 - ACTIVATION_RANGE / 2),
                int(Hd / 2 - ACTIVATION_RANGE / 2),
                int(Wd / 2 + ACTIVATION_RANGE / 2),
                int(Hd / 2 + ACTIVATION_RANGE / 2))
        
        #Center of Screen
        centerX = int(Wd/2)
        centerY = int(Hd/2)

#-------------------------------------------------
# updateColors(col): Uses 
#-------------------------------------------------
def updateColors(col):
    #Get Colors: 
    red, green, blue = hex_to_rgb(col)
    #Lower and upper colors (frame is BGR not RGB)
    global lower, upper
    lower = [blue-COLVAR, green-COLVAR, red-COLVAR]
    upper = [blue+COLVAR, green+COLVAR, red+COLVAR]

    #Error check: 
    for i in range(len(lower)):
        if lower[i] < 0:
            lower[i] = 0
        if upper[i] > 255: 
            upper[i] = 255
    

#-------------------------------------------------
# waitRightClick(): infinite loop until right
#   mouse pressed
#-------------------------------------------------
def waitRightClick():
    while not (win32api.GetKeyState(0x05) == -127 or win32api.GetKeyState(0x05) == -128):
        time.sleep(.00001)

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




if __name__ == "__main__": 
    #Open connection
    espInit()

    #Get monitor width and height, Get center of screen:
    getScreenRes()

    #Get Colors: 
    updateColors(COLOR)

    #Record Time
    start = time.time()
    lastAvg = time.time()
    lastCycle = time.time()
    lastshot = time.time()
    toggle = 1

    #Wait for user 
    print("Press M4 to start")
    while not (win32api.GetKeyState(0x05) == -127 or win32api.GetKeyState(0x05) == -128):
        time.sleep(.02)
    print("Starting...")
    time.sleep(1)
    print("GO!")

    

    loop = True
    while loop:
        #Check MB4 for toggle: 
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

            #Get location of each color within range 
            getCol1 = time.time()
            [y, x] = np.where((lower[0] <= frame[:,:,0]) & (upper[0] >= frame[:,:,0]) & 
                            (lower[1] <= frame[:,:,1]) & (upper[1] >= frame[:,:,1]) & 
                            (lower[2] <= frame[:,:,2]) & (upper[2] >= frame[:,:,2]))
            getCol2 = time.time()

            #Clear Search parameters 
            distances = []
            closest = 10000
            closestEnemy = None

            #Check for successfull hit in middle of screen
            getDist1 = time.time()
            if (MID_X in x[np.where(np.logical_and(y>=MID_Y - HIT_REGION, y<=MID_Y + HIT_REGION))]) or \
                (MID_Y in y[np.where(np.logical_and(x>=MID_X - HIT_REGION, x<=MID_X + HIT_REGION))]):
                hit = str("hit\n")
                esp.write(hit.encode())
                esp.read(1)
                esp.reset_input_buffer()
                lstClickTime=time.time()
            

            #Else Check whole region 
            else: 
                for i in range(len(x)):
                    #Else get distances TODO Optimize? 
                    dist = int(math.sqrt((x[i] - ACTIVATION_RANGE/2)**2 + (y[i] - ACTIVATION_RANGE/2)**2))  
                    distances.append(dist)

                    #Get closest obj.
                    if distances[i] < closest: 
                        closest = distances[i]
                        closestEnemy = i
            getDist2 = time.time()
            

            if closestEnemy is not None: 
                #get dX, dY 
                movX = int(((x[closestEnemy] - MID_X) + 1) * SENS) 
                movY = int(((y[closestEnemy] - MID_Y) + 1) * SENS) 
                data = str(movX) + ':' + str(movY) + '\n' 


                minmove = abs(movX) > 2 or abs(movY) > 2
                maxmove = abs(movX) < 150 and abs(movY) < 150

                writet1 = time.time()
                if(minmove and maxmove and ESP_ENABLE): 
                    #Wait for confirmation from last execution 
                    resp = esp.readline()
                    while b"complete" not in resp:
                        resp = esp.readline()

                    esp.write(data.encode()) 
                writet2 = time.time()
            

                if ((time.time() - lastshot) > .1):
                    hit = str("hit\n")
                    esp.write(hit.encode())
                    resp = esp.readline()
                    lastshot = time.time()
                    #Wait for confirmation 
                    while b"complete" not in resp:
                        resp = esp.readline()
                        print(resp) 





            times = [getImg1, getImg2, getCol1, getCol2, getDist1, getDist2] 
            printTimes(times)   
