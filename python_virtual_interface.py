import sys
import math
import time
import copy
import random
import pygame
import serial
import serial.tools.list_ports
import keyboard
from tkinter import Tk, messagebox

pygame.init()
pygame.font.init()

SCR_W, SCR_H = 1000, 600
screen = pygame.display.set_mode((SCR_W, SCR_H))
pygame.display.set_caption("Robot emulator MODIFICATED")

root_tk = Tk()
root_tk.wm_withdraw()

try:
    icon = pygame.image.load("icon_new.png")
    pygame.display.set_icon(icon)
except Exception:
    pass

# =========================================================================
# 1. ЗАСТАВКА В СТИЛЕ VALVE -> CS2 (ТУМАН)
# =========================================================================
def play_intro_animation():
    clock_intro = pygame.time.Clock()
    font_valve = pygame.font.SysFont("impact", 76)
    font_cs = pygame.font.SysFont("arial", 46, bold=True)

    # Этап 1: Красная надпись "Team BB" на черном фоне (2 секунды)
    start_t = pygame.time.get_ticks()
    while pygame.time.get_ticks() - start_t < 2000:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        screen.fill((0, 0, 0))
        txt_bb = font_valve.render("Team BB", True, (215, 25, 25))
        rect_bb = txt_bb.get_rect(center=(SCR_W // 2, SCR_H // 2))
        # Легкое появление/затухание
        elapsed = pygame.time.get_ticks() - start_t
        alpha = 255
        if elapsed < 300:
            alpha = int(255 * (elapsed / 300))
        elif elapsed > 1600:
            alpha = int(255 * ((2000 - elapsed) / 400))
        txt_bb.set_alpha(max(0, min(255, alpha)))
        screen.blit(txt_bb, rect_bb)
        pygame.display.flip()
        clock_intro.tick(60)

    # Этап 2: Появление "Robot emulator MODIFICATED" сквозь дымку/туман (2.2 секунды)
    fog_particles = [
        [random.randint(-100, SCR_W + 100), random.randint(150, 450), random.randint(90, 180), random.uniform(-1.5, 1.5)]
        for _ in range(35)
    ]
    start_t2 = pygame.time.get_ticks()
    while pygame.time.get_ticks() - start_t2 < 2200:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        elapsed = pygame.time.get_ticks() - start_t2
        prog = min(1.0, elapsed / 2200.0)

        # Фон плавно переходит из черного в темно-синий CS2
        bg_r = int(22 * prog)
        bg_g = int(27 * prog)
        bg_b = int(36 * prog)
        screen.fill((bg_r, bg_g, bg_b))

        # Оранжево-синий градиентный акцент как в интро CS2
        glow = pygame.Surface((SCR_W, SCR_H), pygame.SRCALPHA)
        pygame.draw.circle(glow, (230, 126, 34, int(55 * math.sin(prog * math.pi))), (SCR_W // 2, SCR_H // 2), 260)
        screen.blit(glow, (0, 0))

        txt_title = font_cs.render("Robot emulator MODIFICATED", True, (240, 245, 255))
        txt_title.set_alpha(int(255 * min(1.0, prog * 1.4)))
        screen.blit(txt_title, txt_title.get_rect(center=(SCR_W // 2, SCR_H // 2)))

        # Слои тумана, рассеивающиеся в стороны
        fog_alpha = int(110 * (1.0 - prog))
        if fog_alpha > 2:
            for fp in fog_particles:
                fp[0] += fp[3] * 2.5
                f_surf = pygame.Surface((fp[2] * 2, fp[2]), pygame.SRCALPHA)
                pygame.draw.ellipse(f_surf, (180, 195, 215, fog_alpha), (0, 0, fp[2] * 2, fp[2]))
                screen.blit(f_surf, (fp[0] - fp[2], fp[1] - fp[2] // 2))

        pygame.display.flip()
        clock_intro.tick(60)

play_intro_animation()

# =========================================================================
# 2. БЕЗОПАСНОЕ ПОДКЛЮЧЕНИЕ ARDUINO
# =========================================================================
ports = list(serial.tools.list_ports.comports())
ser_port = None
for p in ports:
    if any(k in p.description.lower() for k in ("arduino", "ch340", "ch341", "usb-serial", "usb")):
        ser_port = p.device
        break

SerialObj = None
if ser_port:
    try:
        SerialObj = serial.Serial(ser_port, baudrate=9600, timeout=0.1)
    except Exception:
        SerialObj = None

FPS = 80
clock = pygame.time.Clock()

font_title = pygame.font.SysFont("arial", 24, bold=True)
font_card = pygame.font.SysFont("arial", 16, bold=True)
font_btn = pygame.font.SysFont("arial", 30, bold=True)
font_hud = pygame.font.SysFont("arial", 14, bold=True)

# =========================================================================
# 3. БАЗОВЫЕ СПРАЙТЫ И ХРАНИЛИЩЕ КОНФИГУРАЦИЙ (РОБОТЫ, ПУЛЬТЫ, ПОЛЯ)
# =========================================================================
def make_wheel_surface(wheel_type="normal", is_left=True, w=46, h=42):
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    wheel_y = 0 if is_left else h - 16
    motor_y = 16 if is_left else 4
    # Желтый мотор-редуктор
    pygame.draw.rect(surf, (240, 195, 20), (5, motor_y, w - 10, 20), border_radius=2)
    pygame.draw.rect(surf, (150, 110, 0), (5, motor_y, w - 10, 20), 2, border_radius=2)
    if wheel_type == "normal":
        pygame.draw.rect(surf, (30, 32, 38), (0, wheel_y, w, 16), border_radius=4)
    elif wheel_type == "omni":
        pygame.draw.rect(surf, (165, 175, 190), (0, wheel_y, w, 16), border_radius=3)
        for rx in range(4, w - 4, 8):
            pygame.draw.rect(surf, (25, 28, 32), (rx, wheel_y - 1, 5, 18), border_radius=2)
    else:
        # Только мотор без колеса
        pygame.draw.rect(surf, (210, 215, 225), (w // 2 - 3, wheel_y + 6, 6, 10))
    return surf

def render_robot_config_surface(cfg, scale=1.0):
    base_size = 180
    surf = pygame.Surface((base_size, base_size), pygame.SRCALPHA)
    cx, cy = base_size // 2, base_size // 2
    shape = cfg.get("shape", "square")

    if shape == "square":
        pygame.draw.rect(surf, (200, 220, 240, 200), (cx - 48, cy - 48, 96, 96), border_radius=10)
        pygame.draw.rect(surf, (100, 130, 160), (cx - 48, cy - 48, 96, 96), 3, border_radius=10)
        pygame.draw.rect(surf, (255, 75, 75), (cx + 34, cy - 10, 10, 20))
    elif shape == "circle":
        pygame.draw.circle(surf, (210, 230, 245, 200), (cx, cy), 54)
        pygame.draw.circle(surf, (130, 160, 190), (cx, cy), 54, 3)
        pygame.draw.polygon(surf, (255, 75, 75), [(cx + 48, cy), (cx + 34, cy - 9), (cx + 34, cy + 9)])
    else:  # rect (4WD)
        pygame.draw.rect(surf, (200, 220, 240, 200), (cx - 62, cy - 40, 124, 80), border_radius=12)
        pygame.draw.rect(surf, (110, 140, 170), (cx - 62, cy - 40, 124, 80), 3, border_radius=12)
        pygame.draw.polygon(surf, (255, 75, 75), [(cx + 56, cy), (cx + 42, cy - 9), (cx + 42, cy + 9)])

    for m in cfg.get("motors", []):
        w_surf = make_wheel_surface(m["wheel"], m["y"] < 0)
        m_rect = w_surf.get_rect(center=(cx + m["x"], cy + m["y"]))
        surf.blit(w_surf, m_rect)
        # Номер мотора (М1, М2...)
        num_txt = font_hud.render(f"M{m['id']}", True, (255, 255, 255))
        pygame.draw.circle(surf, (20, 25, 35), m_rect.center, 10)
        surf.blit(num_txt, num_txt.get_rect(center=m_rect.center))

    if scale != 1.0:
        surf = pygame.transform.rotozoom(surf, 0, scale)
    return surf

def generate_base_metal_floor(w, h):
    floor = pygame.Surface((w, h))
    floor.fill((26, 29, 34))
    step = 28
    for row, y_pos in enumerate(range(0, h + step, step)):
        off = (step // 2) if row % 2 == 1 else 0
        for x_pos in range(-step, w + step, step):
            cx, cy = x_pos + off, y_pos
            if ((x_pos // step) + row) % 2 == 0:
                pts = [(cx - 6, cy - 2), (cx - 2, cy - 6), (cx + 6, cy + 2), (cx + 2, cy + 6)]
            else:
                pts = [(cx - 6, cy + 2), (cx + 2, cy - 6), (cx + 6, cy - 2), (cx - 2, cy + 6)]
            pygame.draw.polygon(floor, (42, 46, 54), pts)
    for gx in range(0, w, 100):
        pygame.draw.line(floor, (34, 38, 45), (gx, 0), (gx, h), 1)
    for gy in range(0, h, 100):
        pygame.draw.line(floor, (34, 38, 45), (0, gy), (w, gy), 1)
    return floor

bg_metal_floor = generate_base_metal_floor(SCR_W, SCR_H)

# Списки сохраненных конфигураций (изначально заполнены стартовыми пресетами)
saved_robots = [
    {
        "name": "2WD Квадрат", "shape": "square",
        "motors": [
            {"id": 1, "x": -28, "y": -44, "wheel": "normal"},
            {"id": 2, "x": -28, "y": 44, "wheel": "normal"},
        ]
    },
    {
        "name": "2WD Круглый", "shape": "circle",
        "motors": [
            {"id": 1, "x": -10, "y": -46, "wheel": "normal"},
            {"id": 2, "x": -10, "y": 46, "wheel": "normal"},
        ]
    },
    {
        "name": "4WD Вездеход", "shape": "rect",
        "motors": [
            {"id": 1, "x": 32, "y": -44, "wheel": "normal"},
            {"id": 2, "x": 32, "y": 44, "wheel": "normal"},
            {"id": 3, "x": -32, "y": -44, "wheel": "normal"},
            {"id": 4, "x": -32, "y": 44, "wheel": "normal"},
        ]
    },
]

saved_remotes = [
    {
        "name": "Стандартный WASD",
        "buttons": [
            {"x": 70, "y": 40, "key": "w", "label": "W", "motor_id": 0, "dir": 1},   # motor_id=0 -> все моторы
            {"x": 70, "y": 110, "key": "s", "label": "S", "motor_id": 0, "dir": -1},
            {"x": 25, "y": 75, "key": "a", "label": "A", "motor_id": -1, "dir": 1},  # -1 -> танковый лево
            {"x": 115, "y": 75, "key": "d", "label": "D", "motor_id": -2, "dir": 1}, # -2 -> танковый право
            {"x": 180, "y": 40, "key": "u", "label": "U", "motor_id": 1, "dir": 1},
            {"x": 180, "y": 110, "key": "j", "label": "J", "motor_id": 1, "dir": -1},
            {"x": 230, "y": 40, "key": "i", "label": "I", "motor_id": 2, "dir": 1},
            {"x": 230, "y": 110, "key": "k", "label": "K", "motor_id": 2, "dir": -1},
        ]
    }
]

saved_fields = [
    {"name": "Пустой полигон", "objects": []},
    {
        "name": "Тренировочная трасса",
        "objects": [
            {"x": 220, "y": 140, "w": 40, "h": 260, "type": "wall"},
            {"x": 740, "y": 180, "w": 40, "h": 260, "type": "wall"},
            {"x": 460, "y": 260, "w": 45, "h": 45, "type": "box"},
            {"x": 530, "y": 310, "w": 45, "h": 45, "type": "box"},
        ]
    }
]

# Активные выбранные конфигурации для запуска на поле
active_robot_idx = 0
active_remote_idx = 0
active_field_idx = 0

# =========================================================================
# 4. ПЕРЕМЕННЫЕ СОСТОЯНИЙ ИНТЕРФЕЙСА И КОНСТРУКТОРОВ (TINKERCAD STYLE)
# =========================================================================
programm_run = True
game_state = "MENU"  # "MENU", "LOADING", "GAME"
menu_tab = "PLAY"    # "PLAY", "CFG_ROBOT", "CFG_REMOTE", "CFG_FIELD", "MANAGER"

# Рабочие буферы для 3 конструкторов
draft_robot = copy.deepcopy(saved_robots[0])
selected_draft_motor = None
drag_motor_idx = None

draft_remote = {"name": "Мой Пульт", "buttons": []}
selected_remote_btn = None
drag_remote_btn = None
waiting_key_bind = False

draft_field = {"name": "Мое Поле", "objects": []}
selected_field_obj = None
drag_field_obj = None

# Уведомление "Сохранено!"
toast_text = ""
toast_timer = 0

# Анимация кнопки GO и загрузки
go_shimmer_x = 0.0
load_start_ticks = 0
LOADING_DURATION_MS = 2000

# Игровые переменные поля
robot_pos = pygame.math.Vector2(500, 300)
robot_angle = 0.0
live_field_objects = []
SPEED_MODES = {'1': 2.0, '2': 4.5, '3': 7.5}
current_gear = '2'
esc_press = 0
last_key_time = 0
mouse_was_pressed = False

def show_toast(msg):
    global toast_text, toast_timer
    toast_text = msg
    toast_timer = pygame.time.get_ticks()

def draw_tinkercad_grid(surface, rect):
    pygame.draw.rect(surface, (238, 243, 248), rect, border_radius=8)
    for gx in range(rect.left, rect.right, 20):
        col = (195, 215, 235) if (gx - rect.left) % 100 == 0 else (220, 230, 240)
        pygame.draw.line(surface, col, (gx, rect.top), (gx, rect.bottom), 1)
    for gy in range(rect.top, rect.bottom, 20):
        col = (195, 215, 235) if (gy - rect.top) % 100 == 0 else (220, 230, 240)
        pygame.draw.line(surface, col, (rect.left, gy), (rect.right, gy), 1)
    pygame.draw.rect(surface, (140, 165, 190), rect, 2, border_radius=8)

# =========================================================================
# ОСНОВНОЙ ЦИКЛ ПРОГРАММЫ
# =========================================================================
while programm_run:
    mouse_pos = pygame.mouse.get_pos()
    mouse_pressed = pygame.mouse.get_pressed()[0]
    mouse_clicked = mouse_pressed and not mouse_was_pressed
    mouse_was_pressed = mouse_pressed
    window_active = pygame.key.get_focused()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            programm_run = False
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            drag_motor_idx = None
            drag_remote_btn = None
            drag_field_obj = None
        elif event.type == pygame.KEYDOWN and waiting_key_bind and selected_remote_btn is not None:
            key_name = pygame.key.name(event.key)
            draft_remote["buttons"][selected_remote_btn]["key"] = key_name
            draft_remote["buttons"][selected_remote_btn]["label"] = key_name.upper()[:4]
            waiting_key_bind = False

    # =====================================================================
    # ЭКРАН 1: ГЛАВНОЕ МЕНЮ И КОНСТРУКТОРЫ
    # =====================================================================
    if game_state == "MENU":
        screen.fill((22, 27, 36))

        # --- ЛЕВАЯ БОКОВАЯ ПАНЕЛЬ В СТИЛЕ CS:GO (5 КНОПОК) ---
        nav_w = 72
        pygame.draw.rect(screen, (15, 19, 26), (0, 0, nav_w, SCR_H))
        pygame.draw.line(screen, (40, 48, 62), (nav_w, 0), (nav_w, SCR_H), 2)

        nav_buttons = [
            {"id": "PLAY", "y": 25, "hint": "Старт"},
            {"id": "CFG_ROBOT", "y": 100, "hint": "Робот"},
            {"id": "CFG_REMOTE", "y": 175, "hint": "Пульт"},
            {"id": "CFG_FIELD", "y": 250, "hint": "Поле"},
            {"id": "MANAGER", "y": 325, "hint": "Сборки"},
        ]

        for nb in nav_buttons:
            r_btn = pygame.Rect(8, nb["y"], 56, 56)
            is_act = (menu_tab == nb["id"])
            is_hov = r_btn.collidepoint(mouse_pos)
            if is_hov and mouse_clicked:
                menu_tab = nb["id"]
                waiting_key_bind = False

            if is_act:
                pygame.draw.rect(screen, (34, 44, 58), r_btn, border_radius=8)
                pygame.draw.rect(screen, (46, 204, 113), (0, nb["y"] + 8, 4, 40))
            elif is_hov:
                pygame.draw.rect(screen, (26, 33, 44), r_btn, border_radius=8)

            cx, cy = r_btn.center
            c_ico = (255, 255, 255) if is_act else (140, 155, 175)
            if nb["id"] == "PLAY":
                pygame.draw.circle(screen, c_ico, (cx, cy), 17, 2)
                pygame.draw.polygon(screen, c_ico, [(cx - 4, cy - 7), (cx - 4, cy + 7), (cx + 8, cy)])
            elif nb["id"] == "CFG_ROBOT":
                pygame.draw.rect(screen, c_ico, (cx - 11, cy - 7, 22, 16), 2, border_radius=3)
                pygame.draw.line(screen, c_ico, (cx, cy - 7), (cx, cy - 14), 2)
                pygame.draw.circle(screen, c_ico, (cx, cy - 15), 2)
                pygame.draw.circle(screen, c_ico, (cx - 5, cy), 2)
                pygame.draw.circle(screen, c_ico, (cx + 5, cy), 2)
            elif nb["id"] == "CFG_REMOTE":
                pygame.draw.rect(screen, c_ico, (cx - 14, cy - 9, 28, 18), 2, border_radius=5)
                pygame.draw.line(screen, c_ico, (cx - 8, cy - 3), (cx - 8, cy + 3), 2)
                pygame.draw.line(screen, c_ico, (cx - 11, cy), (cx - 5, cy), 2)
                pygame.draw.circle(screen, c_ico, (cx + 7, cy - 2), 2)
                pygame.draw.circle(screen, c_ico, (cx + 10, cy + 2), 2)
            elif nb["id"] == "CFG_FIELD":
                pygame.draw.rect(screen, c_ico, (cx - 13, cy - 13, 26, 26), 2)
                pygame.draw.line(screen, c_ico, (cx - 13, cy), (cx + 13, cy), 1)
                pygame.draw.line(screen, c_ico, (cx, cy - 13), (cx, cy + 13), 1)
            elif nb["id"] == "MANAGER":
                pygame.draw.rect(screen, c_ico, (cx - 14, cy - 11, 7, 22), 2)
                pygame.draw.rect(screen, c_ico, (cx - 3, cy - 11, 7, 22), 2)
                pygame.draw.rect(screen, c_ico, (cx + 8, cy - 11, 7, 22), 2)

            lbl = font_hud.render(nb["hint"], True, c_ico)
            screen.blit(lbl, lbl.get_rect(center=(cx, nb["y"] + 64)))

        work_x = nav_w + 20

        # -----------------------------------------------------------------
        # ВКЛАДКА 1: ГЛАВНЫЙ ЭКРАН ВЫБОРА РОБОТА И КНОПКА GO
        # -----------------------------------------------------------------
        if menu_tab == "PLAY":
            screen.blit(font_title.render("ВЫБОР РОБОТА ДЛЯ ЗАПУСКА", True, (230, 235, 245)), (work_x, 20))
            card_w, card_h = 165, 235
            for i, r_cfg in enumerate(saved_robots[:4]):
                cx = work_x + i * (card_w + 15)
                cy = 75
                c_rect = pygame.Rect(cx, cy, card_w, card_h)
                is_sel = (active_robot_idx == i)
                if c_rect.collidepoint(mouse_pos) and mouse_clicked:
                    active_robot_idx = i

                pygame.draw.rect(screen, (34, 42, 54), c_rect, border_radius=8)
                r_img = render_robot_config_surface(r_cfg, 0.78)
                screen.blit(r_img, r_img.get_rect(center=(cx + card_w // 2, cy + 82)))
                t_name = font_card.render(r_cfg["name"][:16], True, (235, 240, 245))
                screen.blit(t_name, t_name.get_rect(center=(cx + card_w // 2, cy + 170)))

                chk = pygame.Rect(cx + card_w // 2 - 13, cy + 195, 26, 26)
                pygame.draw.rect(screen, (20, 25, 32), chk, border_radius=4)
                if is_sel:
                    pygame.draw.rect(screen, (46, 204, 113), c_rect, 3, border_radius=8)
                    pygame.draw.rect(screen, (46, 204, 113), chk, border_radius=4)
                    pygame.draw.lines(screen, (255, 255, 255), False, [(chk.x + 5, chk.y + 13), (chk.x + 11, chk.y + 19), (chk.x + 21, chk.y + 7)], 3)

            info_box = pygame.Rect(work_x, 340, 680, 140)
            pygame.draw.rect(screen, (28, 34, 45), info_box, border_radius=8)
            screen.blit(font_card.render(f"Активный робот: {saved_robots[active_robot_idx]['name']}", True, (46, 204, 113)), (work_x + 20, 360))
            screen.blit(font_card.render(f"Активный пульт: {saved_remotes[active_remote_idx]['name']}", True, (52, 152, 219)), (work_x + 20, 395))
            screen.blit(font_card.render(f"Активное поле: {saved_fields[active_field_idx]['name']}", True, (230, 126, 34)), (work_x + 20, 430))

            btn_go = pygame.Rect(SCR_W - 230, SCR_H - 85, 205, 62)
            pulse = int(math.sin(pygame.time.get_ticks() * 0.006) * 15)
            pygame.draw.rect(screen, (36, min(255, 175 + pulse), 78), btn_go, border_radius=6)
            shim = pygame.Surface((btn_go.w, btn_go.h), pygame.SRCALPHA)
            go_shimmer_x = (go_shimmer_x + 4.5) % (btn_go.w + 140)
            sx = go_shimmer_x - 70
            pygame.draw.polygon(shim, (255, 255, 255, 75), [(sx, 0), (sx + 35, 0), (sx + 10, btn_go.h), (sx - 25, btn_go.h)])
            screen.blit(shim, btn_go.topleft)
            pygame.draw.rect(screen, (130, 255, 170), btn_go, 2, border_radius=6)
            g_t = font_btn.render("GO", True, (255, 255, 255))
            screen.blit(g_t, g_t.get_rect(center=btn_go.center))

            if btn_go.collidepoint(mouse_pos) and mouse_clicked:
                game_state = "LOADING"
                load_start_ticks = pygame.time.get_ticks()

        # -----------------------------------------------------------------
        # ВКЛАДКА 2: КОНСТРУКТОР РОБОТА (TINKERCAD STYLE)
        # -----------------------------------------------------------------
        # ВКЛАДКА 2: КОНСТРУКТОР РОБОТА (TINKERCAD STYLE)
        # -----------------------------------------------------------------
        elif menu_tab == "CFG_ROBOT":
            screen.blit(font_title.render("КОНСТРУКТОР РОБОТА // TINKERCAD WORKPLANE", True, (230, 235, 245)), (work_x, 15))

            # СЛЕВА: Блок 1 (Моторы) и Блок 2 (Колеса: обычное и омни)
            left_panel = pygame.Rect(work_x, 60, 210, 510)
            pygame.draw.rect(screen, (30, 37, 48), left_panel, border_radius=8)

            screen.blit(font_card.render("1. МОТОРЫ (Перенос)", True, (240, 195, 20)), (work_x + 15, 72))
            btn_add_motor = pygame.Rect(work_x + 15, 102, 180, 48)
            pygame.draw.rect(screen, (45, 56, 72), btn_add_motor, border_radius=6)
            pygame.draw.rect(screen, (240, 195, 20), (work_x + 25, 114, 34, 22), border_radius=3)
            screen.blit(font_card.render("+ Мотор DC", True, (255, 255, 255)), (work_x + 70, 116))
            if btn_add_motor.collidepoint(mouse_pos) and mouse_clicked and len(draft_robot["motors"]) < 8:
                new_id = len(draft_robot["motors"]) + 1
                draft_robot["motors"].append({"id": new_id, "x": 0, "y": -44 if new_id % 2 == 1 else 44, "wheel": "none"})
                selected_draft_motor = len(draft_robot["motors"]) - 1

            screen.blit(font_card.render("2. КОЛЕСА (На мотор)", True, (52, 152, 219)), (work_x + 15, 170))
            btn_w_norm = pygame.Rect(work_x + 15, 200, 180, 46)
            btn_w_omni = pygame.Rect(work_x + 15, 256, 180, 46)
            pygame.draw.rect(screen, (45, 56, 72), btn_w_norm, border_radius=6)
            pygame.draw.rect(screen, (45, 56, 72), btn_w_omni, border_radius=6)
            screen.blit(font_card.render("Обычное колесо", True, (255, 255, 255)), (work_x + 30, 213))
            screen.blit(font_card.render("Омни-колесо", True, (130, 220, 255)), (work_x + 42, 269))

            if selected_draft_motor is not None and selected_draft_motor < len(draft_robot["motors"]):
                if btn_w_norm.collidepoint(mouse_pos) and mouse_clicked:
                    draft_robot["motors"][selected_draft_motor]["wheel"] = "normal"
                if btn_w_omni.collidepoint(mouse_pos) and mouse_clicked:
                    draft_robot["motors"][selected_draft_motor]["wheel"] = "omni"

                btn_del_m = pygame.Rect(work_x + 15, 325, 180, 38)
                pygame.draw.rect(screen, (180, 50, 50), btn_del_m, border_radius=6)
                screen.blit(font_card.render("Удалить мотор", True, (255, 255, 255)), (work_x + 35, 334))
                if btn_del_m.collidepoint(mouse_pos) and mouse_clicked:
                    draft_robot["motors"].pop(selected_draft_motor)
                    for idx_m, m_item in enumerate(draft_robot["motors"]):
                        m_item["id"] = idx_m + 1
                    selected_draft_motor = None

            # ПО ЦЕНТРУ: Рабочая сетка Tinkercad с платформой и перетаскиванием моторов
            workplane = pygame.Rect(work_x + 225, 60, 430, 510)
            draw_tinkercad_grid(screen, workplane)
            wp_center = workplane.center

            r_preview = render_robot_config_surface(draft_robot, 1.8)
            screen.blit(r_preview, r_preview.get_rect(center=wp_center))

            for idx_m, m in enumerate(draft_robot["motors"]):
                mx = wp_center[0] + int(m["x"] * 1.8)
                my = wp_center[1] + int(m["y"] * 1.8)
                m_box = pygame.Rect(mx - 26, my - 26, 52, 52)
                if selected_draft_motor == idx_m:
                    pygame.draw.rect(screen, (46, 204, 113), m_box, 2, border_radius=6)
                if m_box.collidepoint(mouse_pos) and mouse_clicked:
                    selected_draft_motor = idx_m
                    drag_motor_idx = idx_m

            if drag_motor_idx is not None and mouse_pressed:
                nx = int((mouse_pos[0] - wp_center[0]) / 1.8)
                ny = int((mouse_pos[1] - wp_center[1]) / 1.8)
                draft_robot["motors"][drag_motor_idx]["x"] = max(-65, min(65, nx))
                draft_robot["motors"][drag_motor_idx]["y"] = max(-65, min(65, ny))

            # СПРАВА: Выбор формы платформы (карточки с галочкой) и кнопка СОХРАНИТЬ
            right_panel = pygame.Rect(work_x + 670, 60, 220, 510)
            pygame.draw.rect(screen, (30, 37, 48), right_panel, border_radius=8)
            screen.blit(font_card.render("Форма платформы:", True, (220, 225, 235)), (right_panel.x + 15, 72))

            shapes_list = [("square", "Квадрат"), ("circle", "Круг"), ("rect", "Прямоуг.")]
            for s_i, (s_code, s_lbl) in enumerate(shapes_list):
                s_card = pygame.Rect(right_panel.x + 15, 105 + s_i * 95, 190, 82)
                is_sh = (draft_robot["shape"] == s_code)
                pygame.draw.rect(screen, (42, 52, 66), s_card, border_radius=6)
                if is_sh:
                    pygame.draw.rect(screen, (46, 204, 113), s_card, 3, border_radius=6)
                screen.blit(font_card.render(s_lbl, True, (255, 255, 255)), (s_card.x + 15, s_card.y + 30))
                chk_s = pygame.Rect(s_card.right - 36, s_card.y + 28, 24, 24)
                pygame.draw.rect(screen, (46, 204, 113) if is_sh else (20, 25, 32), chk_s, border_radius=4)
                if s_card.collidepoint(mouse_pos) and mouse_clicked:
                    draft_robot["shape"] = s_code

            btn_save_r = pygame.Rect(right_panel.x + 15, right_panel.bottom - 65, 190, 48)
            pygame.draw.rect(screen, (39, 174, 96), btn_save_r, border_radius=6)
            screen.blit(font_card.render("СОХРАНИТЬ РОБОТА", True, (255, 255, 255)), (btn_save_r.x + 16, btn_save_r.y + 14))
            if btn_save_r.collidepoint(mouse_pos) and mouse_clicked:
                new_cfg = copy.deepcopy(draft_robot)
                new_cfg["name"] = f"Кастом Робот #{len(saved_robots) + 1}"
                saved_robots.append(new_cfg)
                active_robot_idx = len(saved_robots) - 1
                show_toast(f"Сохранено: {new_cfg['name']}")

        # -----------------------------------------------------------------
        # ВКЛАДКА 3: КОНСТРУКТОР ПУЛЬТА (КНОПКИ И ПРИВЯЗКА К МОТОРАМ)
        # -----------------------------------------------------------------
        elif menu_tab == "CFG_REMOTE":
            screen.blit(font_title.render("КОНСТРУКТОР ПУЛЬТА // ПРИВЯЗКА К МОТОРАМ", True, (230, 235, 245)), (work_x, 15))

            # Слева: добавление кнопок на пульт
            l_rem = pygame.Rect(work_x, 60, 210, 510)
            pygame.draw.rect(screen, (30, 37, 48), l_rem, border_radius=8)
            btn_add_b = pygame.Rect(work_x + 15, 80, 180, 46)
            pygame.draw.rect(screen, (52, 152, 219), btn_add_b, border_radius=6)
            screen.blit(font_card.render("+ Кнопка пульта", True, (255, 255, 255)), (work_x + 32, 93))
            if btn_add_b.collidepoint(mouse_pos) and mouse_clicked and len(draft_remote["buttons"]) < 12:
                draft_remote["buttons"].append({"x": 140, "y": 80, "key": "f", "label": "F", "motor_id": 1, "dir": 1})
                selected_remote_btn = len(draft_remote["buttons"]) - 1

            # По центру: корпус пульта на сетке Tinkercad
            wp_rem = pygame.Rect(work_x + 225, 60, 430, 510)
            draw_tinkercad_grid(screen, wp_rem)
            pad_rect = pygame.Rect(wp_rem.centerx - 150, wp_rem.centery - 90, 300, 180)
            pygame.draw.rect(screen, (40, 46, 56), pad_rect, border_radius=18)
            pygame.draw.rect(screen, (90, 105, 125), pad_rect, 3, border_radius=18)

            for b_i, b_obj in enumerate(draft_remote["buttons"]):
                bx = pad_rect.x + b_obj["x"]
                by = pad_rect.y + b_obj["y"]
                b_r = pygame.Rect(bx - 20, by - 20, 40, 40)
                col_b = (46, 204, 113) if selected_remote_btn == b_i else (70, 82, 100)
                pygame.draw.rect(screen, col_b, b_r, border_radius=8)
                t_b = font_card.render(b_obj["label"], True, (255, 255, 255))
                screen.blit(t_b, t_b.get_rect(center=b_r.center))

                if b_r.collidepoint(mouse_pos) and mouse_clicked:
                    selected_remote_btn = b_i
                    drag_remote_btn = b_i
                    waiting_key_bind = False

            if drag_remote_btn is not None and mouse_pressed:
                draft_remote["buttons"][drag_remote_btn]["x"] = max(25, min(275, mouse_pos[0] - pad_rect.x))
                draft_remote["buttons"][drag_remote_btn]["y"] = max(25, min(155, mouse_pos[1] - pad_rect.y))

            # Справа: меню настройки выбранной кнопки пульта + СОХРАНИТЬ
            r_rem = pygame.Rect(work_x + 670, 60, 220, 510)
            pygame.draw.rect(screen, (30, 37, 48), r_rem, border_radius=8)
            if selected_remote_btn is not None and selected_remote_btn < len(draft_remote["buttons"]):
                sb = draft_remote["buttons"][selected_remote_btn]
                screen.blit(font_card.render("Настройка кнопки:", True, (46, 204, 113)), (r_rem.x + 15, 75))

                # Назначить клавишу клавиатуры
                b_key = pygame.Rect(r_rem.x + 15, 110, 190, 40)
                pygame.draw.rect(screen, (230, 126, 34) if waiting_key_bind else (50, 62, 80), b_key, border_radius=6)
                k_str = "Жмите клавишу..." if waiting_key_bind else f"Клавиша: [{sb['label']}]"
                screen.blit(font_card.render(k_str, True, (255, 255, 255)), (b_key.x + 20, b_key.y + 10))
                if b_key.collidepoint(mouse_pos) and mouse_clicked:
                    waiting_key_bind = True

                # Выбор мотора (Мотор 1, 2, 3, 4)
                screen.blit(font_hud.render("Привязать к мотору:", True, (200, 210, 225)), (r_rem.x + 15, 165))
                for m_num in range(1, 5):
                    bm = pygame.Rect(r_rem.x + 15 + (m_num - 1) * 48, 190, 42, 36)
                    pygame.draw.rect(screen, (46, 204, 113) if sb["motor_id"] == m_num else (50, 62, 80), bm, border_radius=5)
                    screen.blit(font_card.render(f"M{m_num}", True, (255, 255, 255)), (bm.x + 10, bm.y + 8))
                    if bm.collidepoint(mouse_pos) and mouse_clicked:
                        sb["motor_id"] = m_num

                # Направление вращения (Вперед / Назад)
                b_dir = pygame.Rect(r_rem.x + 15, 240, 190, 38)
                pygame.draw.rect(screen, (50, 62, 80), b_dir, border_radius=6)
                d_str = "Ход: ВПЕРЕД (+)" if sb["dir"] == 1 else "Ход: НАЗАД (-)"
                screen.blit(font_card.render(d_str, True, (255, 255, 255)), (b_dir.x + 22, b_dir.y + 9))
                if b_dir.collidepoint(mouse_pos) and mouse_clicked:
                    sb["dir"] *= -1

            btn_save_rem = pygame.Rect(r_rem.x + 15, r_rem.bottom - 65, 190, 48)
            pygame.draw.rect(screen, (39, 174, 96), btn_save_rem, border_radius=6)
            screen.blit(font_card.render("СОХРАНИТЬ ПУЛЬТ", True, (255, 255, 255)), (btn_save_rem.x + 22, btn_save_rem.y + 14))
            if btn_save_rem.collidepoint(mouse_pos) and mouse_clicked:
                new_rem = copy.deepcopy(draft_remote)
                new_rem["name"] = f"Пульт #{len(saved_remotes) + 1}"
                saved_remotes.append(new_rem)
                active_remote_idx = len(saved_remotes) - 1
                show_toast(f"Сохранено: {new_rem['name']}")

        # -----------------------------------------------------------------
        # ВКЛАДКА 4: КОНСТРУКТОР ПОЛЯ (СТЕНЫ И ДВИЖИМЫЕ КУБИКИ)
        # -----------------------------------------------------------------
        elif menu_tab == "CFG_FIELD":
            screen.blit(font_title.render("КОНСТРУКТОР ПОЛЯ // СТЕНЫ И КУБИКИ", True, (230, 235, 245)), (work_x, 15))

            l_fld = pygame.Rect(work_x, 60, 210, 510)
            pygame.draw.rect(screen, (30, 37, 48), l_fld, border_radius=8)

            btn_add_wall = pygame.Rect(work_x + 15, 80, 180, 46)
            btn_add_box = pygame.Rect(work_x + 15, 140, 180, 46)
            pygame.draw.rect(screen, (192, 57, 43), btn_add_wall, border_radius=6)
            pygame.draw.rect(screen, (230, 126, 34), btn_add_box, border_radius=6)
            screen.blit(font_card.render("+ Стена (Блок)", True, (255, 255, 255)), (work_x + 35, 93))
            screen.blit(font_card.render("+ Движимый куб", True, (255, 255, 255)), (work_x + 25, 153))

            if btn_add_wall.collidepoint(mouse_pos) and mouse_clicked:
                draft_field["objects"].append({"x": 450, "y": 250, "w": 80, "h": 30, "type": "wall"})
                selected_field_obj = len(draft_field["objects"]) - 1
            if btn_add_box.collidepoint(mouse_pos) and mouse_clicked:
                draft_field["objects"].append({"x": 500, "y": 300, "w": 42, "h": 42, "type": "box"})
                selected_field_obj = len(draft_field["objects"]) - 1

            # Смена типа выбранного объекта (Стена <-> Движимый) и поворот 90 град
            if selected_field_obj is not None and selected_field_obj < len(draft_field["objects"]):
                fo = draft_field["objects"][selected_field_obj]
                btn_tog = pygame.Rect(work_x + 15, 215, 180, 40)
                btn_rot = pygame.Rect(work_x + 15, 265, 180, 40)
                pygame.draw.rect(screen, (52, 73, 94), btn_tog, border_radius=6)
                pygame.draw.rect(screen, (52, 73, 94), btn_rot, border_radius=6)
                screen.blit(font_card.render("Тип: Стена/Куб", True, (255, 255, 255)), (work_x + 32, 225))
                screen.blit(font_card.render("Повернуть 90°", True, (255, 255, 255)), (work_x + 35, 275))
                if btn_tog.collidepoint(mouse_pos) and mouse_clicked:
                    fo["type"] = "box" if fo["type"] == "wall" else "wall"
                if btn_rot.collidepoint(mouse_pos) and mouse_clicked:
                    fo["w"], fo["h"] = fo["h"], fo["w"]

            btn_save_fld = pygame.Rect(work_x + 15, l_fld.bottom - 65, 180, 48)
            pygame.draw.rect(screen, (39, 174, 96), btn_save_fld, border_radius=6)
            screen.blit(font_card.render("СОХРАНИТЬ ПОЛЕ", True, (255, 255, 255)), (btn_save_fld.x + 22, btn_save_fld.y + 14))
            if btn_save_fld.collidepoint(mouse_pos) and mouse_clicked:
                new_fld = copy.deepcopy(draft_field)
                new_fld["name"] = f"Поле #{len(saved_fields) + 1}"
                saved_fields.append(new_fld)
                active_field_idx = len(saved_fields) - 1
                show_toast(f"Сохранено: {new_fld['name']}")

            # Мини-карта поля (масштаб 0.65 от реального 1000x600)
            map_rect = pygame.Rect(work_x + 230, 90, 650, 390)
            draw_tinkercad_grid(screen, map_rect)
            for f_i, obj in enumerate(draft_field["objects"]):
                ox = map_rect.x + int(obj["x"] * 0.65)
                oy = map_rect.y + int(obj["y"] * 0.65)
                ow = int(obj["w"] * 0.65)
                oh = int(obj["h"] * 0.65)
                o_r = pygame.Rect(ox, oy, ow, oh)
                col_o = (192, 57, 43) if obj["type"] == "wall" else (230, 126, 34)
                pygame.draw.rect(screen, col_o, o_r, border_radius=4)
                if selected_field_obj == f_i:
                    pygame.draw.rect(screen, (46, 204, 113), o_r, 2, border_radius=4)
                if o_r.collidepoint(mouse_pos) and mouse_clicked:
                    selected_field_obj = f_i
                    drag_field_obj = f_i

            if drag_field_obj is not None and mouse_pressed:
                nx = int((mouse_pos[0] - map_rect.x) / 0.65)
                ny = int((mouse_pos[1] - map_rect.y) / 0.65)
                draft_field["objects"][drag_field_obj]["x"] = max(0, min(920, nx))
                draft_field["objects"][drag_field_obj]["y"] = max(0, min(550, ny))

        # -----------------------------------------------------------------
        # ВКЛАДКА 5 (4-Я КНОПКА): МЕНЕДЖЕР ВСЕХ КОНФИГУРАЦИЙ (3 КОЛОНКИ)
        # -----------------------------------------------------------------
        elif menu_tab == "MANAGER":
            screen.blit(font_title.render("МЕНЕДЖЕР СБОРОК // ВЫБОР ПОЛЯ, РОБОТА И ПУЛЬТА", True, (230, 235, 245)), (work_x, 18))

            cols = [
                ("1. ПОЛЕ (Слева)", saved_fields, "field"),
                ("2. РОБОТ (Центр)", saved_robots, "robot"),
                ("3. ПУЛЬТ (Справа)", saved_remotes, "remote"),
            ]
            col_w = 280
            for c_i, (c_title, items_list, c_type) in enumerate(cols):
                cx = work_x + c_i * (col_w + 20)
                screen.blit(font_card.render(c_title, True, (160, 180, 205)), (cx, 65))

                for it_i, item in enumerate(items_list[:5]):
                    iy = 100 + it_i * 88
                    b_rect = pygame.Rect(cx, iy, col_w, 76)
                    if c_type == "field":
                        is_sel = (active_field_idx == it_i)
                    elif c_type == "robot":
                        is_sel = (active_robot_idx == it_i)
                    else:
                        is_sel = (active_remote_idx == it_i)

                    pygame.draw.rect(screen, (34, 42, 54), b_rect, border_radius=8)
                    screen.blit(font_card.render(item["name"], True, (240, 245, 250)), (cx + 15, iy + 27))

                    chk = pygame.Rect(b_rect.right - 40, iy + 24, 28, 28)
                    pygame.draw.rect(screen, (20, 25, 32), chk, border_radius=4)
                    if is_sel:
                        pygame.draw.rect(screen, (46, 204, 113), b_rect, 3, border_radius=8)
                        pygame.draw.rect(screen, (46, 204, 113), chk, border_radius=4)
                        pygame.draw.lines(screen, (255, 255, 255), False, [(chk.x + 6, chk.y + 14), (chk.x + 12, chk.y + 20), (chk.x + 22, chk.y + 8)], 3)

                    if b_rect.collidepoint(mouse_pos) and mouse_clicked:
                        if c_type == "field":
                            active_field_idx = it_i
                        elif c_type == "robot":
                            active_robot_idx = it_i
                        else:
                            active_remote_idx = it_i

        # Всплывающее уведомление о сохранении
        if toast_text and pygame.time.get_ticks() - toast_timer < 2000:
            t_surf = font_card.render(toast_text, True, (255, 255, 255))
            t_bg = pygame.Rect(SCR_W // 2 - 140, SCR_H - 45, 280, 32)
            pygame.draw.rect(screen, (39, 174, 96), t_bg, border_radius=6)
            screen.blit(t_surf, t_surf.get_rect(center=t_bg.center))

    # =====================================================================
    # ЭКРАН 2: ЗАГРУЗКА ПОЛЯ (2 СЕКУНДЫ)
    # =====================================================================
    elif game_state == "LOADING":
        screen.fill((18, 22, 29))
        elapsed = pygame.time.get_ticks() - load_start_ticks
        progress = min(1.0, elapsed / LOADING_DURATION_MS)

        r_cfg = saved_robots[active_robot_idx]
        big_r = render_robot_config_surface(r_cfg, 1.8)
        screen.blit(big_r, big_r.get_rect(center=(SCR_W // 2, SCR_H // 2 - 70)))

        load_txt = font_title.render("Загрузка конфигурации...", True, (235, 240, 245))
        screen.blit(load_txt, load_txt.get_rect(center=(SCR_W // 2, SCR_H // 2 + 75)))

        bar_w, bar_h = 460, 24
        bar_x, bar_y = (SCR_W - bar_w) // 2, SCR_H // 2 + 115
        pygame.draw.rect(screen, (32, 38, 48), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        fill_w = int((bar_w - 8) * progress)
        if fill_w > 0:
            pygame.draw.rect(screen, (46, 204, 113), (bar_x + 4, bar_y + 4, fill_w, bar_h - 8), border_radius=2)

        if elapsed >= LOADING_DURATION_MS:
            robot_pos = pygame.math.Vector2(SCR_W // 2, SCR_H // 2)
            robot_angle = 0.0
            live_field_objects = [
                {"rect": pygame.Rect(o["x"], o["y"], o["w"], o["h"]), "type": o["type"]}
                for o in saved_fields[active_field_idx]["objects"]
            ]
            game_state = "GAME"

    # =====================================================================
    # ЭКРАН 3: ИГРОВОЕ ПОЛЕ, ФИЗИКА КОЛЕС/ОМНИ-КОЛЕС И ТРАНСЛЯЦИЯ ПУЛЬТА
    # =====================================================================
    elif game_state == "GAME":
        screen.blit(bg_metal_floor, (0, 0))

        cur_robot_cfg = saved_robots[active_robot_idx]
        cur_remote_cfg = saved_remotes[active_remote_idx]

        # 1. Отрисовка объектов поля (стены и движимые кубы)
        for obj in live_field_objects:
            col_obj = (192, 57, 43) if obj["type"] == "wall" else (230, 126, 34)
            pygame.draw.rect(screen, col_obj, obj["rect"], border_radius=5)
            pygame.draw.rect(screen, (255, 255, 255), obj["rect"], 1, border_radius=5)

        # 2. Обработка ввода и физика каждого мотора
        active_keys_now = set()
        if window_active:
            if keyboard.is_pressed('m'):
                game_state = "MENU"
            if keyboard.is_pressed('z'):
                robot_pos = pygame.math.Vector2(SCR_W // 2, SCR_H // 2)
                robot_angle = 0.0
            for g_k in ('1', '2', '3'):
                if keyboard.is_pressed(g_k):
                    current_gear = g_k

            spd = SPEED_MODES[current_gear]
            forward_vec = pygame.math.Vector2(1, 0).rotate(-robot_angle)
            strafe_vec = pygame.math.Vector2(0, 1).rotate(-robot_angle)

            motor_power = {m["id"]: 0.0 for m in cur_robot_cfg["motors"]}
            tank_turn_cmd = 0.0

            for btn in cur_remote_cfg["buttons"]:
                try:
                    if keyboard.is_pressed(btn["key"]):
                        active_keys_now.add(btn["key"])
                        m_id = btn["motor_id"]
                        if m_id == 0:
                            for k_m in motor_power:
                                motor_power[k_m] += spd * btn["dir"]
                        elif m_id == -1:
                            tank_turn_cmd += spd * 0.75
                        elif m_id == -2:
                            tank_turn_cmd -= spd * 0.75
                        elif m_id in motor_power:
                            motor_power[m_id] += spd * btn["dir"]
                except Exception:
                    pass

            net_forward = 0.0
            net_strafe = 0.0
            net_torque = tank_turn_cmd

            for m in cur_robot_cfg["motors"]:
                if m["wheel"] == "none":
                    continue
                pwr = motor_power.get(m["id"], 0.0)
                if pwr != 0.0:
                    net_forward += pwr
                    net_torque += -pwr * (m["y"] / 45.0) * 0.65
                    if m["wheel"] == "omni":
                        net_strafe += pwr * (m["x"] / 60.0) * 0.55

            num_wheels = max(1, sum(1 for m in cur_robot_cfg["motors"] if m["wheel"] != "none"))
            delta_pos = (forward_vec * (net_forward / num_wheels)) + (strafe_vec * (net_strafe / num_wheels))
            robot_angle += net_torque / num_wheels

            next_pos = robot_pos + delta_pos
            robot_hitbox = pygame.Rect(0, 0, 96, 96)
            robot_hitbox.center = (round(next_pos.x), round(next_pos.y))

            blocked = False
            for obj in live_field_objects:
                if robot_hitbox.colliderect(obj["rect"]):
                    if obj["type"] == "wall":
                        blocked = True
                    elif obj["type"] == "box":
                        obj["rect"].x += round(delta_pos.x)
                        obj["rect"].y += round(delta_pos.y)
                        obj["rect"].clamp_ip(pygame.Rect(0, 0, SCR_W, SCR_H))

            if not blocked:
                robot_pos = next_pos
                robot_pos.x = max(50, min(SCR_W - 50, robot_pos.x))
                robot_pos.y = max(50, min(SCR_H - 50, robot_pos.y))

        # 3. Отрисовка робота на поле
        r_base_surf = render_robot_config_surface(cur_robot_cfg, 1.0)
        r_rot_surf = pygame.transform.rotate(r_base_surf, robot_angle)
        screen.blit(r_rot_surf, r_rot_surf.get_rect(center=(round(robot_pos.x), round(robot_pos.y))))

        # 4. ТРАНСЛЯЦИЯ ПУЛЬТА В ПРАВОМ НИЖНЕМ УГЛУ ПОЛЯ
        hud_pad = pygame.Rect(SCR_W - 315, SCR_H - 195, 300, 180)
        pad_surf = pygame.Surface((hud_pad.w, hud_pad.h), pygame.SRCALPHA)
        pygame.draw.rect(pad_surf, (20, 25, 34, 210), (0, 0, hud_pad.w, hud_pad.h), border_radius=14)
        pygame.draw.rect(pad_surf, (70, 90, 115, 240), (0, 0, hud_pad.w, hud_pad.h), 2, border_radius=14)
        screen.blit(pad_surf, hud_pad.topleft)

        for btn in cur_remote_cfg["buttons"]:
            bx = hud_pad.x + btn["x"]
            by = hud_pad.y + btn["y"]
            b_r = pygame.Rect(bx - 18, by - 18, 36, 36)
            is_pressed_now = btn["key"] in active_keys_now
            pygame.draw.rect(screen, (46, 204, 113) if is_pressed_now else (45, 55, 70), b_r, border_radius=7)
            t_b = font_hud.render(btn["label"], True, (255, 255, 255))
            screen.blit(t_b, t_b.get_rect(center=b_r.center))

        # Верхняя строка статуса
        top_hud = font_hud.render(
            f"Робот: {cur_robot_cfg['name']} | Пульт: {cur_remote_cfg['name']} | Скор: {current_gear} (1-3) | [Z] Сброс | [M] Меню",
            True, (210, 220, 235)
        )
        screen.blit(top_hud, (15, 15))

    # Выход по двойному ESC при активном окне
    now = pygame.time.get_ticks()
    if window_active and (now - last_key_time > 250):
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