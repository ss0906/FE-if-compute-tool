import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
import matplotlib.font_manager as fm
import urllib.request

# --- 🛠 基本設定（Linux環境対応の日本語フォント自動ダウンロード） ---
plt.rcParams["axes.unicode_minus"] = False


@st.cache_resource
def load_japanese_font():
    """Linux環境（Streamlit Cloud）でも確実に日本語を表示するためのフォント設定"""
    # 信頼性の高いパブリックなNoto SansフォントのURL
    font_url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTC/NotoSansCJKjp-Regular.ttc"
    font_path = "NotoSansCJKjp-Regular.ttc"

    # ローカルにフォントがなければダウンロード
    if not os.path.exists(font_path):
        try:
            urllib.request.urlretrieve(font_url, font_path)
        except Exception as e:
            # ダウンロード失敗時はOSの標準フォントをフォールバックに指定
            return ["sans-serif", "Hiragino Sans", "Yu Gothic", "TakaoPGothic"]

    # フォントをMatplotlibに登録
    fm.fontManager.addfont(font_path)
    prop = fm.FontProperties(fname=font_path)
    return prop.get_name()


# 決定した日本語フォント名を適用
try:
    font_name = load_japanese_font()
    plt.rcParams["font.family"] = font_name
except:
    plt.rcParams["font.family"] = ["sans-serif", "Hiragino Sans", "Yu Gothic", "TakaoPGothic"]

# （これ以降の GROWTH_CORRECTIONS などのコードはそのまま）
GROWTH_CORRECTIONS = {
    "（なし）": [0, 0, 0, 0, 0, 0, 0, 0],
    "HP": [15, 0, 0, 0, 0, 0, 0, 0], "力": [0, 15, 0, 5, 0, 0, 5, 0], "魔力": [0, 0, 15, 0, 5, 0, 0, 5],
    "技": [0, 5, 0, 15, 0, 0, 5, 0], "速さ": [0, 0, 5, 5, 15, 0, 0, 0], "幸運": [0, 0, 5, 0, 0, 15, 0, 5],
    "守備": [0, 0, 0, 0, 0, 5, 10, 5], "魔防": [0, 0, 5, 0, 0, 0, 5, 10]
}
STATS_COLUMNS = ["HP", "力", "魔力", "技", "速さ", "幸運", "守備", "魔防"]
HISTORY_FILE = "history.csv"


# --- 💾 データ読み込み（キャッシュ化） ---
@st.cache_data
def load_and_clean_csv(filename, set_index=None):
    try:
        df = pd.read_csv(filename, encoding="utf-8-sig")
        df.columns = df.columns.str.strip()
        if set_index:
            df = df.set_index(set_index)
        return df
    except:
        return pd.DataFrame()


df_char = load_and_clean_csv("キャラ.csv", set_index="キャラ名")
df_class = load_and_clean_csv("クラス.csv", set_index="クラス名")
df_init = load_and_clean_csv("初期パラメーター.csv")
df_class_base = load_and_clean_csv("クラス基本値.csv", set_index="クラス名")
df_class_limit = load_and_clean_csv("クラス上限値.csv", set_index="クラス名")


# --- 🛠 ヘルパー関数 ---
def get_modified_personal_growth(char_name, good, bad):
    if char_name not in df_char.index:
        return pd.Series(0.0, index=STATS_COLUMNS)
    base = df_char.loc[char_name, STATS_COLUMNS].astype(float).copy()
    if "カムイ" in char_name:
        base += pd.Series(GROWTH_CORRECTIONS.get(good, [0] * 8), index=STATS_COLUMNS)
        base -= pd.Series(GROWTH_CORRECTIONS.get(bad, [0] * 8), index=STATS_COLUMNS)
    return base


# 履歴の管理
if "intervals" not in st.session_state:
    st.session_state.intervals = []
if "current_char" not in st.session_state:
    st.session_state.current_char = None
if "current_lv" not in st.session_state:
    st.session_state.current_lv = 1

# --- 📱 UI 構築 ---
st.title("⚔️ FE if 期待値シミュレーター (Mobile Opt)")

