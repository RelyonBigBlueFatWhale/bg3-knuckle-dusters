# -*- coding: utf-8 -*-
"""指虎探针包（Knuckle Dusters Probe）—— 生成全部数据文件。

设计要点（每条都有原版依据，见 D:\\DSH\\指虎-调研报告.md）：
  · 近战主手位 + 双手（Twohanded）
  · 攻击走徒手判定：SpellRoll Attack(AttackType.MeleeUnarmedAttack) + AttackSpellOverride 挂到武器上
  · 徒手动画：整段复制 Target_UnarmedAttack 的 SpellAnimation，特效/音效抄武僧徒手打击
  · 额外伤害走 CharacterUnarmedDamage(...)（徒手专属通道）
  · 戴摩三章上架：往 DEN_/HAV_/LOW_Weaponsmith_Trade 追加（CanMerge 1，照 ActTwoExpansion 的写法）
"""
import io
import os
import uuid

def H():
    """生成 h+g 形态的本地化 handle（8-4-4-4-12 全十六进制）"""
    s = uuid.uuid4().hex
    return "h%s" % s[:8] + "g" + s[8:12] + "g" + s[12:16] + "g" + s[16:20] + "g" + s[20:32]

ROOT = r"D:\DSH\knuckle_mod"
MOD = "KnuckleDusters"
PUB = os.path.join(ROOT, "Public", MOD)
DATA = os.path.join(PUB, "Stats", "Generated", "Data")
RT = os.path.join(PUB, "RootTemplates")
LOCP = os.path.join(PUB, "Localization")
LOCR = os.path.join(ROOT, "Localization")

MOD_UUID = "b0b86379-2d63-4fb9-8ef8-665c09281874"   # 固定：modsettings 注册要用同一个

# 三个物品的根模板 UUID（固定下来：SE 指令、宝箱表、注册脚本都要用同一套）
T_RARE = "d6476755-6fb1-4752-91e4-a51ada4747da"
T_VERY = "94187658-a74c-4e44-a709-b3526ef1fbfd"
T_LEG = "7e69ee66-6202-42b3-8e17-b587fd9a0276"

# ---- 本地化 handle ----
HL = {k: H() for k in (
    "rare_name", "rare_desc", "very_name", "very_desc", "leg_name", "leg_desc",
    "fist_name", "fist_desc", "claw_name", "claw_desc", "chill_name", "chill_desc",
    "shell_name", "shell_desc", "atk_name", "atk_desc", "sunder_name", "sunder_desc")}

# ---- 原版参考常量（照抄，勿改） ----
UNARMED_ANIM = ("8b8bb757-21ce-4e02-a2f3-97d55cf2f90b,,;"
                "6606c30b-be1c-4f17-ae6b-1a591c80b18c,366693ee-d97f-4294-a4dd-a2145ddc4e6a,9f2d32b9-529a-4b75-b3df-6e1ae1395280;"
                "f4ac302b-1569-404f-bd52-1fe443e265df,479ee5da-2967-41e1-b7d1-a94e864a5f25,79323098-edb3-4993-ba50-9b5f705e9878;"
                "e8a5c57f-855b-4227-acaa-11e8ce8d7d64,b5cb923d-0c08-4c20-89a9-44b9bf98c6cb,6282d127-0c06-4365-9d53-6f32ef350127;"
                "7bb52cd4-0b1c-4926-9165-fa92b75876a3,,;"
                "2b81c18b-9698-4262-a623-932c2bb1296d,ecbf9949-3b33-432c-b735-e47aaed0924a,e71a7c08-fdc1-4a0b-9a90-1c793c58553c;"
                "0b07883a-08b8-43b6-ac18-84dc9e84ff50,,;,,;,,")
MAINHAND_DMG = "DealDamage(max(1,MainMeleeWeapon), MainMeleeWeaponDamageType)"
# 徒手伤害值：酒馆殴斗者 / 武僧具现 / 各类 CharacterUnarmedDamage 加成都只作用于这个量。
# 伤害链里不出现 UnarmedDamage，等于把这些加成整条丢掉（原版 Target_ShadowStrike_Instant_Unarmed 就把它写进链里）。
UNARMED_DMG = "DealDamage(max(1,UnarmedDamage), Bludgeoning)"
# 指虎攻击的完整伤害链：徒手伤害值（吃徒手类加成）+ 武器骰/附魔 + 武器 functor（吃武器类增益）
ATTACK_DMG = UNARMED_DMG + ";" + MAINHAND_DMG + ";ExecuteWeaponFunctors(MainHand)"
TOOLTIP_DMG = "DealDamage(MartialArtsUnarmedDamage, Bludgeoning);DealDamage(MainMeleeWeapon, MainMeleeWeaponDamageType)"

