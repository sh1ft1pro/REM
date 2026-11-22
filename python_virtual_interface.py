import sys
import math
import time
import random
from datetime import datetime
from time import time_ns

import pygame
import serial
import serial.tools.list_ports
import keyboard
from tkinter import Tk, messagebox

pygame.init()
pygame.font.init()

screen = pygame.display.set_mode([1000, 600])

root_tk = Tk()
root_tk.wm_withdraw()

programm_run = True

# Старые переменные для совместимости
x = 30
y = 30
speed = 1
esc_press = 0
enter_press = 0
backspace_press = 0
flag_work = True

# =========================================================================
# НАСТРОЙКИ УПРАВЛЕНИЯ (ПЕРЕБИНЖИВАТЬ ЗДЕСЬ)
# =========================================================================
KEY_BINDS = {
    # Общее движение (2WD и 4WD)
    "forward": "w",
    "backward": "s",
    "tank_left": "a",
    "tank_right": "d",
    "pivot_left": "q",
    "pivot_right": "e",

    # Раздельное управление для 2WD (Левое и Правое колесо)
    "w2_left_fwd": "u",
    "w2_left_bwd": "j",
    "w2_right_fwd": "i",
    "w2_right_bwd": "k",

    # Раздельное управление для 4WD (4 независимых колеса)
    "w4_fl_fwd": "r",  # Переднее левое вперед
    "w4_fl_bwd": "f",  # Переднее левое назад
    "w4_fr_fwd": "t",  # Переднее правое вперед
    "w4_fr_bwd": "g",  # Переднее правое назад
    "w4_rl_fwd": "y",  # Заднее левое вперед
    "w4_rl_bwd": "h",  # Заднее левое назад
    "w4_rr_fwd": "u",  # Заднее правое вперед
    "w4_rr_bwd": "j",  # Заднее правое назад

    # Служебные клавиши
    "reset_pos": "z",
    "back_to_menu": "m",
    "print_pos": "p",
}

# Стартовый экран и иконка
try:
    system_starting = pygame.image.load('starting_new.png')
    screen.fill((255, 255, 255))
    screen.blit(system_starting, (0, 0))
    pygame.display.flip()
    time.sleep(0.4)
except Exception:
    pass

try:
    icon = pygame.image.load("icon_new.png")
    pygame.display.set_icon(icon)
except Exception:
    pass

pygame.display.set_caption("Robot emulator MODIFICATED")

# Поиск и безопасная инициализация COM-порта Arduino
ports = list(serial.tools.list_ports.comports())
ser_port = None
for p in ports:
    desc = p.description.lower()
    if any(k in desc for k in ("arduino", "ch340", "ch341", "usb-serial", "usb")):
        ser_port = p.device
        break

SerialObj = None
if ser_port is None:
    messagebox.showinfo('Предупреждение', 'Плата Arduino не найдена! Запуск в режиме автономной эмуляции.')
else:
    try:
        SerialObj = serial.Serial(ser_port, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=0.1)
    except Exception as e:
        messagebox.showinfo('Ошибка порта', f'Не удалось открыть порт {ser_port}: {e}')
        SerialObj = None

FPS = 80
clock = pygame.time.Clock()

font_title = pygame.font.SysFont("arial", 28, bold=True)
font_card = pygame.font.SysFont("arial", 18, bold=True)
font_btn = pygame.font.SysFont("arial", 32, bold=True)
font_hud = pygame.font.SysFont("arial", 15, bold=True)

