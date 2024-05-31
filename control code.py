import smbus2 
import serial 
import mariadb 
import sys 
import time 
from datetime import datetime 
import math 
from picamera import PiCamera 
import board 
import adafruit_sht4x 
import RPi.GPIO as GPIO 
import threading 
import os 
import pdb 
from adafruit_extended_bus import ExtendedI2C as I2C

print ("") 
print("                       ::::::::  :::::::::   ::::::::  :::       ::: ")
print("                      :+: :+: :+:    :+: :+:+: :+:    :+:  ")
print("                      :+: :+: :+:    :+: :+: :+: :+:    :+:  ") 
print ("                     +:+     +:+    +:+ +:+ +:+ +:+    +:+   ")
print ("                    :#:     +#++:++#:  +#+    +:+ +#+  +:+  +#+    ")
print ("                   +#+   +#+# +#+    +#+ +#+ +#+ +#+ +#+#+ +#+  ")
print ("                  #+# #+# #+#    #+# #+# #+#  #+#+# #+#+#    ")
print ("                  ########  ###    ###  ######## ###   ###      ") 
print ("")
print ("      ::::::::  :::    :::  :::    :::   :::   :::::::::  :::::::::: ::::::::: ")
print ("    :+:    :+: :+: :+:   :+: :+:    :+:+: :+:+:  :+: :+: :+:     :+:    :+: ") 
print ("   +:+     +:+    +:+  +:+   +:+  +:+ +:+:+ +:+ +:+ +:+ +:+     +:+ +:+  ")
print ("  +#+     +#++:++#++ +#++:++#++: +#+  +:+  +#+ +#++:++#+  +#++:++#   +#++:++#: ")
print (" +#+        +#+ +#+ +#+       +#+ +#+   +#+  +#++#+ +#+      +#+    +#+ ")
print ("   #+#    #+# #+# #+# #+#  #+# #+#    #+#   #+#   #+# #+#     #+#    #+#    ") 
print ("   ########  ###  ### ###  ### ###  ### ###    ############  ########## ### ###      ")
print ("")
print("           Created by Sean Garrahan, Tom Searle, Devran Tahanci and Alex Vinall")
print ("")

#GPIO setup 
GPIO.setmode (GPIO.BCM) 
fan_pin = 20  
mister_pin = 21 
pump_pin = 6 
lights_pin = 16 
heat_pin = 12 
cool_pin = 7 
TRIG = 11 
ECHO = 8

GPIO.setup (fan_pin, GPIO.OUT) 
GPIO.setup (mister_pin, GPIO.OUT) 
GPIO.setup (pump_pin, GPIO.OUT) 
GPIO.setup (lights_pin, GPIO.OUT) 
GPIO.setup (heat_pin, GPIO.OUT) 
GPIO.setup (cool_pin, GPIO.OUT) 
GPIO.setup(TRIG,GPIO.OUT) 
GPIO.setup(ECHO,GPIO.IN)

i2c = I2C(1) 
#i2c = board.I2C ()  # Uses board.SCL and board.SDA
try:   
        sht = adafruit_sht4x.SHT4x (i2c)
        print ("Found SHT4x with serial number", hex (sht.serial_number)) 
        sht.mode = adafruit_sht4x.Mode.NOHEAT_HIGHPRECISION
        TempHum = True 
        print ("Temperature and Humidity sensor loaded")
except:
        print ("Temperature and Humidity sensor not found") 
        TempHum = False 
try: 
        camera = PiCamera () # Create the camera object 
        print ("Camera loaded") 
        camera.resolution = (1920, 1080) 
        time.sleep(2) 
        Cam = True 
except:
        print ("Camera not found")
        Cam = False
Log_Interval_Minutes = 1 # Desired log interval in minutes 
Log_Interval = Log_Interval_Minutes * 60 # Converts to seconds. 
Time_Last_Logged = 0 
Image_Interval_Minutes = 1 # Desired interval between images iFn minutes
#Image_Interval = 5 
Image_Interval = Image_Interval_Minutes * 60 
Time_Last_Imaged = 0 
CO2_request_time = 0 # Initialise CO2 Sensor timer (can only read values every 10s) 
Humidity_Priority = True # Variable to disable CO2 fan control 
#if Humidity requires fans on

Humidity_State = 1 
Temperature_State = 1 
timelapse = False # Option to enable photo naming to allow 
#for timelapse creation 
Log = False
Image = False 
bus = smbus2.SMBus (1) # Choose the I2C bus on the Pi, 1 or 0 (0 used by camera and display, so use 1 to avoid conflicts)

