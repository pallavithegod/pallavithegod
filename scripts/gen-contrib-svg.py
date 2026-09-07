#!/usr/bin/env python3
"""
scripts/gen-contrib-svg.py

Rebuilds assets/contrib-rocket.svg directly from GitHub's live contribution calendar.
Features per-commit ignition rocket barrage animation and column-based restoration wave.
"""

import urllib.request
import re
import os
import sys
import xml.etree.ElementTree as ET

def fetch_contributions(username="pallavithegod"):
    url = f"https://github.com/users/{username}/contributions"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
    })
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode("utf-8")

    # Extract table rows from tbody
    tbody_match = re.search(r'<tbody[^>]*>(.*?)</tbody>', html, re.DOTALL)
    if not tbody_match:
        raise ValueError("Could not find <tbody> in GitHub contributions page")

    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', tbody_match.group(1), re.DOTALL)
    grid = []
    for row in rows:
        cells = re.findall(r'<td[^>]*data-date="([^"]+)"[^>]*data-level="([^"]+)"', row)
        grid.append(cells)

    if not grid or len(grid) < 7:
        raise ValueError("Unexpected grid structure in contribution table")

    # Transpose 7 rows into 52-53 weekly columns
    max_cols = max(len(r) for r in grid)
    weeks = []
    for c in range(max_cols):
        col = []
        for r in range(len(grid)):
            if c < len(grid[r]):
                date, level = grid[r][c]
                col.append({"date": date, "level": int(level)})
        weeks.append(col)

    # Keep last 53 weeks
    if len(weeks) > 53:
        weeks = weeks[-53:]

    # Extract total contribution count
    header_counts = re.findall(r'([0-9,]+)\s+contributions?\s+in\s+(?:the\s+last\s+year|\d{4})', html)
    total_count = header_counts[0] if header_counts else "371"

    return weeks, total_count

