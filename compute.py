import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import platform

# --- 🛠 基本設定 ---
plt.rcParams["axes.unicode_minus"] = False
if platform.system() == "Darwin":
    plt.rcParams["font.family"] = "Hiragino Sans"
elif platform.system() == "Windows":
    plt.rcParams["font.family"] = "Yu Gothic"
else:
    plt.rcParams["font.family"] = "TakaoPGothic"

GROWTH_CORRECTIONS = {
    "HP": [15, 0, 0, 0, 0, 0, 0, 0],
    "力": [0, 15, 0, 5, 0, 0, 5, 0],
    "魔力": [0, 0, 15, 0, 5, 0, 0, 5],
    "技": [0, 5, 0, 15, 0, 0, 5, 0],
    "速さ": [0, 0, 5, 5, 15, 0, 0, 0],
    "幸運": [0, 0, 5, 0, 0, 15, 0, 5],
    "守備": [0, 0, 0, 0, 0, 5, 10, 5],
    "魔防": [0, 0, 5, 0, 0, 0, 5, 10],
    "（なし）": [0, 0, 0, 0, 0, 0, 0, 0]
}

STATS_COLUMNS = ["HP", "力", "魔力", "技", "速さ", "幸運", "守備", "魔防"]


def load_and_clean_csv(filename, set_index=None):
    try:
        df = pd.read_csv(filename, encoding="utf-8-sig")
        df.columns = df.columns.str.strip()
        if set_index: df = df.set_index(set_index)
        return df
    except:
        return pd.DataFrame()


df_char = load_and_clean_csv("キャラ.csv", set_index="キャラ名")
df_class = load_and_clean_csv("クラス.csv", set_index="クラス名")
df_init = load_and_clean_csv("初期パラメーター.csv")
df_class_base = load_and_clean_csv("クラス基本値.csv", set_index="クラス名")


class GrowthApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FE if 総合期待値シミュレーター (加入時CC対応)")
        self.root.geometry("1900x1050")
        self.intervals = []
        self.selected_char = ""
        self.selected_category = ""
        self.create_widgets()

    def _get_modified_personal_growth(self, char_name):
        if char_name not in df_char.index: return pd.Series(0.0, index=STATS_COLUMNS)
        base = df_char.loc[char_name, STATS_COLUMNS].astype(float).copy()
        if "カムイ" in char_name:
            good, bad = self.cb_good.get(), self.cb_bad.get()
            plus = pd.Series(GROWTH_CORRECTIONS.get(good, [0] * 8), index=STATS_COLUMNS)
            minus = pd.Series(GROWTH_CORRECTIONS.get(bad, [0] * 8), index=STATS_COLUMNS)
            base = base + plus - minus
        return base

    def create_widgets(self):
        top_frame = tk.Frame(self.root, pady=10);
        top_frame.pack(fill=tk.X)
        self._create_category_selection(top_frame)
        content_frame = tk.Frame(self.root, padx=15);
        content_frame.pack(fill=tk.BOTH, expand=True)

        left_panel = tk.Frame(content_frame, width=500, padx=10);
        left_panel.pack(side=tk.LEFT, fill=tk.Y)
        self.lbl_status = tk.Label(left_panel, text="キャラを選択してください", font=("", 14, "bold"), fg="#1a73e8")
        self.lbl_status.pack(anchor="w", pady=5)

        # カムイ長短
        kamui_frame = tk.LabelFrame(left_panel, text="カムイ得意・不得意設定", padx=10, pady=5);
        kamui_frame.pack(fill=tk.X, pady=5)
        self.cb_good = ttk.Combobox(kamui_frame, values=list(GROWTH_CORRECTIONS.keys()), state="readonly", width=12);
        self.cb_good.grid(row=0, column=1, padx=5);
        self.cb_good.current(0)
        self.cb_bad = ttk.Combobox(kamui_frame, values=list(GROWTH_CORRECTIONS.keys()), state="readonly", width=12);
        self.cb_bad.grid(row=0, column=3, padx=5);
        self.cb_bad.current(0)
        self.cb_good.bind("<<ComboboxSelected>>", lambda e: self.update_graph());
        self.cb_bad.bind("<<ComboboxSelected>>", lambda e: self.update_graph())

        # 親設定
        parent_frame = tk.LabelFrame(left_panel, text="子世代用：両親の設定", padx=10, pady=5);
        parent_frame.pack(fill=tk.X, pady=5)
        self.cb_parent_growth = ttk.Combobox(parent_frame, values=["（なし）"] + list(df_char.index), state="readonly")
        self.cb_parent_growth.pack(fill=tk.X, pady=2);
        self.cb_parent_growth.current(0)
        self.cb_parent_growth.bind("<<ComboboxSelected>>", lambda e: self.update_graph())
        self.father_stat_entries = self._create_stat_inputs(parent_frame, "父：ステータス")
        self.mother_stat_entries = self._create_stat_inputs(parent_frame, "母：ステータス")

        # ルート設定
        route_frame = tk.LabelFrame(left_panel, text="育成ルート設定", padx=10, pady=5);
        route_frame.pack(fill=tk.X, pady=5)
        lv_row = tk.Frame(route_frame);
        lv_row.pack(fill=tk.X)
        tk.Label(lv_row, text="開始Lv:").pack(side=tk.LEFT);
        self.ent_start = tk.Entry(lv_row, width=5);
        self.ent_start.pack(side=tk.LEFT)
        tk.Label(lv_row, text="→ 終了Lv:").pack(side=tk.LEFT);
        self.ent_end = tk.Entry(lv_row, width=5);
        self.ent_end.insert(0, "20");
        self.ent_end.pack(side=tk.LEFT)

        cls_row = tk.Frame(route_frame, pady=5);
        cls_row.pack(fill=tk.X)
        self.cb_class = ttk.Combobox(cls_row, values=["（クラス未選択）"] + list(df_class.index), state="readonly",
                                     width=20)
        self.cb_class.pack(side=tk.LEFT);
        self.cb_class.current(0)
        tk.Button(cls_row, text="追加", command=self.add_interval, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)

        self.listbox = tk.Listbox(left_panel, height=5);
        self.listbox.pack(fill=tk.X, pady=5)
        tk.Button(left_panel, text="📊 期待値計算実行", command=self.calculate_expectations, bg="#2196F3", fg="white",
                  font=("", 12, "bold"), height=2).pack(fill=tk.X, pady=5)
        tk.Button(left_panel, text="リセット", command=self.clear_intervals).pack(fill=tk.X)

        # グラフ・表
        right_panel = tk.Frame(content_frame);
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)
        self.fig, self.ax_rate = plt.subplots(figsize=(10, 4));
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_panel);
        self.canvas.get_tk_widget().pack(fill=tk.X)
        self.tree = ttk.Treeview(right_panel, columns=["区分"] + STATS_COLUMNS, show="headings", height=15)
        for col in ["区分"] + STATS_COLUMNS: self.tree.heading(col, text=col); self.tree.column(col, width=90,
                                                                                                anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True)

    def _create_category_selection(self, parent):
        configs = [("共通", "#9E9E9E", ["共通"]), ("白夜", "#2196F3", ["白夜"]), ("暗夜", "#F44336", ["暗夜"]),
                   ("透魔", "#00BCD4", ["透魔"]), ("子世代", "#FF9800", ["子", "外伝"])]
        for i, (title, color, keywords) in enumerate(configs):
            frame = tk.Frame(parent, bd=1, relief=tk.RIDGE);
            frame.grid(row=0, column=i, sticky="nsew", padx=3)
            tk.Label(frame, text=title, bg=color, fg="white", font=("", 10, "bold")).pack(fill=tk.X)
            canvas = tk.Canvas(frame, width=220, height=150, bg="white", highlightthickness=0);
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            content = tk.Frame(canvas, bg="white");
            canvas.create_window((0, 0), window=content, anchor="nw")
            mask = df_init["カテゴリ"].apply(lambda x: any(k in str(x) for k in keywords))
            for _, row in df_init[mask].iterrows():
                tk.Button(content, text=row["キャラ名"], width=18,
                          command=lambda n=row["キャラ名"], c=row["カテゴリ"]: self.select_unit(n, c)).pack()
            content.update_idletasks();
            canvas.config(scrollregion=canvas.bbox("all"));
            parent.columnconfigure(i, weight=1)

    def _create_stat_inputs(self, parent, label):
        tk.Label(parent, text=label, font=("", 8, "bold")).pack(anchor="w")
        f = tk.Frame(parent);
        f.pack(fill=tk.X)
        entries = {}
        for i, stat in enumerate(STATS_COLUMNS):
            r, c = divmod(i, 4);
            tk.Label(f, text=stat, width=3).grid(row=r, column=c * 2)
            e = tk.Entry(f, width=6);
            e.grid(row=r, column=c * 2 + 1, padx=1);
            entries[stat] = e
        return entries

    def select_unit(self, name, cat):
        self.selected_char, self.selected_category = name, cat
        match = df_init[(df_init["キャラ名"] == name) & (df_init["カテゴリ"] == cat)]
        if not match.empty:
            self.ent_start.delete(0, tk.END);
            self.ent_start.insert(0, str(int(match.iloc[0]["Lv"])))
        self.update_graph()

    def add_interval(self):
        try:
            s, e, cls = int(self.ent_start.get()), int(self.ent_end.get()), self.cb_class.get()
            if cls == "（クラス未選択）" or s > e: raise ValueError  # s==e を許可
            self.intervals.append({"start": s, "end": e, "class": cls})
            self.listbox.insert(tk.END, f"Lv.{s}→{e} ({cls})")
            self.ent_start.delete(0, tk.END);
            self.ent_start.insert(0, str(e))
        except:
            messagebox.showwarning("エラー", "レベル入力を確認してください。開始Lvは終了Lv以下である必要があります。")

    def clear_intervals(self):
        self.intervals = [];
        self.listbox.delete(0, tk.END)

    def update_graph(self):
        if not self.selected_char: return
        self.ax_rate.clear()
        personal_g = self._get_modified_personal_growth(self.selected_char)
        p_name = self.cb_parent_growth.get()
        p_bonus = self._get_modified_personal_growth(p_name) // 2 if p_name != "（なし）" else 0
        cls_name = self.cb_class.get()
        cls_bonus = df_class.loc[cls_name, STATS_COLUMNS].astype(float) if cls_name != "（クラス未選択）" else 0
        total = personal_g + p_bonus + cls_bonus
        x = range(len(STATS_COLUMNS))
        self.ax_rate.bar(x, personal_g, label="個人", color="#90caf9")
        self.ax_rate.bar(x, p_bonus, bottom=personal_g, label="親", color="#f48fb1")
        self.ax_rate.bar(x, cls_bonus, bottom=personal_g + p_bonus, label="クラス", color="#a5d6a7")
        self.ax_rate.set_xticks(x);
        self.ax_rate.set_xticklabels(STATS_COLUMNS);
        self.ax_rate.set_ylim(0, 200);
        self.canvas.draw()

    def calculate_expectations(self):
        if not self.selected_char or not self.intervals: return
        for item in self.tree.get_children(): self.tree.delete(item)
        try:
            # 1. 初期値の決定
            match = df_init[
                (df_init["キャラ名"] == self.selected_char) & (df_init["カテゴリ"] == self.selected_category)]
            curr = match.iloc[0][STATS_COLUMNS].astype(float).copy()

            # 子世代遺伝計算
            if any(k in self.selected_category for k in ["子", "外伝"]):
                f_s = pd.Series({s: float(self.father_stat_entries[s].get() or 0) for s in STATS_COLUMNS})
                m_s = pd.Series({s: float(self.mother_stat_entries[s].get() or 0) for s in STATS_COLUMNS})
                if f_s.sum() > 0 or m_s.sum() > 0:
                    genetic_bonus = ((f_s + m_s - curr * 2).clip(lower=0) / 4).clip(upper=(2 + curr / 10))
                    curr += genetic_bonus

            self.tree.insert("", tk.END, values=[f"加入(Lv.{self.intervals[0]['start']})"] + [f"{v:.2f}" for v in curr],
                             tags=('bold',))

            # 2. 育成ルート計算
            # ※加入時のデフォルトクラスを特定
            prev_class = self.intervals[0]['class']

            for i, itm in enumerate(self.intervals):
                current_class = itm["class"]

                # 【クラスチェンジ判定】
                # クラス名が前のクラスと異なる場合、補正を計算して「その時点のステータス」を出力
                if current_class != prev_class:
                    diff = df_class_base.loc[current_class, STATS_COLUMNS] - df_class_base.loc[
                        prev_class, STATS_COLUMNS]
                    curr += diff.astype(float)
                    # CC直後の実数値を表示
                    self.tree.insert("", tk.END, values=[f"→ {current_class} 変更後"] + [f"{v:.2f}" for v in curr],
                                     tags=('cc',))

                # 成長計算
                lv_diff = itm["end"] - itm["start"]
                if lv_diff > 0:
                    personal_g = self._get_modified_personal_growth(self.selected_char)
                    p_name = self.cb_parent_growth.get()
                    p_g = self._get_modified_personal_growth(p_name) // 2 if p_name != "（なし）" else 0
                    cls_g = df_class.loc[current_class, STATS_COLUMNS].astype(float)
                    curr += ((personal_g + p_g + cls_g) / 100.0) * lv_diff
                    self.tree.insert("", tk.END,
                                     values=[f"Lv.{itm['end']} ({current_class})"] + [f"{v:.2f}" for v in curr])

                prev_class = current_class

            self.tree.tag_configure('bold', background="#e3f2fd")
            self.tree.tag_configure('cc', background="#fff9c4")  # クラスチェンジ行を黄色で強調
        except Exception as e:
            messagebox.showerror("計算失敗", str(e))
if __name__ == "__main__":
    root = tk.Tk();
    app = GrowthApp(root);
    root.mainloop()