# 额外伤害的实现方式：**并入徒手伤害本身的骰子**（角色级通道），照抄原版装备的做法
#   MAG_Radiant_UnarmedAttack_Passive / MAG_Cold_... → Boosts "CharacterUnarmedDamage(1d4, Cold)"
#   阿斯代伦飞升 → "CharacterWeaponDamage(1d10,Necrotic);CharacterUnarmedDamage(1d10,Necrotic)"（一对）
# 为什么走这条：它是"伤害掷骰的一部分"，因此
#   ① 参与抗性/易伤结算（碎甲能翻倍）
#   ② 自动覆盖所有徒手攻击 —— 徒手打击、武艺：徒手打击、疾风连击系列
# 关键细节：必须**挂在被动上**（PassivesOnEquip），不要直接写在武器 Boosts 里 ——
#   写在武器 Boosts 时 tooltip 会把裸骰子渲染出来（多出 "1d4" / "2d6" 这样的行）；
#   原版同类装备（手套类徒手附伤）也全部是 passives 承载。
TIER_BOOST = {
    "Rare":     "IF(IsMeleeUnarmedAttack()):CharacterUnarmedDamage(1d4, Piercing)",
    # 珍奇：一条**无条件** 1d6 寒冷 + 一条**附条件**（濡湿时）1d6 寒冷。
    # 不要写成一个 2d6 分支（IF(WET):2d6 / IF(not WET):1d6）—— tooltip 不判断条件、会把两支都列出来，
    # 于是显示成 "+2d6 寒冷" 这种看着像另一段独立伤害的行。两条各自 1d6，读起来才是"基础 + 追加"。
    "VeryRare": ("IF(IsMeleeUnarmedAttack()):CharacterUnarmedDamage(1d6, Cold);"
                 "IF(IsMeleeUnarmedAttack() and HasStatus('WET', context.Target)):CharacterUnarmedDamage(1d6, Cold)"),
    # 传奇：两个 1d10 骰子（= 2d10）并入徒手伤害
    "Leg":      "IF(IsMeleeUnarmedAttack()):CharacterUnarmedDamage(2d10, Bludgeoning)",
}
# 每件武器承载附伤骰的隐藏被动名
TIER_RIDER_PASSIVE = {
    "Rare": "KD_Rider_Claw",
    "VeryRare": "KD_Rider_Chill",
    "Leg": "KD_Rider_Shell",
}
# 传奇额外的碎甲施加（两条 IF 都只判断 1 层是否存在，避免同一串里顺序求值一次叠满）
SUNDER = (";IF(HasStatus('KD_ARMORBREAK_1', context.Target)):ApplyStatus(KD_ARMORBREAK_2,100,3)"
          ";IF(not HasStatus('KD_ARMORBREAK_1', context.Target)):ApplyStatus(KD_ARMORBREAK_1,100,3)")

# 武僧的徒手系能力走的是另外的法术，默认不会用我们的伤害链 —— 给它们各做一份替身，
# 再用 AttackSpellOverride 顶掉原版，这样疾风连击/附赠徒手打击也会带上武器伤害与附伤。
MONK_ATTACKS = [
    ("Target_FlurryOfBlows",
     "Flurry",
     "Attack(AttackType.MeleeUnarmedAttack);Cast2[Attack(AttackType.MeleeUnarmedAttack)]",
     "BonusActionPoint:1;KiPoint:1"),
    ("Target_UnarmedStrike_Monk",
     "UStrike",
     "Attack(AttackType.MeleeUnarmedAttack)",
     "BonusActionPoint:1"),
]

# 视觉模式：
#   "dagger" = 沿用原版匕首的网格（占位，但模板字段完整 —— 实测唯一能让物件真正生成的配置）
#   "none"   = 不挂网格；实测这样会让模板缺少 visual/physics，物件发不进背包（引擎直接丢弃），
#              所以默认必须用 "dagger"，除非将来有了真正的指虎网格
VISUAL_MODE = "dagger"

# 发布开关：python gen_knuckles.py --release
#   探针版（默认）保留：SE 自动发放脚本、教程宝箱兜底、名字带 "(Probe)"
#   发布版（--release）剥掉以上三项，只保留戴摩三章上架与正式命名
import sys as _sys
RELEASE = ("--release" in _sys.argv)

# 匕首根模板（视觉占位）
EQ_TYPE_ID = "2d85d633-d496-44a1-a643-0e95ef879a6d"
PARENT_TMPL = "569b0f3d-abcd-4b01-aaf0-979091288163"
PHYS_TMPL = "76fd694e-35c8-9109-0d8c-78bf8e107c76"
VISUAL_TMPL = "cb8ea426-fecc-de0f-ffb2-be1596ae68c0"
# 我们自己生成的武器视觉（Content/Assets/Weapons/[PAK]_Knuckles/_merged.lsx 里的 VisualBank ID）
VISUAL_TMPL_BY_ITEM = {
    "KD_SteelSpikeFist": "a1f3c2e4-5b6d-4e7f-8a90-1b2c3d4e5f60",
    "KD_BoneChill": "b2e4d3f5-6c7e-4f80-9ab1-2c3d4e5f6071",
    "KD_Unsharpened": "c3f5e406-7d8f-4081-abc2-3d4e5f607182",
}


def w(path, text):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)
    print("  %-78s %6d B" % (os.path.relpath(path, ROOT), len(text.encode("utf-8"))))


LINE = "// " + "=" * 76 + "\n"

