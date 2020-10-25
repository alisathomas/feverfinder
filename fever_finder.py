import RPi.GPIO as GPIO
import time
from Adafruit_AMG88xx import Adafruit_AMG88xx
import pygame
import os
import math
import numpy as np
from scipy.interpolate import griddata
from colour import Color
from picamera import PiCamera
from datetime import date
from datetime import datetime
import tinys3
import yaml
import boto3

#importing AWS keys
os.environ["AWS_ACCESS_KEY_ID"] = 'redacted'
os.environ["AWS_SECRET_ACCESS_KEY"] = 'redacted'

GPIO.setmode(GPIO.BCM)

TRIG = 23
ECHO = 24


while (True):
    print ("Distance Measurement In Progress")
    
    GPIO.setup(TRIG, GPIO.OUT)
    GPIO.setup(ECHO, GPIO.IN)
    
    GPIO.output(TRIG, False)
    print ("Waiting For Sensor to Settle")
    time.sleep(2)
    
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()
        
    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()
        
    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150
    distance = round(distance, 2)

    print ("Distance: ", distance, "cm")
    
    if(distance >5 and distance < 10):
        print ("1st trial successful")
        #low range of the sensor (this will be blue on the screen)
        MINTEMP = 26
        
        #high range of the sensor (this will be red on the screen)
        MAXTEMP = 40
        
        #how many color values we can have
        COLORDEPTH = 1024
        
        os.putenv('SDL_FBDEV', '/dev/fb1')
        pygame.init()
        
        #initialize the sensor
        sensor = Adafruit_AMG88xx()
        
        points = [(math.floor(ix / 8), (ix % 8)) for ix in range(0, 64)]
        grid_x, grid_y = np.mgrid[0:7:32j, 0:7:32j]
        
        #sensor is an 8x8 grid so lets do a square
        height = 240
        width = 240
        
        #the list of colors we can choose from
        blue = Color("indigo")
        colors = list(blue.range_to(Color("red"), COLORDEPTH))
        
        #create the array of colors
        colors = [(int(c.red * 255), int(c.green * 255), int(c.blue * 255)) for c in colors]
        
        displayPixelWidth = width / 30
        displayPixelHeight = height / 30
        
        lcd = pygame.display.set_mode((width, height))
        
        lcd.fill((255,0,0))
        
        pygame.display.update()
        pygame.mouse.set_visible(False)
        
        lcd.fill((0,0,0))
        pygame.display.update()
        
        #some utility functions
        def constrain(val, min_val, max_val):
            return min(max_val, max(min_val, val))
        
        def map(x, in_min, in_max, out_min, out_max):
          return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
        
        #let the sensor initialize
        time.sleep(.1)
            
        while(1):
        
            #read the pixels
            pixels = sensor.readPixels()
            pixels = [map(p, MINTEMP, MAXTEMP, 0, COLORDEPTH - 1) for p in pixels]

            #perdorm interpolation
            bicubic = griddata(points, pixels, (grid_x, grid_y), method='cubic')
    
            #draw everything
            for ix, row in enumerate(bicubic):
                for jx, pixel in enumerate(row):
                    pygame.draw.rect(lcd, colors[constrain(int(pixel), 0, COLORDEPTH- 1)], (displayPixelHeight * ix, displayPixelWidth * jx, displayPixelHeight, displayPixelWidth))
            
            Max = 0.0
            temps = sensor.readPixels()
            for item in temps:
                if (item > Max):
                    Max = item
            
            Max = Max*9/5 + 32
            black = (0, 0, 0)
            white = (255, 255, 255)
            green = (0, 255, 0) 
            Blue = (0, 0, 128) 
            X=400
            Y=400
            font = pygame.font.Font('freesansbold.ttf', 10) 
            text = font.render('Your Temperature is: ' + str(Max) + '°F', True, white, black)
            if (Max>70):
                text = font.render('Temperature is: ' + str(Max) + '°F. You are sick!', True, white, black)
            textRect = text.get_rect() 
            textRect.midright = (X//2, Y//2)
            lcd.blit(text, textRect)
            pygame.display.update()
            if(Max>70):
                camera = PiCamera()
                #camera.start_preview(alpha=192)
                time.sleep(1)
                now = datetime.now()
                current_time = now.strftime("%H:%M:%S")
                today = date.today()
                filepath = "./images/"+ str(Max) + "°F_" + str(today) + "_" + str(current_time) + ".jpg"
                camera.capture("./images/"+ str(Max) + "°F_" + str(today) + "_" + str(current_time) + ".jpg")
                camera.close()
                client = boto3.client(
                    's3',
                    aws_access_key_id='redacted',
                    aws_secret_access_key='redacted',
                    # aws_session_token=SESSION_TOKEN
                )
                testfile = str(Max) + "°F_" + str(today) + "_" + str(current_time) + ".jpg"
                bucket_name = 'iotlabbucket'
                folder_name = 'images'
                key = folder_name + '/' +testfile   
                s3test = boto3.resource('s3')
                bucket = s3test.Bucket(bucket_name)
                bucket.upload_file(filepath, key)
                
                # Cleanup
                if os.path.exists(filepath):
                    os.remove(filepath)
                #camera.stop_preview()

            time.sleep(10)
            pygame.quit()
            break
        continue
    GPIO.cleanup
