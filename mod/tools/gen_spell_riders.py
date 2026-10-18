# -*- coding: utf-8 -*-
"""Move the weapon-rider bridge from a passive Boost into the attack spells.

Why: the passive version fired even when the buff was NOT on the weapon (the user
reported every rider showing up unconditionally). Conditions inside a damage-modifier
Boost on a passive are evidently not evaluated the way we need.

SpellSuccess is a different place: its conditions are evaluated at damage-resolution
time with the full attack context (our own armorbreak conditionals live there), and --
per the reference notes -- damage written in SpellSuccess counts as this attack's
damage, so it also participates in resistance/vulnerability. That is strictly better
than a character-level damage modifier.

Idempotent by construction: it always regenerates the live file from a `.base` copy,
so running it twice cannot stack the riders twice.

Run: python gen_spell_riders.py
"""
import io
import os
import shutil

DATA = r"D:\DSH\knuckle_mod\Public\KnuckleDusters\Stats\Generated\Data"

TARGETS = ["KD_2_Attacks.txt", "KD_5_VanillaOverrides.txt"]

# (status, dice, damage type) -- produced by gen_rider_bridge.py's scan and then
# eyeballed; keep in sync with it.
RIDERS = [
    ("HOLY_WEAPON", "2d8", "Radiant"),
    ("DIPPED", "1d4", "Fire"),
    ("DIPPED", "1d4", "Poison"),
    ("POISON_WYVERN_DIPPED", "3d6", "Poison"),
    ("POISON_SERPENT_VENOM_DIPPED", "2d6", "Poison"),
    ("POISON_PURPLE_WORM_DIPPED", "6d6", "Poison"),
    ("OIL_OF_SHARPNESS_MELEE", "3", "Piercing"),
    ("HOBGOBLIN_LEADERSHIP_EQP", "1d4", "Force"),
    ("WILD_MAGIC_ENCHANT", "1d4", "Force"),
]


def chain():
    """Conditionals must name the context explicitly.

    Measured across two builds:
      * passive Boost, bare HasStatus  -> the damage was applied unconditionally
        (the modifier gets registered statically; the condition is not what gates it)
      * SpellSuccess, bare HasStatus   -> the damage never applied, i.e. the condition
        IS evaluated there, but it resolved against the wrong entity (the target), so
        a self-buff like HOLY_WEAPON read as false.

    Vanilla writes exactly this shape when it wants the attacker's own status, e.g.
    `IF(not Player(context.Source)):ApplyStatus(...)`, and our own armorbreak line uses
    `HasStatus('KD_ARMORBREAK_1', context.Target)` for the target side. So the fix is
    to say `context.Source` out loud.
    """
    parts = []
    for st, dice, dtype in RIDERS:
        parts.append("IF(HasStatus('%s', context.Source)):DealDamage(%s, %s)" % (st, dice, dtype))
    return ";".join(parts)


def ensure_base(path):
    base = path + ".base"
    if not os.path.isfile(base):
        shutil.copyfile(path, base)
        print("  created base copy:", os.path.basename(base))
    return base


def build(name):
    live = os.path.join(DATA, name)
    base = ensure_base(live)
    src = io.open(base, encoding="utf-8").read()
    riders = chain()
    out = []
    n = 0
    for ln in src.split("\n"):
        if ln.startswith('data "SpellSuccess" "'):
            # keep the vanilla/our chain verbatim, append the rider conditionals
            body = ln[len('data "SpellSuccess" "'):]
            if body.endswith('"'):
                body = body[:-1]
            ln = 'data "SpellSuccess" "%s;%s"' % (body, riders)
            n += 1
        out.append(ln)
    io.open(live, "w", encoding="utf-8", newline="\n").write("\n".join(out))
    print("  %-28s SpellSuccess patched: %d" % (name, n))
    return n


def main():
    print("rider chain: %d clauses" % len(RIDERS))
    total = 0
    for t in TARGETS:
        total += build(t)
    print("done, %d SpellSuccess lines now carry the riders" % total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
