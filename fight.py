import tkinter as tk
from tkinter import ttk, messagebox


class DamageCalcApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FE if ダメージ計算シミュレーター")
        self.root.geometry("600x650")

        self.create_widgets()

    def create_widgets(self):
        # メインフレーム
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(expand=True, fill=tk.BOTH)

        tk.Label(main_frame, text="--- 戦闘パラメータ入力 ---", font=("", 12, "bold")).grid(row=0, column=0,
                                                                                            columnspan=2, pady=10)

        # 入力項目の定義 (内部キー: [ラベル名, 初期値])
        self.inputs = {}

        # 攻撃側設定
        atk_group = [
            ("atk_type", "攻撃タイプ (1:物理 / 2:魔法)", "1"),
            ("ATK", "攻撃力 (ATK)", "20"),
            ("MGK", "魔法力 (MGK)", "10"),
            ("WEPON", "武器威力", "8"),
            ("critical", "倍率 (通常:1 / クリティカル:3)", "1"),
            ("Ncritical", "定数補正 (追撃など:0 / スキル:-4)", "0"),
            ("level", "レベル補正 (1~4)", "0"),
            ("sukumi", "武器相性 (三すくみ ±2)", "0"),
        ]

        # 防御・補正設定
        def_group = [
            ("DF", "敵・物理防御 (DF)", "10"),
            ("MDF", "敵・魔法防御 (MDF)", "5"),
            ("terrain", "地形効果 (回避/守備など)", "0"),
            ("offline", "攻陣/防陣補正 (通常:1 / 弱化:0.5)", "1"),
            ("special", "特効/奥義補正 (1 / 3 / 4)", "1"),
        ]

        # フォームの作成
        current_row = 1
        for key, label, default in atk_group + def_group:
            tk.Label(main_frame, text=label, anchor="w").grid(row=current_row, column=0, sticky="ew", pady=2)
            ent = tk.Entry(main_frame)
            ent.insert(0, default)
            ent.grid(row=current_row, column=1, padx=10, pady=2)
            self.inputs[key] = ent
            current_row += 1

        # 計算ボタン
        btn_calc = tk.Button(main_frame, text="ダメージ計算実行", command=self.run_compute,
                             bg="#ffecb3", font=("", 11, "bold"), height=2)
        btn_calc.grid(row=current_row, column=0, columnspan=2, sticky="ew", pady=20)

        # 結果表示
        self.result_var = tk.StringVar(value="最終ダメージ: --")
        tk.Label(main_frame, textvariable=self.result_var, font=("", 16, "bold"), fg="#d32f2f").grid(
            row=current_row + 1, column=0, columnspan=2)

    def get_attack_power(self, data, attack_type):
        base_stat = data['ATK'] if attack_type == 1 else data['MGK']
        # 計算式: ステータス + (武器 + クリティカル補正) * 倍率 + レベル + 属性相性
        return base_stat + (data['WEPON'] + data['Ncritical']) * data['critical'] + data['level'] + data['sukumi']

    def get_defense_power(self, data, attack_type):
        base_df = data['DF'] if attack_type == 1 else data['MDF']
        return base_df + data['terrain']

    def run_compute(self):
        try:
            # データの読み取りと数値化
            user_data = {k: float(v.get()) for k, v in self.inputs.items()}
            attack_type = int(user_data['atk_type'])

            if attack_type not in [1, 2]:
                raise ValueError("攻撃タイプは1か2を入力してください")

            atk_power = self.get_attack_power(user_data, attack_type)
            def_power = self.get_defense_power(user_data, attack_type)

            # ダメージ = (攻撃力 - 防御力) * オフライン補正 * スペシャル補正
            damage = (atk_power - def_power) * user_data['offline'] * user_data['special']
            final_damage = max(0, damage)

            self.result_var.set(f"最終ダメージ: {final_damage:.1f}")

        except ValueError as e:
            messagebox.showerror("入力エラー", "数値を正しく入力してください。\n" + str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = DamageCalcApp(root)
    root.mainloop()