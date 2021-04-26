#!/usr/bin/env python

#versies 
# 001: functies stepper werken
# 002: functies servo's testen
# 003: knoppen op lcd testen
# 004: cw werkt
# 005: test meting en weergave
# 006: test meting en weergaven (overgenomen van SWRbrug006.py)
# 007: opsplitsing meting en lcd in verschillende functies

#nota's
#servo 0 = 'transmitter'
#servo 1 = 'antenna'

#todo

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
# photo_sensor = 1     #is een lokale variabele in de stepper_calibrate functie
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
wpm=20 #CW speed
dit_lengte = (40*30/wpm)/1000  #bij 30 wpm is de dit 40 msec  = bij 15 wpm is dit 80
dah_lengte = dit_lengte*3
Buzzer_PIN = 10
GPIO.setup(Buzzer_PIN, GPIO.OUT, initial= GPIO.LOW)
#** ADC
adc = ADCPi(0x68, 0x69, 16)  #adres 1 / adres 2 / bitrate
#** correcties metingen
diode_spanning_FWD = 0.16
diode_spanning_REV = 0.163
meet_parameter_FWD = 0.089
meet_parameter_REV = 0.089


#***** functies
#** PWR en RPWR meten
'''
Todo: de uitlezing nog opsplitsen naar functie van lcd
> welke data heb ik nodig op lcd?
> deze data opvragen via "lcd_data=a,b,c,d,..."
> in de meetfunctie deze data terugsturen via "return a,b,c,d,...." 

'''
def PWR_meten():        
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

'''     TE TESTEN     '''
def lcd_gemeten_data(FWD_spanning, FWD_pwr, REV_spanning, REV_pwr, SWR):
    lcd.cursor_position(0, 0)
    lcd.message=str(FWD_spanning)
    lcd.cursor_position(0, 1)
    lcd.message=str(REV_spanning)
    if FWD_pwr>=100:        
        lcd.cursor_position(7,0)
    elif FWD_pwr>=10:
        lcd.cursor_position(8,0)
    else:
        lcd.cursor_position(9,0)
    lcd.message=str(FWD_pwr)
    if REV_pwr>=100:        
        lcd.cursor_position(7,1)
    elif REV_pwr>=10:
        lcd.cursor_position(8,1)
    else:
        lcd.cursor_position(9,1)
    lcd.message=str(REV_pwr)
    lcd.cursor_position(13, 0)
    lcd.message=str("SWR")
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

#** testen of knop ingedrukt is
def lcd_button(): #deze functie moet wel continu opgeroepen worden in een loop, er zijn geen interrupts! Soms moet je iets langer
                  #drukken om effect te hebben, bijvoorbeeld tijdens een sleep()
    if lcd.down_button:
        lcd.message = "Down!  "
    if lcd.up_button:
        lcd.message = "Up!    "        
    if lcd.left_button:
        lcd.message = "Left!  "        
    if lcd.right_button:
        lcd.message = "Right! "        
    if lcd.select_button:
        lcd.message = "Select!"

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
        sleep(.1)  #vertraging, zonder heeft de stepper geen kracht
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

def buzzer(code):
    '''TODO: morse vereenvoudigen? Alle letters apart declareren in setup?'''
    if code=="call":
        dah(); dah(); dah(); pauze()
        dah(); dit(); pauze()
        dit(); dit(); dit(); dit(); dit(); pauze()
        dah(); dah(); pauze()
        dit(); dit(); dah(); dit()
    if code=="qrp":
        dah(); dah(); dit(); dah(); pauze()
        dit(); dah(); dit(); pauze()
        dit(); dah(); dah(); dit()

#***** main
''' Stramien
- Continu:
    - power en swr meten en weergeven op display
    - als swr te hoog wordt, alarm geven
    - wachten op druk op de knop 'tune'
- als knop tunen ingedrukt geweest is
    - continu in de gaten houden of er bij tunen niet langer dan 30 seconden gezonden wordt!
    - vragen aan operator om te stoppen met zenden
    - testen of pwr 0 is
    - schakelaar spoel naar nulpunt => eerste checken of power = 0 vooraleer te schakelen
    - na schakelen altijd power afleggen van stepper
    - servo's naar nulpunt
    - vragen aan operator om te zenden met laag vermogen
    - als vermogen te hoog dan alarm geven
    - 100 linkse servo afregelen voor laagste reflected power
    - 110 rechtse servo idem
    - terug naar 110 tot reflected niet meer zakt
    - positie beste swr opslaan
    - indien swr niet goed genoeg dan
        - vragen om te stoppen met zenden
        - spoel eentje opschuiven  => eerste checken of power = 0 vooraleer te schakelen
        - na schakelen altijd power afleggen van stepper
        - opnieuw zenden
        - en terug naar 100
        - als 'beste' swr slechter is dan vorige stand spoel dan eentje terugkeren (eerst power= 0 checken!)
        - op opgeslagen positie beste swr zetten
'''
'''
optimalisatiemogelijkheden:
    - sleep verkorten bij stepper of een systeem zoeken waarbij hij kan vermeden worden. Als er geen meerdere posities na elkaar moet
    gewisseld worden dan kan die sleep na het commando weggelaten worden
'''
lcd_basis()

while True:
    PWR_meten()