# ============================================================ 武器
def build_weapons():
    t = [LINE,
         "// 指虎三件套 —— 近战主手位 / 双手 / 攻击按徒手结算\n",
         LINE]
    def weapon(stat, tmpl, rarity, value_level, enchant, boosts, passives, override=None):
        t.append('\nnew entry "%s"\n' % stat)
        t.append('type "Weapon"\n')
        t.append('using "_BaseWeapon"\n')   # Slot=Melee Main Weapon / 1d4 / WeaponRange 150 / Weapon Group SimpleMeleeWeapon
        t.append('data "RootTemplate" "%s"\n' % tmpl)
        t.append('data "Damage Type" "Bludgeoning"\n')
        t.append('data "Damage" "1d4"\n')
        t.append('data "Weapon Properties" "Melee;Twohanded;Dippable;Magical"\n')
        t.append('data "Proficiency Group" "SimpleWeapons"\n')
        t.append('data "Rarity" "%s"\n' % rarity)
        t.append('data "ValueLevel" "%s"\n' % value_level)
        t.append('data "ValueUUID" "8b2ad47c-891e-4a19-bab8-43cd5e964cb1"\n')
        t.append('data "DefaultBoosts" "WeaponProperty(Magical);CannotBeDisarmed();"\n')
        t.append('data "BoostsOnEquipMainHand" ""\n')     # 不是刀剑，不给挥砍类武器动作
        if boosts:
            t.append('data "Boosts" "%s"\n' % boosts)
        if override:
            t.append('data "StatusOnEquip" "%s"\n' % override)
        t.append('data "PassivesOnEquip" "%s"\n' % passives)
        t.append('data "Unique" "1"\n')

    # 稀有：钢刺之拳 —— 钢爪（附伤骰由隐藏被动 KD_Rider_Claw 承载，不写在武器 Boosts 上）
    # 攻击覆写改由 StatusOnEquip 上的隐藏技术状态承载（原版 UNARMEDATTACK_OVERRIDE_BOAR 的写法）
    weapon("KD_SteelSpikeFist", T_RARE, "Rare", "3", 1,
           "",
           "KD_SteelFist;KD_Trait_Claw;" + TIER_RIDER_PASSIVE["Rare"],
           override="KD_OVERRIDE_RARE")
    # 珍奇：彻骨之寒 —— 刺骨
    weapon("KD_BoneChill", T_VERY, "VeryRare", "6", 2,
           "",
           "KD_SteelFist;KD_Trait_Chill;" + TIER_RIDER_PASSIVE["VeryRare"],
           override="KD_OVERRIDE_VERY")
    # 传奇：无锋 —— 剥壳
    weapon("KD_Unsharpened", T_LEG, "Legendary", "9", 3,
           "",
           "KD_SteelFist;KD_Trait_Shell;" + TIER_RIDER_PASSIVE["Leg"],
           override="KD_OVERRIDE_LEG")
    w(os.path.join(DATA, "KD_1_Weapons.txt"), "".join(t))

# ============================================================ 攻击法术
def build_attacks():
    t = [LINE,
         "// 指虎攻击：整条从原版徒手攻击 Target_UnarmedAttack 派生（不是从武器攻击派生！）\n",
         "// 关键：WeaponTypes \"None\" —— 原版 Target_ShadowStrike_Instant_Unarmed 就是靠它 + 徒手 AttackType 翻面的\n",
         "// 与武器版 Target_MainHandAttack 的差别：武器版是 WeaponTypes \"Melee\"，那会让引擎仍按武器攻击结算\n",
         LINE]
    t.append('\nnew entry "Target_KD_Attack"\n')
    t.append('type "SpellData"\n')
    t.append('using "Target_UnarmedAttack"\n')          # 徒手全套字段：SpellFlags / 动画 / 无 WeaponTypes
    t.append('data "SpellRoll" "Attack(AttackType.MeleeUnarmedAttack)"\n')
    t.append('data "WeaponTypes" "None"\n')             # 翻面开关（照抄原版徒手版写法）
    t.append('data "SpellSuccess" "%s"\n' % ATTACK_DMG)
    t.append('data "TooltipDamageList" "%s"\n' % TOOLTIP_DMG)
    t.append('data "TooltipAttackSave" "MeleeUnarmedAttack"\n')
    t.append('data "DisplayName" "%s;1"\n' % HL["atk_name"])
    t.append('data "Description" "%s;1"\n' % HL["atk_desc"])
    t.append('data "CastEffect" "9d8f170e-35d7-4cdb-b1f9-5493cf771b19"\n')
    t.append('data "PrepareSound" "Vocal_Component_Monk_Damage"\n')
    t.append('data "CastSound" "Spell_Cast_Monk_UnarmedStrike_L1to3"\n')
    t.append('data "TargetSound" "Spell_Impact_Monk_UnarmedStrike_L1to3"\n')
    t.append('data "Sheathing" "DontChange"\n')

    # 三件各自的攻击变体：附伤已改为"并入徒手骰"（见 TIER_BOOST），
    # 这里只保留"命中时施加的状态"（流血检定 / 碎甲）—— 状态施加与伤害通道无关，不受抗性影响。
    t.append('\nnew entry "Target_KD_Attack_Rare"\n')
    t.append('type "SpellData"\n')
    t.append('using "Target_KD_Attack"\n')
    t.append('data "SpellSuccess" "%s;ApplyStatus(KD_BLEED_CHECK,100,1)"\n' % ATTACK_DMG)

    t.append('\nnew entry "Target_KD_Attack_VeryRare"\n')
    t.append('type "SpellData"\n')
    t.append('using "Target_KD_Attack"\n')

    t.append('\nnew entry "Target_KD_Attack_Legendary"\n')
    t.append('type "SpellData"\n')
    t.append('using "Target_KD_Attack"\n')
    t.append('data "SpellSuccess" "%s%s"\n' % (ATTACK_DMG, SUNDER))

    # 武僧徒手系能力（疾风连击 / 武艺：徒手打击）的同款替身：保留原版的连击结构与消耗，
    # 只把伤害链换成我们这套（含武器骰、附魔、functor）；额外伤害本身是角色级徒手骰加成，
    # 因此这三类能力会自动带上它，不需要为每个品阶各做一份。
    for vanilla, tag, roll, costs in MONK_ATTACKS:
        name = "Target_KD_%s" % tag
        t.append('\nnew entry "%s"\n' % name)
        t.append('type "SpellData"\n')
        t.append('using "Target_KD_Attack"\n')
        t.append('data "SpellRoll" "%s"\n' % roll)
        t.append('data "UseCosts" "%s"\n' % costs)
        t.append('// 顶掉原版：%s\n' % vanilla)
    w(os.path.join(DATA, "KD_2_Attacks.txt"), "".join(t))

