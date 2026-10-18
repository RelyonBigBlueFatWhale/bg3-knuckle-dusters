# -*- coding: utf-8 -*-
"""Override the three Open Hand flurry variants so each strike carries the knuckles.

Why the previous rounds failed on "Flurry of Blows": the Open Hand monk does NOT cast
Target_FlurryOfBlows. It casts one of

    Target_OpenHandTechnique_Push / _Knock / _NoReactions      (Public/SharedDev)

Each of those does `using "Target_FlurryOfBlows"` but **overrides SpellSuccess and
SpellFlags itself**, so editing the base spell (SpellRoll / WeaponTypes / SpellSuccess /
IsAttack) had zero effect on what the player actually presses. The player's screenshot
("疾风连击: 推击") is exactly this variant.

This generator emits same-name overrides for the three variants that keep EVERYTHING
vanilla -- animation, cast sound, DisplayName, UseCosts, the Open Hand special effect
(Force / PRONE / OPEN_HAND_NO_REACTIONS) -- and only injects the weapon damage +
weapon functor pair so that each of the two strikes carries them, plus the IsAttack
flag so the engine treats the spell as an attack at all.

Run: python gen_flurry_variants.py
"""
import io
import os
import re

SRC = r"D:\DSH\knuckle_tools\vdev\Public\SharedDev\Stats\Generated\Data\Spell_Target.txt"
OUT = r"D:\DSH\knuckle_mod\Public\KnuckleDusters\Stats\Generated\Data\KD_7_FlurryVariants.txt"

VARIANTS = [
    "Target_OpenHandTechnique_Push",
    "Target_OpenHandTechnique_Knock",
    "Target_OpenHandTechnique_NoReactions",
]

FIRST = "DealDamage(UnarmedDamage , Bludgeoning)"
WEAPON = (";DealDamage(max(0,MainMeleeWeapon), MainMeleeWeaponDamageType)"
          ";ExecuteWeaponFunctors(MainHand)")

HEADER = """// ============================================================================
// 散打宗三支「疾风连击：X」变体的同名覆盖（2026-10-18）
//
// 为什么必须单独覆盖：这三支法术 using "Target_FlurryOfBlows"，但**自己重写了
// SpellSuccess 与 SpellFlags**。所以改基类（SpellRoll / WeaponTypes / SpellSuccess /
// IsAttack）对玩家真正按下的这一支毫无作用 —— 这就是"主手吃得到附伤、疾风连击吃不到"
// 的最后一段原因。
//
// 做法：原版内容一字不改（动画、音效、DisplayName、消耗、散打宗特效 Force / PRONE /
// NO_REACTIONS 全部保留），只做两件事：
//   ① 在每一击的伤害链里插入「武器伤害 + 武器 functor」，两击都带；
//   ② SpellFlags 补上 IsAttack（原版这几支是纯徒手法术，没有这个标志）。
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


def inject(success):
    """Insert the weapon pair after the first unarmed strike, and inside Cast2."""
    if ';Cast2[' in success:
        head, tail = success.split(';Cast2[', 1)
        new_head = head + WEAPON
        new_tail = tail.replace(FIRST, FIRST + WEAPON, 1)
        return new_head + ';Cast2[' + new_tail
    return success + WEAPON


def build():
    text = io.open(SRC, encoding="utf-8-sig", errors="replace").read()
    parts = [HEADER]
    for name in VARIANTS:
        b = block(text, name)
        if not b:
            raise SystemExit("block not found: %s" % name)
        out, patched_success, patched_flags = [], False, False
        for ln in b.rstrip().split("\n"):
            if ln.startswith('data "SpellSuccess" "'):
                m = re.match(r'data "SpellSuccess" "(.*)"\s*$', ln)
                out.append('data "SpellSuccess" "%s"' % inject(m.group(1)))
                patched_success = True
            elif ln.startswith('data "SpellFlags" "'):
                m = re.match(r'data "SpellFlags" "(.*)"\s*$', ln)
                flags = m.group(1)
                if "IsAttack" not in flags:
                    flags = "IsAttack;" + flags
                out.append('data "SpellFlags" "%s"' % flags)
                patched_flags = True
            else:
                out.append(ln)
        print("  %-38s success=%s flags=%s" % (name, patched_success, patched_flags))
        parts.append("\n".join(out) + "\n")
    io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(parts))
    print("wrote %s (%d B)" % (os.path.basename(OUT), os.path.getsize(OUT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
