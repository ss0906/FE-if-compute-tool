def get_attack_power(data, attack_type):
    """攻撃力を計算する"""
    # 物理(1)か魔法(2)かを選択
    base_stat = data['ATK'] if attack_type == 1 else data['MGK']

    # 計算式: ステータス + (武器 + クリティカル補正) * 倍率 + レベル + 属性相性
    return base_stat + (data['WEPON'] + data['Ncritical']) * data['critical'] + data['level'] + data['sukumi']


def get_defense_power(data, attack_type):
    """防御力を計算する"""
    # 物理(1)か魔法(2)かに対応する防御ステータスを選択
    base_df = data['DF'] if attack_type == 1 else data['MDF']
    return base_df + data['terrain']


def compute_damage(data, attack_type):
    """最終ダメージを計算する"""
    if attack_type not in [1, 2]:
        return "error"

    atk_power = get_attack_power(data, attack_type)
    def_power = get_defense_power(data, attack_type)

    # ダメージ = (攻撃力 - 防御力) * オフライン補正 * スペシャル補正
    damage = (atk_power - def_power) * data['offline'] * data['special']
    return max(0, damage)  # ダメージがマイナスにならないよう調整


def main():
    print("--- ダメージ計算シミュレーター ---")
    attack_type = int(input("攻撃タイプを選択 (物理:1, 魔法:2): "))

    # 設定項目とメッセージの定義
    fields = {
        "ATK": "攻撃力 (ATK)",
        "MGK": "魔法力 (MGK)",
        "WEPON": "武器威力 (WEPON)",
        "critical": "クリティカル (1~3)",
        "Ncritical": "クリティカル定数 (-4 or 0)",
        "level": "レベル補正 (1~4)",
        "sukumi": "属性相性 (0 or ±2)",
        "DF": "物理防御 (DF)",
        "MDF": "魔法防御 (MDF)",
        "terrain": "地形効果",
        "offline": "攻陣補正 (1 or 0.5)",
        "special": "スペシャル補正 (1, 3, or 4)"
    }

    # 一括入力
    user_data = {}
    for key, label in fields.items():
        user_data[key] = float(input(f"{label} を入力してください: "))

    # 計算実行
    result = compute_damage(user_data, attack_type)

    print("\n" + "=" * 20)
    print(f"最終ダメージ: {result}")
    print("=" * 20)


if __name__ == '__main__':
    main()