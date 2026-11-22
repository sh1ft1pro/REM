import os
import sys
import json
import math
import copy
import random
import pygame
import serial
import serial.tools.list_ports

# =========================================================================
# 1. ИНИЦИАЛИЗАЦИЯ
# =========================================================================
pygame.init()
pygame.font.init()

SCR_W, SCR_H = 1000, 600
screen = pygame.display.set_mode((SCR_W, SCR_H))
pygame.display.set_caption("Robot Emulator MODIFICATED")

try:
    icon = pygame.image.load("icon_new.png")
    pygame.display.set_icon(icon)
except Exception:
    pass

engine_cvars = {
    "r_mode_3d": False,
    "r_antialiasing": True,
    "r_hd_supersample": True,
    "r_pbr_lighting": True,
    "r_shadows": True,
    "r_fog": True,
    "r_fog_density": 0.0014,
    "r_fov": 540.0,
    "cl_showfps": True,
    "sv_maxspeed": 1.0,
    "fps_max": 0,
    "snap_slots": True,   # <-- НОВОЕ: магнитные слоты вкл/выкл
}

# =========================================================================
# 2. МАТЕРИАЛЫ
# =========================================================================
class PBRMaterial:
    def __init__(self, name, albedo, metallic=0.0, roughness=0.5, specular_power=32.0):
        self.name = name
        self.albedo = albedo
        self.metallic = metallic
        self.roughness = roughness
        self.specular_power = specular_power

MATERIALS = {
    "sand":    PBRMaterial("Песок",    (214, 186, 130), 0.0, 0.92, 8.0),
    "brick":   PBRMaterial("Кирпич",   (168, 68, 56),   0.0, 0.78, 16.0),
    "metal":   PBRMaterial("Металл",   (125, 136, 150), 0.82, 0.35, 48.0),
    "steel":   PBRMaterial("Сталь",    (188, 198, 212), 0.95, 0.18, 96.0),
    "rubber":  PBRMaterial("Резина",   (32, 35, 40),    0.0, 0.85, 12.0),
    "brass":   PBRMaterial("Латунь",   (235, 185, 30),  0.90, 0.25, 64.0),
    "chassis": PBRMaterial("Алюминий", (185, 208, 230), 0.75, 0.30, 54.0),
    "beacon":  PBRMaterial("Индикатор",(240, 65, 65),   0.20, 0.20, 72.0),
    "roller":  PBRMaterial("Ролик",    (60, 65, 75),    0.4,  0.55, 24.0),
}

