import csv
import math
import platform
import tkinter as tk
from tkinter import ttk

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# --- 🛠 日本語フォント設定 ---
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.family"] = "Yu Gothic"

if platform.system() == "Darwin":
    plt.rcParams["font.family"] = "Hiragino Sans"
elif platform.system() == "Linux":
    plt.rcParams["font.family"] = "TakaoPGothic"

# --- CSV読み込み関数 ---
def load_csv_with_category(filename):
    data = {}
    categories = {}
    with open(filename, "r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row in reader:
            name = row.pop("キャラ名")
            category = row.pop("カテゴリ")
            data[name] = {key: int(value) for key, value in row.items()}
            categories.setdefault(category, []).append(name)
    return data, categories

def load_csv(filename):
    data = {}
    with open(filename, "r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row in reader:
            name = row.pop("クラス名")
            data[name] = {key: int(value) for key, value in row.items()}
    return data

# --- CSV読み込み ---
char_growth, char_categories = load_csv_with_category("キャラ.csv")
class_growth = load_csv("クラス.csv")

# --- 成長補正値 ---
growth_bonus = {stat: 15 for stat in ["HP", "力", "魔力", "技", "速さ", "幸運", "守備", "魔防"]}
growth_malus = {stat: -15 for stat in growth_bonus}

# --- ウィンドウ作成 ---
root = tk.Tk()
root.title("FE if 成長率計算ツール")
root.geometry("800x650")

# --- ウィジェット配置 ---
tk.Label(root, text="キャラカテゴリ:").grid(row=0, column=0)
category_var = tk.StringVar()
category_dropdown = ttk.Combobox(root, textvariable=category_var, values=list(char_categories.keys()))
category_dropdown.grid(row=0, column=1)

tk.Label(root, text="キャラ:").grid(row=1, column=0)
char_var = tk.StringVar()
char_dropdown = ttk.Combobox(root, textvariable=char_var)
char_dropdown.grid(row=1, column=1)

tk.Label(root, text="クラス:").grid(row=2, column=0)
class_var = tk.StringVar()
class_dropdown = ttk.Combobox(root, textvariable=class_var, values=["（なし）"] + list(class_growth.keys()))
class_dropdown.grid(row=2, column=1)

tk.Label(root, text="親:").grid(row=3, column=0)
parent_var = tk.StringVar()
parent_dropdown = ttk.Combobox(root, textvariable=parent_var, values=["（なし）"] + list(char_growth.keys()))
parent_dropdown.grid(row=3, column=1)

tk.Label(root, text="得意:").grid(row=4, column=0)
good_stat_var = tk.StringVar()
good_stat_dropdown = ttk.Combobox(root, textvariable=good_stat_var, values=["（なし）"] + list(growth_bonus.keys()))
good_stat_dropdown.grid(row=4, column=1)

tk.Label(root, text="不得意:").grid(row=5, column=0)
bad_stat_var = tk.StringVar()
bad_stat_dropdown = ttk.Combobox(root, textvariable=bad_stat_var, values=["（なし）"] + list(growth_malus.keys()))
bad_stat_dropdown.grid(row=5, column=1)

def update_characters(event):
    category = category_var.get()
    if category in char_categories:
        char_dropdown["values"] = char_categories[category]
        char_dropdown.set("")

category_dropdown.bind("<<ComboboxSelected>>", update_characters)

# --- グラフ描画 ---
def update_graph():
    char = char_var.get()
    class_ = class_var.get()
    parent = parent_var.get()
    good_stat = good_stat_var.get()
    bad_stat = bad_stat_var.get()

    if char not in char_growth:
        ax.clear()
        ax.text(0.5, 0.5, "キャラを選択してください", ha="center", va="center", fontsize=12)
        canvas.draw()
        return

    base_growth = np.array(list(char_growth[char].values()))
    stats = list(char_growth[char].keys())

    parent_bonus = np.zeros_like(base_growth)
    class_bonus = np.zeros_like(base_growth)
    kamui_bonus = np.zeros_like(base_growth)

    if parent != "（なし）" and parent in char_growth:
        parent_bonus = np.array([math.floor(char_growth[parent][stat] / 2) for stat in stats])

    if class_ != "（なし）" and class_ in class_growth:
        class_bonus = np.array([class_growth[class_][stat] for stat in stats])

    if char == "カムイ" :
        kamui_bonus = np.array([
            growth_bonus[stat] if stat == good_stat else growth_malus[stat] if stat == bad_stat else 0
            for stat in stats
        ])

    total_growth = base_growth + parent_bonus + class_bonus + kamui_bonus

    ax.clear()
    x = np.arange(len(stats))
    bar_width = 0.5

    b1 = ax.bar(x, base_growth, width=bar_width, label="基礎成長", color="skyblue")
    b2 = ax.bar(x, parent_bonus, width=bar_width, bottom=base_growth, label="親補正", color="lightgreen")
    b3 = ax.bar(x, class_bonus, width=bar_width, bottom=base_growth + parent_bonus, label="クラス補正", color="orange")
    b4 = ax.bar(x, kamui_bonus, width=bar_width, bottom=base_growth + parent_bonus + class_bonus, label="得意・不得意", color="red")

    # グラフ描画関数の中の数値表示部分をこれに置き換え
    for i in range(len(stats)):
        ax.text(
            i, total_growth[i] + 2,
            f"{total_growth[i]}%", ha="center", fontsize=9
        )

    ax.set_xticks(x)
    ax.set_xticklabels(stats)
    ax.set_ylabel("成長率（%）")
    ax.set_title(f"{char} の成長率\n合計: {sum(total_growth)}%")
    ax.set_ylim(0, max(total_growth) + 30)
    ax.legend()
    canvas.draw()

# --- グラフキャンバス作成 ---
fig, ax = plt.subplots(figsize=(9, 5.5))
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().grid(row=7, column=0, columnspan=2)

# --- 全ドロップダウンでイベントバインド ---
for dropdown in [char_dropdown, class_dropdown, parent_dropdown, good_stat_dropdown, bad_stat_dropdown]:
    dropdown.bind("<<ComboboxSelected>>", lambda e: update_graph())

# --- メインループ開始 ---
root.mainloop()
