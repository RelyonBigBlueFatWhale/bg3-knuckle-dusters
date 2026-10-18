# -*- coding: utf-8 -*-
"""Override the two REAL monk attack spells, in the layer they actually live in.

Root cause of the "weapon riders never reach Flurry / Martial Arts strike" bug:

    Target_FlurryOfBlows      -> Public/SharedDev/Stats/Generated/Data/Spell_Target.txt
    Target_UnarmedStrike_Monk -> same file

Both live in the **SharedDev** layer, which the earlier searches never covered (only
Shared + Gustav were searched), so the first "fix" that renamed them to
Target_Flurry / Target_UnarmedAttack was in fact pointing at dead/other entries and
made things worse. And both vanilla spells deal damage like this:

    DealDamage(UnarmedDamage, Bludgeoning)          (Flurry: twice, via Cast2)
    DealDamage(UnarmedDamage, Bludgeoning)          (UnarmedStrike_Monk)

i.e. pure unarmed damage with **no weapon damage and no ExecuteWeaponFunctors**, so
CharacterWeaponDamage riders (Divine Favor, Elemental Weapon, ...) have nothing to
attach to. That is the whole bug.

Fix: same-name override of both spells, keeping vanilla's SpellSuccess verbatim and
APPENDING the two weapon lines. Appending (rather than rewriting) means the parse is
guaranteed to follow a pattern the engine already accepts, and the two unarmed
strikes still happen exactly as before.

Run: python make_monk_overrides.py
"""
import io
import os
import re
import uuid

SRC = r"D:\DSH\knuckle_tools\vdev\Public\SharedDev\Stats\Generated\Data\Spell_Target.txt"
OUT = r"D:\DSH\knuckle_mod\Public\KnuckleDusters\Stats\Generated\Data\KD_5_VanillaOverrides.txt"
LOCA = [
    (r"D:\DSH\knuckle_mod\Public\KnuckleDusters\Localization\Chinese\KnuckleDusters.xml", "Chinese"),
    (r"D:\DSH\knuckle_mod\Localization\Chinese\KnuckleDusters.xml", "Chinese"),
    (r"D:\DSH\knuckle_mod\Public\KnuckleDusters\Localization\English\KnuckleDusters.xml", "English"),
    (r"D:\DSH\knuckle_mod\Localization\English\KnuckleDusters.xml", "English"),
]

WEAPON_LINES = (";DealDamage(max(0,MainMeleeWeapon), MainMeleeWeaponDamageType)"
                ";ExecuteWeaponFunctors(MainHand)")

TARGETS = [
    ("Target_FlurryOfBlows", "flurry"),
    ("Target_UnarmedStrike_Monk", "unarmed"),
]

MARK_TEXT = {
    "Chinese": {"flurry": "疾风连击（KD覆盖生效）", "unarmed": "徒手打击（KD覆盖生效）"},
    "English": {"flurry": "Flurry of Blows (KD override live)",
                "unarmed": "Unarmed Strike (KD override live)"},
}

HEADER = """// ============================================================================
// 同名覆盖：武僧两支攻击法术（2026-10-18 修正）
//
// 三轮失败的真正原因：这两支法术在 **SharedDev** 层，之前只查了 Shared 与 Gustav，
// 误判成"名字不存在"，于是把覆盖目标改成了 Target_Flurry / Target_UnarmedAttack
// （前者是死条目、后者是另一种法术），结果一直空转。
//
// 它们原版的伤害链是**纯徒手**：
//     DealDamage(UnarmedDamage, Bludgeoning)              （疾风连击：Cast2 打两下）
//     DealDamage(UnarmedDamage, Bludgeoning)              （武艺：附赠打击）
// 没有 MainMeleeWeapon、没有 ExecuteWeaponFunctors —— 所以元素武器/神圣恩宠这类
// CharacterWeaponDamage 附伤无处附着，这就是用户看到"附伤不生效"的全部原因。
//
// 修法：原版 SpellSuccess **一字不改**，只在末尾追加两行武器伤害与武器 functor。
// 追加而不是重写，保证语法沿用引擎已接受的形式；两下徒手打击照旧。
// ============================================================================

"""


def block(text, name):
    m = re.search(r'(?m)^new entry "%s"\r?\n' % re.escape(name), text)
    if not m:
        return None
    rest = text[m.end():]
    nxt = re.search(r'(?m)^new entry "', rest)
    body = rest[:nxt.start()] if nxt else rest
    return 'new entry "%s"\n' % name + body.rstrip() + "\n"


def patch(name, marker_handle):
    t = io.open(SRC, encoding="utf-8-sig", errors="replace").read()
    b = block(t, name)
    if not b:
        raise SystemExit("block not found in SharedDev: %s" % name)
    lines = b.rstrip().split("\n")
    out, done = [], False
    for ln in lines:
        if ln.startswith('data "SpellSuccess"'):
            m = re.match(r'data "SpellSuccess" "(.*)"\s*$', ln)
            if not m:
                raise SystemExit("cannot parse SpellSuccess of %s" % name)
            out.append('// KD_APPEND: 原版伤害链保持原样，只追加武器伤害与武器 functor')
            out.append('data "SpellSuccess" "%s%s"' % (m.group(1), WEAPON_LINES))
            done = True
        elif ln.startswith('data "DisplayName"') and marker_handle:
            out.append('data "DisplayName" "%s;1"' % marker_handle)
        else:
            out.append(ln)
    if not done:
        raise SystemExit("%s has no SpellSuccess line" % name)
    return "\n".join(out) + "\n"


def main():
    handles = {}
    for path, lang in LOCA:
        if not os.path.isfile(path):
            continue
        s = io.open(path, encoding="utf-8-sig").read()
        add = ""
        for key in ("flurry", "unarmed"):
            h = handles.get(key)
            if not h:
                h = ("h" + uuid.uuid4().hex[:8] + "g" + uuid.uuid4().hex[:4] + "g"
                     + uuid.uuid4().hex[:4] + "g" + uuid.uuid4().hex[:4] + "g" + uuid.uuid4().hex[:12])
                handles[key] = h
            if h in s:
                continue
            add += '\t<content contentuid="%s" version="1">%s</content>\n' % (h, MARK_TEXT[lang][key])
        if add:
            s = s.replace("</contentList>", add + "</contentList>")
            io.open(path, "w", encoding="utf-8", newline="\n").write(s)
    print("loca handles:", handles)

    parts = [HEADER]
    for name, key in TARGETS:
        parts.append(patch(name, handles.get(key)))
        print("  patched:", name)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(parts))
    print("wrote %s (%d B)" % (os.path.basename(OUT), os.path.getsize(OUT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