# ============================================================ 状态
def build_statuses():
    t = [LINE,
         "// 状态：流血检定 / 碎甲两层\n",
         LINE]
    t.append('\nnew entry "KD_BLEED_CHECK"\n')
    t.append('type "StatusData"\n')
    t.append('data "StatusType" "BOOST"\n')
    t.append('data "StackId" "KD_BLEED_CHECK"\n')
    t.append('data "StackType" "Overwrite"\n')
    t.append('data "OnApplyRoll" "RollDieAgainstPercent(DiceType.d10,2)"\n')   # 2/10 = 20%
    t.append('data "OnApplySuccess" "ApplyStatus(BLEEDING,100,2)"\n')
    t.append('data "OnApplyFail" ""\n')
    t.append('data "StatusPropertyFlags" "DisableOverhead;DisableCombatlog;DisablePortraitIndicator"\n')

    for i in (1, 2):
        t.append('\nnew entry "KD_ARMORBREAK_%d"\n' % i)
        t.append('type "StatusData"\n')
        t.append('data "StatusType" "BOOST"\n')
        t.append('data "DisplayName" "%s;1"\n' % HL["sunder_name"])
        t.append('data "Description" "%s;1"\n' % HL["sunder_desc"])
        t.append('data "Icon" "statIcons_Mag_Attack_Debuff"\n')
        t.append('data "StackId" "KD_ARMORBREAK_%d"\n' % i)
        t.append('data "StackType" "Overwrite"\n')      # 各自独立刷新，不互相覆盖
        t.append('data "Boosts" "Resistance(Bludgeoning, Vulnerable)"\n')
        t.append('data "StatusPropertyFlags" "DisableOverhead;DisableCombatlog"\n')

    # 攻击覆写：由 StatusOnEquip 上的隐藏技术状态承载。
    # 写在武器 Boosts 里时，tooltip 会把 AttackSpellOverride 的第一个参数以原始 stat 名直接打出来
    # （原版没有任何武器这样用，属于 tooltip 未覆盖的路径）；原版对同一函数用的是状态承载
    # （UNARMEDATTACK_OVERRIDE_BOAR / WOLF / WOLF_DIRE 三个状态），照抄即可，tooltip 不再出现杂物。
    for tag, spell in (("RARE", "Target_KD_Attack_Rare"),
                       ("VERY", "Target_KD_Attack_VeryRare"),
                       ("LEG", "Target_KD_Attack_Legendary")):
        t.append('\nnew entry "KD_OVERRIDE_%s"\n' % tag)
        t.append('type "StatusData"\n')
        t.append('data "StatusType" "BOOST"\n')
        t.append('data "StackId" "KD_OVERRIDE_%s"\n' % tag)
        t.append('data "StackType" "Overwrite"\n')
        # 主手攻击 + 武僧徒手系能力（疾风连击 / 武艺：徒手打击）一起顶掉
        boosts = ["AttackSpellOverride(%s, Target_MainHandAttack)" % spell]
        for vanilla, atag, _roll, _costs in MONK_ATTACKS:
            boosts.append("AttackSpellOverride(Target_KD_%s, %s)" % (atag, vanilla))
        t.append('data "Boosts" "%s"\n' % ";".join(boosts))
        t.append('data "StatusPropertyFlags" "DisableOverhead;DisableCombatlog;DisablePortraitIndicator"\n')
    w(os.path.join(DATA, "KD_3_Statuses.txt"), "".join(t))

