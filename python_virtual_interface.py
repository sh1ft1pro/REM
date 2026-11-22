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
import math

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


# --- ЗАГРУЗКА ИЗОБРАЖЕНИЙ ---
# --- ПРОЦЕДУРНАЯ ГЕНЕРАЦИЯ СПРАЙТОВ (вместо загрузки PNG) ---

# 1. Платформа (квадрат 100x100 с полупрозрачным фоном и рамкой)
img_platform = pygame.Surface((100, 100), pygame.SRCALPHA)
pygame.draw.rect(img_platform, (200, 220, 240, 180), (0, 0, 100, 100), border_radius=10) # Тело
pygame.draw.rect(img_platform, (100, 130, 160, 255), (0, 0, 100, 100), width=3, border_radius=10) # Рамка
pygame.draw.rect(img_platform, (255, 80, 80, 255), (85, 40, 10, 20)) # Красный маркер "переда" справа

# 2. Функция сборки колеса с мотором из прямоугольников
def make_wheel_surface(is_left):
    surf = pygame.Surface((50, 45), pygame.SRCALPHA)
    wheel_y = 0 if is_left else 27
    motor_y = 18 if is_left else 5
    
    # Черное колесо (прямоугольник)
    pygame.draw.rect(surf, (30, 30, 35, 255), (0, wheel_y, 50, 18), border_radius=4)
    # Желтый мотор (прямоугольник)
    pygame.draw.rect(surf, (240, 195, 20, 255), (5, motor_y, 40, 22), border_radius=2)
    pygame.draw.rect(surf, (160, 120, 0, 255), (5, motor_y, 40, 22), width=2, border_radius=2)
    return surf

img_wheel_left = make_wheel_surface(is_left=True)
img_wheel_right = make_wheel_surface(is_left=False)

# --- ПАРАМЕТРЫ РОБОТА ---
robot_pos = pygame.math.Vector2(400, 300)  # Стартовые координаты центра платформы (x, y)
robot_angle = 0.0                          # Угол поворота в градусах (0 — смотрит вправо)

# Смещения колес относительно центра платформы (настройте под размеры ваших спрайтов)
# Положительный X — вперед к носу, отрицательный — назад к корме.
# Положительный Y — право, отрицательный — лево (в экранных координатах Pygame).
WHEEL_OFFSET_X = -30  # Колеса сдвинуты назад, как на фото
WHEEL_TRACK_HALF = 45 # Половина колеи (расстояние от центральной оси до каждого колеса)

offset_left = pygame.math.Vector2(WHEEL_OFFSET_X, -WHEEL_TRACK_HALF)
offset_right = pygame.math.Vector2(WHEEL_OFFSET_X, WHEEL_TRACK_HALF)
wheel_base = WHEEL_TRACK_HALF * 2  # Полная ширина колеи (нужна для расчета радиуса поворота)

# --- НАСТРОЙКИ СКОРОСТИ ---
SPEED_MODES = {
    '1': {'move': 2.0, 'rot': 1.5},  # Медленно
    '2': {'move': 4.5, 'rot': 3.0},  # Средне
    '3': {'move': 7.5, 'rot': 5.0}   # Быстро
}
current_mode = '2'
move_speed = SPEED_MODES[current_mode]['move']
rot_speed = SPEED_MODES[current_mode]['rot']

while programm_run:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            programm_run = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            pass

    with open("pult_sender_sys_output.txt", "r", encoding="utf-8") as file:
        x_read, y_read, left, right = [line.strip() for line in file]

        # 1. ПЕРЕКЛЮЧЕНИЕ СКОРОСТИ (1, 2, 3)
    for key in ('1', '2', '3'):
        if keyboard.is_pressed(key):
            move_speed = SPEED_MODES[key]['move']
            rot_speed = SPEED_MODES[key]['rot']

    # Вектор направления "вперед" (инвертируем Y для стандартной математики углов)
    forward_vec = pygame.math.Vector2(1, 0).rotate(-robot_angle)

    # 2. ЛОГИКА ДВИЖЕНИЯ И ПОВОРОТОВ
    # Сначала проверяем повороты вокруг одного колеса (приоритетнее обычной езды)

    # Поворот налево вокруг ЛЕВОГО колеса (левое стоит, правое едет вперед)
    if keyboard.is_pressed('q'):
        pivot = robot_pos + offset_left.rotate(-robot_angle)
        robot_angle += rot_speed
        robot_pos = pivot - offset_left.rotate(-robot_angle)

    # Поворот направо вокруг ПРАВОГО колеса (правое стоит, левое едет вперед)
    elif keyboard.is_pressed('e'):
        pivot = robot_pos + offset_right.rotate(-robot_angle)
        robot_angle -= rot_speed
        robot_pos = pivot - offset_right.rotate(-robot_angle)

    # Езда вперед / назад
    elif keyboard.is_pressed('w'):
        robot_pos += forward_vec * move_speed
    elif keyboard.is_pressed('s'):
        robot_pos -= forward_vec * move_speed

    # Танковый разворот на месте (вращение вокруг центра оси между колесами)
    elif keyboard.is_pressed('a'):
        axle_center = robot_pos + pygame.math.Vector2(WHEEL_OFFSET_X, 0).rotate(-robot_angle)
        robot_angle += rot_speed
        robot_pos = axle_center - pygame.math.Vector2(WHEEL_OFFSET_X, 0).rotate(-robot_angle)
    elif keyboard.is_pressed('d'):
        axle_center = robot_pos + pygame.math.Vector2(WHEEL_OFFSET_X, 0).rotate(-robot_angle)
        robot_angle -= rot_speed
        robot_pos = axle_center - pygame.math.Vector2(WHEEL_OFFSET_X, 0).rotate(-robot_angle)


    # 3. СБОРКА РОБОТА И ОТРИСОВКА
    # Вычисляем актуальные мировые координаты для каждого колеса
    pos_left_wheel = robot_pos + offset_left.rotate(-robot_angle)
    pos_right_wheel = robot_pos + offset_right.rotate(-robot_angle)

    # Поворачиваем все три спрайта на актуальный угол
    rot_platform = pygame.transform.rotate(img_platform, robot_angle)
    rot_wheel_l = pygame.transform.rotate(img_wheel_left, robot_angle)
    rot_wheel_r = pygame.transform.rotate(img_wheel_right, robot_angle)

    # Центрируем прямоугольники (Rect) по вычисленным точкам, чтобы избежать биения при повороте
    rect_platform = rot_platform.get_rect(center=(round(robot_pos.x), round(robot_pos.y)))
    rect_wheel_l = rot_wheel_l.get_rect(center=(round(pos_left_wheel.x), round(pos_left_wheel.y)))
    rect_wheel_r = rot_wheel_r.get_rect(center=(round(pos_right_wheel.x), round(pos_right_wheel.y)))



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

    # Отрисовка (замените 'screen' на имя вашей переменной окна Pygame)
    screen.blit(rot_platform, rect_platform)
    screen.blit(rot_wheel_l, rect_wheel_l)
    screen.blit(rot_wheel_r, rect_wheel_r)
 
    pygame.display.flip()
    screen.fill([255, 255, 255])

    clock.tick(FPS)



pygame.quit()
SerialObj.close()