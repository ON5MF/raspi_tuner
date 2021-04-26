#versies 
# 001: volt-meting met lcd-display
# 002: volt omrekenen naar pwr
# 003: SWR berekenen
# 004: continu loop om SWR weer te geven
# 005: nu wordt er effectief gemeten
# 006: lcd verbeteren

#nota's

#todo

#***** libraries
import board
import busio
import adafruit_character_lcd.character_lcd_rgb_i2c as character_lcd
import datetime
from time import sleep
from ADCPi import ADCPi
from math import sqrt

#***** variabelen en constanten declareren

#***** functies
    
#***** initialiseren
#     LCD
lcd_columns = 16
lcd_rows = 2
i2c = busio.I2C(board.SCL, board.SDA)
lcd = character_lcd.Character_LCD_RGB_I2C(i2c, lcd_columns, lcd_rows)
lcd.color = [50, 50, 0]
lcd.cursor_position(0, 0)
lcd.message="    V     W  SWR"
lcd.cursor_position(0, 1)
lcd.message="    V     W"

#     ADC
adc = ADCPi(0x68, 0x69, 16)  #adres 1 / adres 2 / bitrate
#     metingen
diode_spanning_FWD = 0.16
diode_spanning_REV = 0.163
meet_parameter_FWD = 0.089
meet_parameter_REV = 0.089
#***** main
while True:
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
    if SWR>5:    #display rood bij hoge SWR
        lcd.color = [100, 0, 0]
    elif SWR>2.5:  #display geel bij redelijke SWR
        lcd.color = [50,50,0]
    else:        #display groen bij goeie SWR
        lcd.color = [0,100,0]
    SWR=int(SWR*10+.5)/10
    if SWR==999:
        SWR="oo "
    if FWD_pwr==0:
        SWR="???"
        lcd.color = [0,100,0]
    #zet data op display
    lcd.cursor_position(0, 0)
    if FWD_spanning>=0.01:
        lcd.message=str(FWD_spanning)
    else:
        lcd.message="0.0 "
    lcd.cursor_position(0, 1)
    if REV_spanning>=0.01:
        lcd.message=str(REV_spanning)
    else:
        lcd.message="0.0 "
#     if FWD_pwr>=100:        
#         lcd.cursor_position(7,0)
#     elif FWD_pwr>=10:
#         lcd.cursor_position(8,0)
#     else:
#         lcd.cursor_position(9,0)
    lcd.cursor_position(7,0)
    if FWD_pwr>=100:        
        spacer=""
    elif FWD_pwr>=10:
        spacer=" "
    else:
        spacer="  "    
    lcd.message=spacer + str(FWD_pwr)
#     if REV_pwr>=100:        
#         lcd.cursor_position(7,1)
#     elif REV_pwr>=10:
#         lcd.cursor_position(8,1)
#     else:
#         lcd.cursor_position(9,1)       
    lcd.cursor_position(7,1)
    if REV_pwr>=100:
        spacer=""
    elif REV_pwr>=10:
        spacer=" "
    else:
        spacer="  "
    lcd.message=spacer + str(REV_pwr)
    lcd.cursor_position(13, 0)
    lcd.message=str("SWR")
    lcd.cursor_position(13, 1)
    lcd.message=str(SWR)  