def generate_rocket_svg(weeks, total_count, output_path="assets/contrib-rocket.svg"):
    month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Month labels calculation
    month_labels = []
    last_month = None
    last_x = -100.0
    for w_idx, week in enumerate(weeks):
        first_day = week[0]["date"]
        month_num = int(first_day.split("-")[1])
        if month_num != last_month:
            x_pos = 28.0 + w_idx * 16.0
            if x_pos - last_x >= 40.0:
                month_labels.append((x_pos, month_names[month_num]))
                last_month = month_num
                last_x = x_pos

    # Contribution color scale
    colors = {
        0: "#161b22",
        1: "#1a4d3c",
        2: "#1e8a62",
        3: "#2ee6a0",
        4: "#8affd0"
    }

    # Collect active dots: (x, y, level, col_idx)
    # Order: column ascending (left to right), y descending (bottom to top)
    active_dots = []
    for col_idx, week in enumerate(weeks):
        x = 28.0 + col_idx * 16.0
        for row_idx in range(len(week) - 1, -1, -1):
            day = week[row_idx]
            if day["level"] > 0:
                y = 88.0 + row_idx * 16.0
                active_dots.append({
                    "x": x,
                    "y": y,
                    "level": day["level"],
                    "col_idx": col_idx,
                    "color": colors.get(day["level"], "#1a4d3c")
                })

    total_active = len(active_dots)
    print(f"Total active contribution cells: {total_active}")

    dur = "13.80s"
    flight_time = 0.0246
    delta_t = 0.7645 / max(total_active - 1, 1) if total_active > 1 else 0.01

    for idx, dot in enumerate(active_dots):
        t_start = idx * delta_t
        t_hit = t_start + flight_time
        dot["idx"] = idx
        dot["t_start"] = t_start
        dot["t_hit"] = t_hit

    # Build SVG content
    lines = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append('<svg xmlns="http://www.w3.org/2000/svg" width="900" height="244" viewBox="0 0 900 244" role="img" aria-label="Contribution Activity">')
    lines.append('')
    lines.append('  <rect x="0.5" y="0.5" width="899" height="243" rx="10" fill="#0D1117" stroke="#30363d" stroke-width="1.2"/>')
    lines.append('')
    lines.append('  <text x="22" y="34" font-family="Consolas, \'JetBrains Mono\', \'SF Mono\', Menlo, monospace" font-size="18" font-weight="700" fill="#f1f5f9">Contribution Activity</text>')
    lines.append(f'  <text x="22" y="56" font-family="Consolas, \'JetBrains Mono\', \'SF Mono\', Menlo, monospace" font-size="13.5" fill="#7d8590">{total_count} contributions in the last year</text>')
    lines.append('')

    # Month headers
    for x_pos, m_name in month_labels:
        lines.append(f'<text x="{x_pos:.1f}" y="76" font-family="Consolas, \'JetBrains Mono\', \'SF Mono\', Menlo, monospace" font-size="11" fill="#7d8590">{m_name}</text>')

    # Inactive background squares (always 53 weeks x 7 rows)
    num_cols = len(weeks)
    for col_idx in range(num_cols):
        x = 28.0 + col_idx * 16.0
        for row_idx in range(7):
            y = 88.0 + row_idx * 16.0
            lines.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="12" height="12" rx="2.4" fill="#161b22"/>')

    # Active contribution squares with ignition and restore wave
    active_dots_rect_order = sorted(active_dots, key=lambda d: (d["col_idx"], d["y"]))
    for dot in active_dots_rect_order:
        x = dot["x"]
        y = dot["y"]
        c = dot["color"]
        t_hit = dot["t_hit"]
        t_off = t_hit + 0.0029
        t_restore_start = 0.3986 + dot["col_idx"] * 0.00947
        t_restore_end = t_restore_start + 0.0304

        kt = f"0.0000;{t_hit:.4f};{t_off:.4f};{t_restore_start:.4f};{t_restore_end:.4f};1.0000"
        lines.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="12" height="12" rx="2.4" fill="{c}"><animate attributeName="opacity" values="1;1;0;0;1;1" keyTimes="{kt}" dur="{dur}" repeatCount="indefinite" calcMode="linear"/></rect>')

    # Ripple circles and flying rockets
    for dot in active_dots:
        cx = dot["x"] + 6.0
        cy = dot["y"] + 6.0
        t_start = dot["t_start"]
        t_hit = dot["t_hit"]
        t_dissolve = t_hit + 0.0015
        dist = 208.0 - dot["y"]

        circle_kt = f"0.0000;{t_start:.4f};{t_start:.4f};{t_hit:.4f};1.0000"
        circle_r_kt = f"0.0000;{t_start:.4f};{t_hit:.4f};1.0000"
        lines.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="9" fill="none" stroke="#3dffc0" stroke-width="1.3" opacity="0"><animate attributeName="opacity" values="0;0;0.6;0;0" keyTimes="{circle_kt}" dur="{dur}" repeatCount="indefinite"/><animate attributeName="r" values="8;8;13;13" keyTimes="{circle_r_kt}" dur="{dur}" repeatCount="indefinite"/></circle>')

        group_kt = f"0.0000;{t_start:.4f};{t_start:.4f};{t_hit:.4f};{t_dissolve:.4f};1.0000"
        trans_kt = f"0.0000;{t_start:.4f};{t_hit:.4f};1.0000"
        trans_val = f"0,0;0,0;0,-{dist:.1f};0,-{dist:.1f}"

        rocket_markup = (
            f'<g opacity="0">'
            f'<animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="{group_kt}" dur="{dur}" repeatCount="indefinite"/>'
            f'<animateTransform attributeName="transform" type="translate" values="{trans_val}" keyTimes="{trans_kt}" dur="{dur}" repeatCount="indefinite"/>'
            f'<polygon points="{cx:.1f},203.0 {cx+6.2:.1f},221.0 {cx:.1f},217.5 {cx-6.2:.1f},221.0" fill="#b8ffe0"/>'
            f'<polygon points="{cx:.1f},208.0 {cx+2.2:.1f},216.0 {cx-2.2:.1f},216.0" fill="#f4fffb"/>'
            f'<path d="M{cx-3.0:.1f},221.0 Q{cx:.1f},230.0 {cx+3.0:.1f},221.0" fill="#7dffc8" opacity="0.7"/>'
            f'</g>'
        )
        lines.append(rocket_markup)

    # Footer legend
    legend = '<text x="22" y="228" font-family="Consolas, \'JetBrains Mono\', \'SF Mono\', Menlo, monospace" font-size="11" fill="#7d8590">Less</text><rect x="52" y="220" width="9" height="9" rx="2" fill="#161b22"/><rect x="64" y="220" width="9" height="9" rx="2" fill="#1a4d3c"/><rect x="76" y="220" width="9" height="9" rx="2" fill="#1e8a62"/><rect x="88" y="220" width="9" height="9" rx="2" fill="#2ee6a0"/><rect x="100" y="220" width="9" height="9" rx="2" fill="#8affd0"/><text x="118" y="228" font-family="Consolas, \'JetBrains Mono\', \'SF Mono\', Menlo, monospace" font-size="11" fill="#7d8590">More</text>'
    lines.append(legend)
    lines.append('</svg>')

    full_svg = "\n".join(lines)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_svg)

    # Verify with strict XML parser
    ET.parse(output_path)
    print(f"Generated and validated {output_path} successfully ({len(lines)} lines).")

if __name__ == "__main__":
    target_user = sys.argv[1] if len(sys.argv) > 1 else os.getenv("GH_USERNAME", "pallavithegod")
    target_file = sys.argv[2] if len(sys.argv) > 2 else "assets/contrib-rocket.svg"
    print(f"Fetching GitHub contribution data for '{target_user}'...")
    weeks_data, count_str = fetch_contributions(target_user)
    print(f"Extracted {len(weeks_data)} weeks of activity. Total count: {count_str}")
    generate_rocket_svg(weeks_data, count_str, target_file)