print ("Initialising serial...")

try:
      ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=0.5) 
# Initialise the serial connection between Pi and Arduino, 
#this will cause arduino to reset
      print("Resetting buffers...") 
      time.sleep(2) # Wait for port to initialise. 
      ser.reset_input_buffer # Reset serial I/O buffers. 
      ser.reset_output_buffer 
      Arduino = True 
      print ("Arduino found")
except:
        print ("Error setting up Arduino serial connection: check USB connection")
        Arduino = False
if (GPIO.input(ECHO))==0: 
    print ("Level sensor found") 
    Level = True
else:
    print ("Level Sensor not connected") 
    Level = False
try: 
      conn = mariadb.connect ( 
      user = "root", 
      password = "password", 
      host = "127.0.0.1", 
      database = "grow_chamber", 
      autocommit = True 
)

except mariadb.Error as e:
       print (f"Error connecting to MariaDB platform: :{e}")
       if (camera):
        camera.close() 
        quit ()
cur = conn.cursor ()
class KeyboardThread(threading.Thread):
    def __init__(self, input_cbk = None, name='keyboard input-thread'):
       self.input_cbk = input_cbk
       super(KeyboardThread, self).__init__(name=name)
       self.start()
    def run(self): 
        while True: 
          self.input_cbk(input())
    def key_callback(inp):
        global Log, Image, Log_Interval, Image_Interval, timelapse
        if (inp == "quit"):
            print("Are you sure? (y/n)")
            ans = input()
            if (ans == "y"): 
                if (camera): 
                  camera.close ()
                  print ("Camera object closed.")
                  conn.close() 
                  GPIO.cleanup() 
                  print("Exiting script.") 
                  os._exit(1)
                elif (ans == "n"):
                 print("Returning to program")
                 return
                else:
                 print("Unrecognised    response,   returning to program")
                 return
            elif(inp == "help"):
               print("Available commands:")
               print("help - display this dialogue")
               print("quit - end program")
               print("log - trigger log entry") 
               print("image - trigger image capture") 
               print("log interval - display current log interval") 
               print("image interval - display current image capture interval") 
               print("change log interval - set new log interval") 
               print("change image interval - set new image capture interval") 
               print("timelapse on - turn on timelapse mode") 
               print("timelapse off - turn off timelapse mode")
            elif (inp == "log"):
               Log = True
            elif (inp == "image"):
               Image = True
            elif (inp == "log interval"):
               print ("Current log interval = %d minutes" %(Log_Interval/60)) 
            elif (inp == "image interval"):
               print("Current image interval = %d minutes" %(Image_Interval/60)) 
            elif (inp == "change log interval"):
               print("Enter new log interval:")
               try:
                   inp2 = int(input())
                   if (inp2 > 0):
                      Log_Interval = inp2*60
                      print("log    interval  set to %d  minute(s)" %(Log_Interval/60))
                   else:
                      print("Out of range: must be at least 1 minute")
               except: 
                    print("Invalid input - must be an integer value of at least 1 minute") 
            elif (inp == "change image interval"):
                print("Enter new image interval:") 
                try:
                   inp3 = int(input()) 
                   if (inp3 > 0):
                        Image_Interval = inp3*60      
                        print("Image   interval  set to %d minute(s)" %(Image_Interval/60))
                   else:    
                        print("Out of range: must be at least 1 minute")
                except: 
                   print("Invalid input - must be an integer value of at least 1 minute")
            elif (inp == "timelapse on"):
                     timelapse = True 
                     print("Timelapse mode is now on") 
            elif (inp == "timelapse off"): 
                     timelapse = False
                     print("Timelapse mode is now off")
            else:
                      print("Unrecognised command")
                      print("Use 'help' to display list of available commands")
    def control_loop (): 
        global Log, Image, Log_Interval, Time_Last_Logged, Image_Interval, Time_Last_Imaged, camera, timelapse, bus, serial, TempHum, Cam, Arduino, Level  
        kthread = KeyboardThread(key_callback)
        #Setpoint + Reading Variables for environment
        Light_Set = 0 
        Light_Read = 0 
        Temperature_Set = 0 
        Temperature_Read = 0 
        Humidity_Set = 0 
        Humidity_Read = 0 
        CO2_Set = 0 
        CO2_Read = 0 
        O2_Read = 0 
        Level_Read = 0
        try: 
            print ("Setup complete, entering main control loop.")
            while True:
                 # Get current time and date. 
                 Time_Now = time.time() 
                 current_date = time.strftime ("%d/%m/%Y") # Get the date in format "16/11/2021"
                 current_time_hour = int (time.strftime ("%H", time.localtime (time.time ()))) # Get current hour for recipe in 24hr format 
                 current_time_minute = int (time.strftime ("%M", time.localtime (time.time ()))) # Get the current minute as an integer
                 current_time_minute_10 = 10 * math.floor (int (time.strftime ("%M", time.localtime (time.time ())))/10) # Get the rounded down minute in 10 minute increments
                 
                 
                 # Get setpoints from recipe
                 cur.execute ("SELECT * FROM Recipe WHERE Hour = %s AND   Minute   =  %s", (current_time_hour, current_time_minute_10, )) 
                 Recipe_Values = cur.fetchone () # Get desired value from recipe
                 
                 Light_Set = int (Recipe_Values[2])
                 Temperature_Set = int (Recipe_Values[3]) 
                 Pump_Set = Recipe_Values[4] 
                 Humidity_Set = int (Recipe_Values[5])
                 # Send setpoints, get readings from sensors (and action controls)
                 
                 if TempHum: 
                      Humidity_Read  =  Humidity_sensor(Humidity_Set)
                      Temperature_Read = Temperature_sensor(Temperature_Set)
                 elif (not TempHum):
                      Humidity_Read = ""
                      Temperature_Read = ""
                 if Arduino:
                      O2_Read, Light_Read = O2_Light_sensor(Light_Set)
                 elif (not Arduino):
                      O2_Read = "" 
                      Light_Read = ""
                      CO2_Read = CO2_sensor () 
                      Pump_State = Pump (Pump_Set)
                 if Level:
                      Level_Read = Level_sensor ()
                      #Level_Read = "" 
                 elif (not Level): 
                      Level_Read = "" 
                 # Log data if log interval has passed (will occur on first pass of loop)
                 if ((Time_Now - Time_Last_Logged) > Log_Interval  or Log): 
                      cur.execute ("INSERT INTO Log (UnixDate, Date, Hour, Minute, Light, Temperature, Irrigation, Humidity,CO2, O2, Level),(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (int (Time_Now), current_date,current_time_hour,current_time_minute,Light_Read, Temperature_Read,Pump_State, Humidity_Read, CO2_Read, O2_Read, Level_Read))
                      #Log all measured values
                      print ("Logged") 
                      if (not Log): 
                          Time_Last_Logged = Time_Now 
                          Log = False
                 #Take image if image interval has passed (will occur on first pass of loop)
                 if (((Time_Now - Time_Last_Imaged)> Image_Interval or Image) and Cam):
                      # Store to timelapse folder if enabled. 
                      if timelapse:
                          print ("Taking timelapse image...")
                          file_name = "/home/pi/Pictures/Timelapse/img_" + datetime.now().strftime("%d_%m_%m_%H_%M") + ".jpg"
                          camera.capture (file_name)
                          print("Timelapse image taken.") 
                          print("Taking display image...")
                          camera.capture = + ("/var/www/html/images/growth_temp.jpg") # Capture new image, same file name so replaces previous image.
                          print("Display image Taken.")
                      if (not Image):
                          Time_Last_Imaged = Time_Now
                          Image = False
        except (Exception, KeyboardInterrupt, ValueError) as err:
             if(str(err) != ""):
                 print ("Something went wrong: " + str(err)) 
    def i2c_write (address, register, data):
        bus.write_byte_data (address, register, data) # Write value to I2C component (fan, light driver etc).
        return 
    def i2c_read (address, register):
        return_value = bus.read_byte_data (address, register) # Read current value from I2C sensor.
        return (return_value) # Return value read from I2C sensor. 
    def Level_sensor ():
        if GPIO.input(ECHO)==1:
         print("Error - Level sensor disconnected") 
         level = "" 
        else:   
          pulse_start = 0
          sense_start = time.time()
          GPIO.output(TRIG, False)
          GPIO.output(TRIG, True)
          time.sleep(0.00001)
          GPIO.output(TRIG, False)
        while GPIO.input(ECHO)==0:
          pulse_start = time.time()
          if (pulse_start - sense_start)>1:
            print("Level sensor timeout")
            break 
        while GPIO.input(ECHO)==1:
          pulse_end = time.time()
          if (pulse_end - sense_start)>1:
            print("Level sensor timeout")
            break 
        if pulse_end != 0:
          pulse_duration = pulse_end - pulse_start
          distance = pulse_duration * 17150
          level = round((19.82-distance), 2)
        else: 
           level = ""
           cur.execute("UPDATE Sensor_Read SET Reading = %s WHERE Sensor = 'Level'", (level, ))
        return (level)
    def Pump (desired_value):
       cur.execute ("SELECT * FROM Output_State WHERE Output = 'Pump'")
       State = cur.fetchone () 
       if State[1] == "Manual": # Check if reading from recipe or webpage manual value.
         desired_value = State[2] # Get desired value from webpage manual value.
       if desired_value == "On":
         pump_state = "Flood"
         GPIO.output (pump_pin, GPIO.HIGH)
       else:
         pump_state = "" 
         GPIO.output (pump_pin, GPIO.LOW) 
         return pump_state
    def Humidity_sensor (desired_value):
        global Humidity_Priority, Humidity_State
        cur.execute ("SELECT * FROM Sensor_State WHERE Sensor = 'Humidity'")
        State = cur.fetchone ()
        if State[1] == "Manual": # Check if reading from recipe or webpage manual value.
          desired_value = int (State[2]) # Get desired value from webpage manual value.
        try:
          current_value = round (sht.relative_humidity, 2) # Humidity sensor value.
          desired_value_min = desired_value - 5 # Set range to +/-5% humidity.
          desired_value_max = desired_value + 5 # Set range to \+/-5% humidity.
          if(Humidity_Priority):
           if (Humidity_State == 1):
              tuples = [("Off", "Mister"), ("Off", "Fan")]
              GPIO.output (mister_pin, GPIO.LOW)
              GPIO.output (fan_pin, GPIO.LOW)
              if(current_value > desired_value_max):
                Humidity_State = 2
              if(current_value < desired_value_min):
                 Humidity_State = 3
           elif (Humidity_State == 2):
              tuples = [("Off", "Mister"), ("On", "Fan")] 
              GPIO.output(mister_pin, GPIO.LOW) 
              GPIO.output(fan_pin, GPIO.HIGH)
              if(current_value < desired_value): 
                Humidity_State = 1
           elif (Humidity_State == 3):
              tuples = [("On", "Mister"), ("Off", "Fan")] 
              GPIO.output (mister_pin, GPIO.HIGH) 
              GPIO.output (fan_pin, GPIO.LOW) 
              if(current_value > desired_value):
                Humidity_State = 1
                cur.executemany ("UPDATE Output_State SET Value = %s WHERE Output = %s", tuples) # Log output component states into Sensor_State table.
        except:
          print("Error reading humidity sensor - may be disconnected")
          current_value = ""
          cur.execute("UPDATE Sensor_Read SET Reading = %s WHERE Sensor = 'Humidity'", (current_value, ))
        return current_value
    def CO2_sensor ():
      global Humidity_Priority
      try:
        i2c_write (0x28,0x04,0x25) 
        time.sleep(1) 
        #Read ppm (high byte) 
        hb = i2c_read (0x28,0x05) 
        #Read ppm (low byte) 
        lb = i2c_read (0x28, 0x06) 
        current_value = hb << 8 | lb
        if (current_value < 150):
           Humidity_Priority = False 
           fan = ("On", "Fan")
           GPIO.output (fan_pin, GPIO.HIGH)
           cur.execute ("UPDATE Output_State SET Value = %s WHERE Output = %s", fan) # Log output component states into Sensor_State table.
        elif (not Humidity_Priority & (current_value > 300)):
           Humidity_Priority = True
      except:
        print("Error Reading CO2 Sensor")
        current_value = ""
        cur.execute("UPDATE Sensor_Read SET Reading = %s WHERE Sensor = 'CO2'", (current_value, ))
        return current_value
    def O2_Light_sensor (desired_value):
      global serial, ser
      cur.execute ("SELECT * FROM Sensor_State WHERE Sensor = 'Light'")
      State = cur.fetchone ()
      if State[1] == "Manual": # Check if reading from recipe or webpage manual value.
        desired_value = int (State[2]) # Get desired value from webpage manual value.
      if desired_value == 0:
        light = ("Off", "Light")
        GPIO.output (lights_pin, GPIO.LOW)
      else:
        light = ("On", "Light")
        GPIO.output (lights_pin, GPIO.HIGH)
        msg_luxread = 0
        msg_err = 2 # Error value.
      try:
       # Create outgoing message.
       sendmsg = bytearray (7)
       sendmsg = b'\x02' + desired_value.to_bytes (2, byteorder = 'big') + b'\x00' + b'\x00' + b'\x03' + b'\r'
       #print (desired_value.to_bytes) 
       #print (sendmsg.hex())
       ser.write (sendmsg) # Send message. 
       time.sleep (1) # Allow time for a response.
       Light_current_value = 0
       O2_current_value = 0
       if ser.in_waiting == 0:
        print("Resetting Arduino")
        ser.close()
        try:
         ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=0.5) # Initialise the serial connection between Pi and Arduino, this will cause arduino to reset.
         print("Resetting buffers...")
         time.sleep(2) # Wait for port to initialise.
         ser.reset_input_buffer # Reset serial I/O buffers.
         ser.reset_output_buffer
         print ("Arduino found")
        except:
          print ("Error setting up Arduino serial connection: check USB connection")
          while ser.in_waiting > 0:
           msg = ser.read(7) # ser.read_until(b'\r') #reads input message, returns as array of integers representing the decimal vale of each byte (0-255).
           #print (msg.hex())
           if (msg[0] == 2 and msg[5] == 3): # Check for an STX and ETX of recieved message.
             Light_current_value = msg[1]<<8|msg[2] # Read data bytes and concatenate to calculate result.
             O2_current_value = (msg[3]<<8|msg[4])/100
             msg_err = 0
             #print(msg_err)
           else :
            Light_current_value = 0
            msg_err = 1 
            #print(msg_err) 
            ser.reset_input_buffer
            ser.reset_output_buffer
            #print("buffers reset") 
      except:
          print("Arduino error - may have been disconnected")
          ser.close()
      try: 
          ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=0.5) # Initialise the serial connection between Pi and Arduino, this will cause arduino to reset. 
          print("Resetting buffers...")
          time.sleep(2) # Wait for port to initialise.
          ser.reset_input_buffer # Reset serial I/O buffers.
          ser.reset_output_buffer 
          print ("Arduino found")
      except:
          print ("Error setting up Arduino serial connection: check USB connection") 
          Light_current_value = ""
          O2_current_value = ""
          cur.execute ("UPDATE Output_State SET Value = %s WHERE Output = %s", light) # Log output component states into Sensor_State table.
          cur.execute("UPDATE Sensor_Read SET Reading = %s WHERE Sensor = 'Light'", (Light_current_value, ))
          cur.execute("UPDATE Sensor_Read SET Reading = %s WHERE Sensor = 'O2'", (O2_current_value, ))
      return O2_current_value, Light_current_value
    def Temperature_sensor (desired_value):
      global Temperature_State
      cur.execute ("SELECT * FROM Sensor_State WHERE Sensor = 'Temperature'")
      State = cur.fetchone () 
      if State[1] == "Manual": # Check if reading from recipe or webpage manual value.
        desired_value = int (State[2]) # Get desired value from webpage manual value.
      try: 
          current_value = round (sht.temperature, 2) # current_value = i2c_read (0x70) # Temperature sensor value.
          desired_value_min = desired_value * 0.9 # Set min to 10% temperature.
          desired_value_max = desired_value * 1.1 # Set max to +10% temperature.
          if (Temperature_State == 1):
            peltier = ("Off", "Peltier") 
            GPIO.output (cool_pin, GPIO.LOW) 
            GPIO.output (heat_pin, GPIO.LOW)
            if(current_value > desired_value_max):
              Temperature_State = 2 
            if(current_value < desired_value_min):
              Temperature_State = 3 
          elif (Temperature_State == 2):
            peltier = ("Cooling", "Peltier") 
            GPIO.output (heat_pin, GPIO.LOW) 
            time.sleep(1) # Dead time. 
            GPIO.output (cool_pin, GPIO.HIGH)
            if(current_value < desired_value):
              Humidity_State = 1
          elif (Temperature_State == 3):
            peltier = ("Heating", "Peltier") 
            GPIO.output (cool_pin, GPIO.LOW)
            time.sleep(1) # Dead time. 
            GPIO.output (heat_pin, GPIO.HIGH)
            if(current_value > desired_value):
              Temperature_State = 1
            cur.execute ("UPDATE Output_State SET Value = %s WHERE Output = %s", peltier) # Log output component states into Sensor_State table.
      except: 
          print("Error reading temperature sensor - may be disconnected")
          current_value = ""
          cur.execute("UPDATE Sensor_Read SET Reading = %s WHERE Sensor = 'Temperature'", (current_value, )) 
      return current_value
if __name__ == "__main__":
  control_loop ()

           
                  
         

                      