# =========================================================================
# 1. ПРОЦЕДУРНАЯ ГЕНЕРАЦИЯ ПОЛЯ (ТЫСЯЧИ РИФЛЕНЫХ ЭЛЕМЕНТОВ НА ВЕСЬ ЭКРАН)
# =========================================================================
def generate_metal_floor(w, h):
    floor = pygame.Surface((w, h))
    floor.fill((26, 29, 34))  # Темный графитовый металл
    step = 28
    for row, y_pos in enumerate(range(0, h + step, step)):
        offset_x = (step // 2) if row % 2 == 1 else 0
        for x_pos in range(-step, w + step, step):
            cx = x_pos + offset_x
            cy = y_pos
            # Чередуем угол насечек (45 и -45 градусов), как на листе рифленого алюминия
            if ((x_pos // step) + row) % 2 == 0:
                pts = [(cx - 6, cy - 2), (cx - 2, cy - 6), (cx + 6, cy + 2), (cx + 2, cy + 6)]
            else:
                pts = [(cx - 6, cy + 2), (cx + 2, cy - 6), (cx + 6, cy - 2), (cx - 2, cy + 6)]
            pygame.draw.polygon(floor, (42, 46, 54), pts)
            pygame.draw.line(floor, (65, 72, 84), pts[0], pts[1], 1)  # Легкий металлический блик
    # Тонкая координатная сетка поверх пола
    for gx in range(0, w, 100):
        pygame.draw.line(floor, (34, 38, 45), (gx, 0), (gx, h), 1)
    for gy in range(0, h, 100):
        pygame.draw.line(floor, (34, 38, 45), (0, gy), (w, gy), 1)
    return floor

bg_generated = generate_metal_floor(1000, 600)

# =========================================================================
# 2. ПРОЦЕДУРНАЯ ГЕНЕРАЦИЯ 2D-СПРАЙТОВ (3 ВАРИАНТА РОБОТА)
# =========================================================================
def make_wheel_surface(is_left, w=50, h=45):
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    wheel_y = 0 if is_left else h - 18
    motor_y = 18 if is_left else 5
    pygame.draw.rect(surf, (30, 30, 35, 255), (0, wheel_y, w, 18), border_radius=4)
    pygame.draw.rect(surf, (240, 195, 20, 255), (5, motor_y, w - 10, 22), border_radius=2)
    pygame.draw.rect(surf, (160, 120, 0, 255), (5, motor_y, w - 10, 22), width=2, border_radius=2)
    return surf

img_wheel_left = make_wheel_surface(True)
img_wheel_right = make_wheel_surface(False)

# Вариант 1: 2WD Квадрат
plat_1 = pygame.Surface((100, 100), pygame.SRCALPHA)
pygame.draw.rect(plat_1, (200, 220, 240, 190), (0, 0, 100, 100), border_radius=10)
pygame.draw.rect(plat_1, (100, 130, 160, 255), (0, 0, 100, 100), width=3, border_radius=10)
pygame.draw.rect(plat_1, (255, 80, 80, 255), (85, 40, 10, 20))

# Вариант 2: 2WD Круглый
plat_2 = pygame.Surface((120, 120), pygame.SRCALPHA)
pygame.draw.circle(plat_2, (210, 230, 245, 170), (60, 60), 58)
pygame.draw.circle(plat_2, (130, 160, 190, 255), (60, 60), 58, width=3)
for y_slot in (35, 48, 72, 85):
    pygame.draw.line(plat_2, (150, 180, 210, 220), (30, y_slot), (80, y_slot), 3)
pygame.draw.polygon(plat_2, (255, 80, 80, 255), [(112, 60), (96, 50), (96, 70)])

# Вариант 3: 4WD Вездеход
plat_3 = pygame.Surface((150, 120), pygame.SRCALPHA)
pygame.draw.rect(plat_3, (200, 220, 240, 180), (15, 22, 120, 76), border_radius=12)
pygame.draw.rect(plat_3, (110, 140, 170, 255), (15, 22, 120, 76), width=3, border_radius=12)
wheel_coords_4wd = [(25, 4), (90, 4), (25, 98), (90, 98)]
for wx, wy in wheel_coords_4wd:
    pygame.draw.rect(plat_3, (25, 25, 30, 255), (wx, wy, 38, 18), border_radius=4)
    my = wy + 18 if wy < 50 else wy - 16
    pygame.draw.rect(plat_3, (240, 195, 20, 255), (wx + 4, my, 30, 16), border_radius=2)
pygame.draw.rect(plat_3, (35, 35, 40, 255), (52, 38, 46, 44), border_radius=4)
pygame.draw.polygon(plat_3, (255, 80, 80, 255), [(132, 60), (118, 50), (118, 70)])

ROBOT_PRESETS = {
    0: {"name": "2WD Квадрат", "plat": plat_1, "has_ext_wheels": True, "off_x": -30, "track": 45, "is_4wd": False},
    1: {"name": "2WD Круглый", "plat": plat_2, "has_ext_wheels": True, "off_x": -10, "track": 48, "is_4wd": False},
    2: {"name": "4WD Вездеход", "plat": plat_3, "has_ext_wheels": False, "off_x": 0, "track": 52, "is_4wd": True},
}

# =========================================================================
# 3. ИНТЕРАКТИВНЫЙ 3D-РЕНДЕР РОБОТА ДЛЯ ГЛАВНОГО МЕНЮ (ВРАЩЕНИЕ МЫШЬЮ)
# =========================================================================
rot3d_x = 0.55   # Наклон по X (в радианах)
rot3d_y = -0.65  # Поворот по Y
is_dragging_3d = False
last_mouse_3d = (0, 0)

def make_3d_box(cx, cy, cz, sx, sy, sz, color):
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    verts = [
        (cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz),
        (cx + hx, cy + hy, cz - hz), (cx - hx, cy + hy, cz - hz),
        (cx - hx, cy - hy, cz + hz), (cx + hx, cy - hy, cz + hz),
        (cx + hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz + hz),
    ]
    faces = [
        ((0, 1, 2, 3), tuple(max(0, c - 25) for c in color)),
        ((4, 5, 6, 7), tuple(min(255, c + 20) for c in color)),
        ((0, 1, 5, 4), tuple(max(0, c - 15) for c in color)),
        ((2, 3, 7, 6), tuple(max(0, c - 15) for c in color)),
        ((1, 2, 6, 5), tuple(min(255, c + 10) for c in color)),
        ((0, 3, 7, 4), tuple(max(0, c - 20) for c in color)),
    ]
    return verts, faces

def get_robot_3d_meshes(preset_idx):
    meshes = []
    if preset_idx == 0:  # 2WD Квадрат
        meshes.append(make_3d_box(0, 0, 0, 110, 10, 110, (175, 200, 225)))
        meshes.append(make_3d_box(42, -8, 0, 14, 6, 26, (235, 70, 70)))  # Нос
        meshes.append(make_3d_box(-30, 8, -42, 42, 22, 22, (235, 190, 25)))  # Мотор Л
        meshes.append(make_3d_box(-30, 8, 42, 42, 22, 22, (235, 190, 25)))   # Мотор П
        meshes.append(make_3d_box(-30, 8, -62, 54, 54, 18, (35, 38, 44)))    # Колесо Л
        meshes.append(make_3d_box(-30, 8, 62, 54, 54, 18, (35, 38, 44)))     # Колесо П
    elif preset_idx == 1:  # 2WD Круглый (12-гранная призма)
        segs = 14
        r = 62
        top_v = [(math.cos(2 * math.pi * i / segs) * r, -5, math.sin(2 * math.pi * i / segs) * r) for i in range(segs)]
        bot_v = [(math.cos(2 * math.pi * i / segs) * r, 5, math.sin(2 * math.pi * i / segs) * r) for i in range(segs)]
        verts = top_v + bot_v
        faces = [(tuple(range(segs)), (195, 220, 240)), (tuple(range(segs, 2 * segs)), (150, 175, 195))]
        for i in range(segs):
            ni = (i + 1) % segs
            faces.append(((i, ni, ni + segs, i + segs), (165, 190, 215)))
        meshes.append((verts, faces))
        meshes.append(make_3d_box(45, -8, 0, 14, 6, 22, (235, 70, 70)))
        meshes.append(make_3d_box(-10, 10, -45, 42, 22, 22, (235, 190, 25)))
        meshes.append(make_3d_box(-10, 10, 45, 42, 22, 22, (235, 190, 25)))
        meshes.append(make_3d_box(-10, 10, -64, 54, 54, 18, (35, 38, 44)))
        meshes.append(make_3d_box(-10, 10, 64, 54, 54, 18, (35, 38, 44)))
    else:  # 4WD Вездеход
        meshes.append(make_3d_box(0, 0, 0, 150, 10, 86, (175, 200, 225)))
        meshes.append(make_3d_box(0, -14, 0, 52, 18, 48, (40, 44, 52)))  # Батарейный отсек
        meshes.append(make_3d_box(62, -8, 0, 14, 6, 24, (235, 70, 70)))
        for wx in (-42, 42):
            for wz_m, wz_w in ((-32, -52), (32, 52)):
                meshes.append(make_3d_box(wx, 6, wz_m, 36, 20, 20, (235, 190, 25)))
                meshes.append(make_3d_box(wx, 6, wz_w, 48, 48, 18, (35, 38, 44)))
    return meshes

def draw_robot_3d(surface, center_xy, preset_idx, rx, ry):
    meshes = get_robot_3d_meshes(preset_idx)
    render_list = []
    cos_x, sin_x = math.cos(rx), math.sin(rx)
    cos_y, sin_y = math.cos(ry), math.sin(ry)

    for verts, faces in meshes:
        proj = []
        rot_z_vals = []
        for vx, vy, vz in verts:
            # Вращение вокруг Y
            x1 = vx * cos_y + vz * sin_y
            z1 = -vx * sin_y + vz * cos_y
            # Вращение вокруг X
            y2 = vy * cos_x - z1 * sin_x
            z2 = vy * sin_x + z1 * cos_x
            # Перспектива
            fov = 420
            scale = fov / (fov + z2)
            px = center_xy[0] + x1 * scale * 1.35
            py = center_xy[1] + y2 * scale * 1.35
            proj.append((px, py))
            rot_z_vals.append(z2)

        for f_idx, color in faces:
            avg_z = sum(rot_z_vals[i] for i in f_idx) / len(f_idx)
            poly_pts = [proj[i] for i in f_idx]
            render_list.append((avg_z, poly_pts, color))

    # Сортировка граней от дальних к ближним (алгоритм художника)
    render_list.sort(key=lambda item: item[0], reverse=True)
    for _, poly_pts, color in render_list:
        pygame.draw.polygon(surface, color, poly_pts)
        pygame.draw.polygon(surface, (20, 24, 30), poly_pts, 1)

# =========================================================================
# 4. СОСТОЯНИЕ ИГРЫ И ПЕРЕМЕННЫЕ РОБОТА
# =========================================================================
game_state = "MENU"  # "MENU", "LOADING", "GAME"
selected_robot_idx = 0
mouse_was_pressed = False

go_shimmer_x = 0.0
load_start_ticks = 0
LOADING_DURATION_MS = 2000

robot_pos = pygame.math.Vector2(500, 300)
robot_angle = 0.0
SPEED_MODES = {
    '1': {'move': 2.0, 'rot': 1.5},
    '2': {'move': 4.5, 'rot': 3.0},
    '3': {'move': 7.5, 'rot': 5.0}
}
current_gear = '2'
move_speed = SPEED_MODES[current_gear]['move']
rot_speed = SPEED_MODES[current_gear]['rot']
last_key_time = 0

# =========================================================================
# ОСНОВНОЙ ЦИКЛ ПРОГРАММЫ
# =========================================================================
while programm_run:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            programm_run = False
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            is_dragging_3d = False

    try:
        with open("pult_sender_sys_output.txt", "r", encoding="utf-8") as file:
            lines = [line.strip() for line in file]
            if len(lines) >= 4:
                x_read, y_read, left, right = lines[:4]
    except FileNotFoundError:
        pass

    SCR_W, SCR_H = screen.get_size()
    mouse_pos = pygame.mouse.get_pos()
    mouse_pressed = pygame.mouse.get_pressed()[0]
    mouse_clicked = mouse_pressed and not mouse_was_pressed
    mouse_was_pressed = mouse_pressed
    window_active = pygame.key.get_focused()  # Защита от срабатывания клавиш при AFK/свернутом окне

    # ---------------------------------------------------------------------
    # СОСТОЯНИЕ 1: ГЛАВНОЕ МЕНЮ
    # ---------------------------------------------------------------------
    if game_state == "MENU":
        screen.fill((22, 27, 36))
        pygame.draw.rect(screen, (30, 37, 48), (0, 0, SCR_W, 65))

        header_txt = font_title.render("ВЫБОР КОНФИГУРАЦИИ РОБОТА", True, (220, 225, 235))
        screen.blit(header_txt, (40, 18))

        # 3 карточки выбора слева
        card_w, card_h = 175, 240
        start_x, start_y = 40, 110
        gap = 20

        for i in range(3):
            cx = start_x + i * (card_w + gap)
            cy = start_y
            card_rect = pygame.Rect(cx, cy, card_w, card_h)
            is_selected = (selected_robot_idx == i)
            is_hovered = card_rect.collidepoint(mouse_pos)

            if is_hovered and mouse_clicked:
                selected_robot_idx = i

            bg_color = (42, 52, 66) if is_hovered else (32, 39, 50)
            pygame.draw.rect(screen, bg_color, card_rect, border_radius=8)

            preset = ROBOT_PRESETS[i]
            preview_surf = pygame.Surface((160, 150), pygame.SRCALPHA)
            p_img = preset["plat"]
            preview_surf.blit(p_img, p_img.get_rect(center=(80, 75)))
            if preset["has_ext_wheels"]:
                preview_surf.blit(img_wheel_left, img_wheel_left.get_rect(center=(80 + preset["off_x"], 75 - preset["track"])))
                preview_surf.blit(img_wheel_right, img_wheel_right.get_rect(center=(80 + preset["off_x"], 75 + preset["track"])))
            screen.blit(preview_surf, (cx + 7, cy + 15))

            name_surf = font_card.render(preset["name"], True, (230, 235, 240))
            screen.blit(name_surf, name_surf.get_rect(center=(cx + card_w // 2, cy + 175)))

            check_box = pygame.Rect(cx + card_w // 2 - 14, cy + 198, 28, 28)
            pygame.draw.rect(screen, (20, 25, 32), check_box, border_radius=4)
            pygame.draw.rect(screen, (100, 115, 130), check_box, width=2, border_radius=4)

            if is_selected:
                pygame.draw.rect(screen, (46, 204, 113), card_rect, width=4, border_radius=8)
                pygame.draw.rect(screen, (46, 204, 113), check_box, border_radius=4)
                pygame.draw.lines(screen, (255, 255, 255), False, [
                    (check_box.x + 6, check_box.y + 14),
                    (check_box.x + 12, check_box.y + 20),
                    (check_box.x + 22, check_box.y + 8)
                ], 3)

        # --- ПРАВАЯ ЧАСТЬ: 3D-МОДЕЛЬ РОБОТА С ВРАЩЕНИЕМ МЫШЬЮ ---
        viewer_rect = pygame.Rect(SCR_W - 350, 90, 310, 360)
        if viewer_rect.collidepoint(mouse_pos) and mouse_clicked:
            is_dragging_3d = True
            last_mouse_3d = mouse_pos

        if is_dragging_3d and mouse_pressed:
            dx = mouse_pos[0] - last_mouse_3d[0]
            dy = mouse_pos[1] - last_mouse_3d[1]
            rot3d_y += dx * 0.012
            rot3d_x += dy * 0.012
            rot3d_x = max(-1.3, min(1.3, rot3d_x))
            last_mouse_3d = mouse_pos
        else:
            # Плавное автовращение, когда мышь отпущена
            rot3d_y += 0.012

        draw_robot_3d(screen, viewer_rect.center, selected_robot_idx, rot3d_x, rot3d_y)
        hint_3d = font_hud.render("Зажмите ЛКМ, чтобы покрутить в 3D", True, (130, 145, 165))
        screen.blit(hint_3d, hint_3d.get_rect(center=(viewer_rect.centerx, viewer_rect.bottom - 10)))

        # --- ПЕРЕЛИВАЮЩАЯСЯ КНОПКА "GO" ---
        btn_rect = pygame.Rect(SCR_W - 260, SCR_H - 95, 220, 65)
        btn_hovered = btn_rect.collidepoint(mouse_pos)

        pulse = int(math.sin(pygame.time.get_ticks() * 0.006) * 15)
        base_green = (40, min(255, 185 + pulse), 85) if btn_hovered else (34, min(255, 165 + pulse), 74)
        pygame.draw.rect(screen, base_green, btn_rect, border_radius=6)

        shimmer_surf = pygame.Surface((btn_rect.w, btn_rect.h), pygame.SRCALPHA)
        go_shimmer_x = (go_shimmer_x + 4.5) % (btn_rect.w + 140)
        sx = go_shimmer_x - 70
        pygame.draw.polygon(shimmer_surf, (255, 255, 255, 75), [
            (sx, 0), (sx + 35, 0), (sx + 10, btn_rect.h), (sx - 25, btn_rect.h)
        ])
        screen.blit(shimmer_surf, btn_rect.topleft)
        pygame.draw.rect(screen, (130, 255, 170), btn_rect, width=2, border_radius=6)

        go_txt = font_btn.render("GO", True, (255, 255, 255))
        screen.blit(go_txt, go_txt.get_rect(center=btn_rect.center))

        if btn_hovered and mouse_clicked:
            game_state = "LOADING"
            load_start_ticks = pygame.time.get_ticks()

    # ---------------------------------------------------------------------
    # СОСТОЯНИЕ 2: ЭКРАН ЗАГРУЗКИ (2 СЕКУНДЫ)
    # ---------------------------------------------------------------------
    elif game_state == "LOADING":
        screen.fill((18, 22, 29))
        elapsed = pygame.time.get_ticks() - load_start_ticks
        progress = min(1.0, elapsed / LOADING_DURATION_MS)

        preset = ROBOT_PRESETS[selected_robot_idx]
        big_scale = 2.0
        big_plat = pygame.transform.rotozoom(preset["plat"], 0, big_scale)
        screen.blit(big_plat, big_plat.get_rect(center=(SCR_W // 2, SCR_H // 2 - 70)))

        if preset["has_ext_wheels"]:
            big_wl = pygame.transform.rotozoom(img_wheel_left, 0, big_scale)
            big_wr = pygame.transform.rotozoom(img_wheel_right, 0, big_scale)
            screen.blit(big_wl, big_wl.get_rect(center=(SCR_W // 2 + preset["off_x"] * big_scale, SCR_H // 2 - 70 - preset["track"] * big_scale)))
            screen.blit(big_wr, big_wr.get_rect(center=(SCR_W // 2 + preset["off_x"] * big_scale, SCR_H // 2 - 70 + preset["track"] * big_scale)))

        load_txt = font_title.render("Загрузка...", True, (235, 240, 245))
        screen.blit(load_txt, load_txt.get_rect(center=(SCR_W // 2, SCR_H // 2 + 75)))

        bar_w, bar_h = 460, 24
        bar_x = (SCR_W - bar_w) // 2
        bar_y = SCR_H // 2 + 115
        pygame.draw.rect(screen, (32, 38, 48), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        pygame.draw.rect(screen, (70, 85, 105), (bar_x, bar_y, bar_w, bar_h), width=2, border_radius=4)

        fill_w = int((bar_w - 8) * progress)
        if fill_w > 0:
            pygame.draw.rect(screen, (46, 204, 113), (bar_x + 4, bar_y + 4, fill_w, bar_h - 8), border_radius=2)

        if elapsed >= LOADING_DURATION_MS:
            robot_pos = pygame.math.Vector2(SCR_W // 2, SCR_H // 2)
            robot_angle = 0.0
            game_state = "GAME"

    # ---------------------------------------------------------------------
    # СОСТОЯНИЕ 3: ОСНОВНОЕ ПОЛЕ И УПРАВЛЕНИЕ КАЖДЫМ КОЛЕСОМ
    # ---------------------------------------------------------------------
    elif game_state == "GAME":
        screen.blit(bg_generated, (0, 0))

        preset = ROBOT_PRESETS[selected_robot_idx]
        offset_left = pygame.math.Vector2(preset["off_x"], -preset["track"])
        offset_right = pygame.math.Vector2(preset["off_x"], preset["track"])

        # Управление работает ТОЛЬКО когда окно активно (защита от AFK-срабатываний)
        if window_active:
            if keyboard.is_pressed(KEY_BINDS["back_to_menu"]):
                game_state = "MENU"

            for key in ('1', '2', '3'):
                if keyboard.is_pressed(key):
                    current_gear = key
                    move_speed = SPEED_MODES[key]['move']
                    rot_speed = SPEED_MODES[key]['rot']

            forward_vec = pygame.math.Vector2(1, 0).rotate(-robot_angle)

            # 1. Раздельное управление колесами для 2WD (Вариант 1 и 2)
            if not preset["is_4wd"]:
                v_left = 0.0
                v_right = 0.0
                if keyboard.is_pressed(KEY_BINDS["w2_left_fwd"]):
                    v_left += move_speed
                if keyboard.is_pressed(KEY_BINDS["w2_left_bwd"]):
                    v_left -= move_speed
                if keyboard.is_pressed(KEY_BINDS["w2_right_fwd"]):
                    v_right += move_speed
                if keyboard.is_pressed(KEY_BINDS["w2_right_bwd"]):
                    v_right -= move_speed

                if v_left != 0.0 or v_right != 0.0:
                    # Дифференциальная кинематика двух независимых колес
                    linear_v = (v_left + v_right) / 2.0
                    angular_v = math.degrees((v_right - v_left) / (preset["track"] * 2.0))
                    axle_center = robot_pos + pygame.math.Vector2(preset["off_x"], 0).rotate(-robot_angle)
                    axle_center += forward_vec * linear_v
                    robot_angle += angular_v
                    robot_pos = axle_center - pygame.math.Vector2(preset["off_x"], 0).rotate(-robot_angle)

            # 2. Раздельное управление 4 колесами для 4WD (Вариант 3)
            else:
                v_fl, v_fr, v_rl, v_rr = 0.0, 0.0, 0.0, 0.0
                if keyboard.is_pressed(KEY_BINDS["w4_fl_fwd"]):
                    v_fl += move_speed
                if keyboard.is_pressed(KEY_BINDS["w4_fl_bwd"]):
                    v_fl -= move_speed
                if keyboard.is_pressed(KEY_BINDS["w4_fr_fwd"]):
                    v_fr += move_speed
                if keyboard.is_pressed(KEY_BINDS["w4_fr_bwd"]):
                    v_fr -= move_speed
                if keyboard.is_pressed(KEY_BINDS["w4_rl_fwd"]):
                    v_rl += move_speed
                if keyboard.is_pressed(KEY_BINDS["w4_rl_bwd"]):
                    v_rl -= move_speed
                if keyboard.is_pressed(KEY_BINDS["w4_rr_fwd"]):
                    v_rr += move_speed
                if keyboard.is_pressed(KEY_BINDS["w4_rr_bwd"]):
                    v_rr -= move_speed

                if any(v != 0.0 for v in (v_fl, v_fr, v_rl, v_rr)):
                    v_left_side = (v_fl + v_rl) / 2.0
                    v_right_side = (v_fr + v_rr) / 2.0
                    linear_v = (v_left_side + v_right_side) / 2.0
                    angular_v = math.degrees((v_right_side - v_left_side) / (preset["track"] * 2.0))
                    robot_pos += forward_vec * linear_v
                    robot_angle += angular_v

            # 3. Классическое управление (W/A/S/D + Q/E)
            if keyboard.is_pressed(KEY_BINDS["pivot_left"]):
                pivot = robot_pos + offset_left.rotate(-robot_angle)
                robot_angle += rot_speed
                robot_pos = pivot - offset_left.rotate(-robot_angle)
            elif keyboard.is_pressed(KEY_BINDS["pivot_right"]):
                pivot = robot_pos + offset_right.rotate(-robot_angle)
                robot_angle -= rot_speed
                robot_pos = pivot - offset_right.rotate(-robot_angle)
            elif keyboard.is_pressed(KEY_BINDS["forward"]):
                robot_pos += forward_vec * move_speed
            elif keyboard.is_pressed(KEY_BINDS["backward"]):
                robot_pos -= forward_vec * move_speed
            elif keyboard.is_pressed(KEY_BINDS["tank_left"]):
                axle_center = robot_pos + pygame.math.Vector2(preset["off_x"], 0).rotate(-robot_angle)
                robot_angle += rot_speed
                robot_pos = axle_center - pygame.math.Vector2(preset["off_x"], 0).rotate(-robot_angle)
            elif keyboard.is_pressed(KEY_BINDS["tank_right"]):
                axle_center = robot_pos + pygame.math.Vector2(preset["off_x"], 0).rotate(-robot_angle)
                robot_angle -= rot_speed
                robot_pos = axle_center - pygame.math.Vector2(preset["off_x"], 0).rotate(-robot_angle)

            if keyboard.is_pressed(KEY_BINDS["reset_pos"]):
                robot_pos = pygame.math.Vector2(SCR_W // 2, SCR_H // 2)
                robot_angle = 0.0

            if keyboard.is_pressed(KEY_BINDS["print_pos"]):
                print(f"X: {round(robot_pos.x)}, Y: {round(robot_pos.y)}, Angle: {round(robot_angle % 360)}")

        # Отрисовка выбранного робота
        rot_platform = pygame.transform.rotate(preset["plat"], robot_angle)
        screen.blit(rot_platform, rot_platform.get_rect(center=(round(robot_pos.x), round(robot_pos.y))))

        if preset["has_ext_wheels"]:
            pos_l = robot_pos + offset_left.rotate(-robot_angle)
            pos_r = robot_pos + offset_right.rotate(-robot_angle)
            rot_wl = pygame.transform.rotate(img_wheel_left, robot_angle)
            rot_wr = pygame.transform.rotate(img_wheel_right, robot_angle)
            screen.blit(rot_wl, rot_wl.get_rect(center=(round(pos_l.x), round(pos_l.y))))
            screen.blit(rot_wr, rot_wr.get_rect(center=(round(pos_r.x), round(pos_r.y))))

        # Информационная панель (HUD) с текущими биндами колес
        if not preset["is_4wd"]:
            wheels_hint = f"Колеса: Лев[{KEY_BINDS['w2_left_fwd'].upper()}/{KEY_BINDS['w2_left_bwd'].upper()}] Прав[{KEY_BINDS['w2_right_fwd'].upper()}/{KEY_BINDS['w2_right_bwd'].upper()}]"
        else:
            wheels_hint = f"4WD: ПЛ[{KEY_BINDS['w4_fl_fwd'].upper()}/{KEY_BINDS['w4_fl_bwd'].upper()}] ПП[{KEY_BINDS['w4_fr_fwd'].upper()}/{KEY_BINDS['w4_fr_bwd'].upper()}] ЗЛ[{KEY_BINDS['w4_rl_fwd'].upper()}/{KEY_BINDS['w4_rl_bwd'].upper()}] ЗП[{KEY_BINDS['w4_rr_fwd'].upper()}/{KEY_BINDS['w4_rr_bwd'].upper()}]"

        hud_text = font_hud.render(f"{preset['name']} | Скор: {current_gear} (1-3) | {wheels_hint} | [{KEY_BINDS['reset_pos'].upper()}] Сброс | [{KEY_BINDS['back_to_menu'].upper()}] Меню", True, (200, 210, 225))
        screen.blit(hud_text, (15, 15))

    # Служебные команды (работают только при активном окне)
    now = pygame.time.get_ticks()
    if window_active and (now - last_key_time > 250):
        if keyboard.is_pressed('enter'):
            enter_press += 1
            last_key_time = now
            if enter_press >= 2:
                enter_press = 0
                pass

        if keyboard.is_pressed('backspace'):
            backspace_press += 1
            last_key_time = now
            if backspace_press >= 2:
                backspace_press = 0
                robot_pos = pygame.math.Vector2(SCR_W // 2, SCR_H // 2)
                robot_angle = 0.0

        if keyboard.is_pressed('esc'):
            esc_press += 1
            last_key_time = now
            if esc_press >= 2:
                programm_run = False

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
if SerialObj is not None and SerialObj.is_open:
    SerialObj.close()