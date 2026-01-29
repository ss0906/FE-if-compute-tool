def ATACK_compute(ATK,MGK,WEPON,critical,Ncritical,level,sukumi,type):
    ans=0
    if type != 1 and type != 2:
        ans="error"
    elif type ==1:
        ans=ATK+(WEPON+Ncritical)*critical+level+sukumi
    elif type ==2:
        ans=MGK+(WEPON+Ncritical)*critical+level+sukumi
    return ans

def DF_compute(DF,MDF,terrain,type):
    ans=0
    if  type !=1  and type !=2:
        ans="error"
    elif type==1:
        ans=DF+terrain
    elif type==2:
        ans=MDF+terrain
    return ans
def Damage_compute(ATK,MGK,WEPON,critical,Ncritical,level,sukumi,DF,MDF,terrain,offline,special,type):
    damage=0
    off=ATACK_compute(ATK,MGK,WEPON,critical,Ncritical,level,sukumi,type)
    df=DF_compute(DF,MDF,terrain,type)
    if off == "error"or df=="error":
        damage="error"
    else:
        damage=(off-df)*offline*special
    return damage

def main():
    # 入力したい項目の名前をリストにする
    type=int(input("物理1,魔法2:"))
    ATACK_fields = ["ATK", "MGK", "WEPON", "critical", "Ncritical","level", "sukumi"]
    Defence_field=["DF","MDF","terrain"]
    sp_field=["offline","special"]

    # 結果を格納する辞書
    data_at = {}
    data_df={}
    data_sp={}

    for field in ATACK_fields:
        # 順番に名前を表示して入力を促す
        if field == "critical" :
            value= input(f"{field} の値は1~3を入力してください: ")
        elif field == "Ncritical" :
            value = input(f"{field} の値を-4又は0を入力してください: ")
        elif field == "level":
            value = input(f"{field} の値を1~4を入力してください: ")
        elif field == "sukumi":
            value = input(f"{field} の値を0又は+-2で入力してください: ")
        else:
            value = input(f"{field} の値を入力してください: ")
        data_at[field] = float(value)

    for field in Defence_field:
        value= input(f"{field} の値を入力してください: ")
        data_df[field] = float(value)
    for field in sp_field:
        if field =="offline":
                value = input(f"{field} の値を1か0.5で入力してください: ")
        else:
                value = input(f"{field} の値1か3又は4で入力してください: ")
        data_sp[field] = float(value)
    damage=Damage_compute(data_at["ATK"], data_at["MGK"], data_at["WEPON"], data_at["critical"], data_at["Ncritical"],
                       data_at["level"], data_at["sukumi"],data_df["DF"],data_df["MDF"],data_df["terrain"],data_sp["offline"],data_sp["special"],type)
    print(damage)
    return

if __name__ == '__main__':
    main()