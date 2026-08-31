import os
import requests
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

# -----------------------------------------------------------------
# 1. ページの設定
# -----------------------------------------------------------------
st.set_page_config(
    page_title="安小 就学時検診",
    page_icon="🏫",
    layout="centered",
)

# カスタムCSS（デザイン）
st.markdown("""
    <style>
    /* 【第1・第2ステップ】などの小さな見出し用スタイル */
    .sub-step-title {
        font-size: 1.1rem !important;
        font-weight: bold;
        color: #555555;
        margin-bottom: 0px;
    }
    
    /* 「受付場所」「検査場所」「ご案内」インラインスタイル */
    .info-label {
        font-size: 1.1rem;
        font-weight: bold;
    }
    .venue-large {
        font-size: 1.5rem;
        font-weight: bold;
        color: #1E3A8A;
    }

    /* ボタンの基本設定 */
    div.stButton > button {
        width: 100%;
        border-radius: 8px !important;
        transition: all 0.3s ease;
    }

    /* 第1ステップ：「受付を完了し…」専用の特大ボタンテキスト */
    div.element-container:has(#reception-complete-btn) + div.element-container div.stButton > button {
        font-size: 1.4rem !important;
        font-weight: 800 !important;
        padding: 1.2rem 1rem !important;
        line-height: 1.4 !important;
    }

    /* 第2ステップ：各検査完了ボタン（タップ前：薄青 / タップ後：赤） */
    div.element-container:has(.test-status-unselected) + div.element-container div.stButton > button {
        background-color: #93C5FD !important; /* 薄めの青 */
        color: #1E3A8A !important;
        font-size: 1.25rem !important;
        font-weight: bold !important;
        padding: 0.9rem 1rem !important;
        border: none !important;
    }
    div.element-container:has(.test-status-unselected) + div.element-container div.stButton > button:hover {
        background-color: #60A5FA !important;
    }

    div.element-container:has(.test-status-selected) + div.element-container div.stButton > button {
        background-color: #DC3545 !important; /* 赤色 */
        color: #FFFFFF !important;
        font-size: 1.25rem !important;
        font-weight: bold !important;
        padding: 0.9rem 1rem !important;
        border: none !important;
        box-shadow: 0 4px 10px rgba(220, 53, 69, 0.3);
    }
    div.element-container:has(.test-status-selected) + div.element-container div.stButton > button:hover {
        background-color: #BD2130 !important;
    }

    /* 第2ステップ：「次のステップへ進む」ボタン（全状態特大サイズ統一） */
    div.element-container:has(#next-step-btn-container) + div.element-container div.stButton > button {
        font-size: 1.35rem !important;
        font-weight: 800 !important;
        padding: 1.1rem 1rem !important;
    }

    /* チェック前（無効時）：青色ベース */
    div.element-container:has(#next-step-btn-container) + div.element-container div.stButton > button:disabled {
        background-color: #93C5FD !important; /* 明るめの青色（無効状態） */
        color: #FFFFFF !important;
        opacity: 0.7;
        border: none !important;
    }

    /* チェック完了後（有効時）：赤色ベース */
    div.element-container:has(#next-step-btn-container) + div.element-container div.stButton > button:not(:disabled) {
        background-color: #DC3545 !important; /* 目立つ赤色 */
        color: #FFFFFF !important;
        border: none !important;
        box-shadow: 0 4px 10px rgba(220, 53, 69, 0.3);
    }
    div.element-container:has(#next-step-btn-container) + div.element-container div.stButton > button:not(:disabled):hover {
        background-color: #BD2130 !important;
    }

    /* 未タップ状態（グレーボタン） */
    div.stButton > button[kind="primary"] {
        background-color: #6C757D !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #5A6268 !important;
    }

    /* タップ完了後状態（赤色ボタン） */
    div.stButton > button[kind="secondary"] {
        background-color: #DC3545 !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    div.stButton > button[kind="secondary"]:hover {
        background-color: #BD2130 !important;
    }
    </style>
""", unsafe_allow_html=True)