# --- 👈 サイドバー（設定・ルート構築・履歴管理） ---
with st.sidebar:
    st.header("🛠 育成設定")

    # 1. カムイ設定
    st.subheader("カムイ得意/不得意")
    cb_good = st.selectbox("得意", list(GROWTH_CORRECTIONS.keys()), index=0, key="good")
    cb_bad = st.selectbox("不得意", list(GROWTH_CORRECTIONS.keys()), index=0, key="bad")

    # 2. 子世代用設定
    st.subheader("子世代用：両親設定")
    parent_list = ["（なし）"] + list(df_char.index) if not df_char.empty else ["（なし）"]
    cb_parent = st.selectbox("親候補（成長率用）", parent_list, index=0)

    st.write("子世代初期値補正用ステータス:")
    f_cols = st.columns(4)
    m_cols = st.columns(4)
    father_stats = {}
    mother_stats = {}

    for i, s in enumerate(STATS_COLUMNS):
        with f_cols[i % 4]:
            father_stats[s] = st.number_input(f"父:{s}", min_value=0, max_value=60, value=0, step=1, key=f"f_{s}")
        with m_cols[i % 4]:
            mother_stats[s] = st.number_input(f"母:{s}", min_value=0, max_value=60, value=0, step=1, key=f"m_{s}")

    st.markdown("---")

    # 3. ルート構築
    st.header("🗺 ルート構築")
    if not df_class.empty:
        selected_class = st.selectbox("クラス選択", list(df_class.index))
    else:
        selected_class = st.selectbox("クラス選択", ["（データなし）"])

    c1, c2 = st.columns(2)
    with c1:
        ent_start = st.number_input("開始Lv", min_value=1, max_value=40, value=st.session_state.current_lv)
    with c2:
        ent_end = st.number_input("終了Lv", min_value=1, max_value=40, value=20)

    if st.button("➕ ルートに追加", use_container_width=True):
        st.session_state.intervals.append({"start": ent_start, "end": ent_end, "class": selected_class})
        st.session_state.current_lv = ent_end  # 次の開始Lvを自動セット
        st.rerun()

    # ルートの表示と削除
    if st.session_state.intervals:
        st.write("現在のルート一覧:")
        for idx, itm in enumerate(st.session_state.intervals):
            st.caption(f"[{idx + 1}] Lv.{itm['start']} ➔ {itm['end']} ({itm['class']})")

        if st.button("🗑 選択ルートを全削除", type="secondary", use_container_width=True):
            st.session_state.intervals = []
            if st.session_state.current_char:
                mask = df_init["キャラ名"] == st.session_state.current_char
                if not df_init[mask].empty:
                    st.session_state.current_lv = int(df_init[mask].iloc[0]["Lv"])
            st.rerun()

# --- 🏢 メインコンテンツ ---

# 1. キャラクター選択（スマホで押しやすいようタブ形式に変更）
st.header("👤 キャラクター選択")
tabs = st.tabs(["共通", "白夜", "暗夜", "透魔", "子世代"])
keywords = ["共通", "白夜", "暗夜", "透魔", "子|外伝"]

selected_unit_data = None

for tab, kw in zip(tabs, keywords):
    with tab:
        if not df_init.empty:
            mask = df_init["カテゴリ"].str.contains(kw, na=False)
            sub_df = df_init[mask]

            # スマホ対応：ボタンをグリッド状に配置
            cols = st.columns(3)  # 画面幅に合わせて3列配置
            for idx, row in enumerate(sub_df.iterrows()):
                name = row[1]["キャラ名"]
                with cols[idx % 3]:
                    if st.button(name, key=f"btn_{kw}_{name}", use_container_width=True):
                        st.session_state.current_char = name
                        st.session_state.current_lv = int(row[1]["Lv"])
        else:
            st.warning("CSVデータが読み込めていません。")

if st.session_state.current_char:
    mask = df_init["キャラ名"] == st.session_state.current_char
    selected_unit_data = df_init[mask].iloc[0]
    st.info(
        f"現在の選択: **{st.session_state.current_char}** ({selected_unit_data['カテゴリ']}) - 初期Lv.{int(selected_unit_data['Lv'])}")
else:
    st.warning("キャラクターを選択してください。")

# 2. 📊 成長率グラフ表示
if st.session_state.current_char and not df_char.empty:
    st.subheader("📈 選択中の合計成長率")

    pg = get_modified_personal_growth(st.session_state.current_char, cb_good, cb_bad)

    fig, ax = plt.subplots(figsize=(10, 4))

    if cb_parent != "（なし）":
        p_g = get_modified_personal_growth(cb_parent, cb_good, cb_bad)
        char_growth = (pg + p_g) / 2
        ax.bar(STATS_COLUMNS, pg / 2, label="個人/2", color="#90caf9")
        ax.bar(STATS_COLUMNS, p_g / 2, bottom=pg / 2, label="親/2", color="#f48fb1")
        bottom_val = (pg / 2) + (p_g / 2)
    else:
        char_growth = pg
        ax.bar(STATS_COLUMNS, pg, label="個人", color="#90caf9")
        bottom_val = pg

    cl_g = df_class.loc[selected_class, STATS_COLUMNS].astype(float) if (
                not df_class.empty and selected_class in df_class.index) else 0
    total_rates = char_growth + cl_g
    ax.bar(STATS_COLUMNS, cl_g, bottom=bottom_val, label="クラス", color="#a5d6a7")

    for i, total in enumerate(total_rates):
        ax.text(i, total + 2, f"{int(total)}%", ha='center', fontweight='bold', fontsize=9)

    ax.set_ylabel("成長率 (%)")
    ax.set_ylim(0, 220)
    ax.legend(loc="upper right")
    st.pyplot(fig)

