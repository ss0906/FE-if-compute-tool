import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import platform
import sys

# --- 🛠 基本設定 & フォント対策 ---
plt.rcParams["axes.unicode_minus"] = False
if platform.system() == "Darwin":
    plt.rcParams["font.family"] = "Hiragino Sans"
elif platform.system() == "Windows":
    plt.rcParams["font.family"] = "Yu Gothic"
else:
    plt.rcParams["font.family"] = "TakaoPGothic"

GROWTH_CORRECTIONS = {
    "HP": [15, 0, 0, 0, 0, 0, 0, 0], "力": [0, 15, 0, 5, 0, 0, 5, 0], "魔力": [0, 0, 15, 0, 5, 0, 0, 5],
    "技": [0, 5, 0, 15, 0, 0, 5, 0], "速さ": [0, 0, 5, 5, 15, 0, 0, 0], "幸運": [0, 0, 5, 0, 0, 15, 0, 5],
    "守備": [0, 0, 0, 0, 0, 5, 10, 5], "魔防": [0, 0, 5, 0, 0, 0, 5, 10], "（なし）": [0, 0, 0, 0, 0, 0, 0, 0]
}
STATS_COLUMNS = ["HP", "力", "魔力", "技", "速さ", "幸運", "守備", "魔防"]


def load_and_clean_csv(filename, set_index=None):
    try:
        df = pd.read_csv(filename, encoding="utf-8-sig")
        df.columns = df.columns.str.strip()
        if set_index: df = df.set_index(set_index)
        return df
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return pd.DataFrame()


# データの読み込み
df_char = load_and_clean_csv("キャラ.csv", set_index="キャラ名")
df_class = load_and_clean_csv("クラス.csv", set_index="クラス名")
df_init = load_and_clean_csv("初期パラメーター.csv")
df_class_base = load_and_clean_csv("クラス基本値.csv", set_index="クラス名")
df_class_limit = load_and_clean_csv("クラス上限値.csv", set_index="クラス名")


class GrowthApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FE if 期待値シミュレーター (ルート別初期値対応版)")
        self.root.geometry("1900x1050")

        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

        self.intervals = []
        self.selected_char = ""
        self.selected_category_full = ""  # 実際の「暗夜12章加入」などの文字列
        self.current_unit_data = None  # 選択されたルートの初期値行
        self.selected_class = tk.StringVar(value="（未選択）")

        self.create_widgets()

    def exit_app(self):
        if messagebox.askokcancel("終了確認", "シミュレーターを終了しますか？"):
            self.root.destroy()
            sys.exit()

    def _get_modified_personal_growth(self, char_name):
        if char_name not in df_char.index: return pd.Series(0.0, index=STATS_COLUMNS)
        base = df_char.loc[char_name, STATS_COLUMNS].astype(float).copy()
        if "カムイ" in char_name:
            good, bad = self.cb_good.get(), self.cb_bad.get()
            base += pd.Series(GROWTH_CORRECTIONS.get(good, [0] * 8), index=STATS_COLUMNS)
            base -= pd.Series(GROWTH_CORRECTIONS.get(bad, [0] * 8), index=STATS_COLUMNS)
        return base

    def create_widgets(self):
        # 1. 上部：キャラ選択 (ルート判別対応)
        top_frame = tk.Frame(self.root, pady=10);
        top_frame.pack(fill=tk.X)
        configs = [("共通", "#9E9E9E", "共通"), ("白夜", "#2196F3", "白夜"),
                   ("暗夜", "#F44336", "暗夜"), ("透魔", "#00BCD4", "透魔"),
                   ("子世代", "#FF9800", "子|外伝")]

        for i, (title, color, kw) in enumerate(configs):
            frame = tk.Frame(top_frame, bd=1, relief=tk.RIDGE);
            frame.grid(row=0, column=i, sticky="nsew", padx=3)
            tk.Label(frame, text=title, bg=color, fg="white", font=("", 10, "bold")).pack(fill=tk.X)
            can = tk.Canvas(frame, width=220, height=140, bg="white", highlightthickness=0);
            can.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scr = ttk.Scrollbar(frame, orient="vertical", command=can.yview);
            scr.pack(side=tk.RIGHT, fill=tk.Y);
            can.configure(yscrollcommand=scr.set)
            content = tk.Frame(can, bg="white");
            can.create_window((0, 0), window=content, anchor="nw")

            mask = df_init["カテゴリ"].str.contains(kw, na=False)
            for _, row in df_init[mask].iterrows():
                tk.Button(content, text=row["キャラ名"], width=20,
                          command=lambda n=row["キャラ名"], k=kw: self.select_unit(n, k)).pack(pady=1)

            content.bind("<Configure>", lambda e, c=can: c.configure(scrollregion=c.bbox("all")))
            self._bind_mousewheel(can);
            top_frame.columnconfigure(i, weight=1)

        content_frame = tk.Frame(self.root, padx=15);
        content_frame.pack(fill=tk.BOTH, expand=True)

        # 2. 左パネル (操作エリア)
        left_panel = tk.Frame(content_frame, width=650, padx=15);
        left_panel.pack(side=tk.LEFT, fill=tk.Y)
        left_panel.pack_propagate(False)

        self.lbl_status = tk.Label(left_panel, text="キャラを選択してください", font=("", 16, "bold"), fg="#1a73e8")
        self.lbl_status.pack(anchor="w", pady=5)

        # 設定
        settings_f = tk.Frame(left_panel);
        settings_f.pack(fill=tk.X)
        kamui_f = tk.LabelFrame(settings_f, text="カムイ得意・不得意", padx=10, pady=5);
        kamui_f.pack(fill=tk.X, pady=5)
        self.cb_good = ttk.Combobox(kamui_f, values=list(GROWTH_CORRECTIONS.keys()), state="readonly", width=12);
        self.cb_good.grid(row=0, column=1);
        self.cb_good.current(0)
        self.cb_bad = ttk.Combobox(kamui_f, values=list(GROWTH_CORRECTIONS.keys()), state="readonly", width=12);
        self.cb_bad.grid(row=0, column=3);
        self.cb_bad.current(0)
        for cb in [self.cb_good, self.cb_bad]: cb.bind("<<ComboboxSelected>>", lambda e: self.update_graph())

        parent_f = tk.LabelFrame(settings_f, text="子世代用：両親設定", padx=10, pady=5);
        parent_f.pack(fill=tk.X, pady=5)
        self.cb_parent_growth = ttk.Combobox(parent_f, values=["（なし）"] + list(df_char.index), state="readonly");
        self.cb_parent_growth.pack(fill=tk.X);
        self.cb_parent_growth.current(0)
        self.cb_parent_growth.bind("<<ComboboxSelected>>", lambda e: self.update_graph())
        self.father_stat_entries = self._create_stat_inputs(parent_f, "父：ステータス")
        self.mother_stat_entries = self._create_stat_inputs(parent_f, "母：ステータス")

        # クラス選択
        class_sel_f = tk.LabelFrame(left_panel, text="クラス一括選択", padx=10, pady=5);
        class_sel_f.pack(fill=tk.BOTH, expand=True, pady=5)
        can_cl = tk.Canvas(class_sel_f, bg="white", highlightthickness=0);
        can_cl.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scr_cl = ttk.Scrollbar(class_sel_f, orient="vertical", command=can_cl.yview);
        scr_cl.pack(side=tk.RIGHT, fill=tk.Y);
        can_cl.configure(yscrollcommand=scr_cl.set)
        inner_cl = tk.Frame(can_cl, bg="white")
        can_cl.create_window((0, 0), window=inner_cl, anchor="nw")
        for idx, name in enumerate(df_class.index):
            r, c = divmod(idx, 3)
            tk.Button(inner_cl, text=name, width=20, font=("", 9), command=lambda n=name: self.set_class(n),
                      bg="#f8f9fa").grid(row=r, column=c, padx=3, pady=2)
        inner_cl.bind("<Configure>", lambda e: can_cl.configure(scrollregion=can_cl.bbox("all")))
        self._bind_mousewheel(can_cl)

        # ルート確定
        route_f = tk.LabelFrame(left_panel, text="ルート確定", padx=10, pady=10);
        route_f.pack(fill=tk.X, pady=5)
        tk.Label(route_f, text="選択中:").pack(side=tk.LEFT)
        tk.Label(route_f, textvariable=self.selected_class, fg="#d32f2f", font=("", 10, "bold")).pack(side=tk.LEFT,
                                                                                                      padx=10)
        tk.Label(route_f, text="Lv:").pack(side=tk.LEFT);
        self.ent_start = tk.Entry(route_f, width=4);
        self.ent_start.pack(side=tk.LEFT)
        tk.Label(route_f, text="→").pack(side=tk.LEFT);
        self.ent_end = tk.Entry(route_f, width=4);
        self.ent_end.insert(0, "20");
        self.ent_end.pack(side=tk.LEFT)
        tk.Button(route_f, text="追加", command=self.add_interval, bg="#4CAF50", fg="white", width=8).pack(
            side=tk.RIGHT)

        self.listbox = tk.Listbox(left_panel, height=4, font=("", 10));
        self.listbox.pack(fill=tk.X, pady=5)
        tk.Button(left_panel, text="📊 期待値計算実行", command=self.calculate_expectations, bg="#2196F3", fg="white",
                  font=("", 14, "bold"), height=2).pack(fill=tk.X, pady=5)
        tk.Button(left_panel, text="リスト全削除", command=self.clear_intervals).pack(fill=tk.X, pady=2)
        tk.Button(left_panel, text="🚪 アプリを終了", command=self.exit_app, bg="#f44336", fg="white",
                  font=("", 10, "bold")).pack(fill=tk.X, pady=10)

        # 3. 右パネル
        right_panel = tk.Frame(content_frame);
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.fig, self.ax_rate = plt.subplots(figsize=(10, 3.5));
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_panel);
        self.canvas.get_tk_widget().pack(fill=tk.X)
        self.tree = ttk.Treeview(right_panel, columns=["区分"] + STATS_COLUMNS, show="headings", height=22)
        for col in ["区分"] + STATS_COLUMNS: self.tree.heading(col, text=col); self.tree.column(col, width=85,
                                                                                                anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True)

    def _bind_mousewheel(self, canvas):
        def _on_mw(e):
            if platform.system() == "Windows":
                canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            else:
                canvas.yview_scroll(int(-1 * e.delta), "units")

        canvas.bind_all("<MouseWheel>", _on_mw)

    def _create_stat_inputs(self, parent, label):
        tk.Label(parent, text=label, font=("", 8)).pack(anchor="w");
        f = tk.Frame(parent);
        f.pack()
        entries = {}
        for i, s in enumerate(STATS_COLUMNS):
            r, c = divmod(i, 4);
            tk.Label(f, text=s, width=3).grid(row=r, column=c * 2)
            e = tk.Entry(f, width=6);
            e.grid(row=r, column=c * 2 + 1);
            entries[s] = e
        return entries

    def select_unit(self, name, kw):
        # 名前とキーワードの両方でフィルタリング
        mask = (df_init["キャラ名"] == name) & (df_init["カテゴリ"].str.contains(kw, na=False))
        if not df_init[mask].empty:
            match = df_init[mask].iloc[0]
            self.current_unit_data = match
            self.selected_char = name
            self.selected_category_full = match["カテゴリ"]
            self.lbl_status.config(text=f"選択中: {name} ({self.selected_category_full})")
            self.ent_start.delete(0, tk.END);
            self.ent_start.insert(0, str(int(match["Lv"])))
            self.update_graph()

    def set_class(self, name):
        self.selected_class.set(name); self.update_graph()

    def add_interval(self):
        try:
            s, e, cls = int(self.ent_start.get()), int(self.ent_end.get()), self.selected_class.get()
            if cls == "（未選択）" or s > e: raise ValueError
            self.intervals.append({"start": s, "end": e, "class": cls})
            self.listbox.insert(tk.END, f"Lv.{s}→{e} ({cls})");
            self.ent_start.delete(0, tk.END);
            self.ent_start.insert(0, str(e))
        except:
            messagebox.showwarning("エラー", "クラスとレベルを正しく設定してください。")

    def clear_intervals(self):
        self.intervals = []; self.listbox.delete(0, tk.END)

    def update_graph(self):
        if not self.selected_char: return
        self.ax_rate.clear()
        pg = self._get_modified_personal_growth(self.selected_char);
        p_name = self.cb_parent_growth.get()
        p_g = self._get_modified_personal_growth(p_name) // 2 if p_name != "（なし）" else 0
        cl_name = self.selected_class.get()
        cl_g = df_class.loc[cl_name, STATS_COLUMNS].astype(float) if cl_name in df_class.index else 0
        total = pg + p_g + cl_g;
        x = range(len(STATS_COLUMNS))
        self.ax_rate.bar(x, pg, label="個人", color="#90caf9");
        self.ax_rate.bar(x, p_g, bottom=pg, label="親", color="#f48fb1");
        self.ax_rate.bar(x, cl_g, bottom=pg + p_g, label="クラス", color="#a5d6a7")
        for i, v in enumerate(total): self.ax_rate.text(i, v + 2, f"{int(v)}%", ha='center', fontweight='bold')
        self.ax_rate.set_xticks(x);
        self.ax_rate.set_xticklabels(STATS_COLUMNS);
        self.ax_rate.set_ylim(0, 200);
        self.canvas.draw()

    def calculate_expectations(self):
        if self.current_unit_data is None or not self.intervals: return
        for itm in self.tree.get_children(): self.tree.delete(itm)
        try:
            # 正しいルートの初期値を参照
            curr = self.current_unit_data[STATS_COLUMNS].astype(float).copy()

            # 子世代遺伝
            if any(k in self.selected_category_full for k in ["子", "外伝"]):
                fs = pd.Series({s: float(self.father_stat_entries[s].get() or 0) for s in STATS_COLUMNS})
                ms = pd.Series({s: float(self.mother_stat_entries[s].get() or 0) for s in STATS_COLUMNS})
                if fs.sum() > 0 or ms.sum() > 0:
                    gen_sum = (fs + ms - curr * 2).clip(lower=0)
                    bonus = (gen_sum / 4).clip(upper=(2 + curr / 10))
                    curr += bonus

            prev_cls = self.intervals[0]['class']
            curr = curr.clip(upper=df_class_limit.loc[prev_cls, STATS_COLUMNS])
            self.tree.insert("", tk.END,
                             values=[f"加入(Lv.{self.intervals[0]['start']}: {prev_cls})"] + [f"{v:.2f}" for v in curr],
                             tags=('bold',))

            for itm in self.intervals:
                if itm['class'] != prev_cls:
                    curr = (curr + (df_class_base.loc[itm['class'], STATS_COLUMNS] - df_class_base.loc[
                        prev_cls, STATS_COLUMNS])).clip(upper=df_class_limit.loc[itm['class'], STATS_COLUMNS])
                    self.tree.insert("", tk.END, values=[f"→ {itm['class']} 変更"] + [f"{v:.2f}" for v in curr],
                                     tags=('cc',))
                diff = itm['end'] - itm['start']
                if diff > 0:
                    pg = self._get_modified_personal_growth(self.selected_char)
                    p_g = self._get_modified_personal_growth(
                        self.cb_parent_growth.get()) // 2 if self.cb_parent_growth.get() != "（なし）" else 0
                    total_g = (pg + p_g + df_class.loc[itm['class'], STATS_COLUMNS]) / 100.0
                    curr = (curr + total_g * diff).clip(upper=df_class_limit.loc[itm['class'], STATS_COLUMNS])
                    self.tree.insert("", tk.END,
                                     values=[f"Lv.{itm['end']} ({itm['class']})"] + [f"{v:.2f}" for v in curr])
                prev_cls = itm['class']
            self.tree.tag_configure('bold', background="#e3f2fd");
            self.tree.tag_configure('cc', background="#fff9c4")
        except Exception as e:
            messagebox.showerror("計算失敗", str(e))


if __name__ == "__main__":
    root = tk.Tk();
    app = GrowthApp(root);
    root.mainloop()