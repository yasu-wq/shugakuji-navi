import streamlit as st
import pandas as pd
import requests

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
# 1. 全体会場配置図（どのステップでも1タップで開閉可能）
# -----------------------------------------------------------------
# スプレッドシートやSecretsから地図画像のURLを取得（未設定時はデフォルトのプレースホルダー）
try:
    map_url = st.secrets.get("map_image_url", "https://images.unsplash.com/photo-1580582932707-520aed937b7b?q=80&w=1000")
except:
    map_url = "https://images.unsplash.com/photo-1580582932707-520aed937b7b?q=80&w=1000"

with st.expander("🗺️ 【どこでも確認】全体会場配置図を開く / 閉じる", expanded=False):
    st.image(map_url, caption="校内会場配置図（南校舎・北校舎）", use_container_width=True)
    st.caption("※教室の場所がわからない場合は、このマップを広げてご確認ください。")

st.divider()

# -----------------------------------------------------------------
# 2. データ読み込み（GAS Web API連携 兼 フォールバック）
# -----------------------------------------------------------------
@st.cache_data(ttl=300)  # 5分間キャッシュしてアクセスを高速化
def load_data():
    # 令和8年度 計画書に基づくデフォルトデータ（連携が繋がらない場合のバックアップ）
    default_data = pd.DataFrame([
        {"step": 1, "item_name": "受付案内", "venue": "南校舎2F廊下 または ひまわり 1", "details": "事前に送付された「お知らせ（桜色）」と「健康診断票（黄色）」をご用意ください。クリアファイルと番号札をお渡しします。", "type": "reception"},
        {"step": 2, "item_name": "視力検査", "venue": "家庭科室", "details": "お子様と一緒に検査を受けてください。", "type": "test"},
        {"step": 2, "item_name": "聴力検査", "venue": "1-1、1-2、ひまわり 5", "details": "空いている教室から優先して受診してください。", "type": "test"},
        {"step": 3, "item_name": "内科検診", "venue": "図工室", "details": "大本 崇 先生。※受診前にお子様のお着替え（上半身を脱ぐ）が必要です。", "type": "doctor"},
        {"step": 3, "item_name": "歯科検診", "venue": "5-1", "details": "前田 秀朗 先生。", "type": "doctor"},
        {"step": 3, "item_name": "耳鼻科検診", "venue": "イングリッシュルーム", "details": "田代 亨 先生。", "type": "doctor"},
        {"step": 3, "item_name": "眼科検診", "venue": "5-2", "details": "馬場 幸夫 先生。", "type": "doctor"},
        {"step": 4, "item_name": "教育相談", "venue": "ひまわり 2", "details": "待機場所：理科室。※相談をご希望される方のみ。", "type": "optional"},
        {"step": 4, "item_name": "結果通知", "venue": "ひまわり 3", "details": "【全員必須】クリアファイルと健康診断票を提出し、結果通知をお受け取りください。", "type": "final"}
    ])

    try:
        # GASのウェブアプリURLからデータを読み込み
        gas_url = st.secrets.get("gas_api_url")
        if gas_url:
            response = requests.get(gas_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                df = pd.DataFrame(data)
                if not df.empty:
                    return df
    except Exception as e:
        pass
    return default_data

df_settings = load_data()

# -----------------------------------------------------------------
# 3. アプリの画面遷移ロジック
# -----------------------------------------------------------------
steps_names = ["1. 受付", "2. 視力・聴力検査", "3. 医師検診", "4. 教育相談・結果通知", "5. 終了"]
if st.session_state.step <= 5:
    st.progress((st.session_state.step - 1) / 4.0)
    st.caption(f"進捗状況: {steps_names[st.session_state.step - 1]}")

# 各ステップの描画
if st.session_state.step == 1:
    st.header("【第1ステップ】 受付")
    reception_info = df_settings[df_settings["type"] == "reception"].iloc[0]
    st.markdown(f"""
    **■ 受付場所**
    *   **{reception_info['venue']}**

    **■ ご案内**
    *   {reception_info['details']}
    """)
    if st.button("受付を完了し、番号札とクリアファイルを受け取りました"):
        st.session_state.step = 2
        st.rerun()

elif st.session_state.step == 2:
    st.header("【第2ステップ】 視力・聴力検査")
    st.write("お子様と一緒に以下の検査会場へお回りください。順番の指定はありません。空いている会場からお進みください。")

    tests = df_settings[df_settings["type"] == "test"]
    checkboxes = {}
    for idx, row in tests.iterrows():
        st.markdown(f"**■ {row['item_name']}（会場：{row['venue']}）**")
        st.write(row['details'])
        checkboxes[row['item_name']] = st.checkbox(f"{row['item_name']}を受診した", key=f"chk_{idx}")
        st.write("")

    all_tested = all(checkboxes.values())
    if st.button("次のステップ（医師による検診）へ進む", disabled=not all_tested):
        st.session_state.step = 3
        st.rerun()
    elif not all_tested:
        st.info("すべての検査の受診完了チェックを入れると、次のステップに進めます。")

elif st.session_state.step == 3:
    st.header("【第3ステップ】 医師による検診")
    st.write("以下の4つの検診をすべて受診してください。順番の指定はありません。混雑状況を見て、空いている会場からお回りください。")

    doctors = df_settings[df_settings["type"] == "doctor"]
    checkboxes = {}
    for idx, row in doctors.iterrows():
        st.markdown(f"**■ {row['item_name']}（会場：{row['venue']}）**")
        st.write(row['details'])
        checkboxes[row['item_name']] = st.checkbox(f"{row['item_name']}を受診した", key=f"chk_{idx}")
        st.write("")

    all_doctor_done = all(checkboxes.values())
    if st.button("次のステップ（教育相談・結果通知）へ進む", disabled=not all_doctor_done):
        st.session_state.step = 4
        st.rerun()
    elif not all_doctor_done:
        st.info("4つすべての検診の受診完了チェックを入れると、次のステップに進めます。")

elif st.session_state.step == 4:
    st.header("【第4ステップ】 教育相談・結果通知")
    st.write("健康診断の最終ステップです。クリアファイルと診断票を提出し、結果通知をお受け取りください。")

    # 教育相談
    opt_data = df_settings[df_settings["type"] == "optional"]
    if not opt_data.empty:
        opt_row = opt_data.iloc[0]
        st.markdown(f"**■ {opt_row['item_name']}（会場：{opt_row['venue']}）**")
        st.write(opt_row['details'])
        has_consultation = st.radio("教育相談の希望について：", ("希望しない / 相談は不要", "希望し、面談が完了した"))
        st.write("")

    # 結果通知
    final_data = df_settings[df_settings["type"] == "final"].iloc[0]
    st.markdown(f"**■ {final_data['item_name']}（会場：{final_data['venue']}）**")
    st.write(final_data['details'])
    checked_final = st.checkbox("結果通知を受け取り、すべての書類とクリアファイルを提出した")

    if st.button("健診を終了する", disabled=not checked_final):
        st.session_state.step = 5
        st.rerun()
    elif not checked_final:
        st.info("結果通知の受取チェックを入れると、終了画面に進めます。")

elif st.session_state.step == 5:
    st.balloons()
    st.header("健診がすべて終了しました")
    st.markdown("""
    お疲れ様でした。本日の就学時健康診断はすべて終了いたしました。

    **■ お帰りの際のご確認**
    *   クリアファイルや受付番号札の返却忘れはございませんか？
    *   お忘れ物がないか、身の回りをお確かめください。

    お気をつけてお帰りください。来年春のご入学を、職員一同心よりお待ちしております。
    """)
    if st.button("最初の画面に戻る（次の受診者のためにリセット）"):
        st.session_state.step = 1
        st.rerun()
