import os
from PIL import Image, ImageDraw, ImageFont

# 日本語フォント設定（文字化け対策）
def get_japanese_font(font_size=12):
    font_paths = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/ipafont-gothic/ipag.ttf",
        "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
        "C:\\Windows\\Fonts\\msgothic.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc"
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, font_size)
            except Exception:
                continue
    return ImageFont.load_default()

def hex_to_rgb(hex_str, default_color=(255, 255, 255)):
    if not hex_str or not isinstance(hex_str, str) or not hex_str.startswith("#"):
        return default_color
    try:
        hex_str = hex_str.lstrip("#")
        if len(hex_str) == 6:
            return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        pass
    return default_color

def generate_map_image(map_grid, map_bg=None, map_halign=None, map_valign=None, merged_ranges=None, map_borders=None, row_heights=None, col_widths=None):
    if not map_grid:
        return None

    rows = len(map_grid)
    cols = max(len(r) for r in map_grid)

    col_w_list = [int(col_widths[i]) if col_widths and i < len(col_widths) else 80 for i in range(cols)]
    row_h_list = [int(row_heights[i]) if row_heights and i < len(row_heights) else 40 for i in range(rows)]

    col_x = [10]
    for w in col_w_list:
        col_x.append(col_x[-1] + w)

    row_y = [10]
    for h in row_h_list:
        row_y.append(row_y[-1] + h)

    img_w = col_x[-1] + 10
    img_h = row_y[-1] + 10

    image = Image.new("RGB", (img_w, img_h), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    font = get_japanese_font(font_size=12)

    render_grid = [[True for _ in range(cols)] for _ in range(rows)]
    merge_info_map = {}

    if merged_ranges:
        for m in merged_ranges:
            r_start = m["row"] - 1
            c_start = m["col"] - 1
            num_r = m["numRows"]
            num_c = m["numCols"]
            merge_info_map[(r_start, c_start)] = (num_r, num_c)
            for r in range(r_start, r_start + num_r):
                for c in range(c_start, c_start + num_c):
                    if r < rows and c < cols:
                        if not (r == r_start and c == c_start):
                            render_grid[r][c] = False

    # セルの背景色とベース領域の描画
    for r in range(rows):
        for c in range(cols):
            if not render_grid[r][c]:
                continue

            num_r, num_c = merge_info_map.get((r, c), (1, 1))
            x1, y1 = col_x[c], row_y[r]
            x2, y2 = col_x[min(c + num_c, cols)], row_y[min(r + num_r, rows)]

            cell_bg = (255, 255, 255)
            if map_bg and r < len(map_bg) and c < len(map_bg[r]):
                cell_bg = hex_to_rgb(map_bg[r][c], (255, 255, 255))

            draw.rectangle([x1, y1, x2, y2], fill=cell_bg, outline=(220, 220, 220), width=1)

            # テキスト描画
            text = str(map_grid[r][c]).strip() if map_grid[r][c] is not None else ""
            if text:
                h_align = map_halign[r][c] if map_halign and r < len(map_halign) and c < len(map_halign[r]) else "center"
                v_align = map_valign[r][c] if map_valign and r < len(map_valign) and c < len(map_valign[r]) else "middle"

                bbox = draw.textbbox((0, 0), text, font=font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]

                cell_w, cell_h = x2 - x1, y2 - y1

                tx = x1 + 5 if h_align == "left" else (x2 - text_w - 5 if h_align == "right" else x1 + (cell_w - text_w) / 2)
                ty = y1 + 3 if v_align == "top" else (y2 - text_h - 5 if v_align == "bottom" else y1 + (cell_h - text_h) / 2)

                draw.text((tx, ty), text, fill=(0, 0, 0), font=font)

    # 罫線の正確な上書き描画
    if map_borders:
        for r in range(min(rows, len(map_borders))):
            for c in range(min(cols, len(map_borders[r]))):
                b = map_borders[r][c]
                if not b:
                    continue
                x1, y1 = col_x[c], row_y[r]
                x2, y2 = col_x[c+1], row_y[r+1]

                if b.get("top"):
                    draw.line([(x1, y1), (x2, y1)], fill=hex_to_rgb(b["top"], (0,0,0)), width=2)
                if b.get("bottom"):
                    draw.line([(x1, y2), (x2, y2)], fill=hex_to_rgb(b["bottom"], (0,0,0)), width=2)
                if b.get("left"):
                    draw.line([(x1, y1), (x1, y2)], fill=hex_to_rgb(b["left"], (0,0,0)), width=2)
                if b.get("right"):
                    draw.line([(x2, y1), (x2, y2)], fill=hex_to_rgb(b["right"], (0,0,0)), width=2)

    return image
