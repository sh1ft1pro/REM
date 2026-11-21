import sys
from time import time_ns

import pygame
import serial
import serial.tools.list_ports

from datetime import datetime
import time

from tkinter import *
from tkinter import messagebox


pygame.init()

screen = pygame.display.set_mode([900, 790])


Tk().wm_withdraw() #to hide the main window

programm_run = True

x = 30
y = 30

flag_left = False
flag_right = False

robot = pygame.image.load('robot_new.png')
bg = pygame.image.load("bg_new.png")

system_starting = pygame.image.load('starting.png')
icon = pygame.image.load("icon_new.jpg")

screen.fill([255, 255, 255])
screen.blit(system_starting, (0, 0))
pygame.display.flip()

pygame.display.set_caption("Robot emulator MODIFICATED")
pygame.display.set_icon(icon)


speed = 20

"""
def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    
    print("=== Поиск Arduino ===")
    for p in ports:
        print(f" - {p.device} ({p.description})")
        
    for p in ports:
        desc = p.description.lower()
        # Ищем Ардуино или популярные китайские чипы (CH340/CH341)
        if "arduino" in desc or "ch340" in desc or "ch341" in desc or "usb-serial" in desc or "usb" in desc:
            return p.device
    return None
"""

ports = list(serial.tools.list_ports.comports())
ser_port = None  # Изначально порт не найден

for p in ports:
    desc = p.description.lower()
    if "arduino" in desc or "ch340" in desc or "ch341" in desc or "usb-serial" in desc or "usb" in desc:
        ser_port = p.device
        break  # Нашли плату — дальше искать не нужно

if ser_port is None:  # Если после цикла переменная так и осталась пустой
    messagebox.showinfo('Ошибка', 'Плата Arduino не найдена!')
    sys.exit()


# настройка порта
#ser_port = p.device

SerialObj = serial.Serial(ser_port)
SerialObj.baudrate = 9600
SerialObj.bytesize = 8
SerialObj.parity = 'N'
SerialObj.stopbits = 1

FPS = 80 # 80
clock = pygame.time.Clock()

TEXTCOLOUR = (255, 20, 0)
fontObj = pygame.font.Font(None, 40)

SerialObj.close()
SerialObj = serial.Serial(ser_port)
SerialObj.baudrate = 9600
SerialObj.bytesize = 8
SerialObj.parity = 'N'
SerialObj.stopbits = 1

flag_work = True



while programm_run:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            programm_run = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            pass

    with open("pult_sender_sys_output.txt", "r", encoding="utf-8") as file:
        x_read, y_read, left, right = [line.strip() for line in file]


    #x_read = SerialObj.readline().decode('utf-8').strip()
    #y_read = SerialObj.readline().decode('utf-8').strip()
    #left = SerialObj.readline().decode('utf-8').strip()
    #right = SerialObj.readline().decode('utf-8').strip()
    

    if (x_read == "1"):
        x += speed
    elif (x_read == "0"):
        x -= speed
    if (y_read == "1"):
        y += speed
    elif (y_read == "0"):
        y -= speed


    if ((left == "1") and (right == "0")  and flag_work == True):
        flag_left = True
        flag_right = False

        flag_work = False


    elif ((left == "0") and (right == "1") and flag_work == True):
        flag_right = True
        flag_left = False

        flag_work = False


    elif ((left == "0") and (right == "0")):
        lag_left = False
        flag_right = False


    if ((left == "1") and (right == "1")):
        lag_left = False
        flag_right = False

        flag_work = True




    if ((flag_left == True) and (flag_right == False)):
        robot = pygame.transform.rotate(robot, 90)
        flag_right = False
        flag_left = False


    elif ((flag_left == False) and (flag_right == True)):
        robot = pygame.transform.rotate(robot, -90)
        flag_right = False
        flag_left = False

    screen.fill([255, 255, 255])


    screen.blit(bg, [0, 0])
    screen.blit(robot, (x, y))

    



    pygame.display.flip()
    screen.fill([255, 255, 255])

    clock.tick(FPS)



pygame.quit()
SerialObj.close()