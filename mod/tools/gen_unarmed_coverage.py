# -*- coding: utf-8 -*-
"""Extend the "every weapon rider lands on unarmed strikes" coverage.

How the whole thing works (why riders are generic but spells are not):

  * A rider such as Holy Weapon's `WeaponDamage(2d8,Radiant)` only lands when the
    attack is resolved as a WEAPON attack and the damage chain contains
    `MainMeleeWeapon` / `ExecuteWeaponFunctors(MainHand)`. It does not care which
    rider it is -- so once a spell is in this shape, EVERY weapon-attached damage
    bonus applies to it. That side needs no enumeration.
  * But each spell is its own entry, and the ones we already converted are only
    five: MainHand attack (via AttackSpellOverride), Target_FlurryOfBlows,
    the three Target_OpenHandTechnique_* variants, and Target_UnarmedStrike_Monk.
  * A scan of Shared + SharedDev for `DealDamage(...UnarmedDamage...)` found 16
    spells. The ones still resolving as pure unarmed (and therefore ignoring every
    weapon rider) are handled here:

        Target_UnarmedAttack            generic unarmed attack (other classes/features)
        Target_StunningStrike_Unarmed   monk Stunning Strike
        Target_ShadowStrike_Instant_Unarmed  monk Shadow Step strike
        Target_KiResonation_Punch       monk Ki Resonation

    deliberately NOT touched:
        Target_ConcussiveSmash_* / Target_Slash_* / Target_PiercingThrust_*
            -> those are the Spiritual Weapon summon's own attacks; they belong to
               a different entity and must keep their own stats.
        Projectile_FangsOfTheFireSnake / Projectile_Deflect_Missiles
            -> a projectile and a reaction, not melee weapon strikes.

Each converted spell keeps its animation, costs, DisplayName and special effects;
we only (a) flip the roll to MeleeWeaponAttack, (b) declare WeaponTypes Melee,
(c) insert the weapon damage + weapon functor pair, and (d) add IsAttack.

`max(0, MainMeleeWeapon)` is what keeps this safe: with no weapon equipped the term
is 0, so a bare-handed character behaves exactly as vanilla.

Run: python gen_unarmed_coverage.py
"""
import io
import os
import re

OUT = r"D:\DSH\knuckle_mod\Public\KnuckleDusters\Stats\Generated\Data\KD_9_UnarmedCoverage.txt"
SRCS = [
    r"D:\DSH\knuckle_tools\vdev\Public\SharedDev\Stats\Generated\Data",
    r"D:\DSH\knuckle_tools\vall\Public\Shared\Stats\Generated\Data",
]

TARGETS = [
    "Target_UnarmedAttack",
    "Target_StunningStrike_Unarmed",
    "Target_ShadowStrike_Instant_Unarmed",
    "Target_KiResonation_Punch",
]

WEAPON = (";DealDamage(max(0,MainMeleeWeapon), MainMeleeWeaponDamageType)"
          ";ExecuteWeaponFunctors(MainHand)")

HEADER = """// ============================================================================
// 徒手打击覆盖面扩展（2026-10-18）
//
// 目的：让**任何**挂在指虎上的武器附伤（神圣武器、元素武器、以及别人后来加的）
// 都能对"徒手打击"系列生效。附伤那一侧不需要枚举 —— 只要一支法术被改造成
// 「武器攻击 + 伤害链含 MainMeleeWeapon/ExecuteWeaponFunctors」，所有武器侧
// 附伤就都会自动进来。需要枚举的是**法术**，也就是这个文件。
//
// 扫描 Shared + SharedDev 里所有用 DealDamage(...UnarmedDamage...) 的法术，共 16 支。
// 已覆盖（另在 KD_2 / KD_5 / KD_7）：主手攻击、Target_FlurryOfBlows、
// Target_OpenHandTechnique_{Push,Knock,NoReactions}、Target_UnarmedStrike_Monk。
// 本文件补上剩下 4 支仍在按纯徒手结算的：
//   Target_UnarmedAttack（通用徒手攻击）、Target_StunningStrike_Unarmed（震慑拳）、
//   Target_ShadowStrike_Instant_Unarmed（暗影步打击）、Target_KiResonation_Punch（气之共鸣）。
//
// 刻意不动：
//   Target_ConcussiveSmash_* / Target_Slash_* / Target_PiercingThrust_*
//       —— 这些是"灵体武器"召唤物的自身攻击，属于另一个实体；
//   Projectile_FangsOfTheFireSnake / Projectile_Deflect_Missiles
//       —— 一个是投射物、一个是反应，不是近战武器打击。
//
// 每支法术保留原动画、消耗、名称与特殊效果，只做四件事：
//   ① SpellRoll → MeleeWeaponAttack；② 声明 WeaponTypes Melee；
//   ③ 伤害链插入「武器伤害 + 武器 functor」；④ SpellFlags 补 IsAttack。
// max(0, MainMeleeWeapon) 是安全阀：空手时取 0，与改动前完全一致。
// ============================================================================

"""