def generate_material_floor_surface(mat_key, w, h):
    surf = pygame.Surface((w, h))
    mat = MATERIALS.get(mat_key, MATERIALS["metal"])
    base = mat.albedo
    surf.fill(base)
    rng = random.Random(42)
    if mat_key == "sand":
        for _ in range(4500):
            px, py = rng.randint(0, w - 1), rng.randint(0, h - 1)
            delta = rng.randint(-18, 18)
            col = tuple(max(0, min(255, c + delta)) for c in base)
            surf.set_at((px, py), col)
        for gy in range(0, h, 40):
            pygame.draw.arc(surf, (196, 168, 114), (-20, gy, w + 40, 28), 0, math.pi, 1)
    elif mat_key == "brick":
        bw, bh = 50, 25
        for row, y in enumerate(range(0, h, bh)):
            off = (bw // 2) if row % 2 else 0
            pygame.draw.line(surf, (110, 105, 100), (0, y), (w, y), 2)
            for x in range(-bw, w + bw, bw):
                bx = x + off
                shade = rng.randint(-14, 14)
                b_col = tuple(max(0, min(255, c + shade)) for c in base)
                pygame.draw.rect(surf, b_col, (bx + 2, y + 2, bw - 4, bh - 4))
                pygame.draw.line(surf, (110, 105, 100), (bx, y), (bx, y + bh), 2)
    elif mat_key == "steel":
        for gx in range(0, w, 100):
            pygame.draw.line(surf, (160, 170, 185), (gx, 0), (gx, h), 2)
        for gy in range(0, h, 100):
            pygame.draw.line(surf, (160, 170, 185), (0, gy), (w, gy), 2)
        for gx in range(50, w, 100):
            for gy in range(50, h, 100):
                pygame.draw.line(surf, (210, 220, 232), (gx - 18, gy - 18), (gx + 18, gy + 18), 1)
                pygame.draw.circle(surf, (145, 155, 170), (gx - 42, gy - 42), 2)
    else:
        surf.fill((32, 36, 42))
        step = 28
        for row, y_pos in enumerate(range(0, h + step, step)):
            off = (step // 2) if row % 2 == 1 else 0
            for x_pos in range(-step, w + step, step):
                cx, cy = x_pos + off, y_pos
                pts = ([(cx - 6, cy - 2), (cx - 2, cy - 6), (cx + 6, cy + 2), (cx + 2, cy + 6)]
                       if ((x_pos // step) + row) % 2 == 0 else
                       [(cx - 6, cy + 2), (cx + 2, cy - 6), (cx + 6, cy - 2), (cx - 2, cy + 6)])
                pygame.draw.polygon(surf, (52, 58, 68), pts)
        for gx in range(0, w, 100):
            pygame.draw.line(surf, (42, 47, 56), (gx, 0), (gx, h), 1)
        for gy in range(0, h, 100):
            pygame.draw.line(surf, (42, 47, 56), (0, gy), (w, gy), 1)
    return surf

floor_cache = {}
def get_floor_surface(mat_key):
    if mat_key not in floor_cache:
        floor_cache[mat_key] = generate_material_floor_surface(mat_key, SCR_W, SCR_H)
    return floor_cache[mat_key]

# =========================================================================
# 3. 3D-МЕШИ (только Mecanum-колёса)
# =========================================================================
class Mesh3D:
    def __init__(self, vertices, faces, material):
        self.vertices = vertices
        self.faces = faces
        self.material = material

    def transformed(self, tx=0.0, ty=0.0, tz=0.0, yaw_deg=0.0, pitch_deg=0.0):
        ry = math.radians(yaw_deg)
        rp = math.radians(pitch_deg)
        cy, sy = math.cos(ry), math.sin(ry)
        cp, sp = math.cos(rp), math.sin(rp)
        out = []
        for vx, vy, vz in self.vertices:
            y1 = vy * cp - vz * sp
            z1 = vy * sp + vz * cp
            x2 = vx * cy - z1 * sy
            z2 = vx * sy + z1 * cy
            out.append((x2 + tx, y1 + ty, z2 + tz))
        return Mesh3D(out, self.faces, self.material)

class MeshFactory:
    @staticmethod
    def create_box(cx, cy, cz, sx, sy, sz, material, yaw_deg=0.0):
        hx, hy, hz = sx * 0.5, sy * 0.5, sz * 0.5
        verts = [
            (-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
            (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz),
        ]
        faces = [(0, 1, 2, 3), (5, 4, 7, 6), (4, 0, 3, 7),
                 (1, 5, 6, 2), (4, 5, 1, 0), (3, 2, 6, 7)]
        return Mesh3D(verts, faces, material).transformed(cx, cy, cz, yaw_deg)

    @staticmethod
    def create_cylinder(cx, cy, cz, radius, height, segments, material, axis="y", yaw_deg=0.0):
        verts, faces = [], []
        hh = height * 0.5
        for i in range(segments):
            ang = 2.0 * math.pi * i / segments
            ca, sa = math.cos(ang) * radius, math.sin(ang) * radius
            if axis == "y":
                verts.append((ca, -hh, sa)); verts.append((ca, hh, sa))
            else:
                verts.append((ca, sa, -hh)); verts.append((ca, sa, hh))
        faces.append(tuple(i * 2 for i in range(segments)))
        faces.append(tuple(i * 2 + 1 for i in reversed(range(segments))))
        for i in range(segments):
            ni = (i + 1) % segments
            faces.append((i * 2, ni * 2, ni * 2 + 1, i * 2 + 1))
        return Mesh3D(verts, faces, material).transformed(cx, cy, cz, yaw_deg)

    @staticmethod
    def build_mecanum_meshes(r_cfg):
        """Сборка 3D-мешей: шасси + 4 Mecanum-колеса с роликами под 45°."""
        meshes = []
        sh = r_cfg.get("shape", "rect")
        if sh == "circle":
            meshes.append(MeshFactory.create_cylinder(0, 0, 0, 62, 10, 20, MATERIALS["chassis"], axis="y"))
        elif sh == "rect":
            meshes.append(MeshFactory.create_box(0, 0, 0, 146, 10, 92, MATERIALS["chassis"]))
        else:
            meshes.append(MeshFactory.create_box(0, 0, 0, 112, 10, 112, MATERIALS["chassis"]))
        meshes.append(MeshFactory.create_box(-15, -13, 0, 38, 8, 28, MATERIALS["metal"]))
        meshes.append(MeshFactory.create_box(42, -10, 0, 14, 8, 26, MATERIALS["beacon"]))

        for m in r_cfg.get("motors", []):
            mx, mz = m["x"], m["y"]
            ang = m.get("angle", 0)
            # Ступица
            meshes.append(MeshFactory.create_box(mx, 8, mz, 36, 18, 18, MATERIALS["brass"], ang))
            # Само колесо (цилиндр)
            meshes.append(MeshFactory.create_cylinder(mx, 8, mz, 24, 14, 16, MATERIALS["steel"], axis="z", yaw_deg=ang))
            # Ролики под 45° (знак диагонали зависит от квадранта)
            diag = 1 if (mx * mz) >= 0 else -1
            for r_i in range(6):
                ra = 2.0 * math.pi * r_i / 6.0
                rx = mx + math.cos(ra) * 23 * math.cos(math.radians(ang))
                ry = 8 + math.sin(ra) * 23
                rz = mz + math.cos(ra) * 23 * math.sin(math.radians(ang))
                roller = MeshFactory.create_box(0, 0, 0, 9, 6, 7, MATERIALS["roller"], yaw_deg=ang)
                meshes.append(roller.transformed(rx, ry, rz, pitch_deg=45.0 * diag))
        return meshes

class AuroraRenderer3D:
    def __init__(self):
        self.light_dir = self._norm((0.45, -0.82, 0.35))
        self.ambient = 0.28
        self.fog_color = (22, 27, 36)

    @staticmethod
    def _norm(v):
        l = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2) or 1.0
        return (v[0] / l, v[1] / l, v[2] / l)

    def shade_pbr(self, normal, view_dir, material, distance=0.0):
        if not engine_cvars["r_pbr_lighting"]:
            return material.albedo
        nx, ny, nz = normal
        lx, ly, lz = self.light_dir
        ndotl = max(0.0, nx * lx + ny * ly + nz * lz)
        hx, hy, hz = self._norm((lx + view_dir[0], ly + view_dir[1], lz + view_dir[2]))
        ndoth = max(0.0, nx * hx + ny * hy + nz * hz)
        spec_strength = (1.0 - material.roughness * 0.85) * (0.35 + 0.65 * material.metallic)
        spec = (ndoth ** material.specular_power) * spec_strength * 180.0
        diff = self.ambient + (1.0 - self.ambient) * ndotl * (1.0 - material.metallic * 0.35)
        r = material.albedo[0] * diff + spec * (0.4 + 0.6 * material.metallic)
        g = material.albedo[1] * diff + spec * (0.4 + 0.6 * material.metallic)
        b = material.albedo[2] * diff + spec * (0.4 + 0.6 * material.metallic)
        if engine_cvars["r_fog"] and distance > 40.0:
            fog_f = 1.0 - math.exp(-((distance - 40.0) * engine_cvars["r_fog_density"]) ** 2)
            fog_f = max(0.0, min(0.88, fog_f))
            r = r * (1.0 - fog_f) + self.fog_color[0] * fog_f
            g = g * (1.0 - fog_f) + self.fog_color[1] * fog_f
            b = b * (1.0 - fog_f) + self.fog_color[2] * fog_f
        return (int(max(0, min(255, r))), int(max(0, min(255, g))), int(max(0, min(255, b))))

    def render_showcase(self, surface, center_xy, meshes, rx, ry):
        if engine_cvars["r_shadows"]:
            sh_rect = pygame.Rect(0, 0, 260, 78)
            sh_rect.center = (center_xy[0], center_xy[1] + 74)
            sh_surf = pygame.Surface(sh_rect.size, pygame.SRCALPHA)
            pygame.draw.ellipse(sh_surf, (8, 10, 15, 135), (0, 0, sh_rect.w, sh_rect.h))
            surface.blit(sh_surf, sh_rect.topleft)
        cos_x, sin_x = math.cos(rx), math.sin(rx)
        cos_y, sin_y = math.cos(ry), math.sin(ry)
        render_polys = []
        for mesh in meshes:
            rot_v, proj_v = [], []
            for vx, vy, vz in mesh.vertices:
                x1 = vx * cos_y + vz * sin_y
                z1 = -vx * sin_y + vz * cos_y
                y2 = vy * cos_x - z1 * sin_x
                z2 = vy * sin_x + z1 * cos_x
                rot_v.append((x1, y2, z2))
                scale = 460.0 / (460.0 + z2)
                proj_v.append((center_xy[0] + x1 * scale * 1.65, center_xy[1] + y2 * scale * 1.65))
            for f_idx in mesh.faces:
                if len(f_idx) < 3:
                    continue
                p0, p1, p2 = rot_v[f_idx[0]], rot_v[f_idx[1]], rot_v[f_idx[2]]
                ux, uy, uz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
                vx, vy, vz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]
                nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
                normal = self._norm((nx, ny, nz))
                if normal[2] > 0.25:
                    continue
                avg_z = sum(rot_v[i][2] for i in f_idx) / len(f_idx)
                col = self.shade_pbr(normal, (0.0, 0.0, -1.0), mesh.material, distance=0.0)
                render_polys.append((avg_z, [proj_v[i] for i in f_idx], col))
        render_polys.sort(key=lambda item: item[0], reverse=True)
        for _, pts, col in render_polys:
            pygame.draw.polygon(surface, col, pts)
            if engine_cvars["r_antialiasing"]:
                pygame.draw.aalines(surface, (18, 22, 28), True, pts)
            else:
                pygame.draw.polygon(surface, (18, 22, 28), pts, 1)

    def render_first_person_scene(self, surface, r_pos, r_ang_deg, field_objs, floor_mat_key):
        w, h = surface.get_size()
        horizon = h // 2
        floor_mat = MATERIALS.get(floor_mat_key, MATERIALS["metal"])
        pygame.draw.rect(surface, (20, 25, 34), (0, 0, w, horizon))
        strips = 24
        for s_i in range(strips):
            t0 = s_i / strips
            t1 = (s_i + 1) / strips
            y0 = int(horizon + (h - horizon) * (t0 ** 1.4))
            y1 = int(horizon + (h - horizon) * (t1 ** 1.4)) + 1
            dist_est = (1.0 - t0) * 900.0
            col = self.shade_pbr((0.0, -1.0, 0.0), (0.0, -0.4, -0.9), floor_mat, distance=dist_est)
            pygame.draw.rect(surface, col, (0, y0, w, max(1, y1 - y0)))
        rad_ang = math.radians(-r_ang_deg)
        fwd_x, fwd_y = math.cos(rad_ang), math.sin(rad_ang)
        right_x, right_y = -fwd_y, fwd_x
        fov_scale = engine_cvars["r_fov"]
        grid_step = 100
        start_gx = int((r_pos.x - 800) // grid_step) * grid_step
        start_gy = int((r_pos.y - 800) // grid_step) * grid_step
        dot_col = tuple(min(255, int(c * 1.25)) for c in floor_mat.albedo)
        for gx in range(start_gx, start_gx + 1700, grid_step):
            for gy in range(start_gy, start_gy + 1700, grid_step):
                dx, dy = gx - r_pos.x, gy - r_pos.y
                cam_z = dx * fwd_x + dy * fwd_y
                cam_x = dx * right_x + dy * right_y
                if cam_z > 25:
                    sx = w // 2 + (cam_x / cam_z) * fov_scale
                    sy = horizon + (38.0 / cam_z) * fov_scale
                    if 0 <= sx < w and horizon <= sy < h:
                        pygame.draw.circle(surface, dot_col, (int(sx), int(sy)), 2)
        wall_segments = [
            ((0, 0), (SCR_W, 0), (0.0, 0.0, 1.0), MATERIALS["steel"], 78),
            ((SCR_W, 0), (SCR_W, SCR_H), (-1.0, 0.0, 0.0), MATERIALS["steel"], 78),
            ((SCR_W, SCR_H), (0, SCR_H), (0.0, 0.0, -1.0), MATERIALS["steel"], 78),
            ((0, SCR_H), (0, 0), (1.0, 0.0, 0.0), MATERIALS["steel"], 78),
        ]
        for obj in field_objs:
            r = obj["rect"]
            mat_key = obj.get("mat", "brick")
            mat = MATERIALS.get(mat_key, MATERIALS["brick"])
            wh = 72 if obj["type"] == "wall" else 44
            wall_segments.append(((r.left, r.top), (r.right, r.top), (0.0, 0.0, -1.0), mat, wh))
            wall_segments.append(((r.right, r.top), (r.right, r.bottom), (1.0, 0.0, 0.0), mat, wh))
            wall_segments.append(((r.right, r.bottom), (r.left, r.bottom), (0.0, 0.0, 1.0), mat, wh))
            wall_segments.append(((r.left, r.bottom), (r.left, r.top), (-1.0, 0.0, 0.0), mat, wh))
        polys_3d = []
        near_z = 12.0
        for (x1, y1), (x2, y2), normal, mat, wall_h in wall_segments:
            dx1, dy1 = x1 - r_pos.x, y1 - r_pos.y
            dx2, dy2 = x2 - r_pos.x, y2 - r_pos.y
            z1 = dx1 * fwd_x + dy1 * fwd_y
            xc1 = dx1 * right_x + dy1 * right_y
            z2 = dx2 * fwd_x + dy2 * fwd_y
            xc2 = dx2 * right_x + dy2 * right_y
            if z1 < near_z and z2 < near_z:
                continue
            if z1 < near_z:
                t = (near_z - z1) / (z2 - z1) if z2 != z1 else 0.0
                xc1 += t * (xc2 - xc1); z1 = near_z
            elif z2 < near_z:
                t = (near_z - z2) / (z1 - z2) if z1 != z2 else 0.0
                xc2 += t * (xc1 - xc2); z2 = near_z
            sx1 = w // 2 + (xc1 / z1) * fov_scale
            sx2 = w // 2 + (xc2 / z2) * fov_scale
            bot1 = horizon + (38.0 / z1) * fov_scale
            top1 = horizon - ((wall_h - 38.0) / z1) * fov_scale
            bot2 = horizon + (38.0 / z2) * fov_scale
            top2 = horizon - ((wall_h - 38.0) / z2) * fov_scale
            avg_dist = (z1 + z2) * 0.5
            col = self.shade_pbr(normal, (-fwd_x, -0.2, -fwd_y), mat, distance=avg_dist)
            polys_3d.append((avg_dist, [(sx1, top1), (sx2, top2), (sx2, bot2), (sx1, bot1)], col))
        polys_3d.sort(key=lambda item: item[0], reverse=True)
        for dist, pts, col in polys_3d:
            if engine_cvars["r_shadows"] and dist < 500:
                sh_pts = [pts[3], pts[2], (pts[2][0] + 6, pts[2][1] + 5), (pts[3][0] - 6, pts[3][1] + 5)]
                pygame.draw.polygon(surface, (16, 19, 24), sh_pts)
            pygame.draw.polygon(surface, col, pts)
            if engine_cvars["r_antialiasing"]:
                pygame.draw.aalines(surface, (18, 22, 28), True, pts)
            else:
                pygame.draw.polygon(surface, (18, 22, 28), pts, 1)
        pygame.draw.polygon(surface, (52, 64, 80), [(w // 2 - 145, h), (w // 2 - 102, h - 56), (w // 2 + 102, h - 56), (w // 2 + 145, h)])
        pygame.draw.rect(surface, (235, 68, 68), (w // 2 - 26, h - 63, 52, 10), border_radius=3)

aurora_3d = AuroraRenderer3D()

# =========================================================================
# 4. СПАВН И MECANUM-КИНЕМАТИКА
# =========================================================================
def find_safe_spawn_position(field_objs, preferred_pos=(SCR_W // 2, SCR_H // 2)):
    hitbox_size = 96
    cx, cy = preferred_pos
    for radius in range(0, 460, 20):
        steps = 1 if radius == 0 else max(8, int(2 * math.pi * radius / 20))
        for s in range(steps):
            ang = 2.0 * math.pi * s / steps
            tx = int(cx + math.cos(ang) * radius)
            ty = int(cy + math.sin(ang) * radius)
            if not (55 <= tx <= SCR_W - 55 and 55 <= ty <= SCR_H - 55):
                continue
            test_rect = pygame.Rect(0, 0, hitbox_size, hitbox_size)
            test_rect.center = (tx, ty)
            if not any(test_rect.colliderect(o["rect"]) for o in field_objs):
                return pygame.math.Vector2(tx, ty)
    return pygame.math.Vector2(70, 70)

def compute_mecanum_kinematics(robot_cfg, motor_power):
    """
    Классическая Mecanum 4WD кинематика.
    Знак диагонали роликов: diag = +1 если (x*y) >= 0, иначе -1.
    v_fwd = (p1 + p2 + p3 + p4) / 4
    v_str = (-p1 + p2 + p3 - p4) / 4  (с учётом diag)
    omega = (-p1 + p2 - p3 + p4) / 4  (с учётом diag)
    """
    # Собираем силы по колёсам
    motors = [m for m in robot_cfg.get("motors", []) if m.get("wheel") == "mecanum"]
    if not motors:
        return 0.0, 0.0, 0.0

    # Сортируем: [FL, FR, RL, RR] по квадрантам
    # FL: x<0, y<0 | FR: x>0, y<0 | RL: x<0, y>0 | RR: x>0, y>0
    def quadrant(m):
        if m["x"] < 0 and m["y"] < 0: return 0  # FL
        if m["x"] > 0 and m["y"] < 0: return 1  # FR
        if m["x"] < 0 and m["y"] > 0: return 2  # RL
        return 3  # RR

    powers = [0.0, 0.0, 0.0, 0.0]
    diags = [1, 1, 1, 1]
    for m in motors:
        q = quadrant(m)
        powers[q] = motor_power.get(m["id"], 0.0)
        diags[q] = 1.0 if (m["x"] * m["y"]) >= 0 else -1.0

    p1, p2, p3, p4 = powers
    d1, d2, d3, d4 = diags

    v_fwd = (p1 + p2 + p3 + p4) / 4.0
    v_str = (-p1 * d1 + p2 * d2 + p3 * d3 - p4 * d4) / 4.0
    omega = (-p1 * d1 + p2 * d2 - p3 * d3 + p4 * d4) / 4.0
    return v_fwd, v_str, omega

# =========================================================================
# 5. КОНСОЛЬ РАЗРАБОТЧИКА (с командами привязки моторов)
# =========================================================================
class DeveloperConsole:
    def __init__(self):
        self.is_open = False
        self.input_text = ""
        self.logs = [
            "Mecanum Engine initialized.",
            "Нажмите [=] чтобы скрыть/открыть консоль. Введите 'help'.",
        ]
        self.font = pygame.font.SysFont("consolas", 15, bold=True)

    def log(self, msg):
        self.logs.append(str(msg))
        if len(self.logs) > 14:
            self.logs.pop(0)

    def handle_event(self, event, ctx):
        if event.type != pygame.KEYDOWN:
            return False
        if event.unicode == "=" or event.key == pygame.K_EQUALS:
            self.is_open = not self.is_open
            return True
        if not self.is_open:
            return False
        if event.key == pygame.K_RETURN:
            cmd = self.input_text.strip()
            self.input_text = ""
            if cmd:
                self.execute(cmd, ctx)
        elif event.key == pygame.K_BACKSPACE:
            self.input_text = self.input_text[:-1]
        elif event.unicode and event.unicode.isprintable():
            self.input_text += event.unicode
        return True

    def execute(self, raw_cmd, ctx):
        self.log(f"] {raw_cmd}")
        parts = raw_cmd.split()
        if not parts:
            return
        cmd = parts[0].lower()

        # --- Системные ---
        if cmd == "help":
            self.log("motor add <id> <x> <y> [angle]  - добавить Mecanum-мотор")
            self.log("motor del <id>                   - удалить мотор")
            self.log("motor move <id> <x> <y>          - переместить")
            self.log("motor angle <id> <deg>           - угол оси")
            self.log("motor list                       - список моторов")
            self.log("motor clear                      - удалить все")
            self.log("snap_slots 0/1                   - магнитные слоты")
            self.log("r_mode_3d 0/1 | r_fog 0/1 | r_pbr 0/1 | r_shadows 0/1")
            self.log("sv_maxspeed <0.2..4.0> | respawn | clear")
            return

        if cmd == "clear":
            self.logs.clear()
            return
        if cmd == "respawn":
            ctx["respawn"]()
            self.log("Робот перемещен в безопасную точку.")
            return
        if cmd == "snap_slots" and len(parts) > 1:
            engine_cvars["snap_slots"] = (parts[1] == "1")
            self.log(f"snap_slots = {int(engine_cvars['snap_slots'])}")
            return
        if cmd == "r_mode_3d" and len(parts) > 1:
            engine_cvars["r_mode_3d"] = (parts[1] == "1")
            self.log(f"r_mode_3d = {int(engine_cvars['r_mode_3d'])}")
            return
        if cmd == "r_fog" and len(parts) > 1:
            engine_cvars["r_fog"] = (parts[1] == "1")
            self.log(f"r_fog = {int(engine_cvars['r_fog'])}")
            return
        if cmd == "r_shadows" and len(parts) > 1:
            engine_cvars["r_shadows"] = (parts[1] == "1")
            self.log(f"r_shadows = {int(engine_cvars['r_shadows'])}")
            return
        if cmd == "r_pbr" and len(parts) > 1:
            engine_cvars["r_pbr_lighting"] = (parts[1] == "1")
            self.log(f"r_pbr_lighting = {int(engine_cvars['r_pbr_lighting'])}")
            return
        if cmd == "cl_showfps" and len(parts) > 1:
            engine_cvars["cl_showfps"] = (parts[1] == "1")
            self.log(f"cl_showfps = {int(engine_cvars['cl_showfps'])}")
            return
        if cmd == "fps_max" and len(parts) > 1:
            try:
                engine_cvars["fps_max"] = max(0, int(parts[1]))
                self.log(f"fps_max = {engine_cvars['fps_max']}")
            except ValueError:
                self.log("Ошибка: нужно целое число")
            return
        if cmd == "sv_maxspeed" and len(parts) > 1:
            try:
                engine_cvars["sv_maxspeed"] = max(0.2, min(4.0, float(parts[1])))
                self.log(f"sv_maxspeed = {engine_cvars['sv_maxspeed']}")
            except ValueError:
                self.log("Ошибка: нужно число")
            return

        # --- Привязка моторов ---
        if cmd == "motor":
            if len(parts) < 2:
                self.log("motor add|del|move|angle|list|clear ...")
                return
            sub = parts[1].lower()
            robot = ctx["robot"]

            if sub == "list":
                if not robot["motors"]:
                    self.log("Моторов нет.")
                for m in robot["motors"]:
                    self.log(f"  M{m['id']}: ({m['x']}, {m['y']}) angle={m.get('angle', 0)} wheel={m.get('wheel','none')}")
                return

            if sub == "clear":
                robot["motors"].clear()
                self.log("Все моторы удалены.")
                return

            if sub == "add":
                # motor add <id> <x> <y> [angle]
                if len(parts) < 5:
                    self.log("Синтаксис: motor add <id> <x> <y> [angle]")
                    return
                try:
                    m_id = int(parts[2])
                    mx = int(parts[3])
                    my = int(parts[4])
                    ang = int(parts[5]) if len(parts) > 5 else 0
                except ValueError:
                    self.log("Ошибка: id/x/y/angle должны быть целыми")
                    return
                if any(m["id"] == m_id for m in robot["motors"]):
                    self.log(f"Мотор M{m_id} уже существует.")
                    return
                robot["motors"].append({"id": m_id, "x": mx, "y": my, "wheel": "mecanum", "angle": ang})
                self.log(f"M{m_id} добавлен: ({mx}, {my}) angle={ang}")
                return

            if sub == "del":
                if len(parts) < 3:
                    self.log("Синтаксис: motor del <id>")
                    return
                try:
                    m_id = int(parts[2])
                except ValueError:
                    self.log("Ошибка: id должен быть целым")
                    return
                before = len(robot["motors"])
                robot["motors"] = [m for m in robot["motors"] if m["id"] != m_id]
                if len(robot["motors"]) < before:
                    self.log(f"M{m_id} удалён.")
                else:
                    self.log(f"M{m_id} не найден.")
                return

            if sub == "move":
                if len(parts) < 5:
                    self.log("Синтаксис: motor move <id> <x> <y>")
                    return
                try:
                    m_id = int(parts[2])
                    mx = int(parts[3])
                    my = int(parts[4])
                except ValueError:
                    self.log("Ошибка: нужны целые числа")
                    return
                for m in robot["motors"]:
                    if m["id"] == m_id:
                        m["x"], m["y"] = mx, my
                        self.log(f"M{m_id} -> ({mx}, {my})")
                        return
                self.log(f"M{m_id} не найден.")
                return

            if sub == "angle":
                if len(parts) < 4:
                    self.log("Синтаксис: motor angle <id> <deg>")
                    return
                try:
                    m_id = int(parts[2])
                    ang = int(parts[3])
                except ValueError:
                    self.log("Ошибка: нужны целые числа")
                    return
                for m in robot["motors"]:
                    if m["id"] == m_id:
                        m["angle"] = ang
                        self.log(f"M{m_id} angle = {ang}°")
                        return
                self.log(f"M{m_id} не найден.")
                return

            self.log(f"Неизвестная подкоманда: motor {sub}")
            return

        self.log(f"Неизвестная команда: '{cmd}'. Введите 'help'.")

    def draw(self, surface, fps_val, telemetry_str):
        if engine_cvars["cl_showfps"]:
            fps_surf = self.font.render(f"FPS: {int(fps_val)} | {telemetry_str}", True, (110, 245, 140))
            surface.blit(fps_surf, (SCR_W - fps_surf.get_width() - 14, 14))
        if not self.is_open:
            return
        panel = pygame.Surface((SCR_W, 300), pygame.SRCALPHA)
        panel.fill((14, 18, 24, 235))
        pygame.draw.line(panel, (230, 126, 34), (0, 298), (SCR_W, 298), 2)
        surface.blit(panel, (0, 0))
        header = self.font.render("MECANUM ENGINE // DEVELOPER CONSOLE", True, (230, 126, 34))
        surface.blit(header, (14, 8))
        for idx, line in enumerate(self.logs):
            t = self.font.render(line, True, (215, 225, 235))
            surface.blit(t, (14, 30 + idx * 16))
        pygame.draw.rect(surface, (28, 34, 44), (12, 268, SCR_W - 24, 24), border_radius=4)
        prompt = self.font.render(f"> {self.input_text}_", True, (255, 255, 255))
        surface.blit(prompt, (18, 271))

dev_console = DeveloperConsole()

# =========================================================================
# 6. ЗАСТАВКА И SERIAL
# =========================================================================
def play_intro():
    clock_intro = pygame.time.Clock()
    font_brand = pygame.font.SysFont("impact", 76)
    font_sub = pygame.font.SysFont("arial", 42, bold=True)
    t0 = pygame.time.get_ticks()
    while pygame.time.get_ticks() - t0 < 1200:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
        el = pygame.time.get_ticks() - t0
        screen.fill((0, 0, 0))
        txt = font_brand.render("Team BB", True, (215, 25, 25))
        alpha = int(255 * min(1.0, el / 250.0)) if el < 900 else int(255 * max(0.0, (1200 - el) / 300.0))
        txt.set_alpha(alpha)
        screen.blit(txt, txt.get_rect(center=(SCR_W // 2, SCR_H // 2)))
        pygame.display.flip()
        clock_intro.tick(60)
    t1 = pygame.time.get_ticks()
    while pygame.time.get_ticks() - t1 < 1200:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
        el = pygame.time.get_ticks() - t1
        prog = min(1.0, el / 1200.0)
        screen.fill((18, 22, 29))
        bar_w = int(640 * min(1.0, prog * 1.5))
        pygame.draw.rect(screen, (230, 126, 34), (SCR_W // 2 - bar_w // 2, SCR_H // 2 + 38, bar_w, 4))
        txt2 = font_sub.render("Robot emulator MODIFICATED", True, (240, 245, 255))
        txt2.set_alpha(int(255 * min(1.0, prog * 1.6)))
        screen.blit(txt2, txt2.get_rect(center=(SCR_W // 2, SCR_H // 2)))
        pygame.display.flip()
        clock_intro.tick(60)

play_intro()

ports = list(serial.tools.list_ports.comports())
ser_port = None
for p in ports:
    desc = (p.description or "").lower()
    if any(k in desc for k in ("arduino", "ch340", "ch341", "usb-serial", "usb")):
        ser_port = p.device
        break

SerialObj = None
if ser_port:
    try:
        SerialObj = serial.Serial(ser_port, baudrate=9600, timeout=0.1)
    except Exception:
        SerialObj = None

clock = pygame.time.Clock()
font_title = pygame.font.SysFont("arial", 23, bold=True)
font_card = pygame.font.SysFont("arial", 16, bold=True)
font_btn = pygame.font.SysFont("arial", 30, bold=True)
font_hud = pygame.font.SysFont("arial", 14, bold=True)

# =========================================================================
# 7. 2D-ОТРИСОВКА (только Mecanum-колёса)
# =========================================================================
def make_mecanum_wheel_surface(m_x, m_y, w=48, h=44, ss=2):
    """2D-спрайт Mecanum-колеса. Знак диагонали зависит от квадранта."""
    sw, sh = w * ss, h * ss
    surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
    wheel_y = 0 if m_y < 0 else sh - 17 * ss
    motor_y = 17 * ss if m_y < 0 else 4 * ss

    # Мотор (латунь)
    pygame.draw.rect(surf, (238, 190, 24), (5 * ss, motor_y, (w - 10) * ss, 20 * ss), border_radius=3 * ss)
    pygame.draw.rect(surf, (150, 110, 10), (5 * ss, motor_y, (w - 10) * ss, 20 * ss), 2 * ss, border_radius=3 * ss)
    # Ось
    pygame.draw.rect(surf, (175, 185, 200), (sw // 2 - 4 * ss, 2 * ss, 8 * ss, sh - 4 * ss), border_radius=2 * ss)

    # Корпус колеса
    pygame.draw.rect(surf, (155, 168, 185), (0, wheel_y, sw, 17 * ss), border_radius=3 * ss)
    pygame.draw.rect(surf, (95, 108, 125), (0, wheel_y, sw, 17 * ss), max(1, ss), border_radius=3 * ss)

    # Ролики под 45° — знак диагонали по квадранту
    diag = 1 if (m_x * m_y) >= 0 else -1
    for rx in range(4 * ss, (w - 6) * ss, 8 * ss):
        if diag > 0:
            pts = [(rx, wheel_y + 15 * ss), (rx + 5 * ss, wheel_y + 2 * ss),
                   (rx + 9 * ss, wheel_y + 2 * ss), (rx + 4 * ss, wheel_y + 15 * ss)]
        else:
            pts = [(rx, wheel_y + 2 * ss), (rx + 5 * ss, wheel_y + 15 * ss),
                   (rx + 9 * ss, wheel_y + 15 * ss), (rx + 4 * ss, wheel_y + 2 * ss)]
        pygame.draw.polygon(surf, (25, 28, 34), pts)
    return surf

def render_robot_config_surface(cfg, scale=1.0):
    ss = 2 if engine_cvars["r_hd_supersample"] else 1
    base_size = 190
    surf = pygame.Surface((base_size * ss, base_size * ss), pygame.SRCALPHA)
    cx, cy = (base_size * ss) // 2, (base_size * ss) // 2
    shape = cfg.get("shape", "square")
    font_m = pygame.font.SysFont("arial", 11 * ss, bold=True)

    if shape == "square":
        pygame.draw.rect(surf, (185, 208, 232, 230), (cx - 50 * ss, cy - 50 * ss, 100 * ss, 100 * ss), border_radius=12 * ss)
        pygame.draw.rect(surf, (145, 172, 200, 230), (cx - 38 * ss, cy - 38 * ss, 76 * ss, 76 * ss), border_radius=8 * ss)
        pygame.draw.rect(surf, (85, 112, 142), (cx - 50 * ss, cy - 50 * ss, 100 * ss, 100 * ss), 3 * ss, border_radius=12 * ss)
        pygame.draw.rect(surf, (245, 70, 70), (cx + 35 * ss, cy - 11 * ss, 10 * ss, 22 * ss), border_radius=3 * ss)
    elif shape == "circle":
        pygame.draw.circle(surf, (195, 218, 240, 230), (cx, cy), 56 * ss)
        pygame.draw.circle(surf, (150, 178, 205, 230), (cx, cy), 42 * ss)
        pygame.draw.circle(surf, (95, 125, 155), (cx, cy), 56 * ss, 3 * ss)
        pygame.draw.polygon(surf, (245, 70, 70), [(cx + 50 * ss, cy), (cx + 35 * ss, cy - 9 * ss), (cx + 35 * ss, cy + 9 * ss)])
    else:
        pygame.draw.rect(surf, (185, 208, 232, 230), (cx - 64 * ss, cy - 42 * ss, 128 * ss, 84 * ss), border_radius=12 * ss)
        pygame.draw.rect(surf, (145, 172, 200, 230), (cx - 50 * ss, cy - 30 * ss, 100 * ss, 60 * ss), border_radius=8 * ss)
        pygame.draw.rect(surf, (85, 112, 142), (cx - 64 * ss, cy - 42 * ss, 128 * ss, 84 * ss), 3 * ss, border_radius=12 * ss)
        pygame.draw.polygon(surf, (245, 70, 70), [(cx + 58 * ss, cy), (cx + 43 * ss, cy - 9 * ss), (cx + 43 * ss, cy + 9 * ss)])

    pygame.draw.rect(surf, (45, 55, 68), (cx - 18 * ss, cy - 14 * ss, 30 * ss, 28 * ss), border_radius=4 * ss)
    pygame.draw.circle(surf, (46, 204, 113), (cx - 8 * ss, cy - 6 * ss), 3 * ss)

    for m in cfg.get("motors", []):
        w_surf = make_mecanum_wheel_surface(m["x"], m["y"], ss=ss)
        m_rect = w_surf.get_rect(center=(cx + m["x"] * ss, cy + m["y"] * ss))
        surf.blit(w_surf, m_rect)
        pygame.draw.circle(surf, (20, 25, 35), m_rect.center, 11 * ss)
        pygame.draw.circle(surf, (240, 195, 20), m_rect.center, 11 * ss, max(1, ss))
        num_txt = font_m.render(f"M{m['id']}", True, (255, 255, 255))
        surf.blit(num_txt, num_txt.get_rect(center=m_rect.center))

    final_w = max(1, int(base_size * scale))
    final_h = max(1, int(base_size * scale))
    if engine_cvars["r_antialiasing"] or ss > 1:
        surf = pygame.transform.smoothscale(surf, (final_w, final_h))
    else:
        surf = pygame.transform.scale(surf, (final_w, final_h))
    return surf

# =========================================================================
# 8. КОНФИГУРАЦИИ
# =========================================================================
CONFIG_FILE = "emulator_configs.json"

DEFAULT_DATA = {
    "robots": [
        {"name": "Mecanum Pro 4WD", "shape": "rect",
         "motors": [
             {"id": 1, "x": 36, "y": -44, "wheel": "mecanum", "angle": 0},
             {"id": 2, "x": 36, "y": 44, "wheel": "mecanum", "angle": 0},
             {"id": 3, "x": -36, "y": -44, "wheel": "mecanum", "angle": 0},
             {"id": 4, "x": -36, "y": 44, "wheel": "mecanum", "angle": 0},
         ]},
        {"name": "Mecanum Компакт", "shape": "square",
         "motors": [
             {"id": 1, "x": 30, "y": -30, "wheel": "mecanum", "angle": 0},
             {"id": 2, "x": 30, "y": 30, "wheel": "mecanum", "angle": 0},
             {"id": 3, "x": -30, "y": -30, "wheel": "mecanum", "angle": 0},
             {"id": 4, "x": -30, "y": 30, "wheel": "mecanum", "angle": 0},
         ]},
        {"name": "Mecanum Круглый", "shape": "circle",
         "motors": [
             {"id": 1, "x": 40, "y": -40, "wheel": "mecanum", "angle": 0},
             {"id": 2, "x": 40, "y": 40, "wheel": "mecanum", "angle": 0},
             {"id": 3, "x": -40, "y": -40, "wheel": "mecanum", "angle": 0},
             {"id": 4, "x": -40, "y": 40, "wheel": "mecanum", "angle": 0},
         ]},
    ],
    "remotes": [
        {"name": "Стандарт Mecanum",
         "buttons": [
             {"x": 70, "y": 38, "key": "w", "label": "W", "motor_id": 0, "dir": 1},
             {"x": 70, "y": 112, "key": "s", "label": "S", "motor_id": 0, "dir": -1},
             {"x": 26, "y": 75, "key": "a", "label": "A", "motor_id": -1, "dir": 1},
             {"x": 114, "y": 75, "key": "d", "label": "D", "motor_id": -2, "dir": 1},
             {"x": 180, "y": 38, "key": "q", "label": "Q", "motor_id": -3, "dir": 1},
             {"x": 230, "y": 38, "key": "e", "label": "E", "motor_id": -4, "dir": 1},
             {"x": 180, "y": 112, "key": "u", "label": "U", "motor_id": 1, "dir": 1},
             {"x": 230, "y": 112, "key": "i", "label": "I", "motor_id": 2, "dir": 1},
         ]}
    ],
    "fields": [
        {"name": "Металлический ангар", "floor_mat": "metal", "objects": []},
        {"name": "Кирпичный полигон", "floor_mat": "sand",
         "objects": [
             {"x": 220, "y": 140, "w": 44, "h": 260, "type": "wall", "mat": "brick"},
             {"x": 740, "y": 180, "w": 44, "h": 260, "type": "wall", "mat": "brick"},
             {"x": 460, "y": 260, "w": 46, "h": 46, "type": "box", "mat": "steel"},
             {"x": 540, "y": 310, "w": 46, "h": 46, "type": "box", "mat": "metal"},
         ]}
    ]
}

def load_all_configs():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                robots = data.get("robots") or copy.deepcopy(DEFAULT_DATA["robots"])
                remotes = data.get("remotes") or copy.deepcopy(DEFAULT_DATA["remotes"])
                fields = data.get("fields") or copy.deepcopy(DEFAULT_DATA["fields"])
                # Миграция: все колёса -> mecanum
                for r in robots:
                    for m in r.get("motors", []):
                        m["wheel"] = "mecanum"
                return robots, remotes, fields
        except Exception:
            pass
    return (copy.deepcopy(DEFAULT_DATA["robots"]),
            copy.deepcopy(DEFAULT_DATA["remotes"]),
            copy.deepcopy(DEFAULT_DATA["fields"]))

def save_all_configs():
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"robots": saved_robots, "remotes": saved_remotes, "fields": saved_fields},
                      f, ensure_ascii=False, indent=2)
    except Exception as e:
        dev_console.log(f"Ошибка сохранения: {e}")

saved_robots, saved_remotes, saved_fields = load_all_configs()
active_robot_idx = 0
active_remote_idx = 0
active_field_idx = 0

MOTOR_SNAP_SLOTS = [
    (-36, -44), (0, -46), (36, -44),
    (-36, 44),  (0, 46),  (36, 44),
    (-36, -36), (36, -36), (-36, 36), (36, 36),
    (-48, 0),   (48, 0)
]

def snap_to_motor_slot(raw_x, raw_y, snap_radius=18):
    best_slot = None
    best_dist = snap_radius
    for sx, sy in MOTOR_SNAP_SLOTS:
        d = math.hypot(raw_x - sx, raw_y - sy)
        if d <= best_dist:
            best_dist = d
            best_slot = (sx, sy)
    if best_slot is not None:
        return best_slot
    return (round(raw_x / 6) * 6, round(raw_y / 6) * 6)

# =========================================================================
# 9. СОСТОЯНИЕ
# =========================================================================
programm_run = True
game_state = "MENU"
menu_tab = "HOME"

rot3d_x = 0.55
rot3d_y = -0.65
is_dragging_3d = False
last_mouse_3d = (0, 0)
cached_showcase_idx = -1
cached_showcase_meshes = []

draft_robot = copy.deepcopy(saved_robots[0])
selected_draft_motor = None
drag_motor_idx = None

draft_remote = copy.deepcopy(saved_remotes[0])
selected_remote_btn = None
drag_remote_btn = None
waiting_key_bind = False

draft_field = copy.deepcopy(saved_fields[0])
selected_field_obj = None
drag_field_obj = None

toast_text = ""
toast_timer = 0
go_shimmer_x = 0.0
load_start_ticks = 0
LOADING_DURATION_MS = 1400

robot_pos = pygame.math.Vector2(500, 300)
robot_angle = 0.0
live_field_objects = []
SPEED_MODES = {'1': 2.2, '2': 4.6, '3': 7.5}
current_gear = '2'
esc_press = 0
last_key_time = 0
mouse_was_pressed = False

def show_toast(msg):
    global toast_text, toast_timer
    toast_text = msg
    toast_timer = pygame.time.get_ticks()

def respawn_robot_safely():
    global robot_pos, robot_angle
    robot_pos = find_safe_spawn_position(live_field_objects, (SCR_W // 2, SCR_H // 2))
    robot_angle = 0.0

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
# 10. ГЛАВНЫЙ ЦИКЛ
# =========================================================================
while programm_run:
    dt = clock.tick(engine_cvars["fps_max"]) / 1000.0
    dt_scale = min(3.0, dt * 80.0) if dt > 0 else 1.0

    mouse_pos = pygame.mouse.get_pos()
    mouse_state = pygame.mouse.get_pressed()
    mouse_left = mouse_state[0]
    mouse_clicked = mouse_left and not mouse_was_pressed
    mouse_was_pressed = mouse_left
    window_active = pygame.key.get_focused()
    keys_pressed = pygame.key.get_pressed()

    ctx = {"respawn": respawn_robot_safely, "robot": draft_robot}

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            programm_run = False
            continue
        if dev_console.handle_event(event, ctx):
            continue
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            drag_motor_idx = None
            drag_remote_btn = None
            drag_field_obj = None
            is_dragging_3d = False
        elif event.type == pygame.KEYDOWN:
            if waiting_key_bind and selected_remote_btn is not None:
                if 0 <= selected_remote_btn < len(draft_remote["buttons"]):
                    key_name = pygame.key.name(event.key)
                    if key_name:
                        draft_remote["buttons"][selected_remote_btn]["key"] = key_name
                        draft_remote["buttons"][selected_remote_btn]["label"] = key_name.upper()[:4]
                waiting_key_bind = False
            elif event.key == pygame.K_ESCAPE:
                now = pygame.time.get_ticks()
                if now - last_key_time < 500:
                    esc_press += 1
                    if esc_press >= 2:
                        programm_run = False
                else:
                    esc_press = 1
                last_key_time = now

    if game_state == "MENU":
        screen.fill((22, 27, 36))
        nav_w = 74
        pygame.draw.rect(screen, (15, 19, 26), (0, 0, nav_w, SCR_H))
        pygame.draw.line(screen, (40, 48, 62), (nav_w, 0), (nav_w, SCR_H), 2)

        nav_buttons = [
            {"id": "HOME", "y": 18, "hint": "Главная"},
            {"id": "PLAY", "y": 94, "hint": "Запуск"},
            {"id": "CFG_ROBOT", "y": 170, "hint": "Робот"},
            {"id": "CFG_REMOTE", "y": 246, "hint": "Пульт"},
            {"id": "CFG_FIELD", "y": 322, "hint": "Поле"},
            {"id": "MANAGER", "y": 398, "hint": "Сборки"},
            {"id": "SETTINGS", "y": 510, "hint": "Настройки"},
        ]

        for nb in nav_buttons:
            r_btn = pygame.Rect(9, nb["y"], 56, 54)
            is_act = (menu_tab == nb["id"])
            is_hov = r_btn.collidepoint(mouse_pos)
            if is_hov and mouse_clicked and not dev_console.is_open:
                menu_tab = nb["id"]
                waiting_key_bind = False
                drag_motor_idx = None
                drag_remote_btn = None
                drag_field_obj = None
            if is_act:
                pygame.draw.rect(screen, (34, 44, 58), r_btn, border_radius=8)
                pygame.draw.rect(screen, (46, 204, 113), (0, nb["y"] + 8, 4, 38))
            elif is_hov:
                pygame.draw.rect(screen, (26, 33, 44), r_btn, border_radius=8)
            cx, cy = r_btn.center
            c_ico = (255, 255, 255) if is_act else (140, 155, 175)
            if nb["id"] == "HOME":
                pygame.draw.polygon(screen, c_ico, [(cx, cy - 13), (cx - 13, cy), (cx + 13, cy)], 2)
                pygame.draw.rect(screen, c_ico, (cx - 9, cy, 18, 12), 2)
            elif nb["id"] == "PLAY":
                pygame.draw.circle(screen, c_ico, (cx, cy), 16, 2)
                pygame.draw.polygon(screen, c_ico, [(cx - 4, cy - 7), (cx - 4, cy + 7), (cx + 8, cy)])
            elif nb["id"] == "CFG_ROBOT":
                pygame.draw.rect(screen, c_ico, (cx - 11, cy - 7, 22, 16), 2, border_radius=3)
                pygame.draw.line(screen, c_ico, (cx, cy - 7), (cx, cy - 14), 2)
                pygame.draw.circle(screen, c_ico, (cx - 5, cy), 2)
                pygame.draw.circle(screen, c_ico, (cx + 5, cy), 2)
            elif nb["id"] == "CFG_REMOTE":
                pygame.draw.rect(screen, c_ico, (cx - 14, cy - 9, 28, 18), 2, border_radius=5)
                pygame.draw.line(screen, c_ico, (cx - 8, cy - 3), (cx - 8, cy + 3), 2)
                pygame.draw.line(screen, c_ico, (cx - 11, cy), (cx - 5, cy), 2)
                pygame.draw.circle(screen, c_ico, (cx + 8, cy), 2)
            elif nb["id"] == "CFG_FIELD":
                pygame.draw.rect(screen, c_ico, (cx - 12, cy - 12, 24, 24), 2)
                pygame.draw.line(screen, c_ico, (cx - 12, cy), (cx + 12, cy), 1)
                pygame.draw.line(screen, c_ico, (cx, cy - 12), (cx, cy + 12), 1)
            elif nb["id"] == "MANAGER":
                for ox in (-11, -2, 7):
                    pygame.draw.rect(screen, c_ico, (cx + ox, cy - 10, 5, 20), 2)
            elif nb["id"] == "SETTINGS":
                pygame.draw.circle(screen, c_ico, (cx, cy), 10, 3)
                pygame.draw.circle(screen, c_ico, (cx, cy), 3)
            lbl = font_hud.render(nb["hint"], True, c_ico)
            screen.blit(lbl, lbl.get_rect(center=(cx, nb["y"] + 62)))

        work_x = nav_w + 22
        can_interact = not dev_console.is_open

        # HOME
        if menu_tab == "HOME":
            screen.blit(font_title.render("REM", True, (235, 240, 250)), (work_x, 22))
            screen.blit(font_card.render("ЛКМ — вращение | [=] — консоль | snap_slots вкл/выкл", True, (150, 165, 185)), (work_x, 56))
            view_area = pygame.Rect(work_x, 90, 580, 460)
            pygame.draw.rect(screen, (28, 34, 46), view_area, border_radius=12)
            pygame.draw.rect(screen, (48, 58, 76), view_area, 2, border_radius=12)
            if view_area.collidepoint(mouse_pos) and mouse_clicked and can_interact:
                is_dragging_3d = True
                last_mouse_3d = mouse_pos
            if is_dragging_3d and mouse_left:
                dx = mouse_pos[0] - last_mouse_3d[0]
                dy = mouse_pos[1] - last_mouse_3d[1]
                rot3d_y += dx * 0.012
                rot3d_x = max(-1.35, min(1.35, rot3d_x + dy * 0.012))
                last_mouse_3d = mouse_pos
            else:
                rot3d_y += 0.009 * dt_scale
            cur_r = saved_robots[active_robot_idx]
            if cached_showcase_idx != active_robot_idx:
                cached_showcase_meshes = MeshFactory.build_mecanum_meshes(cur_r)
                cached_showcase_idx = active_robot_idx
            aurora_3d.render_showcase(screen, view_area.center, cached_showcase_meshes, rot3d_x, rot3d_y)
            stat_box = pygame.Rect(work_x + 600, 90, 280, 355)
            pygame.draw.rect(screen, (30, 37, 48), stat_box, border_radius=12)
            screen.blit(font_card.render("АКТИВНАЯ СБОРКА:", True, (46, 204, 113)), (stat_box.x + 18, 108))
            screen.blit(font_card.render(f"Робот: {cur_r['name']}", True, (240, 245, 250)), (stat_box.x + 18, 144))
            screen.blit(font_card.render(f"Моторов: {len(cur_r['motors'])} шт.", True, (200, 210, 225)), (stat_box.x + 18, 178))
            screen.blit(font_card.render(f"Колёса: Mecanum", True, (130, 220, 255)), (stat_box.x + 18, 212))
            screen.blit(font_card.render(f"Пульт: {saved_remotes[active_remote_idx]['name']}", True, (200, 210, 225)), (stat_box.x + 18, 246))
            cur_f = saved_fields[active_field_idx]
            f_mat_name = MATERIALS.get(cur_f.get("floor_mat", "metal"), MATERIALS["metal"]).name
            screen.blit(font_card.render(f"Поле: {cur_f['name']}", True, (200, 210, 225)), (stat_box.x + 18, 280))
            screen.blit(font_card.render(f"Покрытие: {f_mat_name}", True, (230, 175, 95)), (stat_box.x + 18, 314))
            mode_str = "3D (От 1-го лица)" if engine_cvars["r_mode_3d"] else "2D (Вид сверху)"
            screen.blit(font_card.render(f"Режим: {mode_str}", True, (240, 195, 20)), (stat_box.x + 18, 352))

        # PLAY
        elif menu_tab == "PLAY":
            screen.blit(font_title.render("ВЫБОР РОБОТА", True, (230, 235, 245)), (work_x, 20))
            card_w, card_h = 165, 235
            for i, r_cfg in enumerate(saved_robots[:5]):
                cx = work_x + i * (card_w + 14)
                cy = 75
                c_rect = pygame.Rect(cx, cy, card_w, card_h)
                is_sel = (active_robot_idx == i)
                if c_rect.collidepoint(mouse_pos) and mouse_clicked and can_interact:
                    active_robot_idx = i
                    cached_showcase_idx = -1
                pygame.draw.rect(screen, (34, 42, 54), c_rect, border_radius=8)
                r_img = render_robot_config_surface(r_cfg, 0.78)
                screen.blit(r_img, r_img.get_rect(center=(cx + card_w // 2, cy + 82)))
                t_name = font_card.render(r_cfg["name"][:17], True, (235, 240, 245))
                screen.blit(t_name, t_name.get_rect(center=(cx + card_w // 2, cy + 170)))
                chk = pygame.Rect(cx + card_w // 2 - 13, cy + 195, 26, 26)
                pygame.draw.rect(screen, (20, 25, 32), chk, border_radius=4)
                if is_sel:
                    pygame.draw.rect(screen, (46, 204, 113), c_rect, 3, border_radius=8)
                    pygame.draw.rect(screen, (46, 204, 113), chk, border_radius=4)
                    pygame.draw.lines(screen, (255, 255, 255), False, [(chk.x + 5, chk.y + 13), (chk.x + 11, chk.y + 19), (chk.x + 21, chk.y + 7)], 3)
            info_box = pygame.Rect(work_x, 340, 640, 140)
            pygame.draw.rect(screen, (28, 34, 45), info_box, border_radius=8)
            screen.blit(font_card.render(f"Активный робот: {saved_robots[active_robot_idx]['name']}", True, (46, 204, 113)), (work_x + 20, 360))
            screen.blit(font_card.render(f"Активный пульт: {saved_remotes[active_remote_idx]['name']}", True, (52, 152, 219)), (work_x + 20, 395))
            screen.blit(font_card.render(f"Активное поле: {saved_fields[active_field_idx]['name']}", True, (230, 126, 34)), (work_x + 20, 430))

        # CFG_ROBOT
        elif menu_tab == "CFG_ROBOT":
            screen.blit(font_title.render("КОНСТРУКТОР РОБОТА // MECANUM", True, (230, 235, 245)), (work_x, 15))
            left_panel = pygame.Rect(work_x, 60, 210, 510)
            pygame.draw.rect(screen, (30, 37, 48), left_panel, border_radius=8)
            screen.blit(font_card.render("1. МОТОРЫ (только Mecanum)", True, (240, 195, 20)), (work_x + 15, 72))
            btn_add_motor = pygame.Rect(work_x + 15, 98, 180, 38)
            pygame.draw.rect(screen, (45, 56, 72), btn_add_motor, border_radius=6)
            screen.blit(font_card.render("+ Mecanum-мотор", True, (255, 255, 255)), (work_x + 32, 107))
            if btn_add_motor.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open and len(draft_robot["motors"]) < 8:
                used = {m["id"] for m in draft_robot["motors"]}
                new_id = next(i for i in range(1, 99) if i not in used)
                if engine_cvars["snap_slots"]:
                    slot_x, slot_y = MOTOR_SNAP_SLOTS[(new_id - 1) % len(MOTOR_SNAP_SLOTS)]
                else:
                    slot_x, slot_y = 0, 0
                draft_robot["motors"].append({"id": new_id, "x": slot_x, "y": slot_y, "wheel": "mecanum", "angle": 0})
                selected_draft_motor = len(draft_robot["motors"]) - 1

            screen.blit(font_card.render("2. МАГНИТНЫЕ СЛОТЫ", True, (52, 152, 219)), (work_x + 15, 148))
            btn_snap = pygame.Rect(work_x + 15, 174, 180, 40)
            snap_on = engine_cvars["snap_slots"]
            pygame.draw.rect(screen, (46, 204, 113) if snap_on else (48, 58, 74), btn_snap, border_radius=6)
            screen.blit(font_card.render(f"Слоты: {'ВКЛ' if snap_on else 'ВЫКЛ'}", True, (255, 255, 255)), (work_x + 50, 184))
            if btn_snap.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open:
                engine_cvars["snap_slots"] = not snap_on

            screen.blit(font_card.render("3. ДЕЙСТВИЯ", True, (230, 126, 34)), (work_x + 15, 226))
            if selected_draft_motor is not None and 0 <= selected_draft_motor < len(draft_robot["motors"]):
                cur_m = draft_robot["motors"][selected_draft_motor]
                screen.blit(font_card.render(f"Выбран: M{cur_m['id']} ({cur_m['x']}, {cur_m['y']})", True, (240, 195, 20)), (work_x + 15, 254))
                btn_ang = pygame.Rect(work_x + 15, 280, 180, 34)
                pygame.draw.rect(screen, (52, 73, 94), btn_ang, border_radius=6)
                screen.blit(font_card.render(f"Угол: {cur_m.get('angle', 0)}° (клик)", True, (255, 255, 255)), (work_x + 28, 288))
                if btn_ang.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open:
                    angles_cycle = [0, 45, 90, -45]
                    cur_a = cur_m.get("angle", 0)
                    next_idx = (angles_cycle.index(cur_a) + 1) % len(angles_cycle) if cur_a in angles_cycle else 0
                    cur_m["angle"] = angles_cycle[next_idx]
                btn_del_m = pygame.Rect(work_x + 15, 322, 180, 34)
                pygame.draw.rect(screen, (180, 50, 50), btn_del_m, border_radius=6)
                screen.blit(font_card.render("Удалить мотор", True, (255, 255, 255)), (work_x + 40, 330))
                if btn_del_m.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open:
                    draft_robot["motors"].pop(selected_draft_motor)
                    selected_draft_motor = None
                    drag_motor_idx = None

            # Подсказка про консоль
            hint_box = pygame.Rect(work_x + 15, 372, 180, 110)
            pygame.draw.rect(screen, (28, 34, 46), hint_box, border_radius=6)
            screen.blit(font_hud.render("Консоль [=]:", True, (230, 126, 34)), (hint_box.x + 8, hint_box.y + 6))
            screen.blit(font_hud.render("motor add 5 50 0", True, (200, 210, 225)), (hint_box.x + 8, hint_box.y + 28))
            screen.blit(font_hud.render("motor move 5 30 40", True, (200, 210, 225)), (hint_box.x + 8, hint_box.y + 46))
            screen.blit(font_hud.render("motor angle 5 45", True, (200, 210, 225)), (hint_box.x + 8, hint_box.y + 64))
            screen.blit(font_hud.render("motor list / motor del 5", True, (200, 210, 225)), (hint_box.x + 8, hint_box.y + 82))

            # Рабочая область
            workplane = pygame.Rect(work_x + 225, 60, 430, 510)
            draw_tinkercad_grid(screen, workplane)
            wp_center = workplane.center
            r_preview = render_robot_config_surface(draft_robot, 1.8)
            screen.blit(r_preview, r_preview.get_rect(center=wp_center))

            # Слоты рисуем ТОЛЬКО если включены
            if engine_cvars["snap_slots"]:
                for sx, sy in MOTOR_SNAP_SLOTS:
                    px = wp_center[0] + int(sx * 1.8)
                    py = wp_center[1] + int(sy * 1.8)
                    pygame.draw.circle(screen, (52, 152, 219), (px, py), 5, 2)

            for idx_m, m in enumerate(draft_robot["motors"]):
                mx = wp_center[0] + int(m["x"] * 1.8)
                my = wp_center[1] + int(m["y"] * 1.8)
                m_box = pygame.Rect(mx - 26, my - 26, 52, 52)
                if selected_draft_motor == idx_m:
                    pygame.draw.rect(screen, (46, 204, 113), m_box, 2, border_radius=6)
                if m_box.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open:
                    selected_draft_motor = idx_m
                    drag_motor_idx = idx_m
            if drag_motor_idx is not None and 0 <= drag_motor_idx < len(draft_robot["motors"]) and mouse_left and not dev_console.is_open:
                raw_x = (mouse_pos[0] - wp_center[0]) / 1.8
                raw_y = (mouse_pos[1] - wp_center[1]) / 1.8
                if engine_cvars["snap_slots"]:
                    snapped_x, snapped_y = snap_to_motor_slot(raw_x, raw_y)
                else:
                    snapped_x = round(raw_x / 6) * 6
                    snapped_y = round(raw_y / 6) * 6
                draft_robot["motors"][drag_motor_idx]["x"] = snapped_x
                draft_robot["motors"][drag_motor_idx]["y"] = snapped_y

            right_panel = pygame.Rect(work_x + 670, 60, 220, 510)
            pygame.draw.rect(screen, (30, 37, 48), right_panel, border_radius=8)
            screen.blit(font_card.render("Форма платформы:", True, (220, 225, 235)), (right_panel.x + 15, 72))
            for s_i, (s_code, s_lbl) in enumerate([("square", "Квадрат"), ("circle", "Круг"), ("rect", "Прямоуг.")]):
                s_card = pygame.Rect(right_panel.x + 15, 105 + s_i * 95, 190, 82)
                is_sh = (draft_robot["shape"] == s_code)
                pygame.draw.rect(screen, (42, 52, 66), s_card, border_radius=6)
                if is_sh:
                    pygame.draw.rect(screen, (46, 204, 113), s_card, 3, border_radius=6)
                screen.blit(font_card.render(s_lbl, True, (255, 255, 255)), (s_card.x + 15, s_card.y + 30))
                chk_s = pygame.Rect(s_card.right - 36, s_card.y + 28, 24, 24)
                pygame.draw.rect(screen, (46, 204, 113) if is_sh else (20, 25, 32), chk_s, border_radius=4)
                if s_card.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open:
                    draft_robot["shape"] = s_code
            btn_save_r = pygame.Rect(right_panel.x + 15, right_panel.bottom - 65, 190, 48)
            pygame.draw.rect(screen, (39, 174, 96), btn_save_r, border_radius=6)
            screen.blit(font_card.render("СОХРАНИТЬ В JSON", True, (255, 255, 255)), (btn_save_r.x + 18, btn_save_r.y + 14))
            if btn_save_r.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open:
                new_cfg = copy.deepcopy(draft_robot)
                new_cfg["name"] = f"Кастом #{len(saved_robots) + 1}"
                saved_robots.append(new_cfg)
                active_robot_idx = len(saved_robots) - 1
                cached_showcase_idx = -1
                save_all_configs()
                show_toast(f"Сохранено: {new_cfg['name']}")

        # CFG_REMOTE
        elif menu_tab == "CFG_REMOTE":
            screen.blit(font_title.render("КОНСТРУКТОР ПУЛЬТА", True, (230, 235, 245)), (work_x, 15))
            l_rem = pygame.Rect(work_x, 60, 210, 510)
            pygame.draw.rect(screen, (30, 37, 48), l_rem, border_radius=8)
            btn_add_b = pygame.Rect(work_x + 15, 80, 180, 46)
            pygame.draw.rect(screen, (52, 152, 219), btn_add_b, border_radius=6)
            screen.blit(font_card.render("+ Кнопка пульта", True, (255, 255, 255)), (work_x + 32, 93))
            if btn_add_b.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open and len(draft_remote["buttons"]) < 12:
                draft_remote["buttons"].append({"x": 140, "y": 80, "key": "f", "label": "F", "motor_id": 1, "dir": 1})
                selected_remote_btn = len(draft_remote["buttons"]) - 1
            btn_clear_b = pygame.Rect(work_x + 15, 140, 180, 40)
            pygame.draw.rect(screen, (75, 88, 108), btn_clear_b, border_radius=6)
            screen.blit(font_card.render("Очистить пульт", True, (255, 255, 255)), (work_x + 34, 150))
            if btn_clear_b.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open:
                draft_remote["buttons"].clear()
                selected_remote_btn = None
                drag_remote_btn = None
                waiting_key_bind = False

            wp_rem = pygame.Rect(work_x + 225, 60, 430, 510)
            draw_tinkercad_grid(screen, wp_rem)
            pad_rect = pygame.Rect(0, 0, 280, 160)
            pad_rect.center = wp_rem.center
            pygame.draw.rect(screen, (40, 46, 56), pad_rect, border_radius=18)
            pygame.draw.rect(screen, (90, 105, 125), pad_rect, 3, border_radius=18)

            for b_i, b_obj in enumerate(draft_remote["buttons"]):
                bx = pad_rect.x + b_obj["x"]
                by = pad_rect.y + b_obj["y"]
                b_r = pygame.Rect(bx - 20, by - 20, 40, 40)
                col_b = (46, 204, 113) if selected_remote_btn == b_i else (70, 82, 100)
                pygame.draw.rect(screen, col_b, b_r, border_radius=8)
                t_b = font_card.render(str(b_obj.get("label", "?")), True, (255, 255, 255))
                screen.blit(t_b, t_b.get_rect(center=b_r.center))
                if b_r.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open:
                    selected_remote_btn = b_i
                    drag_remote_btn = b_i
                    waiting_key_bind = False
            if drag_remote_btn is not None and 0 <= drag_remote_btn < len(draft_remote["buttons"]) and mouse_left and not dev_console.is_open:
                draft_remote["buttons"][drag_remote_btn]["x"] = max(25, min(255, mouse_pos[0] - pad_rect.x))
                draft_remote["buttons"][drag_remote_btn]["y"] = max(25, min(135, mouse_pos[1] - pad_rect.y))

            r_rem = pygame.Rect(work_x + 670, 60, 220, 510)
            pygame.draw.rect(screen, (30, 37, 48), r_rem, border_radius=8)
            if selected_remote_btn is not None and 0 <= selected_remote_btn < len(draft_remote["buttons"]):
                sb = draft_remote["buttons"][selected_remote_btn]
                screen.blit(font_card.render("Настройка кнопки:", True, (46, 204, 113)), (r_rem.x + 15, 75))
                b_key = pygame.Rect(r_rem.x + 15, 110, 190, 40)
                pygame.draw.rect(screen, (230, 126, 34) if waiting_key_bind else (50, 62, 80), b_key, border_radius=6)
                k_str = "Жмите клавишу..." if waiting_key_bind else f"Клавиша: [{sb.get('label', '?')}]"
                screen.blit(font_card.render(k_str, True, (255, 255, 255)), (b_key.x + 20, b_key.y + 10))
                if b_key.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open:
                    waiting_key_bind = True
                screen.blit(font_hud.render("Привязать к мотору:", True, (200, 210, 225)), (r_rem.x + 15, 165))
                for m_num in range(1, 5):
                    bm = pygame.Rect(r_rem.x + 15 + (m_num - 1) * 48, 190, 42, 36)
                    pygame.draw.rect(screen, (46, 204, 113) if sb.get("motor_id") == m_num else (50, 62, 80), bm, border_radius=5)
                    screen.blit(font_card.render(f"M{m_num}", True, (255, 255, 255)), (bm.x + 10, bm.y + 8))
                    if bm.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open:
                        sb["motor_id"] = m_num
                b_dir = pygame.Rect(r_rem.x + 15, 240, 190, 38)
                pygame.draw.rect(screen, (50, 62, 80), b_dir, border_radius=6)
                d_str = "Ход: ВПЕРЕД (+)" if sb.get("dir", 1) == 1 else "Ход: НАЗАД (-)"
                screen.blit(font_card.render(d_str, True, (255, 255, 255)), (b_dir.x + 22, b_dir.y + 9))
                if b_dir.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open:
                    sb["dir"] = -1 if sb.get("dir", 1) == 1 else 1
                btn_del_b = pygame.Rect(r_rem.x + 15, 292, 190, 36)
                pygame.draw.rect(screen, (180, 50, 50), btn_del_b, border_radius=6)
                screen.blit(font_card.render("Удалить кнопку", True, (255, 255, 255)), (btn_del_b.x + 30, btn_del_b.y + 8))
                if btn_del_b.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open:
                    draft_remote["buttons"].pop(selected_remote_btn)
                    selected_remote_btn = None
                    drag_remote_btn = None
                    waiting_key_bind = False
            btn_save_rem = pygame.Rect(r_rem.x + 15, r_rem.bottom - 65, 190, 48)
            pygame.draw.rect(screen, (39, 174, 96), btn_save_rem, border_radius=6)
            screen.blit(font_card.render("СОХРАНИТЬ В JSON", True, (255, 255, 255)), (btn_save_rem.x + 18, btn_save_rem.y + 14))
            if btn_save_rem.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open:
                new_rem = copy.deepcopy(draft_remote)
                new_rem["name"] = f"Пульт #{len(saved_remotes) + 1}"
                saved_remotes.append(new_rem)
                active_remote_idx = len(saved_remotes) - 1
                save_all_configs()
                show_toast(f"Сохранено: {new_rem['name']}")

        # CFG_FIELD
        elif menu_tab == "CFG_FIELD":
            screen.blit(font_title.render("КОНСТРУКТОР ПОЛЯ", True, (230, 235, 245)), (work_x, 15))
            l_fld = pygame.Rect(work_x, 60, 215, 510)
            pygame.draw.rect(screen, (30, 37, 48), l_fld, border_radius=8)
            btn_add_wall = pygame.Rect(work_x + 15, 74, 185, 40)
            btn_add_box = pygame.Rect(work_x + 15, 122, 185, 40)
            pygame.draw.rect(screen, (168, 68, 56), btn_add_wall, border_radius=6)
            pygame.draw.rect(screen, (125, 136, 150), btn_add_box, border_radius=6)
            screen.blit(font_card.render("+ Стена", True, (255, 255, 255)), (work_x + 55, 84))
            screen.blit(font_card.render("+ Куб", True, (255, 255, 255)), (work_x + 65, 132))
            if btn_add_wall.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open:
                draft_field["objects"].append({"x": 450, "y": 250, "w": 80, "h": 30, "type": "wall", "mat": "brick"})
                selected_field_obj = len(draft_field["objects"]) - 1
            if btn_add_box.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open:
                draft_field["objects"].append({"x": 500, "y": 300, "w": 42, "h": 42, "type": "box", "mat": "metal"})
                selected_field_obj = len(draft_field["objects"]) - 1
            screen.blit(font_hud.render("Материал пола:", True, (240, 195, 20)), (work_x + 15, 174))
            mat_keys = ["sand", "brick", "metal", "steel"]
            for m_i, mk in enumerate(mat_keys):
                bx_m = work_x + 15 + (m_i % 2) * 95
                by_m = 196 + (m_i // 2) * 34
                r_m = pygame.Rect(bx_m, by_m, 90, 28)
                is_cur_fm = (draft_field.get("floor_mat", "metal") == mk)
                pygame.draw.rect(screen, (46, 204, 113) if is_cur_fm else (48, 58, 74), r_m, border_radius=5)
                screen.blit(font_hud.render(MATERIALS[mk].name, True, (255, 255, 255)), (r_m.x + 14, r_m.y + 6))
                if r_m.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open:
                    draft_field["floor_mat"] = mk
            if selected_field_obj is not None and 0 <= selected_field_obj < len(draft_field["objects"]):
                fo = draft_field["objects"][selected_field_obj]
                screen.blit(font_hud.render("Материал объекта:", True, (130, 220, 255)), (work_x + 15, 272))
                for m_i, mk in enumerate(mat_keys):
                    bx_m = work_x + 15 + (m_i % 2) * 95
                    by_m = 292 + (m_i // 2) * 34
                    r_m = pygame.Rect(bx_m, by_m, 90, 28)
                    is_cur_om = (fo.get("mat", "brick") == mk)
                    pygame.draw.rect(screen, (52, 152, 219) if is_cur_om else (48, 58, 74), r_m, border_radius=5)
                    screen.blit(font_hud.render(MATERIALS[mk].name, True, (255, 255, 255)), (r_m.x + 14, r_m.y + 6))
                    if r_m.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open:
                        fo["mat"] = mk
                btn_rot = pygame.Rect(work_x + 15, 368, 185, 34)
                btn_del_o = pygame.Rect(work_x + 15, 408, 185, 34)
                pygame.draw.rect(screen, (52, 73, 94), btn_rot, border_radius=6)
                pygame.draw.rect(screen, (180, 50, 50), btn_del_o, border_radius=6)
                screen.blit(font_hud.render("Повернуть 90°", True, (255, 255, 255)), (btn_rot.x + 42, btn_rot.y + 9))
                screen.blit(font_hud.render("Удалить объект", True, (255, 255, 255)), (btn_del_o.x + 38, btn_del_o.y + 9))
                if btn_rot.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open:
                    fo["w"], fo["h"] = fo["h"], fo["w"]
                if btn_del_o.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open:
                    draft_field["objects"].pop(selected_field_obj)
                    selected_field_obj = None
                    drag_field_obj = None
            btn_save_fld = pygame.Rect(work_x + 15, l_fld.bottom - 56, 185, 44)
            pygame.draw.rect(screen, (39, 174, 96), btn_save_fld, border_radius=6)
            screen.blit(font_card.render("СОХРАНИТЬ В JSON", True, (255, 255, 255)), (btn_save_fld.x + 16, btn_save_fld.y + 12))
            if btn_save_fld.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open:
                new_fld = copy.deepcopy(draft_field)
                new_fld["name"] = f"Поле #{len(saved_fields) + 1}"
                saved_fields.append(new_fld)
                active_field_idx = len(saved_fields) - 1
                save_all_configs()
                show_toast(f"Сохранено: {new_fld['name']}")

            map_rect = pygame.Rect(work_x + 230, 90, 650, 390)
            fm_key = draft_field.get("floor_mat", "metal")
            fm_preview = pygame.transform.smoothscale(get_floor_surface(fm_key), (map_rect.w, map_rect.h))
            screen.blit(fm_preview, map_rect.topleft)
            pygame.draw.rect(screen, (95, 115, 140), map_rect, 2, border_radius=6)
            for f_i, obj in enumerate(draft_field["objects"]):
                ox = map_rect.x + int(obj["x"] * 0.65)
                oy = map_rect.y + int(obj["y"] * 0.65)
                ow = int(obj["w"] * 0.65)
                oh = int(obj["h"] * 0.65)
                o_r = pygame.Rect(ox, oy, ow, oh)
                m_obj = MATERIALS.get(obj.get("mat", "brick"), MATERIALS["brick"])
                pygame.draw.rect(screen, m_obj.albedo, o_r, border_radius=4)
                pygame.draw.rect(screen, (25, 30, 38), o_r, 1, border_radius=4)
                if selected_field_obj == f_i:
                    pygame.draw.rect(screen, (46, 204, 113), o_r, 2, border_radius=4)
                if o_r.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open:
                    selected_field_obj = f_i
                    drag_field_obj = f_i
            if drag_field_obj is not None and 0 <= drag_field_obj < len(draft_field["objects"]) and mouse_left and not dev_console.is_open:
                nx = round(int((mouse_pos[0] - map_rect.x) / 0.65) / 10) * 10
                ny = round(int((mouse_pos[1] - map_rect.y) / 0.65) / 10) * 10
                draft_field["objects"][drag_field_obj]["x"] = max(0, min(920, nx))
                draft_field["objects"][drag_field_obj]["y"] = max(0, min(550, ny))

        # MANAGER
        elif menu_tab == "MANAGER":
            screen.blit(font_title.render("МЕНЕДЖЕР СБОРОК", True, (230, 235, 245)), (work_x, 18))
            cols = [
                ("1. ПОЛЕ", saved_fields, "field"),
                ("2. РОБОТ", saved_robots, "robot"),
                ("3. ПУЛЬТ", saved_remotes, "remote"),
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
                    if b_rect.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open:
                        if c_type == "field":
                            active_field_idx = it_i
                        elif c_type == "robot":
                            active_robot_idx = it_i
                            cached_showcase_idx = -1
                        else:
                            active_remote_idx = it_i

        # SETTINGS
        elif menu_tab == "SETTINGS":
            screen.blit(font_title.render("НАСТРОЙКИ", True, (230, 235, 245)), (work_x, 20))
            toggles = [
                ("snap_slots", "Магнитные слоты в конструкторе (прилипание моторов)"),
                ("r_mode_3d", "Режим 3D-рендера (вид от 1-го лица)"),
                ("r_pbr_lighting", "PBR-освещение"),
                ("r_shadows", "Тени"),
                ("r_fog", "Туман"),
                ("r_antialiasing", "Сглаживание"),
                ("r_hd_supersample", "HD-суперсэмплинг"),
                ("cl_showfps", "Показывать FPS"),
            ]
            for idx_t, (cvar_key, label_txt) in enumerate(toggles):
                row_r = pygame.Rect(work_x, 68 + idx_t * 60, 660, 50)
                pygame.draw.rect(screen, (34, 42, 54), row_r, border_radius=8)
                screen.blit(font_card.render(label_txt, True, (240, 245, 250)), (row_r.x + 18, row_r.y + 15))
                chk = pygame.Rect(row_r.right - 46, row_r.y + 11, 28, 28)
                val = engine_cvars[cvar_key]
                pygame.draw.rect(screen, (46, 204, 113) if val else (20, 25, 32), chk, border_radius=5)
                if val:
                    pygame.draw.lines(screen, (255, 255, 255), False, [(chk.x + 6, chk.y + 14), (chk.x + 12, chk.y + 20), (chk.x + 22, chk.y + 8)], 3)
                if row_r.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open:
                    engine_cvars[cvar_key] = not engine_cvars[cvar_key]

        # GO
        if menu_tab in ("HOME", "PLAY", "MANAGER"):
            btn_go = pygame.Rect(SCR_W - 230, SCR_H - 85, 205, 62)
            pulse = int(math.sin(pygame.time.get_ticks() * 0.006) * 15)
            pygame.draw.rect(screen, (36, min(255, 175 + pulse), 78), btn_go, border_radius=6)
            shim = pygame.Surface((btn_go.w, btn_go.h), pygame.SRCALPHA)
            go_shimmer_x = (go_shimmer_x + 4.5 * dt_scale) % (btn_go.w + 140)
            sx = go_shimmer_x - 70
            pygame.draw.polygon(shim, (255, 255, 255, 75), [(sx, 0), (sx + 35, 0), (sx + 10, btn_go.h), (sx - 25, btn_go.h)])
            screen.blit(shim, btn_go.topleft)
            pygame.draw.rect(screen, (130, 255, 170), btn_go, 2, border_radius=6)
            g_t = font_btn.render("GO", True, (255, 255, 255))
            screen.blit(g_t, g_t.get_rect(center=btn_go.center))
            if btn_go.collidepoint(mouse_pos) and mouse_clicked and not dev_console.is_open:
                game_state = "LOADING"
                load_start_ticks = pygame.time.get_ticks()

        if toast_text and pygame.time.get_ticks() - toast_timer < 2000:
            t_surf = font_card.render(toast_text, True, (255, 255, 255))
            t_bg = pygame.Rect(SCR_W // 2 - 140, SCR_H - 45, 280, 32)
            pygame.draw.rect(screen, (39, 174, 96), t_bg, border_radius=6)
            screen.blit(t_surf, t_surf.get_rect(center=t_bg.center))

    elif game_state == "LOADING":
        screen.fill((18, 22, 29))
        elapsed = pygame.time.get_ticks() - load_start_ticks
        progress = min(1.0, elapsed / LOADING_DURATION_MS)
        r_cfg = saved_robots[active_robot_idx]
        big_r = render_robot_config_surface(r_cfg, 1.8)
        screen.blit(big_r, big_r.get_rect(center=(SCR_W // 2, SCR_H // 2 - 70)))
        load_txt = font_title.render("Загрузка сцены...", True, (235, 240, 245))
        screen.blit(load_txt, load_txt.get_rect(center=(SCR_W // 2, SCR_H // 2 + 75)))
        bar_w, bar_h = 460, 24
        bar_x, bar_y = (SCR_W - bar_w) // 2, SCR_H // 2 + 115
        pygame.draw.rect(screen, (32, 38, 48), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        fill_w = int((bar_w - 8) * progress)
        if fill_w > 0:
            pygame.draw.rect(screen, (46, 204, 113), (bar_x + 4, bar_y + 4, fill_w, bar_h - 8), border_radius=2)
        if elapsed >= LOADING_DURATION_MS:
            cur_fld = saved_fields[active_field_idx]
            live_field_objects = [
                {"rect": pygame.Rect(o["x"], o["y"], o["w"], o["h"]),
                 "type": o["type"],
                 "mat": o.get("mat", "brick" if o["type"] == "wall" else "metal")}
                for o in cur_fld.get("objects", [])
            ]
            robot_pos = find_safe_spawn_position(live_field_objects, (SCR_W // 2, SCR_H // 2))
            robot_angle = 0.0
            game_state = "GAME"

    elif game_state == "GAME":
        cur_robot_cfg = saved_robots[active_robot_idx]
        cur_remote_cfg = saved_remotes[active_remote_idx]
        cur_field_cfg = saved_fields[active_field_idx]
        floor_mat_key = cur_field_cfg.get("floor_mat", "metal")

        if engine_cvars["r_mode_3d"]:
            aurora_3d.render_first_person_scene(screen, robot_pos, robot_angle, live_field_objects, floor_mat_key)
        else:
            screen.blit(get_floor_surface(floor_mat_key), (0, 0))
            for obj in live_field_objects:
                mat_obj = MATERIALS.get(obj.get("mat", "brick"), MATERIALS["brick"])
                if engine_cvars["r_shadows"]:
                    sh_r = obj["rect"].move(5, 5)
                    pygame.draw.rect(screen, (15, 18, 24), sh_r, border_radius=5)
                pygame.draw.rect(screen, mat_obj.albedo, obj["rect"], border_radius=5)
                pygame.draw.rect(screen, (235, 240, 245), obj["rect"], 1, border_radius=5)

        hud_pad = pygame.Rect(SCR_W - 315, SCR_H - 195, 300, 180)
        active_buttons_now = []

        if window_active and not dev_console.is_open:
            if keys_pressed[pygame.K_m]:
                game_state = "MENU"
            if keys_pressed[pygame.K_z]:
                respawn_robot_safely()
            if keys_pressed[pygame.K_1]:
                current_gear = '1'
            elif keys_pressed[pygame.K_2]:
                current_gear = '2'
            elif keys_pressed[pygame.K_3]:
                current_gear = '3'

        for btn in cur_remote_cfg["buttons"]:
            bx = hud_pad.x + btn["x"]
            by = hud_pad.y + btn["y"]
            b_r = pygame.Rect(bx - 18, by - 18, 36, 36)
            key_down = False
            if window_active and not dev_console.is_open:
                try:
                    k_code = pygame.key.key_code(btn["key"])
                    key_down = bool(keys_pressed[k_code])
                except Exception:
                    key_down = False
            mouse_down_btn = mouse_left and b_r.collidepoint(mouse_pos)
            if key_down or mouse_down_btn:
                active_buttons_now.append(btn)

        spd = SPEED_MODES[current_gear] * engine_cvars["sv_maxspeed"] * dt_scale
        forward_vec = pygame.math.Vector2(1, 0).rotate(-robot_angle)
        strafe_vec = pygame.math.Vector2(0, 1).rotate(-robot_angle)

        motor_power = {m["id"]: 0.0 for m in cur_robot_cfg["motors"]}
        for btn in active_buttons_now:
            m_id = btn["motor_id"]
            if m_id == 0:
                for k_m in motor_power:
                    motor_power[k_m] += spd * btn["dir"]
            elif m_id in motor_power:
                motor_power[m_id] += spd * btn["dir"]
            # -1..-4 (танк/стрейф) больше не поддерживаются — только Mecanum-кинематика

        v_fwd, v_str, v_rot = compute_mecanum_kinematics(cur_robot_cfg, motor_power)
        delta_pos = (forward_vec * v_fwd) + (strafe_vec * v_str)
        robot_angle = (robot_angle + v_rot) % 360.0

        for axis in ("x", "y"):
            test_pos = pygame.math.Vector2(robot_pos.x, robot_pos.y)
            if axis == "x":
                test_pos.x += delta_pos.x
            else:
                test_pos.y += delta_pos.y
            robot_hitbox = pygame.Rect(0, 0, 92, 92)
            robot_hitbox.center = (round(test_pos.x), round(test_pos.y))
            blocked = False
            for obj in live_field_objects:
                if robot_hitbox.colliderect(obj["rect"]):
                    if obj["type"] == "wall":
                        blocked = True
                    elif obj["type"] == "box":
                        push_x = round(delta_pos.x) if axis == "x" else 0
                        push_y = round(delta_pos.y) if axis == "y" else 0
                        moved_box = obj["rect"].move(push_x, push_y)
                        moved_box.clamp_ip(pygame.Rect(0, 0, SCR_W, SCR_H))
                        if not any(moved_box.colliderect(other["rect"]) for other in live_field_objects if other is not obj):
                            obj["rect"] = moved_box
                        else:
                            blocked = True
            if not blocked:
                robot_pos = test_pos

        robot_pos.x = max(50, min(SCR_W - 50, robot_pos.x))
        robot_pos.y = max(50, min(SCR_H - 50, robot_pos.y))

        if SerialObj is not None and SerialObj.is_open:
            try:
                active_labels = "".join(b["label"] for b in active_buttons_now) or "0"
                SerialObj.write(f"{active_labels}\n".encode("utf-8"))
            except Exception:
                pass

        if not engine_cvars["r_mode_3d"]:
            r_base_surf = render_robot_config_surface(cur_robot_cfg, 1.0)
            if engine_cvars["r_antialiasing"]:
                r_rot_surf = pygame.transform.rotozoom(r_base_surf, robot_angle, 1.0)
            else:
                r_rot_surf = pygame.transform.rotate(r_base_surf, robot_angle)
            if engine_cvars["r_shadows"]:
                sh_surf = pygame.Surface((96, 96), pygame.SRCALPHA)
                pygame.draw.circle(sh_surf, (10, 12, 16, 110), (48, 48), 44)
                screen.blit(sh_surf, sh_surf.get_rect(center=(round(robot_pos.x) + 5, round(robot_pos.y) + 6)))
            screen.blit(r_rot_surf, r_rot_surf.get_rect(center=(round(robot_pos.x), round(robot_pos.y))))

        pad_surf = pygame.Surface((hud_pad.w, hud_pad.h), pygame.SRCALPHA)
        pygame.draw.rect(pad_surf, (20, 25, 34, 215), (0, 0, hud_pad.w, hud_pad.h), border_radius=14)
        pygame.draw.rect(pad_surf, (70, 90, 115, 240), (0, 0, hud_pad.w, hud_pad.h), 2, border_radius=14)
        screen.blit(pad_surf, hud_pad.topleft)
        for btn in cur_remote_cfg["buttons"]:
            bx = hud_pad.x + btn["x"]
            by = hud_pad.y + btn["y"]
            b_r = pygame.Rect(bx - 18, by - 18, 36, 36)
            is_act_b = btn in active_buttons_now
            draw_r = b_r.move(0, 2) if is_act_b else b_r
            pygame.draw.rect(screen, (46, 204, 113) if is_act_b else (45, 55, 70), draw_r, border_radius=7)
            pygame.draw.rect(screen, (130, 255, 170) if is_act_b else (85, 100, 120), draw_r, 1, border_radius=7)
            t_b = font_hud.render(btn["label"], True, (255, 255, 255))
            screen.blit(t_b, t_b.get_rect(center=draw_r.center))

        mode_tag = "3D" if engine_cvars["r_mode_3d"] else "2D"
        top_hud = font_hud.render(
            f"[{mode_tag}] {cur_robot_cfg['name']} | Mecanum | Передача: {current_gear} | [M] Меню | [=] Консоль",
            True, (215, 225, 240))
        screen.blit(top_hud, (15, 15))

    telemetry = f"POS: ({int(robot_pos.x)}, {int(robot_pos.y)}) | YAW: {int(robot_angle)}°"
    dev_console.draw(screen, clock.get_fps(), telemetry)
    pygame.display.flip()

pygame.quit()
if SerialObj is not None and SerialObj.is_open:
    SerialObj.close()