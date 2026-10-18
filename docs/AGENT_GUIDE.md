# AGENT_GUIDE — Machine-facing brief for automated contributors

Audience: an LLM/agent asked to modify, fix or extend this mod.
Read [`MOD_STRUCTURE.md`](MOD_STRUCTURE.md) for the *why*; this file is the *how, and what
will bite you*.

---

## 0. Ground truth

| Item | Value |
|---|---|
| Game | Baldur's Gate 3, Patch 8, build `4.1.1.7209685` |
| Mod UUID | `b0b86379-2d63-4fb9-8ef8-665c09281874` |
| Module folder | `Public/KnuckleDusters/` |
| Stats root | `Public/KnuckleDusters/Stats/Generated/Data/*.txt` |
| Stat layer rule | grep **Shared / SharedDev / Gustav / GustavDev / Honour** before concluding a vanilla value |
| Locale of record | Chinese (player's game language) — handles must exist there |

---

## 1. Hard invariants (violating these breaks the mod silently)

1. **Never write a same-name `TreasureTable` without `CanMerge 1`.** It replaces the
   vanilla table instead of appending (pollution).
2. **Never invent a `ValueUUID`.** Use the vanilla rarity tables:
   Rare `9b6a4ab2-323b-4030-89ab-030252bb6214`,
   VeryRare `81764c3c-c7a9-49a7-b145-d31ffd5aebe1`,
   Legendary `d24c441f-7ebe-4229-8522-cf34c257ff20`.
3. **Never add a `DisplayName`/`Description` handle without the loca entry** in the same
   commit. A missing handle is not an error — it renders `Not Found: Not Found`.
4. **Keep `UseCosts "ActionPoint:1"`** on every attack spell. Removing it silently
   demotes the weapon to a Bonus-Action attack with no Extra Attack.
5. **Keep `ExecuteWeaponFunctors(MainHand)`** in `SpellSuccess`, otherwise no weapon rider
   (vanilla or third-party) will fire.
6. **Open Hand variants must be overridden separately.** `Target_OpenHandTechnique_Push /
   _Knock / _NoReactions` re-override `SpellSuccess` and `SpellFlags`; editing
   `Target_FlurryOfBlows` alone does nothing for Open Hand monks.
7. **`wire_visuals.py` must stay gated** behind `KD_REGEN_STATS=1`; otherwise it
   regenerates and reverts hand-edited stat files.
8. **`ast.parse()` every Python file after patching it.** Several past incidents were
   self-inflicted regex edits that produced file corruption (stripped quotes, deleted
   config dicts) that only surfaced at the next build.

---

## 2. Change recipes

### A. Retune a weapon

```
mod/stats/KD_1_Weapons.txt      # data "Damage", "Properties", "PassivesOnEquip"
mod/stats/KD_2_Attacks.txt      # only if the damage chain changes
```

### B. Add a new on-hit effect

1. Add the status to `KD_3_Statuses.txt`.
2. Add or extend the functor in `KD_8_BreakOnHit.txt`:

```txt
new entry "KD_BreakOnHit"
type "PassiveData"
data "StatsFunctorContext" "OnDamage"
data "StatsFunctors" "ApplyStatus(KD_ARMORBREAK_1,100,3)"
```

3. Ensure the passive is listed in `PassivesOnEquip` of the weapon(s).
4. Reference the working vanilla pattern (`ALCH_Oil_Frost_Passive`) whenever unsure.

### C. Widen rider coverage to another unarmed spell

Use `KD_9_UnarmedCoverage.txt` as the pattern: it is **idempotent** — it inspects the
existing `SpellSuccess` and only appends the weapon channel and `IsAttack` when missing.
Do not hand-edit the same spell in two files.

### D. Change the model placement

`mod/tools/pack_gr2.py`:

```python
_rot_mode = "E"      # collada = (-z, y, x)
tilt  = -42.0        # degrees
drop  = 0.012        # metres
shift = 0.30         # fraction of the part's width, knuckle -> strike direction
```

The transform is applied in model space **before** the axis roll. Changing `_rot_mode`
without re-checking the result in-game will mirror the weapon.

---


### E. Add or fix a translation

1. Edit the table in `mod/tools/gen_localization.py` (`T[<Language>][<key>]`), or the
   XML in `mod/meta/Localization/<Language>/KnuckleDusters.xml` directly.
2. Regenerate and compile:
   `python mod/tools/gen_localization.py --write --compile`
3. Repack. **Never hand-edit a `.loca`** - it is binary
   (`LOCA` magic, then `key[64] + uint16 + UTF-16LE`) and the offsets will drift.
4. Verify no replacement characters leaked: `python loca.py verify <file>.loca` should
   report `0 of N entries contain U+FFFD`.

Language folder names are fixed by the game and must match exactly:
`English French German Spanish Italian Polish Russian Turkish Ukrainian
BrazilianPortuguese Japanese Korean Chinese`. A misspelled folder is silently ignored and
the player sees `Not Found`.

### F. Localization silently loading nothing

If every self-defined handle renders `Not Found` while stats/items work, suspect the
`.loca` binary layout, not the file name or path:

1. ``python mod/tools/loca_bg3.py --verify <file>.loca`` — must report the entry count and
   readable text.
2. Compare against a known-good mod: ``5eSpellsCHS/Localization/Chinese/5eSpells.loca``.
3. Regenerate with ``loca_bg3.py``; the old ``loca.py`` (DOS2 inline UTF-16) is wrong for
   BG3 and produces a file the engine reads as empty without any error.

---
## 3. Build & deploy

```powershell
# 1. stats only (no model work)
python mod/tools/gen_knuckles.py            # regenerate stat txt files

# 2. textures
python mod/tools/polish_textures.py         # optional cleanup of baked lighting
# texconv BC7 DX10 for _BM/_NM/_PM/_GLOW, then pack:
powershell mod/tools/integrate_models_tex.ps1

# 3. pack + install
#    LSLib: D:\Tools\LSLib\Divine.exe
#    preprocessor: <BG3 Toolkit>\preprocessor.exe
```

Deploy target: `%LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\Mods\KnuckleDusters.pak`
plus an entry in `modsettings.lsx`.

**The game must be closed while copying the pak**, otherwise Windows reports
`IOException … being used by another process`.

---

## 4. Pre-pack verification checklist

Run these before every release; all must pass.

```
1. Every `DisplayName`/`Description` handle in mod/stats exists in the loca XML.
2. `grep -c "CanMerge 1" TreasureTable.txt` equals the number of tables appended.
3. No `new TreasureTable "<vanilla name>"` appears without `CanMerge 1`.
4. `grep "ActionPoint:1"` matches every KD attack spell.
5. `grep -c "ExecuteWeaponFunctors(MainHand)"` equals the number of attack spells.
6. Each Open Hand variant file contains all three of Push / Knock / NoReactions.
7. Python tools still parse: `python -c "import ast,glob;[ast.parse(open(f).read()) for f in glob.glob('mod/tools/*.py')]"`
8. Pak opens and contains: stats, meta.lsx, root templates, textures, models.
9. In-game smoke test: equip -> attack costs an Action -> Extra Attack fires ->
   Flurry (all three Open Hand variants) shows the extra weapon damage line.
```

---

## 5. Failure signatures

| Symptom | Cause | Fix |
|---|---|---|
| Tooltip shows `Not Found: Not Found` | handle has no loca entry for the active language | add the handle, rebuild loca |
| Attack costs a Bonus Action | `UseCosts` missing or overridden upstream | restore `ActionPoint:1` |
| No Extra Attack | same as above | same |
| Riders never fire | `ExecuteWeaponFunctors` missing, or the spell is not flagged `IsAttack` | add both |
| Flurry does not add weapon damage (Open Hand only) | base-spell edit, variants not overridden | override `Target_OpenHandTechnique_*` |
| Dammon's whole stock vanishes | TreasureTable written without `CanMerge 1` | rewrite with `CanMerge 1` + `new subtable "-1"` |
| Weapon priced at 15 gp | invented `ValueUUID` | use a vanilla value table UUID |
| Model mirrored / wrong axis | changed `_rot_mode` | revert to `"E"` and retune `tilt` |
| Stats reverted after a build | `wire_visuals.py` regenerated them | run with `KD_REGEN_STATS=0` (default) |

---

## 6. What is deliberately *not* done

* No auto-grant of the items on load — the Lua file only exposes a manual `!kd` console
  command, because auto-grant polluted saves during testing.
* No `Twohanded` property and no off-hand twin item — both were built, tested and
  reverted; see `mod/docs/` research notes for the evidence.
* Spiritual Weapon and projectile spells are intentionally untouched.

---

## 7. Contribution contract

Anything in this repository may be modified and redistributed (see `LICENSE`).
If you change behaviour, update **both** docs and bump `Mods/KnuckleDusters/meta.lsx`
`Version64`. If you change a stat entry's meaning, note it in `CHANGELOG.md`.
