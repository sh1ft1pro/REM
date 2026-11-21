import sys
from time import time_ns

import pygame
import serial
import serial.tools.list_ports

from datetime import datetime
import time

from tkinter import *
from tkinter import messagebox

import keyboard

pygame.init()

screen = pygame.display.set_mode([900, 790])


Tk().wm_withdraw() #to hide the main window

programm_run = True

x = 30
y = 30
speed = 1


#keyboard
esc_press = 0
enter_press = 0
backspace_press = 0

robot = pygame.image.load('robot_new.png')
bg = pygame.image.load("bg_new.png")

system_starting = pygame.image.load('starting_new.png')
icon = pygame.image.load("icon_new.png")

screen.fill([255, 255, 255])
screen.blit(system_starting, (0, 0))
pygame.display.flip()

pygame.display.set_caption("Robot emulator MODIFICATED")
pygame.display.set_icon(icon)


ports = list(serial.tools.list_ports.comports())
ser_port = None  # Изначально порт не найден

for p in ports:
    desc = p.description.lower()
    if "arduino" in desc or "ch340" in desc or "ch341" in desc or "usb-serial" in desc or "usb" in desc:
        ser_port = p.device
        break  # Нашли плату — дальше искать не нужно

if ser_port is None:  # Если после цикла переменная так и осталась пустой
    messagebox.showinfo('Ошибка', 'Плата Arduino не найдена!')
    #sys.exit()


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

    # KEYBOARD
    if keyboard.is_pressed('w'):
        y -= speed

    # Движение назад
    if keyboard.is_pressed('s'):
        y += speed

    # Краб вправо
    if keyboard.is_pressed('a'):
        x -= speed

    # Краб влево
    if keyboard.is_pressed('d'):
        x += speed

    # Поворот влево (angle)
    if keyboard.is_pressed('left'):
        robot = pygame.transform.rotate(robot, 90)

    # Поворот вправо (angle)
    if keyboard.is_pressed('right'):
        robot = pygame.transform.rotate(robot, -90)

    # Вывод текущей позиции
    if keyboard.is_pressed('p'):
        pass

    # Возвращение на начальную позицию
    if keyboard.is_pressed('r'):
        pass

    # Вывод справки
    if keyboard.is_pressed('tab'):
        pass

    # Экстренная остановка всей системы
    if keyboard.is_pressed('space'):
        pass

    # Загрузить реальный код (2 нажатия)
    if keyboard.is_pressed('enter'):
        enter_press += 1
        if enter_press == 2:
            enter_press = 0
            pass

    # Сбросить то, что уже проехал (2 нажатия)
    if keyboard.is_pressed('backspace'):
        backspace_press += 1
        if backspace_press == 2:
            backspace_press = 0
            pass

    # Выйти из программы (2 нажатия)
    if keyboard.is_pressed('esc'):
        esc_press += 1
        if esc_press == 2:
            break


    screen.fill([255, 255, 255])


    screen.blit(bg, [0, 0])
    screen.blit(robot, (x, y))

    



    pygame.display.flip()
    screen.fill([255, 255, 255])

    clock.tick(FPS)



pygame.quit()
SerialObj.close()