# -*- coding: utf-8 -*-
"""Put the weapon-rider bridge into the equip statuses' Boosts.

Three channels have now been measured in game:

  1. PassiveData.Boosts + IF(HasStatus(...))  -> the damage was applied even with the
     buff off, i.e. the condition does not gate a character damage modifier there;
  2. SpellSuccess + IF(HasStatus(...))        -> never applied (bare form resolves
     against the target), and with context.Source still never applied;
  3. StatusData.Boosts + IF(HasStatus(...))   -> this is the shape 5eSpells uses for
     exactly this job (e.g. SPIRIT_SHROUD), so it is the one worth copying.

We already have statuses that are proven to be applied on equip -- KD_OVERRIDE_*:
the main-hand attack visibly becomes "指虎攻击" because of their
AttackSpellOverride. So instead of inventing a new status (and betting that
StatusOnEquip accepts a two-value list), the rider conditionals are appended to the
Boosts of those three statuses.

Idempotent: regenerates from KD_3_Statuses.txt.base every run.

Run: python gen_status_riders.py
"""
import io
import os
import re
import shutil

LIVE = r"D:\DSH\knuckle_mod\Public\KnuckleDusters\Stats\Generated\Data\KD_3_Statuses.txt"

RIDERS = [
    ("HOLY_WEAPON", "2d8", "Radiant"),
]

OVERRIDES = ("KD_OVERRIDE_RARE", "KD_OVERRIDE_VERY", "KD_OVERRIDE_LEG")


def chain():
    # context must be explicit. Precedent: our own KD_Rider_Chill works with
    # IF(IsMeleeUnarmedAttack() and HasStatus('WET', context.Target))..., i.e. the
    # conditional form is honoured when a context is named. Every bare-HasStatus
    # variant we tried (passive and status) applied unconditionally, which matches
    # 'the condition is dropped when there is no entity to resolve it against'.
    return ";".join("IF(HasStatus('%s', context.Source)):CharacterUnarmedDamage(%s, %s)" % (s, d, t)
                    for s, d, t in RIDERS)


def main():
    base = LIVE + ".base"
    if not os.path.isfile(base):
        shutil.copyfile(LIVE, base)
        print("  created base copy")
    src = io.open(base, encoding="utf-8").read()
    riders = chain()

    blocks = re.split(r'(?m)^new entry "', src)
    out = [blocks[0]]
    patched = 0
    for b in blocks[1:]:
        name = b.split('"', 1)[0]
        if name in OVERRIDES:
            b2, n = re.subn(r'(?m)^(data "Boosts" "[^"]*)"$',
                            lambda m: '%s;%s"' % (m.group(1), riders), b)
            if n:
                patched += 1
            b = b2
        out.append(b)
    text = 'new entry "'.join(out)
    io.open(LIVE, "w", encoding="utf-8", newline="\n").write(text)
    print("  patched %d override statuses with %d rider clauses" % (patched, len(RIDERS)))

    for name in OVERRIDES:
        m = re.search(r'(?ms)new entry "%s".*?data "Boosts" "([^"]*)"' % name, text)
        if m:
            print("  %-20s Boosts length=%d  riders=%d"
                  % (name, len(m.group(1)), m.group(1).count("HasStatus")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
