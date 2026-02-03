import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import platform

# --- 🛠 日本語フォント設定 ---
plt.rcParams["axes.unicode_minus"] = False
if platform.system() == "Darwin":
    plt.rcParams["font.family"] = "Hiragino Sans"
elif platform.system() == "Windows":
    plt.rcParams["font.family"] = "Yu Gothic"
else:
    plt.rcParams["font.family"] = "TakaoPGothic"

# --- 📊 データ読み込み ---
try:
    df_char = pd.read_csv("キャラ.csv", encoding="utf-8-sig").set_index("キャラ名")
    df_class = pd.read_csv("クラス.csv", encoding="utf-8-sig").set_index("クラス名")
except Exception as e:
    print(f"CSV読み込みエラー: {e}")
    exit()

STATS_COLUMNS = ["HP", "力", "魔力", "技", "速さ", "幸運", "守備", "魔防"]


class GrowthApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FE if 成長率表示＆期待値計算ツール")
        self.root.geometry("1200x850")
        self.intervals = []
        self.create_widgets()

    def create_widgets(self):
        # 左側：入力パネル
        left_frame = tk.Frame(self.root, padx=10, pady=10)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)

        # 【1. 成長率設定】
        tk.Label(left_frame, text="【1. 成長率・ユニット設定】", font=("", 10, "bold")).pack(anchor="w")
        self.cb_char = self._create_combo(left_frame, "キャラ:", list(df_char.index))
        self.cb_parent = self._create_combo(left_frame, "親 (子世代):", ["（なし）"] + list(df_char.index))
        self.cb_class_view = self._create_combo(left_frame, "現在のクラス:", list(df_class.index))
        self.cb_good = self._create_combo(left_frame, "得意(カムイ):", ["（なし）"] + STATS_COLUMNS)
        self.cb_bad = self._create_combo(left_frame, "不得意(カムイ):", ["（なし）"] + STATS_COLUMNS)

        # 【2. 期待値ルート設定】
        tk.Label(left_frame, text="\n【2. 期待値計算・育成ルート】", font=("", 10, "bold")).pack(anchor="w")
        row_lv = tk.Frame(left_frame)
        row_lv.pack(fill=tk.X)
        tk.Label(row_lv, text="Lv").pack(side=tk.LEFT)
        self.ent_start = tk.Entry(row_lv, width=3);
        self.ent_start.insert(0, "1");
        self.ent_start.pack(side=tk.LEFT)
        tk.Label(row_lv, text="～").pack(side=tk.LEFT)
        self.ent_end = tk.Entry(row_lv, width=4);
        self.ent_end.insert(0, "20");
        self.ent_end.pack(side=tk.LEFT)

        self.cb_route_class = ttk.Combobox(left_frame, values=list(df_class.index), state="readonly")
        self.cb_route_class.pack(fill=tk.X, pady=2)

        tk.Button(left_frame, text="ルートに区間を追加", command=self.add_interval).pack(fill=tk.X, pady=5)
        self.listbox = tk.Listbox(left_frame, height=6)
        self.listbox.pack(fill=tk.X)
        tk.Button(left_frame, text="選択区間を削除", command=self.remove_interval).pack(fill=tk.X)

        tk.Button(left_frame, text="📊 期待値を計算実行", command=self.calculate_expectations, bg="#e8f5e9",
                  height=2).pack(fill=tk.X, pady=15)

        # 右側：表示エリア
        self.right_frame = tk.Frame(self.root)
        self.right_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

        # 上段：成長率グラフ
        self.fig, self.ax_rate = plt.subplots(figsize=(7, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas.get_tk_widget().pack(fill=tk.X, padx=10, pady=5)

        # 下段：期待値表 (Treeview)
        tk.Label(self.right_frame, text="【期待値計算結果（上昇量合計）】", font=("", 11, "bold")).pack(pady=5)

        columns = ["区分"] + STATS_COLUMNS
        self.tree = ttk.Treeview(self.right_frame, columns=columns, show="headings", height=10)

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=80, anchor="center")

        self.tree.pack(expand=True, fill=tk.BOTH, padx=10, pady=5)

    def _create_combo(self, parent, label, values):
        tk.Label(parent, text=label).pack(anchor="w")
        cb = ttk.Combobox(parent, values=values, state="readonly")
        cb.pack(fill=tk.X, pady=2)
        cb.bind("<<ComboboxSelected>>", lambda e: self.update_rate_graph())
        return cb

    def update_rate_graph(self):
        """キャラ・クラス選択時に成長率をリアルタイム更新"""
        char_name = self.cb_char.get()
        cls_name = self.cb_class_view.get()
        if not char_name or not cls_name: return

        try:
            base = df_char.loc[char_name, STATS_COLUMNS]
            parent_name = self.cb_parent.get()
            parent = (df_char.loc[
                          parent_name, STATS_COLUMNS] // 2) if parent_name and parent_name != "（なし）" else pd.Series(0,
                                                                                                                      index=STATS_COLUMNS)
            cls_rate = df_class.loc[cls_name, STATS_COLUMNS]

            kamui = pd.Series(0, index=STATS_COLUMNS)
            if char_name == "カムイ":
                if self.cb_good.get() in STATS_COLUMNS: kamui[self.cb_good.get()] += 15
                if self.cb_bad.get() in STATS_COLUMNS: kamui[self.cb_bad.get()] -= 15

            self.ax_rate.clear()
            x = range(len(STATS_COLUMNS))
            self.ax_rate.bar(x, base, label="キャラ基礎", color="#bbdefb")
            self.ax_rate.bar(x, parent, bottom=base, label="親補正", color="#c8e6c9")
            self.ax_rate.bar(x, cls_rate, bottom=base + parent, label="クラス補正", color="#ffe0b2")
            self.ax_rate.bar(x, kamui, bottom=base + parent + cls_rate, label="得意/不得意", color="#ffcdd2")

            total = base + parent + cls_rate + kamui
            for i, v in enumerate(total):
                self.ax_rate.text(i, v + 1, f"{int(v)}%", ha="center", fontweight="bold")

            self.ax_rate.set_title(f"【現在の成長率】 {char_name} × {cls_name}")
            self.ax_rate.set_xticks(x)
            self.ax_rate.set_xticklabels(STATS_COLUMNS)
            self.ax_rate.set_ylim(0, 130)
            self.ax_rate.legend(loc='upper right', fontsize='x-small', ncol=2)
            self.canvas.draw()
        except Exception as e:
            print(f"成長率描画エラー: {e}")

    def add_interval(self):
        try:
            s, e = int(self.ent_start.get()), int(self.ent_end.get())
            cls = self.cb_route_class.get()
            if not cls or s >= e: raise ValueError
            self.intervals.append({"start": s, "end": e, "class": cls})
            self.listbox.insert(tk.END, f"Lv.{s}-{e}: {cls}")
            self.ent_start.delete(0, tk.END);
            self.ent_start.insert(0, str(e))
            self.ent_end.delete(0, tk.END);
            self.ent_end.insert(0, str(e + 20))
        except:
            messagebox.showerror("エラー", "レベルまたはクラスを正しく選択してください")

    def remove_interval(self):
        selection = self.listbox.curselection()
        if selection:
            idx = selection[0]
            self.intervals.pop(idx)
            self.listbox.delete(idx)

    def calculate_expectations(self):
        """ルートに基づき期待値を計算し表に表示"""
        char_name = self.cb_char.get()
        if not char_name or not self.intervals:
            messagebox.showwarning("注意", "設定が不十分です")
            return

        # 既存の表をクリア
        for item in self.tree.get_children():
            self.tree.delete(item)

        # ユニット固有成長率
        base = df_char.loc[char_name, STATS_COLUMNS]
        parent_name = self.cb_parent.get()
        parent = (df_char.loc[parent_name, STATS_COLUMNS] // 2) if parent_name and parent_name != "（なし）" else 0
        kamui = pd.Series(0, index=STATS_COLUMNS)
        if char_name == "カムイ":
            if self.cb_good.get() in STATS_COLUMNS: kamui[self.cb_good.get()] += 15
            if self.cb_bad.get() in STATS_COLUMNS: kamui[self.cb_bad.get()] -= 15

        unit_fixed = base + parent + kamui
        total_gains = pd.Series(0.0, index=STATS_COLUMNS)

        # 各区間ごとの計算と表示
        for item in self.intervals:
            lv_up = item["end"] - item["start"]
            cls_rate = df_class.loc[item["class"], STATS_COLUMNS]
            interval_gains = ((unit_fixed + cls_rate) / 100.0) * lv_up
            total_gains += interval_gains

            # 区間の上昇量を表に追加
            row_vals = [f"Lv.{item['start']}-{item['end']} ({item['class']})"] + [f"{v:.2f}" for v in interval_gains]
            self.tree.insert("", tk.END, values=row_vals)

        # 合計行を追加
        self.tree.insert("", tk.END, values=["---", "---", "---", "---", "---", "---", "---", "---", "---"])
        total_row = ["【合計上昇量】"] + [f"{v:.2f}" for v in total_gains]
        self.tree.insert("", tk.END, values=total_row, tags=('total',))
        self.tree.tag_configure('total', font=("", 10, "bold"), background="#e1f5fe")


if __name__ == "__main__":
    root = tk.Tk()
    app = GrowthApp(root)
    root.mainloop()