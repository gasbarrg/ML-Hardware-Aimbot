<h1>Machine Learning External Hardware Aimbot</h1>
<strong>DISCLAIMER:</strong> 
<em>This package is for educational purposes only. Cheating or botting is not allowed in CSGO, Valorant, or other competative online FPS. Do not use this package to violate the rules. Please check that the user agreement for your game allows the use of such a program!</em><br>
<strong>NOTICE:</strong> 
<em>This software comes as-is. I will not be making any major updates or responses to better the ease-of-use. This software was developed for educational purposes and will not be maintained for distribution</em>
<br>
<br>

## Purpose 
The idea was to create an aimbot that could be used across a wide variety of games by training a neural network on images of whatever game you choose. Additionally, because of anti-cheat measures being able to detect mouse injections or software emulated mouse movements, an ESP432-S2 was implemented in order to act as an external mouse. 

## Features 
* Efficient screen capturing
* Mouse Movement from external ESP32-S2
* GPU-accelerated neural network inference for enemy/target detection (NVIDIA GPUs only)
* Aim Location Selection 
* Detection Region Selection 
* ML Vision Display 

## ML Vision Display Example: 
![ML Vision](https://github.com/gasbarrg/ML-Hardware-Aimbot/blob/master/SampleCaptures/ML-Embedded-Aimbot.png)

## Hardware Requirements: 
* ESP32-S2
![ESP32-S2](https://github.com/gasbarrg/ML-Hardware-Aimbot/blob/master/SampleCaptures/ESP32.png)
* x2 Micro USB Cables

## Software Requirements:
* You will need to train your own object detection model using YOLOv5. Replace line 192 with the path to your weights. 
* You will need to write code to upload to the ESP32 to interperate mouse movements as a flow of signed 8 bit integers in the form "X:Y" - This code may be uploaded in the futre.  