# アプリタイトル
st.title("安小 就学時検診")

if "step" not in st.session_state:
    st.session_state.step = 1

if "step1_completed" not in st.session_state:
    st.session_state.step1_completed = False

# -----------------------------------------------------------------
# 2. ヘルパー関数（フォント・カラー・マップ描画）
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

def build_map_image(data_json):
    if not isinstance(data_json, dict):
        return None
        
    map_grid = data_json.get("map_design", [])
    if not map_grid:
        return None

    map_bg = data_json.get("map_backgrounds")
    map_halign = data_json.get("map_haligns")
    map_valign = data_json.get("map_valigns")
    map_borders = data_json.get("map_borders")
    merged_ranges = data_json.get("map_merged_ranges")
    row_heights = data_json.get("row_heights")
    col_widths = data_json.get("col_widths")

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

    image = Image.new("RGB", (col_x[-1] + 10, row_y[-1] + 10), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    font = get_japanese_font(12)

    render_grid = [[True for _ in range(cols)] for _ in range(rows)]
    merge_info_map = {}

    if merged_ranges:
        for m in merged_ranges:
            if isinstance(m, dict):
                r_s = m.get("row", 1) - 1
                c_s = m.get("col", 1) - 1
                num_r = m.get("numRows", 1)
                num_c = m.get("numCols", 1)
                merge_info_map[(r_s, c_s)] = (num_r, num_c)
                for r in range(r_s, r_s + num_r):
                    for c in range(c_s, c_s + num_c):
                        if r < rows and c < cols:
                            if not (r == r_s and c == c_s):
                                render_grid[r][c] = False

    for r in range(rows):
        for c in range(cols):
            if not render_grid[r][c]:
                continue
            num_r, num_c = merge_info_map.get((r, c), (1, 1))
            x1, y1 = col_x[c], row_y[r]
            x2, y2 = col_x[min(c + num_c, cols)], row_y[min(r + num_r, rows)]
            cell_bg = hex_to_rgb(map_bg[r][c]) if map_bg and r < len(map_bg) and c < len(map_bg[r]) else (255, 255, 255)
            draw.rectangle([x1, y1, x2, y2], fill=cell_bg)

    for r in range(rows):
        for c in range(cols):
            if not render_grid[r][c]:
                continue
            num_r, num_c = merge_info_map.get((r, c), (1, 1))
            x1, y1 = col_x[c], row_y[r]
            x2, y2 = col_x[min(c + num_c, cols)], row_y[min(r + num_r, rows)]

            if map_borders and r < len(map_borders) and c < len(map_borders[r]):
                b = map_borders[r][c]
                if isinstance(b, dict):
                    if b.get("top"): draw.line([(x1, y1), (x2, y1)], fill=(0, 0, 0), width=2)
                    if b.get("bottom"): draw.line([(x1, y2), (x2, y2)], fill=(0, 0, 0), width=2)
                    if b.get("left"): draw.line([(x1, y1), (x1, y2)], fill=(0, 0, 0), width=2)
                    if b.get("right"): draw.line([(x2, y1), (x2, y2)], fill=(0, 0, 0), width=2)

            text = str(map_grid[r][c]).strip() if map_grid[r][c] is not None else ""
            if text:
                h_align = map_halign[r][c] if map_halign and r < len(map_halign) and c < len(map_halign[r]) else "center"
                v_align = map_valign[r][c] if map_valign and r < len(map_valign) and c < len(map_valign[r]) else "middle"

                bbox = draw.textbbox((0, 0), text, font=font)
                text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                cell_w, cell_h = x2 - x1, y2 - y1

                tx = x1 + 5 if h_align == "left" else (x2 - text_w - 5 if h_align == "right" else x1 + (cell_w - text_w) / 2)
                ty = y1 + 3 if v_align == "top" else (y2 - text_h - 5 if v_align == "bottom" else y1 + (cell_h - text_h) / 2)

                draw.text((tx, ty), text, fill=(0, 0, 0), font=font)

    return image

# -----------------------------------------------------------------
# 3. データ保護ロジック
# -----------------------------------------------------------------
default_settings = pd.DataFrame([
    {"step": 1, "item_name": "受付案内", "venue": "ひまわり 1", "details": "事前に送付された「お知らせ（桜色）」と「健康診断票（黄色）」をご用意ください。", "type": "reception"},
    {"step": 2, "item_name": "視力検査", "venue": "家庭科室", "details": "お子様と一緒に検査を受けてください。", "type": "test"},
    {"step": 2, "item_name": "聴力検査", "venue": "1-1、1-2、ひまわり 5", "details": "空いている教室から優先して受診してください。", "type": "test"},
    {"step": 3, "item_name": "内科検診", "venue": "図工室", "details": "※受診前にお子様のお着替え（上半身を脱ぐ）が必要です。", "type": "doctor"},
    {"step": 3, "item_name": "歯科検診", "venue": "4-1", "details": "歯科検診会場です。", "type": "doctor"},
    {"step": 3, "item_name": "耳鼻科検診", "venue": "活動室南", "details": "耳鼻科検診会場です。", "type": "doctor"},
    {"step": 4, "item_name": "眼科検診", "venue": "4-2", "details": "眼科検診会場です。", "type": "doctor"},
    {"step": 4, "item_name": "教育相談", "venue": "ひまわり 2", "details": "※希望者のみ（待機場所：理科室）。", "type": "optional"},
    {"step": 4, "item_name": "結果通知", "venue": "ひまわり 3", "details": "【全員必須】クリアファイルと健康診断票を提出してください。", "type": "final"}
])

@st.cache_resource
def get_persistent_store():
    return {"raw_data": None, "df_settings": None, "map_img": None}

store = get_persistent_store()

def load_data_force(force_refresh=False):
    if not force_refresh and store["df_settings"] is not None:
        return store["df_settings"], store["map_img"]

    gas_url = st.secrets.get("gas_api_url")
    if gas_url:
        try:
            res = requests.get(gas_url, timeout=15).json()
            if isinstance(res, dict) and "settings" in res and isinstance(res["settings"], list) and len(res["settings"]) > 0:
                store["raw_data"] = res
                store["df_settings"] = pd.DataFrame(res["settings"]).fillna("")
                store["map_img"] = build_map_image(res)
                return store["df_settings"], store["map_img"]
        except Exception:
            pass

    if store["df_settings"] is None:
        return default_settings, None
    return store["df_settings"], store["map_img"]

df_settings, generated_map_img = load_data_force()

# -----------------------------------------------------------------
# 4. 画面描画（ナビゲーションコンテンツ）
# -----------------------------------------------------------------
steps_names = ["1. 受付", "2. 視力・聴力検査", "3. 医師検診", "4. 教育相談・結果通知", "5. 終了"]
if st.session_state.step <= 5:
    st.progress((st.session_state.step - 1) / 4.0)
    st.caption(f"進捗状況: {steps_names[st.session_state.step - 1]}")

if st.session_state.step == 1:
    st.markdown('<p class="sub-step-title">【第1ステップ】</p>', unsafe_allow_html=True)
    st.header("受付")
    
    reception_data = df_settings[df_settings["type"] == "reception"]
    if not reception_data.empty:
        info = reception_data.iloc[0]
        
        st.markdown(
            f'<p><span class="info-label">受付場所：</span><span class="venue-large">{info["venue"]}</span></p>', 
            unsafe_allow_html=True
        )
        st.markdown(
            f'<p><span class="info-label">■ ご案内：</span>{info["details"]}</p>', 
            unsafe_allow_html=True
        )

    st.write("")
    st.markdown("<b>↓受付が済んだらタップしてください。</b>", unsafe_allow_html=True)
    
    btn_type = "secondary" if st.session_state.step1_completed else "primary"
    st.markdown('<div id="reception-complete-btn"></div>', unsafe_allow_html=True)
    
    if st.button("受付を完了し、番号札とクリアファイルを受け取りました", type=btn_type):
        st.session_state.step1_completed = True
        st.session_state.step = 2
        st.rerun()

elif st.session_state.step == 2:
    st.markdown('<p class="sub-step-title">【第2ステップ】</p>', unsafe_allow_html=True)
    st.header("視力・聴力検査")
    st.write("お子様と一緒に以下の検査会場へお回りください。空いている会場からお進みください。")
    st.write("")

    tests = df_settings[df_settings["type"] == "test"]
    completed_status = {}

    for idx, row in tests.iterrows():
        st.divider()

        st.markdown(f"### ■ {row['item_name']}")
        st.markdown(
            f'<p><span class="info-label">検査場所：</span><span class="venue-large">{row["venue"]}</span></p>', 
            unsafe_allow_html=True
        )
        st.markdown(
            f'<p><span class="info-label">■ ご案内：</span>{row["details"]}</p>', 
            unsafe_allow_html=True
        )
        st.write("")

        # ボタンの状態管理用セッションキー
        btn_key = f"test_btn_{idx}"
        if btn_key not in st.session_state:
            st.session_state[btn_key] = False

        is_done = st.session_state[btn_key]
        completed_status[row['item_name']] = is_done

        # CSSで特定のボタンの見た目をターゲットにするアンカー
        status_class = "test-status-selected" if is_done else "test-status-unselected"
        st.markdown(f'<div class="{status_class}"></div>', unsafe_allow_html=True)

        # ボタンラベルテキスト（完了/未完了）
        btn_label = f"✓ {row['item_name']}を受診完了（タップで解除）" if is_done else f"{row['item_name']}を受診した"

        if st.button(btn_label, key=f"btn_act_{idx}"):
            st.session_state[btn_key] = not is_done
            st.rerun()

    st.divider()
    st.write("")

    # 視力・聴力両方のボタンが押されているか確認
    all_checked = all(completed_status.values())

    # ボタン専用スタイルアンカー設定
    st.markdown('<div id="next-step-btn-container"></div>', unsafe_allow_html=True)

    if st.button("次のステップ（医師による検診）へ進む", disabled=not all_checked):
        st.session_state.step = 3
        st.rerun()

elif st.session_state.step == 3:
    st.header("【第3ステップ】 医師による検診")
    st.write("以下の検診をすべて受診してください。混雑状況を見て空いている会場からお回りください。")
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
    
    final_data = df_settings[df_settings["type"] == "final"]
    if not final_data.empty:
        f_info = final_data.iloc[0]
        st.markdown(f"**■ {f_info['item_name']}（会場：{f_info['venue']}）**")
        st.write(f_info['details'])
    checked_final = st.checkbox("結果通知を受け取り、すべての書類とクリアファイルを提出した")
    if st.button("健診を終了する", disabled=not checked_final):
        st.session_state.step = 5
        st.rerun()

elif st.session_state.step == 5:
    st.balloons()
    st.header("健診がすべて終了しました")
    st.markdown("お疲れ様でした。気をつけてお帰りください。")

# -----------------------------------------------------------------
# 共通「前に戻る」ボタン（第2〜第5ステップで表示）
# -----------------------------------------------------------------
if st.session_state.step > 1:
    st.write("")
    if st.button("⬅️ 前のステップに戻る"):
        st.session_state.step -= 1
        st.rerun()

# -----------------------------------------------------------------
# 5. 会場配置図（一番下に常時表示）
# -----------------------------------------------------------------
st.divider()
st.subheader("🗺️ 会場配置図")

if generated_map_img:
    st.image(generated_map_img, caption="校内会場配置図", use_container_width=True)
else:
    st.info("会場配置図を取得できませんでした。各案内の会場情報をご確認ください。")

# -----------------------------------------------------------------
# 管理用サイドバー
# -----------------------------------------------------------------
with st.sidebar:
    if st.button("🔄 マップ・設定を最新に更新"):
        load_data_force(force_refresh=True)
        st.rerun()
