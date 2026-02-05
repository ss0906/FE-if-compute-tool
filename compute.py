import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import platform
import sys

# --- 🛠 基本設定 ---
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
    except:
        return pd.DataFrame()


df_char = load_and_clean_csv("キャラ.csv", set_index="キャラ名")
df_class = load_and_clean_csv("クラス.csv", set_index="クラス名")
df_init = load_and_clean_csv("初期パラメーター.csv")
df_class_base = load_and_clean_csv("クラス基本値.csv", set_index="クラス名")
df_class_limit = load_and_clean_csv("クラス上限値.csv", set_index="クラス名")


class GrowthApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FE if 期待値シミュレーター (上限反映・履歴強化版)")
        self.root.geometry("1900x1050")
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

        self.intervals = []
        self.current_result = None  # これは上限適用前の「生の値」を保持
        self.selected_char = ""
        self.selected_category_full = ""
        self.current_unit_data = None
        self.selected_class = tk.StringVar(value="（未選択）")

        self.create_widgets()

    def exit_app(self):
        if messagebox.askokcancel("終了", "シミュレーターを終了しますか？"):
            self.root.destroy();
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
        # 1. 上部：キャラ選択
        top_frame = tk.Frame(self.root, pady=5);
        top_frame.pack(fill=tk.X)
        configs = [("共通", "#9E9E9E", "共通"), ("白夜", "#2196F3", "白夜"), ("暗夜", "#F44336", "暗夜"),
                   ("透魔", "#00BCD4", "透魔"), ("子世代", "#FF9800", "子|外伝")]
        for i, (title, color, kw) in enumerate(configs):
            frame = tk.Frame(top_frame, bd=1, relief=tk.RIDGE);
            frame.grid(row=0, column=i, sticky="nsew", padx=2)
            tk.Label(frame, text=title, bg=color, fg="white", font=("", 9, "bold")).pack(fill=tk.X)
            can = tk.Canvas(frame, width=200, height=120, bg="white", highlightthickness=0);
            can.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scr = ttk.Scrollbar(frame, orient="vertical", command=can.yview);
            scr.pack(side=tk.RIGHT, fill=tk.Y);
            can.configure(yscrollcommand=scr.set)
            content = tk.Frame(can, bg="white");
            can.create_window((0, 0), window=content, anchor="nw")
            mask = df_init["カテゴリ"].str.contains(kw, na=False)
            for _, row in df_init[mask].iterrows():
                tk.Button(content, text=row["キャラ名"], width=18, font=("", 9),
                          command=lambda n=row["キャラ名"], k=kw: self.select_unit(n, k)).pack(pady=1)
            content.bind("<Configure>", lambda e, c=can: c.configure(scrollregion=c.bbox("all")))
            self._bind_mousewheel(can);
            top_frame.columnconfigure(i, weight=1)

        main_content = tk.Frame(self.root);
        main_content.pack(fill=tk.BOTH, expand=True)

        # 2. 左パネル
        left_panel = tk.Frame(main_content, width=650, padx=10);
        left_panel.pack(side=tk.LEFT, fill=tk.Y)
        left_panel.pack_propagate(False)

        self.lbl_status = tk.Label(left_panel, text="キャラを選択してください", font=("", 14, "bold"), fg="#1a73e8")
        self.lbl_status.pack(anchor="w", pady=5)

        # 設定エリア
        set_f = tk.Frame(left_panel);
        set_f.pack(fill=tk.X)
        k_f = tk.LabelFrame(set_f, text="カムイ得意/不得意", padx=5, pady=2);
        k_f.pack(fill=tk.X, pady=2)
        self.cb_good = ttk.Combobox(k_f, values=list(GROWTH_CORRECTIONS.keys()), state="readonly", width=12);
        self.cb_good.grid(row=0, column=1);
        self.cb_good.current(0)
        self.cb_bad = ttk.Combobox(k_f, values=list(GROWTH_CORRECTIONS.keys()), state="readonly", width=12);
        self.cb_bad.grid(row=0, column=3);
        self.cb_bad.current(0)
        p_f = tk.LabelFrame(set_f, text="子世代用：両親設定", padx=5, pady=2);
        p_f.pack(fill=tk.X, pady=2)
        self.cb_parent_growth = ttk.Combobox(p_f, values=["（なし）"] + list(df_char.index), state="readonly");
        self.cb_parent_growth.pack(fill=tk.X);
        self.cb_parent_growth.current(0)
        self.father_stat_entries = self._create_stat_inputs(p_f, "父：ステータス")
        self.mother_stat_entries = self._create_stat_inputs(p_f, "母：ステータス")

        # クラス選択
        cl_f = tk.LabelFrame(left_panel, text="クラス選択", padx=5, pady=2);
        cl_f.pack(fill=tk.BOTH, expand=True, pady=2)
        can_cl = tk.Canvas(cl_f, bg="white", highlightthickness=0);
        can_cl.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scr_cl = ttk.Scrollbar(cl_f, orient="vertical", command=can_cl.yview);
        scr_cl.pack(side=tk.RIGHT, fill=tk.Y);
        can_cl.configure(yscrollcommand=scr_cl.set)
        inner_cl = tk.Frame(can_cl, bg="white")
        can_cl.create_window((0, 0), window=inner_cl, anchor="nw")
        for idx, name in enumerate(df_class.index):
            r, c = divmod(idx, 2)
            tk.Button(inner_cl, text=name, width=30, height=2, font=("", 10, "bold"),
                      command=lambda n=name: self.set_class(n), bg="#f8f9fa").grid(row=r, column=c, padx=5, pady=3)
        inner_cl.bind("<Configure>", lambda e: can_cl.configure(scrollregion=can_cl.bbox("all")))
        self._bind_mousewheel(can_cl)

        # ルート構築
        rt_f = tk.LabelFrame(left_panel, text="ルート構築", padx=5, pady=5);
        rt_f.pack(fill=tk.X, pady=2)
        tk.Label(rt_f, textvariable=self.selected_class, fg="red", font=("", 10, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Label(rt_f, text="Lv:").pack(side=tk.LEFT);
        self.ent_start = tk.Entry(rt_f, width=4);
        self.ent_start.pack(side=tk.LEFT)
        tk.Label(rt_f, text="→").pack(side=tk.LEFT);
        self.ent_end = tk.Entry(rt_f, width=4);
        self.ent_end.insert(0, "20");
        self.ent_end.pack(side=tk.LEFT)
        tk.Button(rt_f, text="追加", command=self.add_interval, bg="#4CAF50", fg="white", width=8).pack(side=tk.RIGHT)

        list_btn_f = tk.Frame(left_panel);
        list_btn_f.pack(fill=tk.X)
        self.listbox = tk.Listbox(list_btn_f, height=4, font=("", 9));
        self.listbox.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=2)
        tk.Button(list_btn_f, text="選択ルート削除", command=self.delete_selected_interval, bg="#ffc107",
                  width=12).pack(side=tk.RIGHT, padx=2)

        tk.Button(left_panel, text="📊 期待値計算実行", command=self.calculate_expectations, bg="#2196F3", fg="white",
                  font=("", 14, "bold"), height=2).pack(fill=tk.X, pady=2)
        tk.Button(left_panel, text="履歴に保存", command=self.save_to_history, bg="#FF9800", fg="white").pack(fill=tk.X,
                                                                                                              pady=2)
        tk.Button(left_panel, text="全リスト削除", command=self.clear_intervals).pack(fill=tk.X)
        tk.Button(left_panel, text="🚪 終了", command=self.exit_app, bg="#f44336", fg="white").pack(fill=tk.X, pady=10)

        # 3. 右パネル
        right_panel = tk.Frame(main_content);
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.fig, self.ax_rate = plt.subplots(figsize=(10, 3.5));
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_panel);
        self.canvas.get_tk_widget().pack(fill=tk.X)

        self.tree = ttk.Treeview(right_panel, columns=["区分"] + STATS_COLUMNS, show="headings", height=18)
        for col in ["区分"] + STATS_COLUMNS: self.tree.heading(col, text=col); self.tree.column(col, width=85,
                                                                                                anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.tag_configure('limit', foreground="red", font=("", 9, "bold"))

        # 履歴エリア
        hist_f = tk.LabelFrame(right_panel, text="保存済み履歴（上限値適用済み・比較用）", padx=10, pady=5);
        hist_f.pack(fill=tk.X)
        self.history_tree = ttk.Treeview(hist_f, columns=["名前", "ルート情報"] + STATS_COLUMNS, show="headings",
                                         height=6)
        self.history_tree.heading("名前", text="名前");
        self.history_tree.column("名前", width=80, anchor="center")
        self.history_tree.heading("ルート情報", text="育成ルート");
        self.history_tree.column("ルート情報", width=250, anchor="w")
        for col in STATS_COLUMNS: self.history_tree.heading(col, text=col); self.history_tree.column(col, width=65,
                                                                                                     anchor="center")
        self.history_tree.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_f = tk.Frame(hist_f);
        btn_f.pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_f, text="比較実行", command=self.compare_history, bg="#673AB7", fg="white", width=12).pack(pady=2)
        tk.Button(btn_f, text="選択履歴削除", command=self.delete_history, bg="#f44336", fg="white", width=12).pack(
            pady=2)

    def _bind_mousewheel(self, canvas):
        def _on_mw(e):
            if platform.system() == "Windows":
                canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            else:
                canvas.yview_scroll(int(-1 * e.delta), "units")

        canvas.bind_all("<MouseWheel>", _on_mw)

    def _create_stat_inputs(self, parent, label):
        f = tk.Frame(parent);
        f.pack();
        entries = {}
        for i, s in enumerate(STATS_COLUMNS):
            tk.Label(f, text=s, font=("", 8), width=3).grid(row=0, column=i * 2)
            e = tk.Entry(f, width=5);
            e.grid(row=0, column=i * 2 + 1);
            entries[s] = e
        return entries

    def select_unit(self, name, kw):
        mask = (df_init["キャラ名"] == name) & (df_init["カテゴリ"].str.contains(kw, na=False))
        if not df_init[mask].empty:
            self.current_unit_data = df_init[mask].iloc[0]
            self.selected_char, self.selected_category_full = name, self.current_unit_data["カテゴリ"]
            self.lbl_status.config(text=f"選択: {name} ({self.selected_category_full})")
            self.ent_start.delete(0, tk.END);
            self.ent_start.insert(0, str(int(self.current_unit_data["Lv"])))
            self.update_graph()

    def set_class(self, name):
        self.selected_class.set(name); self.update_graph()

    def add_interval(self):
        try:
            s, e, cls = int(self.ent_start.get()), int(self.ent_end.get()), self.selected_class.get()
            self.intervals.append({"start": s, "end": e, "class": cls})
            self.listbox.insert(tk.END, f"Lv.{s}→{e} ({cls})")
            self.ent_start.delete(0, tk.END);
            self.ent_start.insert(0, str(e))
        except:
            pass

    def delete_selected_interval(self):
        selected_idx = self.listbox.curselection()
        if not selected_idx: return
        idx = selected_idx[0]
        self.listbox.delete(idx)
        self.intervals.pop(idx)
        if self.intervals:
            last_lv = self.intervals[-1]['end']
            self.ent_start.delete(0, tk.END);
            self.ent_start.insert(0, str(last_lv))
        elif self.current_unit_data is not None:
            self.ent_start.delete(0, tk.END);
            self.ent_start.insert(0, str(int(self.current_unit_data["Lv"])))

    def clear_intervals(self):
        self.intervals = []; self.listbox.delete(0, tk.END)

    def update_graph(self):
        if not self.selected_char: return
        self.ax_rate.clear()
        pg = self._get_modified_personal_growth(self.selected_char)
        p_name = self.cb_parent_growth.get()
        p_g = self._get_modified_personal_growth(p_name) // 2 if p_name != "（なし）" else 0
        cl_g = df_class.loc[self.selected_class.get(), STATS_COLUMNS].astype(
            float) if self.selected_class.get() in df_class.index else 0

        total_rates = pg + p_g + cl_g
        self.ax_rate.bar(STATS_COLUMNS, pg, label="個人", color="#90caf9")
        self.ax_rate.bar(STATS_COLUMNS, p_g, bottom=pg, label="親", color="#f48fb1")
        self.ax_rate.bar(STATS_COLUMNS, cl_g, bottom=pg + p_g, label="クラス", color="#a5d6a7")

        for i, total in enumerate(total_rates):
            self.ax_rate.text(i, total + 2, f"{int(total)}%", ha='center', fontsize=9, fontweight='bold')

        self.ax_rate.set_ylabel("合計成長率 (%)")
        self.ax_rate.set_ylim(0, 220);
        self.canvas.draw()

    def calculate_expectations(self):
        if self.current_unit_data is None or not self.intervals: return
        for itm in self.tree.get_children(): self.tree.delete(itm)
        curr = self.current_unit_data[STATS_COLUMNS].astype(float).copy()

        if any(k in self.selected_category_full for k in ["子", "外伝"]):
            fs = pd.Series({s: float(self.father_stat_entries[s].get() or 0) for s in STATS_COLUMNS})
            ms = pd.Series({s: float(self.mother_stat_entries[s].get() or 0) for s in STATS_COLUMNS})
            if fs.sum() > 0 or ms.sum() > 0:
                curr += ((fs + ms - curr * 2).clip(lower=0) / 4).clip(upper=(2 + curr / 10))

        prev_cls = self.intervals[0]['class']
        self._insert_row(f"初期({prev_cls})", curr, prev_cls)

        for itm in self.intervals:
            if itm['class'] != prev_cls:
                curr = (curr + (df_class_base.loc[itm['class'], STATS_COLUMNS] - df_class_base.loc[
                    prev_cls, STATS_COLUMNS]))
                prev_cls = itm['class']
            diff = itm['end'] - itm['start']
            if diff > 0:
                pg = self._get_modified_personal_growth(self.selected_char)
                p_g = self._get_modified_personal_growth(
                    self.cb_parent_growth.get()) // 2 if self.cb_parent_growth.get() != "（なし）" else 0
                total_g = (pg + p_g + df_class.loc[itm['class'], STATS_COLUMNS]) / 100.0
                curr = (curr + total_g * diff)
            self._insert_row(f"Lv.{itm['end']}({itm['class']})", curr, itm['class'])
        self.current_result = curr.copy()

    def _insert_row(self, label, stats, cls_name):
        limit = df_class_limit.loc[cls_name, STATS_COLUMNS]
        clamped_stats = stats.clip(upper=limit)
        values = [label];
        is_capped = False
        for s in STATS_COLUMNS:
            val = clamped_stats[s]
            if val >= limit[s]: is_capped = True
            values.append(f"{val:.2f}")
        tag = ('limit',) if is_capped else ()
        self.tree.insert("", tk.END, values=values, tags=tag)

    # --- 履歴保存時、上限値を反映するように修正 ---
    def save_to_history(self):
        if self.current_result is None or not self.intervals: return

        # 最終的なクラスの上限値を取得
        last_cls = self.intervals[-1]['class']
        limit = df_class_limit.loc[last_cls, STATS_COLUMNS]

        # 上限を反映(クリップ)した値を保存用データとする
        capped_result = self.current_result.clip(upper=limit)

        route_str = f"[{self.selected_category_full}] " + " → ".join(
            [f"{i['class']}{i['end']}" for i in self.intervals])
        data = [self.selected_char, route_str] + [f"{v:.1f}" for v in capped_result]  # 上限反映済み

        self.history_tree.insert("", tk.END, values=data)
        messagebox.showinfo("保存", f"{self.selected_char} のルートと上限反映済み結果を保存しました。")

    def compare_history(self):
        selected = self.history_tree.selection()
        if not selected or self.current_result is None: return
        hist_values = self.history_tree.item(selected[0])['values']

        # 履歴値（すでに保存時に上限適用済み）
        h_stats = pd.Series([float(v) for v in hist_values[2:]], index=STATS_COLUMNS)

        # 現在の計算値（表示中のルートの最終クラス上限を適用）
        last_cls = self.intervals[-1]['class']
        c_stats = self.current_result.clip(upper=df_class_limit.loc[last_cls, STATS_COLUMNS])

        diff = c_stats - h_stats

        comp_win = tk.Toplevel(self.root);
        comp_win.title("期待値比較：上限反映済み")
        comp_win.geometry("500x450")
        tk.Label(comp_win,
                 text=f"【比較】 現在 vs 履歴({hist_values[0]})\n※両方のデータに各最終クラスの上限を適用しています",
                 font=("", 9, "bold")).pack(pady=5)

        f = tk.Frame(comp_win, padx=20, pady=10);
        f.pack(fill=tk.BOTH, expand=True)
        tk.Label(f, text="項目", font=("", 9, "bold")).grid(row=0, column=0)
        tk.Label(f, text="現在値", font=("", 9, "bold")).grid(row=0, column=1)
        tk.Label(f, text="履歴値", font=("", 9, "bold")).grid(row=0, column=2)
        tk.Label(f, text="差分", font=("", 9, "bold")).grid(row=0, column=3)

        for i, s in enumerate(STATS_COLUMNS):
            tk.Label(f, text=s).grid(row=i + 1, column=0)
            tk.Label(f, text=f"{c_stats[s]:.2f}").grid(row=i + 1, column=1)
            tk.Label(f, text=f"{h_stats[s]:.1f}").grid(row=i + 1, column=2)
            d_val = diff[s]
            color = "blue" if d_val > 0.01 else "red" if d_val < -0.01 else "black"
            tk.Label(f, text=f"{d_val:+.2f}", fg=color, font=("", 10, "bold")).grid(row=i + 1, column=3)

    def delete_history(self):
        selected_items = self.history_tree.selection()
        if not selected_items: return
        if messagebox.askyesno("削除確認", f"選択した {len(selected_items)} 件の履歴を削除しますか？"):
            for item in selected_items:
                self.history_tree.delete(item)


if __name__ == "__main__":
    root = tk.Tk();
    app = GrowthApp(root);
    root.mainloop()