# ============================================================ 被动（展示 + 附伤通道）
def build_passives():
    def passive(stat, name, desc, icon="Action_UnarmedAttack", boost=None, hidden=False,
                context=None, conditions=None, functors=None):
        s = '\nnew entry "%s"\n' % stat
        s += 'type "PassiveData"\n'
        s += 'data "DisplayName" "%s;1"\n' % name
        s += 'data "Description" "%s;1"\n' % desc
        s += 'data "Icon" "%s"\n' % icon
        s += 'data "Properties" "%s"\n' % ("IsHidden" if hidden else "Highlighted")
        if boost:
            s += 'data "Boosts" "%s"\n' % boost
        if context:
            s += 'data "StatsFunctorContext" "%s"\n' % context
        if conditions:
            s += 'data "Conditions" "%s"\n' % conditions
        if functors:
            s += 'data "StatsFunctors" "%s"\n' % functors
        return s

    t = [LINE,
         "// 被动只做展示（Highlighted，无机制）。\n",
         "// 附伤已经全部搬进攻击法术的 SpellSuccess —— 实测用被动 OnDamage/OnAttack 里的 DealDamage\n",
         "// 打出的独立伤害实例不参与抗性/易伤结算（碎甲只影响了基础钝击伤害）。\n",
         LINE]
    # 展示用
    t.append(passive("KD_SteelFist", HL["fist_name"], HL["fist_desc"]))
    t.append(passive("KD_Trait_Claw", HL["claw_name"], HL["claw_desc"]))
    t.append(passive("KD_Trait_Chill", HL["chill_name"], HL["chill_desc"]))
    t.append(passive("KD_Trait_Shell", HL["shell_name"], HL["shell_desc"]))

    # 附伤骰的载体：隐藏被动（原版手套类的徒手附伤也全是这个结构）。
    # 放在被动里而不是武器 Boosts 里 —— 武器 Boosts 的骰子会被物品 tooltip 直接渲染成裸骰子行。
    for tier, stat in TIER_RIDER_PASSIVE.items():
        desc = {"Rare": "claw", "VeryRare": "chill", "Leg": "shell"}[tier]
        t.append(passive(stat, HL[desc + "_name"], HL[desc + "_desc"],
                         icon="statIcons_Mag_Attack_Debuff", hidden=True,
                         boost=TIER_BOOST[tier]))
    w(os.path.join(DATA, "KD_4_Passives.txt"), "".join(t))

# ============================================================ 戴摩上架
def build_treasure():
    t = [LINE,
         "// 戴摩（Weaponsmith）三章上架：第一章 DEN、第二章 HAV、第三章 LOW\n",
         "// 追加写法照 ActTwoExpansion 对 TUT_Chest_Potions 的做法（CanMerge 1 + new subtable）\n",
         LINE]
    for table, cat in (("DEN_Weaponsmith_Trade", "I_KD_SteelSpikeFist"),
                       ("HAV_Weaponsmith_Trade", "I_KD_BoneChill"),
                       ("LOW_Weaponsmith_Trade", "I_KD_Unsharpened")):
        t.append('\nnew treasuretable "%s"\n' % table)
        t.append('CanMerge 1\n')
        t.append('new subtable "-1"\n')
        t.append('object category "%s",1,0,0,0,0,0,0,0\n' % cat)
    w(os.path.join(PUB, "Stats", "Generated", "TreasureTable.txt"), "".join(t))

# 备用获取（探针专有）：必须追加到同一份 TreasureTable.txt 里；发布版不调用它
def build_treasure_fallback():
    path = os.path.join(PUB, "Stats", "Generated", "TreasureTable.txt")
    lines = ['\n// 备用：教程宝箱里各放一套（探针专有）\n']
    lines.append('new treasuretable "TUT_Chest_Potions"\n')
    lines.append('CanMerge 1\n')
    for cat in ("I_KD_SteelSpikeFist", "I_KD_BoneChill", "I_KD_Unsharpened"):
        lines.append('new subtable "-1"\n')
        lines.append('object category "%s",1,0,0,0,0,0,0,0\n' % cat)
    io.open(path, "a", encoding="utf-8", newline="\n").write("".join(lines))
    print("  已追加教程宝箱兜底（探针专有）")