def load_layer():
    """name -> (block_text, layer_rank); SharedDev shadows Shared."""
    found = {}
    for rank, d in enumerate(SRCS):
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            if not fn.startswith("Spell_") or not fn.endswith(".txt"):
                continue
            t = io.open(os.path.join(d, fn), encoding="utf-8-sig", errors="replace").read()
            for b in re.split(r'(?m)^new entry "', t)[1:]:
                name = b.split('"', 1)[0]
                if name in TARGETS and name not in found:
                    body = b.split("\n", 1)[1] if "\n" in b else ""
                    nxt = re.search(r'(?m)^new entry "', body)
                    if nxt:
                        body = body[:nxt.start()]
                    found[name] = body.rstrip()
    return found


def inject_weapon(success):
    """Add what the chain is missing, never twice.

    Some vanilla unarmed chains (e.g. Target_ShadowStrike_Instant_Unarmed) already call
    ExecuteWeaponFunctors(MainHand) -- duplicating it would apply every weapon rider
    twice, so we only add the pieces that are absent.
    """
    add = ""
    if "MainMeleeWeapon" not in success:
        add += ";DealDamage(max(0,MainMeleeWeapon), MainMeleeWeaponDamageType)"
    if "ExecuteWeaponFunctors" not in success:
        add += ";ExecuteWeaponFunctors(MainHand)"
    return success + add if add else success


def patch(name, body):
    out, got_roll, got_flag = [], False, False
    for ln in body.split("\n"):
        if ln.startswith('data "SpellSuccess" "'):
            m = re.match(r'data "SpellSuccess" "(.*)"\s*$', ln)
            out.append('data "SpellSuccess" "%s"' % inject_weapon(m.group(1)))
        elif ln.startswith('data "SpellRoll" "'):
            m = re.match(r'data "SpellRoll" "(.*)"\s*$', ln)
            roll = m.group(1).replace("MeleeUnarmedAttack )", "MeleeWeaponAttack)") \
                              .replace("MeleeUnarmedAttack)", "MeleeWeaponAttack)")
            out.append('data "SpellRoll" "%s"' % roll)
            got_roll = True
        elif ln.startswith('data "SpellFlags" "'):
            m = re.match(r'data "SpellFlags" "(.*)"\s*$', ln)
            flags = m.group(1)
            if "IsAttack" not in flags:
                flags = "IsAttack;" + flags
            out.append('data "SpellFlags" "%s"' % flags)
            got_flag = True
        elif ln.startswith('data "WeaponTypes" "'):
            out.append('data "WeaponTypes" "Melee"')
        else:
            out.append(ln)
    # fields the vanilla entry may not carry
    if not any(l.startswith('data "WeaponTypes"') for l in out):
        out.insert(1, 'data "WeaponTypes" "Melee"')
    if not got_flag:
        out.insert(1, 'data "SpellFlags" "IsAttack;IsMelee;IsHarmful"')
    return 'new entry "%s"\n' % name + "\n".join(out) + "\n", got_roll


def main():
    found = load_layer()
    parts = [HEADER]
    for name in TARGETS:
        if name not in found:
            print("  MISSING in vanilla:", name)
            continue
        blk, got_roll = patch(name, found[name])
        print("  %-38s roll=%s" % (name, got_roll))
        parts.append(blk)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(parts))
    print("wrote %s (%d B)" % (os.path.basename(OUT), os.path.getsize(OUT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
