import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import platform
import numpy as np

# --- 🛠 日本語フォント設定 ---
plt.rcParams["axes.unicode_minus"] = False
if platform.system() == "Darwin":
    plt.rcParams["font.family"] = "Hiragino Sans"
elif platform.system() == "Windows":
    plt.rcParams["font.family"] = "Yu Gothic"
else:
    plt.rcParams["font.family"] = "TakaoPGothic"


# --- 📊 データ読み込み ---
def load_and_clean_csv(filename, set_index=None):
    try:
        df = pd.read_csv(filename, encoding="utf-8-sig")
        df.columns = df.columns.str.strip()
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].str.strip()
        if set_index:
            df = df.set_index(set_index)
        return df
    except Exception as e:
        print(f"ファイル {filename} の読み込みに失敗しました: {e}")
        return pd.DataFrame()


df_char = load_and_clean_csv("キャラ.csv", set_index="キャラ名")
df_class = load_and_clean_csv("クラス.csv", set_index="クラス名")
df_init = load_and_clean_csv("初期パラメーター.csv")
df_class_base = load_and_clean_csv("クラス基本値.csv", set_index="クラス名")

STATS_COLUMNS = ["HP", "力", "魔力", "技", "速さ", "幸運", "守備", "魔防"]

# カムイ長短補正（画像反映）
K_GOOD_TABLE = {
    "HP": {"HP": 15, "守備": 5, "魔防": 5},
    "力": {"力": 15, "技": 5, "守備": 5},
    "魔力": {"魔力": 20, "速さ": 5, "魔防": 5},
    "技": {"力": 5, "技": 25, "守備": 5},
    "速さ": {"技": 5, "速さ": 15, "幸運": 5},
    "幸運": {"力": 5, "魔力": 5, "幸運": 25},
    "守備": {"幸運": 5, "守備": 10, "魔防": 5},
    "魔防": {"魔力": 5, "速さ": 5, "魔防": 10}
}
K_BAD_TABLE = {
    "HP": {"HP": -10, "守備": -5, "魔防": -5},
    "力": {"力": -10, "技": -5, "守備": -5},
    "魔力": {"魔力": -15, "速さ": -5, "魔防": -5},
    "技": {"力": -5, "技": -20, "守備": -5},
    "速さ": {"技": -5, "速さ": -10, "幸運": -5},
    "幸運": {"力": -5, "魔力": -5, "幸運": -20},
    "守備": {"幸運": -5, "守備": -10, "魔防": -5},
    "魔防": {"魔力": -5, "速さ": -5, "魔防": -10}
}


class GrowthApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FE if 期待値シミュレーター (グラフ表示改善版)")
        self.root.geometry("1400x950")
        self.intervals = []
        self.create_widgets()
        if not df_char.empty:
            self.cb_char.current(0)
            self.on_char_selected()

    def create_widgets(self):
        left_canvas = tk.Canvas(self.root, width=420)
        left_scroll = ttk.Scrollbar(self.root, orient="vertical", command=left_canvas.yview)
        left_frame = tk.Frame(left_canvas, padx=10, pady=10)
        left_canvas.create_window((0, 0), window=left_frame, anchor="nw")
        left_canvas.configure(yscrollcommand=left_scroll.set)
        left_canvas.pack(side=tk.LEFT, fill=tk.Y)
        left_scroll.pack(side=tk.LEFT, fill=tk.Y)

        # 1. ユニット設定
        tk.Label(left_frame, text="【1. ユニット設定】", font=("", 10, "bold")).pack(anchor="w")
        self.cb_char = self._create_combo_simple(left_frame, "キャラ名:", list(df_char.index))
        self.cb_char.bind("<<ComboboxSelected>>", self.on_char_selected)
        self.cb_category = self._create_combo_simple(left_frame, "カテゴリ:", [])
        self.cb_category.bind("<<ComboboxSelected>>", self.on_category_selected)

        # 2. カムイ補正
        tk.Label(left_frame, text="\n【2. カムイ長所・短所】", font=("", 10, "bold")).pack(anchor="w")
        self.cb_good = self._create_combo_simple(left_frame, "長所:", ["（なし）"] + STATS_COLUMNS)
        self.cb_bad = self._create_combo_simple(left_frame, "短所:", ["（なし）"] + STATS_COLUMNS)
        for cb in [self.cb_good, self.cb_bad]:
            cb.bind("<<ComboboxSelected>>", lambda e: self.update_rate_graph())

        # 3. 補正親
        tk.Label(left_frame, text="\n【3. 成長率補正用の親 (子世代用)】", font=("", 10, "bold")).pack(anchor="w")
        self.cb_parent_growth = ttk.Combobox(left_frame, values=["（なし）"] + list(df_char.index), state="readonly")
        self.cb_parent_growth.pack(fill=tk.X, pady=2);
        self.cb_parent_growth.current(0)
        self.cb_parent_growth.bind("<<ComboboxSelected>>", lambda e: self.update_rate_graph())

        # 4. 親パラメータ
        tk.Label(left_frame, text="\n【4. 親の現在値 (遺伝用)】", font=("", 10, "bold")).pack(anchor="w")
        self.father_entries = self._create_stat_inputs(left_frame)
        self.mother_entries = self._create_stat_inputs(left_frame)

        # 5. 加入Lv & ルート
        tk.Label(left_frame, text="\n【5. 加入Lv & 育成ルート】", font=("", 10, "bold")).pack(anchor="w")
        row_lv = tk.Frame(left_frame);
        row_lv.pack(fill=tk.X)
        tk.Label(row_lv, text="加入Lv:").pack(side=tk.LEFT)
        self.ent_start = tk.Entry(row_lv, width=6);
        self.ent_start.pack(side=tk.LEFT)
        tk.Label(row_lv, text=" ～ 終了Lv:").pack(side=tk.LEFT)
        self.ent_end = tk.Entry(row_lv, width=6);
        self.ent_end.insert(0, "20");
        self.ent_end.pack(side=tk.LEFT)

        self.cb_route_class = ttk.Combobox(left_frame, values=list(df_class.index), state="readonly")
        self.cb_route_class.pack(fill=tk.X, pady=2)
        tk.Button(left_frame, text="ルートに追加", command=self.add_interval).pack(fill=tk.X)
        self.listbox = tk.Listbox(left_frame, height=4);
        self.listbox.pack(fill=tk.X)
        tk.Button(left_frame, text="全削除", command=self.clear_intervals).pack(fill=tk.X)

        tk.Button(left_frame, text="📊 期待値計算を実行", command=self.calculate_expectations, bg="#e1f5fe",
                  height=2).pack(fill=tk.X, pady=10)
        left_frame.update_idletasks();
        left_canvas.config(scrollregion=left_canvas.bbox("all"))

        right_frame = tk.Frame(self.root);
        right_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)
        self.fig, self.ax_rate = plt.subplots(figsize=(6, 3));
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_frame);
        self.canvas.get_tk_widget().pack(fill=tk.X)
        self.tree = ttk.Treeview(right_frame, columns=["区分"] + STATS_COLUMNS, show="headings", height=22)
        for col in ["区分"] + STATS_COLUMNS: self.tree.heading(col, text=col); self.tree.column(col, width=80,
                                                                                                anchor="center")
        self.tree.pack(expand=True, fill=tk.BOTH, padx=10, pady=5)

    def _create_combo_simple(self, parent, label, values):
        tk.Label(parent, text=label).pack(anchor="w")
        cb = ttk.Combobox(parent, values=values, state="readonly")
        cb.pack(fill=tk.X, pady=2);
        return cb

    def _create_stat_inputs(self, parent):
        frame = tk.Frame(parent);
        frame.pack(fill=tk.X);
        entries = {}
        for i, stat in enumerate(STATS_COLUMNS):
            r, c = divmod(i, 4);
            tk.Label(frame, text=stat, width=4).grid(row=r * 2, column=c)
            ent = tk.Entry(frame, width=6);
            ent.grid(row=r * 2 + 1, column=c, padx=2);
            entries[stat] = ent
        return entries

    def on_char_selected(self, event=None):
        char_name = self.cb_char.get()
        matched = df_init[df_init["キャラ名"] == char_name]
        cats = [c for c in matched["カテゴリ"].unique().tolist() if str(c) != 'nan']
        self.cb_category.config(values=cats)
        if cats:
            self.cb_category.current(0)
            self.on_category_selected()

    def on_category_selected(self, event=None):
        char_name = self.cb_char.get()
        category = self.cb_category.get()
        match = df_init[(df_init["キャラ名"] == char_name) & (df_init["カテゴリ"] == category)]
        self.ent_start.delete(0, tk.END)
        if not match.empty:
            csv_lv = int(match.iloc[0]["Lv"])
            is_parent_gen = any(r in category for r in ["白夜", "暗夜", "透魔", "共通"])
            self.ent_start.insert(0, str(csv_lv) if is_parent_gen else "10")
        self.update_rate_graph()

    def get_kamui_growth_bonus(self):
        bonus = pd.Series(0, index=STATS_COLUMNS)
        good, bad = self.cb_good.get(), self.cb_bad.get()
        if good in K_GOOD_TABLE:
            for s, v in K_GOOD_TABLE[good].items(): bonus[s] += v
        if bad in K_BAD_TABLE:
            for s, v in K_BAD_TABLE[bad].items(): bonus[s] += v
        return bonus

    def update_rate_graph(self):
        """成長率をグラフ化し、バーの上に%を表示する"""
        char_name = self.cb_char.get()
        cat = self.cb_category.get()
        p_name = self.cb_parent_growth.get()
        if not char_name: return
        is_parent_gen = any(r in cat for r in ["白夜", "暗夜", "透魔", "共通"])

        try:
            base = df_char.loc[char_name, STATS_COLUMNS].copy()
            if char_name == "カムイ": base += self.get_kamui_growth_bonus()

            p_bonus = pd.Series(0, index=STATS_COLUMNS)
            if not is_parent_gen and p_name != "（なし）":
                p_base = df_char.loc[p_name, STATS_COLUMNS].copy()
                if p_name == "カムイ": p_base += self.get_kamui_growth_bonus()
                p_bonus = p_base // 2

            total = base + p_bonus
            self.ax_rate.clear()
            x = range(len(STATS_COLUMNS))

            # バーの描画
            self.ax_rate.bar(x, base, label="本体成長率", color="#bbdefb")
            if p_bonus.sum() > 0:
                self.ax_rate.bar(x, p_bonus, bottom=base, label="親補正", color="#ffcdd2")

            # 数値（%）の表示
            for i, v in enumerate(total):
                self.ax_rate.text(i, v + 2, f"{int(v)}%", ha='center', fontweight='bold')

            self.ax_rate.set_title(f"合計成長率: {char_name}")
            self.ax_rate.set_xticks(x)
            self.ax_rate.set_xticklabels(STATS_COLUMNS)
            self.ax_rate.set_ylim(0, 160)  # 縦軸を160%までに固定
            self.ax_rate.legend(loc='upper right')
            self.canvas.draw()
        except:
            pass

    def calculate_expectations(self):
        char_name = self.cb_char.get();
        category = self.cb_category.get();
        parent_name = self.cb_parent_growth.get()
        if not char_name or not self.intervals: return
        for item in self.tree.get_children(): self.tree.delete(item)

        try:
            match = df_init[(df_init["キャラ名"] == char_name) & (df_init["カテゴリ"] == category)]
            row = match.iloc[0];
            csv_init_lv = int(row["Lv"]);
            csv_stats = row[STATS_COLUMNS].astype(float)
            is_parent_gen = any(r in category for r in ["白夜", "暗夜", "透魔", "共通"])

            char_growth = df_char.loc[char_name, STATS_COLUMNS].copy()
            if char_name == "カムイ": char_growth += self.get_kamui_growth_bonus()
            p_growth = df_char.loc[parent_name, STATS_COLUMNS].copy() if parent_name != "（なし）" else 0
            if parent_name == "カムイ": p_growth += self.get_kamui_growth_bonus()
            total_growth = char_growth + (p_growth // 2 if not is_parent_gen and parent_name != "（なし）" else 0)

            join_lv = int(self.ent_start.get())
            first_int = self.intervals[0];
            join_cls = first_int["class"]

            if not is_parent_gen and parent_name != "（なし）":
                f_s = self._get_input_stats(self.father_entries);
                m_s = self._get_input_stats(self.mother_entries)
                gene = np.minimum(((f_s - csv_stats).clip(lower=0) + (m_s - csv_stats).clip(lower=0)) / 4,
                                  2 + (csv_stats / 10))
                curr = csv_stats + df_class_base.loc[join_cls, STATS_COLUMNS].astype(float) + gene
                if join_lv > 10: curr += ((total_growth + df_class.loc[join_cls, STATS_COLUMNS]) / 100.0) * (
                            join_lv - 10)
            else:
                curr = csv_stats.copy()
                if join_lv > csv_init_lv: curr += ((total_growth + df_class.loc[join_cls, STATS_COLUMNS]) / 100.0) * (
                            join_lv - csv_init_lv)

            self.tree.insert("", tk.END, values=[f"加入時 ({join_lv})"] + [f"{v:.2f}" for v in curr], tags=('bold',))
            for itm in self.intervals:
                lv_up = itm["end"] - itm["start"]
                if lv_up > 0:
                    curr += ((total_growth + df_class.loc[itm["class"], STATS_COLUMNS]) / 100.0) * lv_up
                    self.tree.insert("", tk.END,
                                     values=[f"Lv.{itm['end']} ({itm['class']})"] + [f"{v:.2f}" for v in curr])
            self.tree.tag_configure('bold', background="#e1f5fe", font=("", 10, "bold"))
        except Exception as e:
            messagebox.showerror("計算エラー", str(e))

    def _get_input_stats(self, entries):
        res = []
        for stat in STATS_COLUMNS:
            v = entries[stat].get();
            res.append(float(v) if v else 0.0)
        return pd.Series(res, index=STATS_COLUMNS)

    def add_interval(self):
        try:
            s, e, cls = int(self.ent_start.get()), int(self.ent_end.get()), self.cb_route_class.get()
            if cls:
                self.intervals.append({"start": s, "end": e, "class": cls})
                self.listbox.insert(tk.END, f"Lv.{s}-{e}: {cls}")
                self.ent_start.delete(0, tk.END);
                self.ent_start.insert(0, str(e))
                self.ent_end.delete(0, tk.END);
                self.ent_end.insert(0, str(e + 20))
        except:
            pass

    def clear_intervals(self):
        self.intervals = [];
        self.listbox.delete(0, tk.END)


if __name__ == "__main__":
    root = tk.Tk();
    app = GrowthApp(root);
    root.mainloop()