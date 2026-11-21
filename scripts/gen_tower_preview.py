#!/usr/bin/env python3
"""Generate static isometric SVG preview of the Activity Tower for README.

Reads data/activity-tower.json and draws an isometric projection of the tower.
"""
import json
import math
import colorsys
from pathlib import Path

DATA_FILE = Path("data/activity-tower.json")
OUT_FILE = Path("assets/tower-preview.svg")

# Isometric projection constants
FLOOR_H = 12      # px per floor in projection
FLOOR_W = 140     # px width of floor
FLOOR_D = 60      # px depth of floor
ROOF_H = 8
MARGIN = 50

def iso_point(x, z, y, angle=30):
    """Convert 3D to isometric 2D. x right, z depth, y up."""
    cos30 = math.cos(math.radians(30))
    sin30 = math.sin(math.radians(30))
    # Isometric: x' = (x - z) * cos30, y' = (x + z) * sin30 - y
    return (x - z) * cos30, (x + z) * sin30 - y

def brighten_color(hex_color, factor):
    """Brighten a hex color by factor (0-1)."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
    l = min(1, l * factor + 0.15)
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'

def polygon(points, **attrs):
    pts = ' '.join(f'{x},{y}' for x, y in points)
    attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
    return f'<polygon points="{pts}" {attr_str}/>'

def text(x, y, content, **attrs):
    attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
    return f'<text x="{x}" y="{y}" {attr_str}>{content}</text>'

def main():
    data = json.loads(DATA_FILE.read_text())
    
    FLOOR_H = 10
    FLOOR_W = 120
    FLOOR_D = 50
    ROOF_H = 6
    MARGIN = 60
    
    # Calculate total height
    total_floors = data['totals']['branches']
    repo_count = len(data['repositories'])
    tower_height = total_floors * FLOOR_H + repo_count * ROOF_H
    
    # Canvas size
    CANVAS_W = 500
    CANVAS_H = tower_height + 120
    CENTER_X = CANVAS_W / 2
    BASE_Y = CANVAS_H - 40
    
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}" viewBox="0 0 {CANVAS_W} {CANVAS_H}">')
    svg.append(f'<rect width="{CANVAS_W}" height="{CANVAS_H}" fill="#050a14"/>')
    
    # Subtle grid background
    svg.append('<g stroke="#0a182c" stroke-width="0.4" opacity="0.2">')
    for i in range(0, CANVAS_W, 30):
        svg.append(f'<line x1="{i}" y1="0" x2="{i}" y2="{CANVAS_H}" />')
    for i in range(0, CANVAS_H, 30):
        svg.append(f'<line x1="0" y1="{i}" x2="{CANVAS_W}" y2="{i}" />')
    svg.append('</g>')
    
    # Isometric projection helper
    cos30 = math.cos(math.radians(30))
    sin30 = math.sin(math.radians(30))
    
    def iso_x(x, z):
        return (x - z) * cos30
    
    def iso_y(x, z, y):
        return (x + z) * sin30 - y
    
    # Floor dimensions in 3D space
    FW = 100  # floor width (x)
    FD = 50   # floor depth (z)
    FH = 8    # floor height (y)
    ROOF_H = 5
    
    # Tower center in 3D
    TX = 0
    TZ = 0
    TY = 0
    
    # Current Y position (grows upward)
    ty = 0
    floor_count = 0
    
    # Pre-calculate all floor positions for roof labels
    floors_info = []
    
    for repo in data['repositories']:
        color = repo['color']
        for branch in repo['branches']:
            floors_info.append({
                'repo': repo['name'],
                'branch': branch['name'],
                'color': repo['color'],
                'ty': ty,
                'units': branch['commits_displayed'],
                'total_units': branch['total_commits'],
            })
            ty += FH
            floor_count += 1
        ty += 6  # roof gap
    
    total_ty = ty
    
    # SVG canvas centered
    CX = CANVAS_W / 2
    CY = CANVAS_H - 50 - total_ty * sin30  # Adjust so tower sits on bottom
    
    # Projection helpers
    def proj_x(x, z):
        return (x - z) * cos30
    
    def proj_y(x, z, y):
        return (x + z) * sin30 - y
    
    def to_screen(x, z, y):
        px = CX + proj_x(x, z)
        py = CY + proj_y(x, z, y)
        return px, py
    
    # Draw from bottom to top
    ty = 0
    parts = []
    
    for repo in data['repositories']:
        color = repo['color']
        
        for branch in repo['branches']:
            # Floor position
            px, py = to_screen(TX, TZ, ty)
            # Floor isometric coordinates
            # Floor corners in 3D: (±FW/2, ±FD/2, ty) and (±FW/2, ±FD/2, ty+FH)
            hw = FW / 2
            hd = FD / 2
            
            # Bottom face corners (projected)
            corners = []
            for dx, dz in [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)]:
                sx, sy = to_screen(dx, dz, ty)
                corners.append((sx, sy))
            
            # Top face corners
            top_corners = []
            for dx, dz in [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)]:
                sx, sy = to_screen(dx, dz, ty + FH)
                top_corners.append((sx, sy))
            
            # Right face (visible)
            right_face = [
                to_screen(hw, -hd, ty),
                to_screen(hw, hd, ty),
                to_screen(hw, hd, ty + FH),
                to_screen(hw, -hd, ty + FH),
            ]
            
            # Left face (visible)
            left_face = [
                to_screen(-hw, -hd, ty),
                to_screen(-hw, -hd, ty + FH),
                to_screen(-hw, hd, ty + FH),
                to_screen(-hw, hd, ty),
            ]
            
            # Top face
            top_face = top_corners
            
            # Brightness for this floor
            bright_color = brighten_color(repo['color'], 0.7)
            dim_color = brighten_color(repo['color'], 0.4)
            
            # Draw faces (back to front: left, right, top)
            parts.append(polygon(left_face, fill=dim_color, stroke=repo['color'], stroke_width='0.5', opacity='0.6'))
            parts.append(polygon(right_face, fill=repo['color'], stroke=repo['color'], stroke_width='0.5', opacity='0.8'))
            parts.append(polygon(top_corners, fill=bright_color, stroke=repo['color'], stroke_width='0.5', opacity='0.9'))
            
            # Units on top face as small rectangles
            units = branch['commits_displayed']
            if units > 0:
                u_w, u_h = 8, 8
                start_x = - (units - 1) * 12 / 2
                for i in range(units):
                    ux = start_x + i * 12
                    # Unit position on top face
                    ux_3d = ux
                    uz_3d = 0
                    uy_3d = ty + FH + 2
                    px, py = to_screen(ux_3d, uz_3d, uy_3d)
                    unit_color = brighten_color(repo['color'], 0.5 + 0.5 * (1 - i / max(1, units - 1)))
                    parts.append(f'<rect x="{px - 3}" y="{py - 6}" width="6" height="6" fill="{brighten_color(repo["color"], 0.6 + 0.4 * (1 - i / max(1, units - 1)))}" opacity="0.9" rx="1"/>')
            
            ty += FH
            floor_count += 1
        
        # Repo roof
        roof_color = repo['color']
        # Draw roof as thicker slab
        rw = FW + 10
        rd = FD + 10
        rh = 6
        rhw, rhd = rw / 2, rd / 2
        
        roof_corners = []
        for dx, dz in [(-rhw, -rhd), (rhw, -rhd), (rhw, rhd), (-rhw, rhd)]:
            sx, sy = to_screen(dx, dz, ty)
            roof_corners.append((sx, sy))
        
        roof_top = []
        for dx, dz in [(-rhw, -rhd), (rhw, -rhd), (rhw, rhd), (-rhw, rhd)]:
            sx, sy = to_screen(dx, dz, ty + rh)
            roof_top.append((sx, sy))
        
        roof_left = [
            to_screen(-rhw, -rhd, ty),
            to_screen(-rhw, -rhd, ty + rh),
            to_screen(-rhw, rhd, ty + rh),
            to_screen(-rhw, rhd, ty),
        ]
        
        roof_right = [
            to_screen(rhw, -rhd, ty),
            to_screen(rhw, rhd, ty),
            to_screen(rhw, rhd, ty + rh),
            to_screen(rhw, -rhd, ty + rh),
        ]
        
        parts.append(polygon(roof_left, fill=brighten_color(roof_color, 0.3), stroke=roof_color, stroke_width='0.5', opacity='0.5'))
        parts.append(polygon(roof_right, fill=roof_color, stroke=roof_color, stroke_width='0.5', opacity='0.8'))
        parts.append(polygon(roof_top, fill=brighten_color(roof_color, 0.8), stroke=roof_color, stroke_width='0.5', opacity='0.9'))
        
        # Repo label on roof
        label = repo['name'][:16]
        if repo['is_fork']:
            label += ' (fork)'
        lx, ly = to_screen(0, 0, ty + rh + 8)
        parts.append(f'<text x="{lx}" y="{ly}" text-anchor="middle" font-size="8" fill="{roof_color}" font-family="monospace" font-weight="bold">{label}</text>')
        
        ty += rh
    
    # Subtle ground grid
    grid = ['<g stroke="#0a182c" stroke-width="0.3" opacity="0.15">']
    for i in range(-200, 201, 20):
        for j in range(-200, 201, 20):
            if i == 0 and j == 0:
                continue
            x, y = to_screen(i, j, 0)
            grid.append(f'<circle cx="{x}" cy="{y}" r="0.5" fill="#00f0ff" opacity="0.1"/>')
    grid.append('</g>')
    parts = grid + parts
    
    # Title and stats
    stats = data['totals']
    parts.append(f'<text x="{CANVAS_W/2}" y="25" text-anchor="middle" font-size="16" fill="#00f0ff" font-family="monospace" font-weight="bold">GitHub Activity Tower</text>')
    parts.append(f'<text x="{CANVAS_W/2}" y="45" text-anchor="middle" font-size="10" fill="#88d4ff" font-family="monospace">Repos: {stats["repositories"]}  Floors: {stats["branches"]}  Commits shown: {stats["commits_displayed"]}  Total: {sum(sum(b["total_commits"] for b in r["branches"]) for r in data["repositories"])}</text>')
    parts.append(f'<text x="{CANVAS_W/2}" y="CANVAS_H - 15" text-anchor="middle" font-size="8" fill="#4a6fa5" font-family="monospace">Explore interactive tower → personal-website-k4x.pages.dev/#/activity-tower</text>'.replace('CANVAS_H', str(CANVAS_H)))
    
    svg.extend(parts)
    svg.append('</svg>')
    
    OUT_FILE.write_text('\n'.join(svg))
    print(f'Generated {OUT_FILE}: {CANVAS_W}x{CANVAS_H}')

if __name__ == '__main__':
    main()