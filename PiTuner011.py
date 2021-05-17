#!/usr/bin/env python

#versies 
# 001: functies stepper werken
# 002: functies servo's testen
# 003: knoppen op lcd testen
# 004: cw werkt
# 005: test meting en weergave
# 006: test meting en weergaven (overgenomen van SWRbrug006.py)
# 007: opsplitsing meting en lcd in verschillende functies
# 008: testen met routine na drukken knop
# 009: vertaling morse code vanuit dictionary
# 010: uitwerking modus2
# 011: opstart modus3

'''todo: manier uitzoeken om van SWR-weergave op lcd te switchen naar melding en terug'''

'''todo: optimalisatiemogelijkheden:
    - sleep verkorten bij stepper of een systeem zoeken waarbij hij kan vermeden worden. Als er geen meerdere posities na elkaar moet
    gewisseld worden dan kan die sleep na het commando weggelaten worden
    - wat is snelst, met 180° sweep of stoppen met sweepen als swr weer omhoog gaat?'''
    
'''todo: manier zoeken om met knop tuningproces te onderbreken'''

'''todo: timemout op modus3, als tuner te lang op operator moet wachten dan terug naar modus1'''
    
#nota's
#servo 0 = 'transmitter'
#servo 1 = 'antenna'

#todo

#***** user parameters
max_swr = 2   #alarmdrempel SWR
min_swr = 1.3 # drempel om te stoppen met tunen
max_tuning_power = 15  #max vermogen waarbij mag getuned worden
max_tuning_time = 30 #max tijd in seconden waarbij er aan een stuk getuned mag worden
tuning_pause = 5 #pause tussen 2 tuning beurten
wpm=20 #CW speed

#***** libraries
import RPi.GPIO as GPIO
from adafruit_motorkit import MotorKit
from adafruit_motor import stepper
from adafruit_servokit import ServoKit
import board
import busio
import adafruit_character_lcd.character_lcd_rgb_i2c as character_lcd
import datetime
from time import sleep
from ADCPi import ADCPi
from math import sqrt

