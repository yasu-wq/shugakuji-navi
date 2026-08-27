import os
import requests
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

# -----------------------------------------------------------------
# ページの設定
# -----------------------------------------------------------------
st.set_page_config(
    page_title="就学時健康診断 案内ナビ",
    page_icon="🏫",
    layout="centered",
)

# タイトル
st.title("令和8年度 就学時健康診断 案内ナビ")
st.write("本日の健康診断の順路をご案内いたします。各ステップを完了したら、受診完了チェックを入れて次の案内へ進んでください。")

# セッション状態の初期化
if "step" not in st.session_state:
    st.session_state.step = 1

# -----------------------------------------------------------------
# ヘルパー関数（フォント・カラー）
# -----------------------------------------------------------------
def get_japanese_font(font_size=12):
    """日本語フォントを取得する"""
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
    """HEXカラー(#RRGGBB)をRGBタプルに変換"""
    if not hex_str or not isinstance(hex_str, str) or not hex_str.startswith("#"):
        return default_color
    try:
        hex_str = hex_str.lstrip("#")
        if len(hex_str) == 6:
            return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        pass
    return default_color

# -----------------------------------------------------------------
# 高機能マップ画像自動生成機能（手動罫線・セル結合・配置対応）
# -----------------------------------------------------------------
def generate_map_image(map_grid, map_bg=None, map_halign=None, map_valign=None, map_borders=None, merged_ranges=None, row_heights=None, col_widths=None):
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
            if isinstance(m, dict):
                r_start = m.get("row", 1) - 1
                c_start = m.get("col", 1) - 1
                num_r = m.get("numRows", 1)
                num_c = m.get("numCols", 1)
                merge_info_map[(r_start, c_start)] = (num_r, num_c)
                for r in range(r_start, r_start + num_r):
                    for c in range(c_start, c_start + num_c):
                        if r < rows and c < cols:
                            if not (r == r_start and c == c_start):
                                render_grid[r][c] = False

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

            # セル背景描画
            draw.rectangle([x1, y1, x2, y2], fill=cell_bg)

            # 手動設定された実線罫線のみ描画
            if map_borders and r < len(map_borders) and c < len(map_borders[r]):
                b = map_borders[r][c]
                if isinstance(b, dict):
                    border_color = (0, 0, 0)
                    if b.get("top"):
                        draw.line([(x1, y1), (x2, y1)], fill=border_color, width=1)
                    if b.get("bottom"):
                        draw.line([(x1, y2), (x2, y2)], fill=border_color, width=1)
                    if b.get("left"):
                        draw.line([(x1, y1), (x1, y2)], fill=border_color, width=1)
                    if b.get("right"):
                        draw.line([(x2, y1), (x2, y2)], fill=border_color, width=1)

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

    return image

# -----------------------------------------------------------------
# データ読み込み処理
# -----------------------------------------------------------------
def load_data_and_map():
    # バックアップ用デフォルトデータ
    default_data = pd.DataFrame([
        {"step": 1, "item_name": "受付案内", "venue": "南校舎2F廊下 または ひまわり 1", "details": "事前に送付された「お知らせ（桜色）」と「健康診断票（黄色）」をご用意ください。", "type": "reception"},
        {"step": 2, "item_name": "視力検査", "venue": "家庭科室", "details": "お子様と一緒に検査を受けてください。", "type": "test"},
        {"step": 2, "item_name": "聴力検査", "venue": "1-1、1-2、ひまわり 5", "details": "空いている教室から優先して受診してください。", "type": "test"},
        {"step": 3, "item_name": "内科検診", "venue": "図工室", "details": "※受診前にお子様のお着替え（上半身を脱ぐ）が必要です。", "type": "doctor"},
        {"step": 3, "item_name": "歯科検診", "venue": "4-1", "details": "歯科検診会場です。", "type": "doctor"},
        {"step": 3, "item_name": "耳鼻科検診", "venue": "活動室南", "details": "耳鼻科検診会場です。", "type": "doctor"},
        {"step": 3, "item_name": "眼科検診", "venue": "4-2", "details": "眼科検診会場です。", "type": "doctor"},
        {"step": 4, "item_name": "教育相談", "venue": "ひまわり 2", "details": "※希望者のみ（待機場所：理科室）。", "type": "optional"},
        {"step": 4, "item_name": "結果通知", "venue": "ひまわり 3", "details": "【全員必須】クリアファイルと健康診断票を提出してください。", "type": "final"}
    ])

    map_img = None
    try:
        gas_url = st.secrets.get("gas_api_url")
        if gas_url:
            res = requests.get(gas_url, timeout=10).json()
            if isinstance(res, dict):
                df_settings = pd.DataFrame(res.get("settings", []))
                
                # スプレッドシートからのマップ描画用データ一式
                map_grid = res.get("map_design", [])
                map_bg = res.get("map_backgrounds", None)
                map_halign = res.get("map_haligns", None)
                map_valign = res.get("map_valigns", None)
                map_borders = res.get("map_borders", None)
                merged_ranges = res.get("map_merged_ranges", None)
                row_heights = res.get("row_heights", None)
                col_widths = res.get("col_widths", None)

                # マップ画像の生成
                if map_grid:
                    map_img = generate_map_image(
                        map_grid=map_grid,
                        map_bg=map_bg,
                        map_halign=map_halign,
                        map_valign=map_valign,
                        map_borders=map_borders,
                        merged_ranges=merged_ranges,
                        row_heights=row_heights,
                        col_widths=col_widths
                    )

                # スプレッドシートのデータが存在する場合はそれを整形
                if not df_settings.empty:
                    for col in ["venue", "details"]:
                        if col not in df_settings.columns:
                            df_settings[col] = ""
                    df_settings = df_settings.fillna("")
                    return df_settings, map_img

    except Exception as e:
        st.warning(f"スプレッドシート連動エラー: {e}")

    return default_data, map_img