# ============================================================ 根模板
def build_root_templates():
    rows = [
        # 自定义图标名（配方见 gen_atlas.py：Icons_Items.lsx + TextureBank + 2048 图集 + 380/144 单图）
        ("KD_SteelSpikeFist", T_RARE, "KD_Item_Knuckle_Steel_Spike", HL["rare_name"], HL["rare_desc"]),
        ("KD_BoneChill", T_VERY, "KD_Item_Knuckle_Bone_Chill", HL["very_name"], HL["very_desc"]),
        ("KD_Unsharpened", T_LEG, "KD_Item_Knuckle_Unsharpened", HL["leg_name"], HL["leg_desc"]),
    ]
    t = ['<?xml version="1.0" encoding="utf-8"?>\n', '<save>\n',
         '\t<version major="4" minor="0" revision="6" build="5" lslib_meta="v1,bswap_guids" />\n',
         '\t<region id="Templates">\n', '\t\t<node id="Templates">\n', '\t\t\t<children>\n']
    for name, mk, icon, hname, hdesc in rows:
        t.append('\t\t\t\t<node id="GameObjects">\n')
        t.append('\t\t\t\t\t<attribute id="Description" type="TranslatedString" handle="%s" version="1" />\n' % hdesc)
        t.append('\t\t\t\t\t<attribute id="DisplayName" type="TranslatedString" handle="%s" version="1" />\n' % hname)
        t.append('\t\t\t\t\t<attribute id="EquipmentTypeID" type="guid" value="%s" />\n' % EQ_TYPE_ID)
        t.append('\t\t\t\t\t<attribute id="Icon" type="FixedString" value="%s" />\n' % icon)
        t.append('\t\t\t\t\t<attribute id="LevelName" type="FixedString" value="" />\n')
        t.append('\t\t\t\t\t<attribute id="MapKey" type="FixedString" value="%s" />\n' % mk)
        t.append('\t\t\t\t\t<attribute id="Name" type="LSString" value="%s" />\n' % name)
        t.append('\t\t\t\t\t<attribute id="ParentTemplateId" type="FixedString" value="%s" />\n'
                 % (PARENT_TMPL if VISUAL_MODE == "dagger" else ""))
        t.append('\t\t\t\t\t<attribute id="PhysicsTemplate" type="FixedString" value="%s" />\n'
                 % (PHYS_TMPL if VISUAL_MODE == "dagger" else ""))
        t.append('\t\t\t\t\t<attribute id="Stats" type="FixedString" value="%s" />\n' % name)
        t.append('\t\t\t\t\t<attribute id="Type" type="FixedString" value="item" />\n')
        t.append('\t\t\t\t\t<attribute id="VisualTemplate" type="FixedString" value="%s" />\n'
                 % (VISUAL_TMPL_BY_ITEM.get(name, VISUAL_TMPL) if VISUAL_MODE == "dagger" else ""))
        t.append('\t\t\t\t</node>\n')
    t += ['\t\t\t</children>\n', '\t\t</node>\n', '\t</region>\n', '</save>\n']
    w(os.path.join(RT, "_merged.lsx"), "".join(t))

# ============================================================ 本地化
LOCA = {
    "Chinese": [
        (HL["rare_name"], "钢刺之拳"),
        (HL["rare_desc"], "一套套在指节上的钢刺护手。以指虎出拳时，攻击仍按徒手结算；指节上的尖刺会在命中时撕开皮肉。"),
        (HL["very_name"], "彻骨之寒"),
        (HL["very_desc"], "寒气凝成的指虎，握上去像攥着一把碎冰。对已经被水浸透的目标，寒意会顺着水渗进骨头里。"),
        (HL["leg_name"], "无锋"),
        (HL["leg_desc"], "没有锋刃，只有纯粹的分量。传说它曾把一整套板甲连同里面的人一起打成了铁屑。"),
        (HL["fist_name"], "钢拳"),
        (HL["fist_desc"], "使用此武器时，主手攻击被视为徒手攻击。"),
        (HL["claw_name"], "钢爪"),
        (HL["claw_desc"], "徒手攻击额外造成 1d4 穿刺伤害，并有 20% 概率使目标流血 2 回合。"),
        (HL["chill_name"], "刺骨"),
        (HL["chill_desc"], "徒手攻击额外造成 1d6 寒冷伤害；若目标【濡湿】，再额外造成 1d6 寒冷伤害。"),
        (HL["shell_name"], "剥壳"),
        (HL["shell_desc"], "徒手攻击额外造成 2d10 钝击伤害，并使目标【碎甲】3 回合。"),
        (HL["atk_name"], "指虎攻击"),
        (HL["atk_desc"], "以指虎发动的近战攻击——判定与加成均按徒手攻击结算。"),
        (HL["sunder_name"], "碎甲"),
        (HL["sunder_desc"], "获得钝击易伤。两层碎甲足以让原本抗钝击的目标也变得脆弱。"),
    ],
    "English": [
        (HL["rare_name"], "Steel-Spike Fists"),
        (HL["rare_desc"], "A pair of spiked steel knuckles. Your main-hand attacks with it still count as unarmed attacks; the spikes tear flesh on impact."),
        (HL["very_name"], "Bone-Chill"),
        (HL["very_desc"], "Knuckles wrought from cold. Against a soaked target, the chill sinks straight into the bone."),
        (HL["leg_name"], "The Unsharpened"),
        (HL["leg_desc"], "No edge at all, only sheer weight. They say it once turned a full suit of plate - and the man inside - into iron filings."),
        (HL["fist_name"], "Steel Fist"),
        (HL["fist_desc"], "Your main-hand attacks with this weapon count as unarmed attacks."),
        (HL["claw_name"], "Steel Claw"),
        (HL["claw_desc"], "Unarmed attacks deal an extra 1d4 Piercing damage and have a 20% chance to inflict Bleeding for 2 turns."),
        (HL["chill_name"], "Piercing Cold"),
        (HL["chill_desc"], "Unarmed attacks deal an extra 1d6 Cold damage, or 2d6 against Wet targets."),
        (HL["shell_name"], "Shellbreaker"),
        (HL["shell_desc"], "Unarmed attacks deal an extra 2d10 Bludgeoning damage and apply Sundered for 3 turns."),
        (HL["atk_name"], "Knuckle Strike"),
        (HL["atk_desc"], "A melee attack made with knuckle dusters - resolved as an unarmed attack."),
        (HL["sunder_name"], "Sundered"),
        (HL["sunder_desc"], "Vulnerable to Bludgeoning damage. Two stacks are enough to make even a resistant target fragile."),
    ],
}