# 3. 📝 期待値計算と結果表示
st.markdown("---")
st.header("🧮 期待値計算結果")

if st.button("📊 期待値計算を実行", type="primary", use_container_width=True):
    if selected_unit_data is not None and st.session_state.intervals:
        curr = selected_unit_data[STATS_COLUMNS].astype(float).copy()

        # 子世代初期値補正
        if any(k in selected_unit_data["カテゴリ"] for k in ["子", "外伝"]):
            fs = pd.Series({s: float(father_stats[s]) for s in STATS_COLUMNS})
            ms = pd.Series({s: float(mother_stats[s]) for s in STATS_COLUMNS})
            if fs.sum() > 0 or ms.sum() > 0:
                curr += ((fs + ms - curr * 2).clip(lower=0) / 4).clip(upper=(2 + curr / 10))

        results = []
        prev_cls = st.session_state.intervals[0]['class']

        # 初期状態
        results.append(["初期値", f"初期({prev_cls})"] + [f"{v:.2f}" for v in curr])

        # ルート計算
        for itm in st.session_state.intervals:
            if itm['class'] != prev_cls:
                if not df_class_base.empty:
                    curr = curr + (df_class_base.loc[itm['class'], STATS_COLUMNS] - df_class_base.loc[
                        prev_cls, STATS_COLUMNS])
                prev_cls = itm['class']

            diff = itm['end'] - itm['start']
            if diff > 0 and not df_class.empty:
                pg = get_modified_personal_growth(st.session_state.current_char, cb_good, cb_bad)
                if cb_parent != "（なし）":
                    p_g = get_modified_personal_growth(cb_parent, cb_good, cb_bad)
                    char_growth = (pg + p_g) / 2
                else:
                    char_growth = pg

                curr += (char_growth + df_class.loc[itm['class'], STATS_COLUMNS]) / 100.0 * diff

            # カンスト処理
            if not df_class_limit.empty and itm['class'] in df_class_limit.index:
                limit = df_class_limit.loc[itm['class'], STATS_COLUMNS]
                curr = curr.clip(upper=limit)

            results.append([f"Lv.{itm['end']}", f"({itm['class']})"] + [f"{v:.2f}" for v in curr])

        # 結果をデータフレーム化してスマホでも見やすくスクロール表示
        res_df = pd.DataFrame(results, columns=["レベル", "クラス"] + STATS_COLUMNS)
        st.dataframe(res_df, use_container_width=True)

        # 履歴保存用のセッション状態
        st.session_state.last_result = curr.copy()
        st.session_state.last_route = f"[{selected_unit_data['カテゴリ']}] " + "➔".join(
            [f"{i['class']}{i['end']}" for i in st.session_state.intervals])
    else:
        st.warning("キャラクターを選択し、育成ルートを1つ以上追加してください。")

# 4. 💾 履歴の保存と管理
st.markdown("---")
st.subheader("📥 履歴機能")

if "last_result" in st.session_state:
    if st.button("💾 この結果を履歴に保存", use_container_width=True):
        new_history = pd.DataFrame([{
            "名前": st.session_state.current_char,
            "ルート情報": st.session_state.last_route,
            **{s: round(st.session_state.last_result[s], 1) for s in STATS_COLUMNS}
        }])

        if os.path.exists(HISTORY_FILE):
            try:
                old_h = pd.read_csv(HISTORY_FILE, encoding="utf-8-sig")
                df_total = pd.concat([old_h, new_history], ignore_index=True)
            except:
                df_total = new_history
        else:
            df_total = new_history

        df_total.to_csv(HISTORY_FILE, index=False, encoding="utf-8-sig")
        st.success("履歴を保存しました！")

# 保存されている履歴の表示
if os.path.exists(HISTORY_FILE):
    try:
        df_h = pd.read_csv(HISTORY_FILE, encoding="utf-8-sig")
        if not df_h.empty:
            st.write("📋 保存済みの履歴一覧")
            st.dataframe(df_h, use_container_width=True)
            if st.button("🗑 履歴ファイルをすべて削除", type="secondary"):
                os.remove(HISTORY_FILE)
                st.success("履歴を削除しました。画面を更新してください。")
    except:
        pass