#***** initialiseren
#** photo sensor
photo_pin = 24 #Set GPIO Pin 24
GPIO.setup(photo_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Set pull up to high level(3.3V)
#** motoren
stepper_kit = MotorKit(address=0x60)
servo_kit = ServoKit(channels=16)
servo_kit.servo[0].set_pulse_width_range(630, 2350)
servo_kit.servo[1].set_pulse_width_range(575, 2200)
#** lcd
lcd_columns = 16
lcd_rows = 2
i2c = busio.I2C(board.SCL, board.SDA)
lcd = character_lcd.Character_LCD_RGB_I2C(i2c, lcd_columns, lcd_rows)
lcd.color = [50, 50, 0]
#** buzzer
dit_lengte = (40*30/wpm)/1000  #bij 30 wpm is de dit 40 msec  = bij 15 wpm is dit 80
dah_lengte = dit_lengte*3
Buzzer_PIN = 10
GPIO.setup(Buzzer_PIN, GPIO.OUT, initial= GPIO.LOW)
#** ADC
adc = ADCPi(0x68, 0x69, 12)  #adres 1 / adres 2 / bitrate  (eerst bitrate op 16 maar zeer traag)
#** correcties metingen
diode_spanning_FWD = 0.16
diode_spanning_REV = 0.163
meet_parameter_FWD = 0.089
meet_parameter_REV = 0.089
#**
modus=1 #default om te starten
#** morse code
morse = {'A':'.-', 'B':'-...', 'C':'-.-.', 'D':'-..', 'E':'.',
        'F':'..-.', 'G':'--.', 'H':'....', 'I':'..', 'J':'.---',
        'K':'-.-', 'L':'.-..', 'M':'--', 'N':'-.', 'O':'---',
        'P':'.--.', 'Q':'--.-', 'R':'.-.', 'S':'...', 'T':'-',
        'U':'..-', 'V':'...-', 'W':'.--', 'X':'-..-', 'Y':'-.--',
        'Z':'--..', '1':'.----', '2':'..---', '3':'...--', '4':'....-',
        '5':'.....', '6':'-....', '7':'--...', '8':'---..', '9':'----.',
        '0':'-----'}
#***** functies
#** PWR en RPWR meten
def PWR_meten():
    global FWD_spanning
    global REV_spanning
    global FWD_pwr
    global REV_pwr
    global SWR
    #meting
    FWD_spanning=adc.read_voltage(1)
    REV_spanning=adc.read_voltage(2)
    #omrekening naar power
    FWD_pwr=(FWD_spanning+diode_spanning_FWD)*(FWD_spanning+diode_spanning_FWD)/meet_parameter_FWD
    REV_pwr=(REV_spanning+diode_spanning_REV)*(REV_spanning+diode_spanning_REV)/meet_parameter_REV
    #afronding meting
    FWD_spanning=int(FWD_spanning*100)/100
    REV_spanning=int(REV_spanning*100)/100
    FWD_pwr=int(FWD_pwr)
    REV_pwr=int(REV_pwr)
    #berekening SWR
    if FWD_pwr>REV_pwr:   #divide by zero vermijden!
        SWR=(sqrt(FWD_pwr)+sqrt(REV_pwr))/(sqrt(FWD_pwr)-sqrt(REV_pwr))
    else:
        SWR=999
    if SWR>999:
        SWR=999
    return(SWR, FWD_spanning, REV_spanning, FWD_pwr, REV_pwr)

#** info weergeven op display
def lcd_basis():
    lcd.cursor_position(0, 0)
    lcd.message="    V     W  SWR"
    lcd.cursor_position(0, 1)
    lcd.message="    V     W"

def lcd_gemeten_data(SWR, FWD_spanning, REV_spanning, FWD_pwr, REV_pwr):
    lcd.cursor_position(0, 0)
#     print(format(321,".2f"))
    
    lcd.message=str(format(FWD_spanning,".2f"))
    lcd.cursor_position(0, 1)
    lcd.message=str(format(REV_spanning,".2f"))
    lcd.cursor_position(7,0)
    if FWD_pwr>=100:
        spacer=""
    elif FWD_pwr>=10:
        spacer=" "
    else:
        spacer="  "
    lcd.message=str(spacer+str(FWD_pwr))
    lcd.cursor_position(7,1)
    if REV_pwr>=100:
        spacer=""
    elif REV_pwr>=10:
        spacer=" "
    else:
        spacer="  "
    lcd.message=str(spacer+str(REV_pwr))    
    lcd.cursor_position(13, 1)
    lcd.message=str(SWR)
    if SWR>5:    #display rood bij hoge SWR
        lcd.color = [100, 0, 0]
    elif SWR>2.5:  #display geel bij redelijke SWR
        lcd.color = [50,50,0]
    else:        #display groen bij goeie SWR
        lcd.color = [0,100,0]
    if FWD_pwr==0:
        lcd.color = [0,100,0]

#** servo draaien
def servo_transmitter(angle_transmitter):
    servo_kit.servo[0].angle = angle_transmitter
    
def servo_antenna(angle_antenna):
    servo_kit.servo[1].angle = angle_antenna    

#** stepper naar 0-punt
def stepper_calibrate():  #bron: 'stepper_en_photo002.py'
    photo_sensor=1
    while photo_sensor==1:
        photo_sensor=GPIO.input(photo_pin)
        stepper_kit.stepper1.onestep(style=stepper.DOUBLE, direction=stepper.FORWARD)
        sleep(.05)  #vertraging, zonder heeft de stepper geen kracht
    stepper_kit.stepper1.release()  #stepper afleggen
    sleep(.5) #vertraging anders komt de volgende stap van de stepper in de problemen    
    
#** stepper 1 positie naar rechts
# posities van A - L (12 posities) dus 30 graden per positie => 16,66 stappen per positie
def stepper_rechts():
    for i in range(20):   #normaal 17 maar 20 lijkt beter te lukken door speling op het asje
        stepper_kit.stepper1.onestep(style=stepper.DOUBLE, direction=stepper.BACKWARD)
        sleep(.1)
    stepper_kit.stepper1.release()  #stepper afleggen
    sleep(.5) #vertraging anders komt de volgende stap van de stepper in de problemen    
    
#** stepper 1 positie naar links
def stepper_links():
    for i in range(20):  #17
        stepper_kit.stepper1.onestep(style=stepper.DOUBLE, direction=stepper.FORWARD)
        sleep(.1)
    stepper_kit.stepper1.release()  #stepper afleggen
    sleep(.5) #vertraging anders komt de volgende stap van de stepper in de problemen

#** buzzer 
def dit():
    GPIO.output(Buzzer_PIN,GPIO.HIGH) #Buzzer will be switched on
    sleep(dit_lengte) #Waitmode for 4 seconds
    GPIO.output(Buzzer_PIN,GPIO.LOW) #Buzzer will be switched off 
    sleep(dit_lengte) #Waitmode for another 2 seconds in which the buzzer will be off
    
def dah():
    GPIO.output(Buzzer_PIN,GPIO.HIGH) #Buzzer will be switched on
    sleep(dah_lengte) #Waitmode for 4 seconds
    GPIO.output(Buzzer_PIN,GPIO.LOW) #Buzzer will be switched off 
    sleep(dit_lengte) #Waitmode for another 2 seconds in which the buzzer will be off
    
def pauze():
    sleep(dit_lengte*2) #Waitmode for another 2 seconds in which the buzzer will be off

def buzzer(message):
    encodedMessage=""
    for character in message.upper(): # eerste alles vertalen en in één variabele zetten (encodedMessage)
        if character in morse:
            encodedMessage += morse[character] + " "
        if character == " ": #als er een spatie tussen woorden in CW zit dan moeten we een pauze inlassen
            encodedMessage += " " + " "    # 1 dit van toon + 2 dits per spatie = 7 dits spatie tussen woorden
    for character in encodedMessage:
        if character == ".":
            dit()
        if character == "-":
            dah()
        if character == " ":
            pauze()
            
#***** main

lcd_basis()

while True:    
    
    if lcd.down_button:
        modus=2 #tuning modus
        buzzer("e")
    
    if modus==1:
        PWR_meten()
        lcd_gemeten_data(SWR, FWD_spanning, REV_spanning, FWD_pwr, REV_pwr)
        if SWR > max_swr and FWD_pwr > 1:
            buzzer("high swr")
                
    if modus==2:
        PWR_meten()
        lcd_gemeten_data(SWR, FWD_spanning, REV_spanning, FWD_pwr, REV_pwr)
        if FWD_pwr > 0:     #als er pwr is dan kunnen we niet starten
            buzzer("QRT")
        else:     #nu kunnen we alles mechanisch op 0 zetten
            stepper_calibrate()
            servo_transmitter(0)
            servo_antenna(0)
            tune_teller=0  # teller om te tellen hoeveel keer de loop om te tunen mag draaien
            modus=3
        
    if modus==3:
        PWR_meten()
        lcd_gemeten_data(SWR, FWD_spanning, REV_spanning, FWD_pwr, REV_pwr)
        if FWD_pwr == 0:     #als er pwr is dan kunnen we niet starten
            buzzer("tx")      
        elif FWD_pwr > 15:     #als er pwr is dan kunnen we niet starten
            buzzer("QRP")
        #linkse condensator afregelen
        elif tune_teller<=3:
            tune_teller+=1
            print('tune',tune_teller)
            swrlist=[]
            for graden_transmitter in range(0,180,1):  #linkse servo laten sweepen
#                 print(graden)
                servo_transmitter(graden_transmitter)
                PWR_meten()
#                 lcd_gemeten_data(SWR, FWD_spanning, REV_spanning, FWD_pwr, REV_pwr)
                swrlist.append(SWR)  #lijst maken met SWR-waardes
            min_value = min(swrlist)  #zoek de kleinste waarde
            min_index = swrlist.index(min_value)   #graden van de kleinste swr
            if min_index>10:
                servo_transmitter(min_index-10)   #zet servo naar iets vóór kleinste SWR  (om speling as op te vangen)
            servo_transmitter(min_index)      #zet servo naar kleinste SWR
            print ('tx',tune_teller)
            print (swrlist)
            #rechtse condensator afregelen
            swrlist=[]
#             graden=0
            for graden_antenna in range(0,170,1):  #rechtse servo laten sweepen
                servo_antenna(graden_antenna)
                PWR_meten()
#                 lcd_gemeten_data(SWR, FWD_spanning, REV_spanning, FWD_pwr, REV_pwr)
                swrlist.append(SWR)  #lijst maken met SWR-waardes
            min_value = min(swrlist)  #zoek de kleinste waarde
            min_index = swrlist.index(min_value)   #graden van de kleinste swr
            if min_index>10:
                servo_antenna(min_index-10)   #zet servo naar iets vóór kleinste SWR  (om speling as op te vangen)
            servo_antenna(min_index)      #zet servo naar kleinste SWR
            print('ant',tune_teller)
            print(swrlist)
        
        else:
            buzzer("k k")
            modus=1