def build_localization():
    for lang, entries in LOCA.items():
        t = ['<?xml version="1.0" encoding="utf-8"?>\n', "<contentList>\n"]
        for uid, text in entries:
            t.append('\t<content contentuid="%s" version="1">%s</content>\n' % (uid, text))
        t.append("</contentList>\n")
        body = "".join(t)
        w(os.path.join(LOCP, lang, "KnuckleDusters.xml"), body)
        w(os.path.join(LOCR, lang, "KnuckleDusters.xml"), body)

# ============================================================ meta
def build_meta():
    t = '''<?xml version="1.0" encoding="utf-8"?>
<save>
  <version major="4" minor="8" revision="0" build="500" />
  <region id="Config">
    <node id="root">
      <children>
        <node id="Dependencies" />
        <node id="ModuleInfo">
          <attribute id="Author" type="LSString" value="16084" />
          <attribute id="CharacterCreationLevelName" type="FixedString" value="" />
          <attribute id="Description" type="LSString" value="%s" />
          <attribute id="Folder" type="LSString" value="%s" />
          <attribute id="GMTemplate" type="FixedString" value="" />
          <attribute id="LobbyLevelName" type="FixedString" value="" />
          <attribute id="MD5" type="LSString" value="" />
          <attribute id="MainMenuBackgroundVideo" type="FixedString" value="" />
          <attribute id="MenuLevelName" type="FixedString" value="" />
          <attribute id="Name" type="FixedString" value="%s" />
          <attribute id="NumPlayers" type="uint8" value="4" />
          <attribute id="PhotoBooth" type="FixedString" value="" />
          <attribute id="StartupLevelName" type="FixedString" value="" />
          <attribute id="Tags" type="LSString" value="" />
          <attribute id="Type" type="FixedString" value="Add-on" />
          <attribute id="UUID" type="FixedString" value="%s" />
          <attribute id="Version64" type="int64" value="72057594037927936" />
          <children>
            <node id="PublishVersion">
              <attribute id="Version64" type="int64" value="72057594037927936" />
            </node>
            <node id="Scripts" />
            <node id="TargetModes">
              <children>
                <node id="Target">
                  <attribute id="Object" type="FixedString" value="Story" />
                </node>
              </children>
            </node>
          </children>
        </node>
      </children>
    </node>
  </region>
</save>
''' % (("Knuckle dusters: a melee-slot weapon whose attacks still count as unarmed attacks."
        if RELEASE else
        "Knuckle dusters probe: melee-slot weapon whose attacks count as unarmed."),
       MOD,
       "Knuckle Dusters" if RELEASE else "Knuckle Dusters (Probe)",
       MOD_UUID)
    w(os.path.join(ROOT, "Mods", MOD, "meta.lsx"), t)