# データのロード実行
df_settings, generated_map_img = load_data_and_map()

# -----------------------------------------------------------------
# 1. 全体会場配置図（マップ表示）
# -----------------------------------------------------------------
with st.expander("🗺️ 【どこでも確認】全体会場配置図を開く / 閉じる", expanded=False):
    if generated_map_img:
        st.image(generated_map_img, caption="校内会場配置図（スプレッドシート連携マップ）", use_container_width=True)
    else:
        st.info("スプレッドシートの map_design からマップ画像を作成中、またはデフォルトマップを表示しています。")
    st.caption("※教室の場所がわからない場合は、このマップを広げてご確認ください。")

st.divider()

# -----------------------------------------------------------------
# 2. アプリの画面遷移ロジック（ナビ機能）
# -----------------------------------------------------------------
steps_names = ["1. 受付", "2. 視力・聴力検査", "3. 医師検診", "4. 教育相談・結果通知", "5. 終了"]
if st.session_state.step <= 5:
    st.progress((st.session_state.step - 1) / 4.0)
    st.caption(f"進捗状況: {steps_names[st.session_state.step - 1]}")

if st.session_state.step == 1:
    st.header("【第1ステップ】 受付")
    reception_info = df_settings[df_settings["type"] == "reception"].iloc[0]
    st.markdown(f"**■ 受付場所**\n* **{reception_info['venue']}**\n\n**■ ご案内**\n* {reception_info['details']}")
    if st.button("受付を完了し、番号札とクリアファイルを受け取りました"):
        st.session_state.step = 2
        st.rerun()

elif st.session_state.step == 2:
    st.header("【第2ステップ】 視力・聴力検査")
    st.write("お子様と一緒に以下の検査会場へお回りください。空いている会場からお進みください。")
    tests = df_settings[df_settings["type"] == "test"]
    checkboxes = {}
    for idx, row in tests.iterrows():
        st.markdown(f"**■ {row['item_name']}（会場：{row['venue']}）**")
        st.write(row['details'])
        checkboxes[row['item_name']] = st.checkbox(f"{row['item_name']}を受診した", key=f"chk_{idx}")
        st.write("")
    if st.button("次のステップ（医師による検診）へ進む", disabled=not all(checkboxes.values())):
        st.session_state.step = 3
        st.rerun()

elif st.session_state.step == 3:
    st.header("【第3ステップ】 医師による検診")
    st.write("以下の4つの検診をすべて受診してください。混雑状況を見て空いている会場からお回りください。")
    doctors = df_settings[df_settings["type"] == "doctor"]
    checkboxes = {}
    for idx, row in doctors.iterrows():
        st.markdown(f"**■ {row['item_name']}（会場：{row['venue']}）**")
        st.write(row['details'])
        checkboxes[row['item_name']] = st.checkbox(f"{row['item_name']}を受診した", key=f"chk_{idx}")
        st.write("")
    if st.button("次のステップ（教育相談・結果通知）へ進む", disabled=not all(checkboxes.values())):
        st.session_state.step = 4
        st.rerun()

elif st.session_state.step == 4:
    st.header("【第4ステップ】 教育相談・結果通知")
    opt_data = df_settings[df_settings["type"] == "optional"]
    if not opt_data.empty:
        opt_row = opt_data.iloc[0]
        st.markdown(f"**■ {opt_row['item_name']}（会場：{opt_row['venue']}）**")
        st.write(opt_row['details'])
        st.radio("教育相談の希望について：", ("希望しない / 相談は不要", "希望し、面談が完了した"))
        st.write("")
    
    final_data = df_settings[df_settings["type"] == "final"].iloc[0]
    st.markdown(f"**■ {final_data['item_name']}（会場：{final_data['venue']}）**")
    st.write(final_data['details'])
    checked_final = st.checkbox("結果通知を受け取り、すべての書類とクリアファイルを提出した")
    if st.button("健診を終了する", disabled=not checked_final):
        st.session_state.step = 5
        st.rerun()

elif st.session_state.step == 5:
    st.balloons()
    st.header("健診がすべて終了しました")
    st.markdown("お疲れ様でした。気をつけてお帰りください。")
    if st.button("最初の画面に戻る"):
        st.session_state.step = 1
        st.rerun()
