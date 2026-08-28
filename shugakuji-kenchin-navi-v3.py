import os
import requests
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

# -----------------------------------------------------------------
# 1. ページの設定
# -----------------------------------------------------------------
st.set_page_config(
    page_title="就学時健康診断 案内ナビ",
    page_icon="🏫",
    layout="centered",
)

st.title("令和8年度 就学時健康診断 案内ナビ")

# セッション状態（ユーザー個人の進捗）の初期化
if "step" not in st.session_state:
    st.session_state.step = 1

# -----------------------------------------------------------------
# 2. 【超高速化の肝】グローバル共有キャッシュ
# -----------------------------------------------------------------

@st.cache_data(ttl=600)  # 10分間、全ユーザーでこの結果を使い回す
def get_global_data():
    """GASからデータを1回だけ取得し、全ユーザーで共有する"""
    gas_url = st.secrets.get("gas_api_url")
    if not gas_url:
        return None
    try:
        # サーバーが代表して1回だけGASにアクセス
        return requests.get(gas_url, timeout=30).json()
    except:
        return None

@st.cache_data(show_spinner="地図を作成中...") 
def get_cached_map_image(data_json):
    """
    データから画像を1回だけ生成し、全ユーザーで共有する。
    データの中身が変わらない限り、画像生成（重い処理）は二度と行われません。
    """
    if not data_json:
        return None
    
    # 以前作成した複雑な generate_map_image のロジックをここで実行
    # (ここでは関数を呼び出す形にしています)
    return build_map_logic(data_json)

# -----------------------------------------------------------------
# 3. ヘルパー関数（フォント・カラー・描画ロジック）
# -----------------------------------------------------------------
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
            try: return ImageFont.truetype(path, font_size)
            except: continue
    return ImageFont.load_default()

def hex_to_rgb(hex_str, default_color=(255, 255, 255)):
    if not hex_str or not isinstance(hex_str, str) or not hex_str.startswith("#"):
        return default_color
    try:
        hex_str = hex_str.lstrip("#")
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    except:
        return default_color