# ============================================================ SE 辅助
def build_se():
    lua = '''--[[ 指虎探针：进游戏后自动把三套指虎放进背包（无需控制台）
     触发：SessionLoaded 事件（延迟 DELAY_MS 后开始）+ 模组加载 15 秒后的兜底轮询
     日志：D:\\DSH\\knuckle_grant.log（每一步都落盘，同时打印到 SE 日志）
     手动：控制台可用时输入 !kd 可随时再发一份
]]

local DELAY_MS  = 8000        -- 读档后等多久开始发（毫秒）
local POLL_MS   = 5000        -- 没成功时的重试间隔
local MAX_TRIES = 24          -- 最多重试次数（约 2 分钟）
-- 注意：Ext.IO.SaveFile 只接受"相对 SE 目录"的文件名，写绝对路径会被拒
-- （日志里会看到 IsSafeRelativePath(): Illegal character in filename）。
-- 所以这里用纯文件名；最权威的记录仍然是 SE 自己的 Extender Runtime 日志里的 [KD] 行。
local LOG_PATH  = "knuckle_grant.log"

local ITEMS = {
    { name = "KD_SteelSpikeFist", uuid = "__UUID_RARE__", label = "钢刺之拳 (Rare)" },
    { name = "KD_BoneChill",      uuid = "__UUID_VERY__", label = "彻骨之寒 (VeryRare)" },
    { name = "KD_Unsharpened",    uuid = "__UUID_LEG__",  label = "无锋 (Legendary)" },
}

local LOG, done, tries = {}, false, 0

local function log(msg)
    local ts = "?"
    pcall(function() ts = os.date("%H:%M:%S") end)
    LOG[#LOG + 1] = ts .. "  " .. tostring(msg)
    _P("[KD] " .. tostring(msg))
    pcall(function() Ext.IO.SaveFile(LOG_PATH, table.concat(LOG, "\\n")) end)
end

-- 同一件物品按三种模板引用形式依次试，成功即停
local function tryGive(host, it)
    local forms = { it.name .. "_" .. it.uuid, it.uuid, it.name }
    for _, f in ipairs(forms) do
        local ok = pcall(function() Osi.TemplateAddTo(f, host, 1) end)
        if ok then
            log("已发放 " .. it.label .. "  <- " .. f)
            return true
        end
    end
    log("发放失败：" .. it.label .. "（三种引用形式都报错）")
    return false
end

-- 背包里是否已经有一把（探测多个可能的 Osiris 查询名，全不可用则返回 nil）
local function ownsAny(host)
    local names = { "KD_SteelSpikeFist", "KD_BoneChill", "KD_Unsharpened" }
    for _, g in ipairs({ "GetInventoryItems", "GetItemsInInventory", "GetInventoryItemList" }) do
        local okIdx, fn = pcall(function() return Osi[g] end)
        if okIdx and type(fn) == "function" then
            local ok, items = pcall(fn, host)
            if ok and type(items) == "table" then
                for _, item in ipairs(items) do
                    local ok2, t = pcall(Osi.GetTemplate, item)
                    if ok2 and type(t) == "string" then
                        for _, n in ipairs(names) do
                            if string.find(t, n, 1, true) then return n end
                        end
                    end
                end
                return nil
            end
        end
    end
    return nil
end

local function attempt()
    if done then return end
    local okHost, host = pcall(Osi.GetHostCharacter)
    if not okHost or not host or host == "" then return end
    local owned = ownsAny(host)
    if owned then
        done = true
        log("背包里已有 " .. owned .. "，跳过自动发放（要再来一份就输入 !kd）")
        return
    end
    log("开始发放到 " .. tostring(host))
    for _, it in ipairs(ITEMS) do tryGive(host, it) end
    done = true
    -- 发放后校验：TemplateAddTo 不报错 ≠ 物件真的生成了，所以再扫一次背包把结论写进日志
    pcall(function()
        local found = ownsAny(host)
        if found then
            log("校验通过：背包里确实有 " .. found)
        else
            log("校验失败：背包里仍然没有指虎 —— 说明模板没生成物件（先看 RootTemplate 的 visual/physics 字段是否完整）")
        end
    end)
    log("完成。")
end

local function poll()
    if done then return end
    tries = tries + 1
    attempt()
    if not done and tries < MAX_TRIES then
        Ext.Timer.WaitFor(POLL_MS, poll)
    end
end

local function arm(reason)
    done = false
    tries = 0
    log("已布防（" .. reason .. "），" .. math.floor(DELAY_MS / 1000) .. " 秒后发放")
    Ext.Timer.WaitFor(DELAY_MS, poll)
end

-- 触发点 1：会话加载
local okEvt = pcall(function()
    Ext.Events.SessionLoaded:Subscribe(function() arm("会话加载") end)
end)
if not okEvt then log("订阅 SessionLoaded 失败，改用定时兜底") end

-- 触发点 2：模组加载后兜底（比如事件没触发）
Ext.Timer.WaitFor(15000, function() poll() end)

-- 手动兜底：控制台可用时 !kd
pcall(function()
    Ext.RegisterConsoleCommand("kd", function()
        done = false
        tries = 0
        attempt()
    end)
end)
'''
    lua = (lua.replace("__UUID_RARE__", T_RARE)
              .replace("__UUID_VERY__", T_VERY)
              .replace("__UUID_LEG__", T_LEG))
    w(os.path.join(ROOT, "Mods", MOD, "ScriptExtender", "Lua", "BootstrapServer.lua"), lua)
    # SE 需要这份 Config.json 才会加载本模组的 Lua（照 5eSpells 的写法）
    cfg = ('{\n'
           '    "RequiredVersion": 20,\n'
           '    "ModTable": "%s_%s",\n'
           '    "FeatureFlags": [\n'
           '        "Lua"\n'
           '    ]\n'
           '}\n') % (MOD, MOD_UUID)
    w(os.path.join(ROOT, "Mods", MOD, "ScriptExtender", "Config.json"), cfg)
    # 客户端也放一个占位（便于在 SE 日志里确认模组被加载；不做任何发放）
    client = '''-- 指虎探针：客户端侧只为在 SE 日志里留一行，实际发放全部在 BootstrapServer.lua
_P("[KD] KnuckleDusters client bootstrap loaded")
'''
    w(os.path.join(ROOT, "Mods", MOD, "ScriptExtender", "Lua", "BootstrapClient.lua"), client)


def main():
    print("生成指虎%s包：" % ("发布" if RELEASE else "探针"))
    build_meta()
    build_weapons()
    build_attacks()
    build_statuses()
    build_passives()
    # 戴摩三章上架：两种模式都要有
    build_treasure()
    # 探针专有：教程宝箱兜底（发布版剥掉）
    if not RELEASE:
        build_treasure_fallback()
    build_root_templates()
    build_localization()
    # 探针专有：SE 自动发放脚本与 Config.json（发布版不打包，且清掉旧文件）
    if RELEASE:
        stale = os.path.join(ROOT, "Mods", MOD, "ScriptExtender")
        if os.path.isdir(stale):
            import shutil
            shutil.rmtree(stale)
            print("  已移除探针专用 ScriptExtender 目录：%s" % stale)
    else:
        build_se()
    print("\n模组 UUID = %s" % MOD_UUID)
    print("根模板 UUID：稀有 %s / 珍奇 %s / 传奇 %s" % (T_RARE, T_VERY, T_LEG))


if __name__ == "__main__":
    main()
