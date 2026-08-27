import streamlit as st
import pandas as pd
import requests
from PIL import Image, ImageDraw, ImageFont
import io

# ページの設定
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
# データ読み込み & マップ画像自動生成機能
# -----------------------------------------------------------------
def generate_map_image(map_grid):
    """スプレッドシートの文字配置（2次元配列）からマップ画像を自動作成する"""
    if not map_grid:
        return None
    
    rows = len(map_grid)
    cols = max(len(r) for r in map_grid)
    
    cell_w, cell_h = 70, 45
    img_w, img_h = cols * cell_w + 20, rows * cell_h + 20
    
    # 背景が白い画像を作成
    image = Image.new("RGB", (img_w, img_h), color=(250, 250, 250))
    draw = ImageDraw.Draw(image)
    
    # フォント指定（標準フォントを使用）
    font = ImageFont.load_default()

    for r_idx, row in enumerate(map_grid):
        for c_idx, cell in enumerate(row):
            text = str(cell).strip()
            if not text:
                continue
            
            x1 = c_idx * cell_w + 10
            y1 = r_idx * cell_h + 10
            x2 = x1 + cell_w - 2
            y2 = y1 + cell_h - 2
            
            # マップ要素に応じた色分け
            bg_color = (235, 243, 250) # デフォルト（薄青）
            border_color = (180, 200, 220)
            
            if any(k in text for k in ["受付", "検診", "検査", "相談", "通知"]):
                bg_color = (255, 230, 230) # 健診・受付会場（薄ピンク）
                border_color = (240, 150, 150)
            elif any(k in text for k in ["階段", "WC", "廊下", "↑", "↓", "←", "→"]):
                bg_color = (240, 240, 240) # 共有施設・矢印（グレー）
                border_color = (200, 200, 200)

            # 枠線とセルの描画
            draw.rectangle([x1, y1, x2, y2], fill=bg_color, outline=border_color, width=1)
            
            # 文字描画
            draw.text((x1 + 6, y1 + 12), text[:5], fill=(30, 30, 30), font=font)
            
    return image

#@st.cache_data(ttl=1)  # キャッシュを1秒にして毎回最新データを取得する
def load_data_and_map():
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
                map_grid = res.get("map_design", [])
                if map_grid:
                    map_img = generate_map_image(map_grid)
                return df_settings, map_img
    except Exception as e:
        pass
    return default_data, map_img

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
# 2. アプリの画面遷移ロジック
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