def build_map_logic(data):
    """実際に画像を描画する心臓部（サーバー側で1回だけ動く）"""
    map_grid = data.get("map_design", [])
    if not map_grid: return None
    
    map_bg = data.get("map_backgrounds")
    map_halign = data.get("map_haligns")
    map_valign = data.get("map_valigns")
    map_borders = data.get("map_borders")
    merged_ranges = data.get("map_merged_ranges")
    row_heights = data.get("row_heights")
    col_widths = data.get("col_widths")

    rows = len(map_grid)
    cols = max(len(r) for r in map_grid)
    col_w_list = [int(col_widths[i]) if col_widths and i < len(col_widths) else 80 for i in range(cols)]
    row_h_list = [int(row_heights[i]) if row_heights and i < len(row_heights) else 40 for i in range(rows)]
    col_x = [10]; [col_x.append(col_x[-1] + w) for w in col_w_list]
    row_y = [10]; [row_y.append(row_y[-1] + h) for h in row_h_list]

    image = Image.new("RGB", (col_x[-1] + 10, row_y[-1] + 10), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    font = get_japanese_font(12)

    render_grid = [[True for _ in range(cols)] for _ in range(rows)]
    merge_info_map = {}
    if merged_ranges:
        for m in merged_ranges:
            r_s, c_s = m["row"]-1, m["col"]-1
            merge_info_map[(r_s, c_s)] = (m["numRows"], m["numCols"])
            for r in range(r_s, r_s + m["numRows"]):
                for c in range(c_s, c_s + m["numCols"]):
                    if not (r == r_s and c == c_s): render_grid[r][c] = False

    # 背景
    for r in range(rows):
        for c in range(cols):
            if not render_grid[r][c]: continue
            n_r, n_c = merge_info_map.get((r, c), (1, 1))
            x1, y1, x2, y2 = col_x[c], row_y[r], col_x[min(c+n_c, cols)], row_y[min(r+n_r, rows)]
            bg = hex_to_rgb(map_bg[r][c]) if map_bg and r<len(map_bg) else (255,255,255)
            draw.rectangle([x1, y1, x2, y2], fill=bg)

    # 罫線と文字
    for r in range(rows):
        for c in range(cols):
            if not render_grid[r][c]: continue
            n_r, n_c = merge_info_map.get((r, c), (1, 1))
            x1, y1, x2, y2 = col_x[c], row_y[r], col_x[min(c+n_c, cols)], row_y[min(r+n_r, rows)]
            
            if map_borders and r<len(map_borders) and isinstance(map_borders[r][c], dict):
                b = map_borders[r][c]
                if b.get("top"): draw.line([(x1, y1), (x2, y1)], fill=(0,0,0), width=2)
                if b.get("bottom"): draw.line([(x1, y2), (x2, y2)], fill=(0,0,0), width=2)
                if b.get("left"): draw.line([(x1, y1), (x1, y2)], fill=(0,0,0), width=2)
                if b.get("right"): draw.line([(x2, y1), (x2, y2)], fill=(0,0,0), width=2)

            txt = str(map_grid[r][c]).strip() if map_grid[r][c] else ""
            if txt:
                bbox = draw.textbbox((0, 0), txt, font=font)
                tx = x1 + (x2-x1-(bbox[2]-bbox[0]))/2
                ty = y1 + (y2-y1-(bbox[3]-bbox[1]))/2
                draw.text((tx, ty), txt, fill=(0,0,0), font=font)
    return image

# -----------------------------------------------------------------
# 4. メイン処理（ここから下がアプリの見た目）
# -----------------------------------------------------------------

# 全ユーザー共有データの読み込み
raw_data = get_global_data()
df_settings = pd.DataFrame(raw_data.get("settings", [])) if raw_data else pd.DataFrame()
generated_map_img = get_cached_map_image(raw_data)

# マップ表示
with st.expander("🗺️ 全体会場配置図を確認する", expanded=False):
    if generated_map_img:
        st.image(generated_map_img, use_container_width=True)
    else:
        st.info("マップを読み込み中...")

st.divider()

# ナビゲーション（ここは個人のセッションごとに動く）
if df_settings.empty:
    st.error("設定データが読み込めませんでした。管理者へ連絡してください。")
else:
    steps_names = ["1. 受付", "2. 視力・聴力検査", "3. 医師検診", "4. 教育相談・結果通知", "5. 終了"]
    st.progress((st.session_state.step - 1) / 4.0)
    st.caption(f"進捗: {steps_names[st.session_state.step - 1]}")

    # 各ステップの表示（ロジックは前回と同じ）
    if st.session_state.step == 1:
        st.header("【第1ステップ】 受付")
        info = df_settings[df_settings["type"] == "reception"].iloc[0]
        st.markdown(f"**場所:** {info['venue']}\n\n{info['details']}")
        if st.button("受付完了"):
            st.session_state.step = 2
            st.rerun()
    
    elif st.session_state.step == 2:
        st.header("【第2ステップ】 視力・聴力検査")
        tests = df_settings[df_settings["type"] == "test"]
        all_checked = True
        for i, row in tests.iterrows():
            if not st.checkbox(f"{row['item_name']}（{row['venue']}）", key=f"c2_{i}"):
                all_checked = False
        if st.button("次へ進む", disabled=not all_checked):
            st.session_state.step = 3
            st.rerun()

    elif st.session_state.step == 3:
        st.header("【第3ステップ】 医師による検診")
        docs = df_settings[df_settings["type"] == "doctor"]
        all_checked = True
        for i, row in docs.iterrows():
            if not st.checkbox(f"{row['item_name']}（{row['venue']}）", key=f"c3_{i}"):
                all_checked = False
        if st.button("次へ進む", disabled=not all_checked):
            st.session_state.step = 4
            st.rerun()

    elif st.session_state.step == 4:
        st.header("【第4ステップ】 教育相談・結果通知")
        final = df_settings[df_settings["type"] == "final"].iloc[0]
        st.markdown(f"**場所:** {final['venue']}\n\n{final['details']}")
        if st.checkbox("結果通知を受け取り、すべて完了した"):
            if st.button("健診を終了する"):
                st.session_state.step = 5
                st.rerun()

    elif st.session_state.step == 5:
        st.balloons()
        st.success("健診がすべて終了しました。お疲れ様でした。")
        if st.button("最初に戻る"):
            st.session_state.step = 1
            st.rerun()

# 管理者用サイドバー
with st.sidebar:
    if st.button("🔄 データを強制更新（管理者用）"):
        st.cache_data.clear()
        st.rerun()
