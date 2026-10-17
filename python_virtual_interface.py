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

start_x = 10000 # точка старта
start_y = 10000
start_flag_visible = False


end_x = 10000 # точка старта
end_y = 10000
end_flag_visible = False


medium_visible = False

medium_helper_x = 10000
medium_helper_y = 10000

medium_number = 0

medium_x_mass = []
medium_y_mass = []


flag_left = False
flag_right = False

robot = pygame.image.load('robot.png')
bg = pygame.image.load("bg.png")

system_starting = pygame.image.load('starting.png')
icon = pygame.image.load("icon.jpg")

start = pygame.image.load("start.png")

end = pygame.image.load("end.png")

screen.fill([255, 255, 255])
screen.blit(system_starting, (0, 0))
pygame.display.flip()

pygame.display.set_caption("Robot emulator")
pygame.display.set_icon(icon)


speed = 20


ports = list(serial.tools.list_ports.comports())
number_of_ports = len(ports)
print(number_of_ports)
counter = 0

for p in ports:
    if "Arduino" in p.description:
        print("Arduino Found!")
        print("Connecting...")
        print(p.device)
        break
    counter += 1

if (counter == number_of_ports):
   messagebox.showinfo('Ошибка', 'Плата Arduino не найдена!')
   sys.exit()

# настройка порта
ser_port = p.device

SerialObj = serial.Serial(ser_port)
SerialObj.baudrate = 9600
SerialObj.bytesize = 8
SerialObj.parity = 'N'
SerialObj.stopbits = 1

FPS = 80 # 80
clock = pygame.time.Clock()

TEXTCOLOUR = (255, 20, 0)
fontObj = pygame.font.Font(None, 40)

timer_flag = False
timer_start = 0
timer_end = 0
timer_varning = "0"

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
            if event.button == 1:
                pos = pygame.mouse.get_pos()
                start_flag_visible = True
                start_x = pos[0]
                start_y = pos[1]


            if event.button == 2:
                medium_visible = True

                if (medium_number <= 4):
                    pos = pygame.mouse.get_pos()
                    medium_x_mass.append(pos[0])
                    medium_y_mass.append(pos[1])
                    medium_number += 1
                else:
                    messagebox.showinfo('Ошибка', 'Невозможно создать более 5 checkpoint!')


            if event.button == 3:
                pos = pygame.mouse.get_pos()
                end_flag_visible = True
                end_x = pos[0]
                end_y = pos[1]

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

    if (timer_flag == False):
        pass

    elif (timer_flag == True):
        timer_end = time.time()
        timer_varning = str(round(timer_end - timer_start, 1))

    date_time_text = fontObj.render(f"Таймер: {timer_varning} с", True, TEXTCOLOUR, None)

    screen.fill([255, 255, 255])


    screen.blit(bg, [0, 0])
    screen.blit(robot, (x, y))
    screen.blit(date_time_text, (10, 725))

    if (start_flag_visible == True):
        screen.blit(start, (start_x, start_y))

        obj1 = pygame.Rect(x, y, 70, 90)
        obj2 = pygame.Rect(start_x, start_y, 33, 35)

        if obj1.colliderect(obj2):
            timer_flag = True
            timer_start = time.time()





    if (end_flag_visible == True):
        screen.blit(end, (end_x, end_y))

        obj2 = pygame.Rect(x, y, 70, 90)
        obj3 = pygame.Rect(end_x, end_y, 33, 35)

        if obj2.colliderect(obj3):
            timer_flag = False



    if (medium_visible == True):

        for i in range(len(medium_y_mass)):

            picture = pygame.image.load(f"medium{i+1}.png")
            screen.blit(picture, (medium_x_mass[i], medium_y_mass[i]))



    pygame.display.flip()
    screen.fill([255, 255, 255])

    clock.tick(FPS)



pygame.quit()
SerialObj.close()