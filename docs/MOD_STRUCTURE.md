# BG3 Mod Structure — Monk Weapon: Knuckle Dusters

> Read this first. It explains what every file in this repository does, why it is written
> that way, and how to change it without breaking the game.
> Agent-oriented quick reference: [`AGENT_GUIDE.md`](AGENT_GUIDE.md).

---

## 1. What the mod is

Three craft-free knuckle dusters for Baldur's Gate 3 that behave like **monk unarmed
strikes** while still being **real weapon attacks**. That combination is the whole point:

* because it is a weapon attack, weapon-side riders (`Holy Weapon`, `Elemental Weapon`,
  any future mod's `StatsFunctorContext` boost) apply to it;
* because the damage chain still resolves `UnarmedDamage`, `Tavern Brawler`, monk
  manifestations and the Martial Arts die keep working;
* because it is flagged `IsAttack`, Extra Attack and Flurry of Blows chain correctly.

| Weapon | Rarity | Act | Rider |
|---|---|---|---|
| Steel Spike Fist | Rare | 1 | Steel Claw: +1d4 piercing, 20% bleed |
| Bone Chill | Very Rare | 2 | Piercing Cold: +1d6 cold, +1d6 vs Wet |
| Unsharpened | Legendary | 3 | Armour Break: applies Shatter (bludgeoning vulnerable) |

All three are sold by **Dammon** (`DEN_Weaponsmith_Trade`, `HAV_Weaponsmith_Trade`,
`LOW_Weaponsmith_Trade`) and unlock by act in rarity order.

---

## 2. Repository layout

```
mod/
  stats/                 # all .txt stat files + a merged .lsx for inspection
  meta/                  # meta.lsx (mod identity) + Mods folder metadata
  scriptextender/        # optional Lua (manual `!kd` grant command only)
  tools/                 # every script used to build the mod
  assets/                # models (OBJ), textures (PNG + DDS), AO, icons
  docs/                  # the three research notes written during development
docs/
  MOD_STRUCTURE.md       # this file
  AGENT_GUIDE.md         # machine-facing invariants and verification
  banner.png             # Nexus banner
```

---

## 3. Stat file map

BG3 loads stat files from a pak by scanning `Public/<Module>/Stats/Generated/Data`. The
naming below is convention only — the engine reads every `.txt` there.

| File | Contains | Why it is separate |
|---|---|---|
| `KD_1_Weapons.txt` | 3 weapon entries | one place to tune damage/properties |
| `KD_2_Attacks.txt` | the 3 weapon attack spells | each spell is the *only* place `UseCosts` / animation live |
| `KD_3_Statuses.txt` | `KD_ARMORBREAK_1/2` | status data is hot-reload sensitive, keep isolated |
| `KD_4_Passives.txt` | 7 passives (riders + traits) | passives referenced by `PassivesOnEquip` |
| `KD_5_VanillaOverrides.txt` | Flurry / UnarmedStrike overrides | names collide with vanilla, easy to review |
| `KD_6_MonkWeapon.txt` | `KD_MonkWeapon` passive | the Monk Weapon dice override |
| `KD_7_FlurryVariants.txt` | 3 Open Hand variants | these override the base spell *again* |
| `KD_8_BreakOnHit.txt` | `KD_BreakOnHit` (OnDamage functor) | status application on hit |
| `KD_9_UnarmedCoverage.txt` | 4 more unarmed attack spells | widens rider coverage |

### Key fields, and why

```txt
new entry "KD_WPN_SteelSpike"
type "Weapon"
data "RootTemplate" "8f1e…"
data "Damage Type" "Bludgeoning"
data "Damage" "1d6"
data "Properties" "Melee;Dippable;Magical;Finesse;Light;NoDualWield"
data "ValueUUID" "9b6a4ab2-323b-4030-89ab-030252bb6214"   // vanilla Rare value table
data "StatusOnEquip" "KD_OVERRIDE_STEELSPIKE"
data "PassivesOnEquip" "KD_SteelFist;KD_Trait_SteelSpike;KD_Rider_SteelSpike;KD_MonkWeapon"
```

* **`ValueUUID` must be a real vanilla value table UUID.** Inventing one yields a 15 gp
  weapon. Use the vanilla Rare / VeryRare / Legendary tables.
* **`NoDualWield` instead of `Twohanded`.** `Twohanded` would change the *grip pose*;
  `NoDualWield` blocks the off-hand slot without changing how it is held.
* **`Finesse`** is deliberate: it lets the knuckles ride Dex builds.

### The attack spell — the important part

```txt
new entry "KD_Attack_SteelSpike"
type "SpellData"
data "SpellType" "Target"
data "SpellRoll" "Attack(AttackType.MeleeWeaponAttack)"
data "SpellSuccess" "DealDamage(max(1,UnarmedDamage));DealDamage(max(1,MainMeleeWeapon),MainMeleeWeaponDamageType);ExecuteWeaponFunctors(MainHand)"
data "UseCosts" "ActionPoint:1"
data "DualWieldingUseCosts" "BonusActionPoint:1"
data "SpellFlags" "IsAttack;IsMelee;HasHighGroundRangeEvaluation;RangeIgnoreVerticalThreshold"
```

Three details that took the longest to get right:

1. **`UseCosts "ActionPoint:1"`** — without it the attack costs a Bonus Action and never
   benefits from Extra Attack.
2. **No `CastOffhand` / `DualWieldingSpellAnimation`** — the vanilla dual-wield animation
   set is for light weapons; using it made the knuckles play the wrong pose.
3. **`ExecuteWeaponFunctors(MainHand)`** — this is what lets *any* weapon-attached rider
   fire, including riders added by other mods later.

---

## 4. Why Flurry needed its own overrides

This is the single biggest gotcha in the mod.

Open Hand monks do not cast `Target_FlurryOfBlows` directly. They cast one of:

```
Target_OpenHandTechnique_Push
Target_OpenHandTechnique_Knock
Target_OpenHandTechnique_NoReactions
```

Those three **override `SpellSuccess` and `SpellFlags` again**, so editing the base
Flurry spell has no effect on them. The fix in `KD_7_FlurryVariants.txt` is to override
each variant and add the weapon damage line **per strike**, while keeping the original
effects:

```txt
data "SpellSuccess" "DealDamage(max(1,UnarmedDamage));DealDamage(max(1,MainMeleeWeapon),MainMeleeWeaponDamageType);ExecuteWeaponFunctors(MainHand);…original effect lines…"
data "SpellFlags" "IsAttack;IsMelee;…"
```

Same class of problem for `Target_UnarmedStrike_Monk`, `Target_StunningStrike_Unarmed`,
`Target_ShadowStrike_Instant_Unarmed`, `Target_KiResonation_Punch` — see `KD_9`.

---

## 5. Vendor integration (and the pollution trap)

`TreasureTable.txt` appends the items to Dammon's three per-act tables.

```txt
new TreasureTable "DEN_Weaponsmith_Trade"
CanMerge 1
new subtable "-1"
object category "I_KD_WPN_SteelSpike",1,0,0,0,0,0,0,0
```

Rules learned the hard way:

* **`CanMerge 1` is the documented append syntax.** Writing a same-name table *without*
  it silently replaces the whole vanilla table — that is data pollution (it would strip
  Dammon's entire stock).
* `"-1"` as the first subtable field means "guaranteed, exactly one".
* The item template name (`I_KD_WPN_…`) is the **root template name**, not the stat name.
* Merchant stock re-rolls on **long rest or level-up**, and is scaled to the *first party
  member's* level — so "not in stock" usually means "rest once".

---

## 6. Models, materials and the GR2 pipeline

The weapon is a **rigid** rig (no skin weights):

```
Dummy_<stem>          # root
  Dummy_Sheath        # sheathed socket
  Dummy_Attachment    # hand socket
  <stem>_Mesh         # the visual
```

* Template DAE long axis is **Z**; the in-game placement is produced by
  `tools/pack_gr2.py` with `_rot_mode "E"` → `collada = (-z, y, x)`, tilt **−42°**,
  drop **12 mm**, shift **30 % of the part width** along the knuckle→strike axis.
* Materials use the `CHAR_BASE_GM` template plus `Glowmap` / `GlowMultiplier 2.0` /
  `GlowColor` so the rune engraving is emissive.
* Textures are BC7 DX10 DDS: `_BM`, `_NM`, `_PM`, `_GLOW` per weapon.
* `tools/polish_textures.py` flattens baked icon lighting out of the maps; run it before
  packing if you regenerate textures from a render.

Rebuild order:

```powershell
python mod/tools/gen_knuckles.py         # only if you want to regenerate stats
python mod/tools/polish_textures.py      # optional, texture cleanup
powershell mod/tools/integrate_models_tex.ps1   # texconv + pack_all
```

> `wire_visuals.py` used to call `gen_knuckles.py` implicitly and silently reverted
> hand-edited stat files. It is now gated behind `KD_REGEN_STATS=1`. Keep it that way.

---

## 7. Localization

Every `DisplayName` / `Description` is a **handle** (`h…;version`), never a literal string.
The handle must exist in a loca file for the language the player runs — a missing
handle renders as `Not Found: Not Found` in the tooltip.

The mod ships **all 13 languages BG3 supports**:

```
English  French  German  Spanish  Italian  Polish  Russian  Turkish  Ukrainian
BrazilianPortuguese  Japanese  Korean  Chinese
```

Folder layout (both roots are populated on purpose — some loaders only look at one):

```
Localization/<Language>/KnuckleDusters.loca
Public/KnuckleDusters/Localization/<Language>/KnuckleDusters.loca
```

Source of truth is the XML, one file per language:

```
mod/meta/Localization/<Language>/KnuckleDusters.xml
```

### Updating translations

`mod/tools/gen_localization.py` holds the whole translation table (`T[<Language>][<key>]`)
and regenerates every XML, then compiles each one with `loca.py`:

```powershell
python mod/tools/gen_localization.py --write            # XML only
python mod/tools/gen_localization.py --write --compile  # XML + .loca
```

To fix a translation, edit the table (or the XML directly) and re-run with `--compile`,
then repack. Do **not** hand-edit a `.loca` — it is a binary format
(`LOCA` magic, then `key[64] + uint16 length + UTF-16LE value`).

Terminology follows the game's own wording where it exists (`unarmed attack`,
`piercing / cold / bludgeoning damage`, `Bleeding`, `Wet`, `Vulnerable`); `Shellbreaker`
and `Sundered` are names invented for this mod and are translated for tone, not from a
source term. If you play in one of these languages and something reads badly, that is a
one-line fix in the table.

Handles currently used (all verified present):

| Handle | Text |
|---|---|
| `h27456ed8…` | Steel Spike Fist (attack display name) |
| `h548a5901…` | attack description |
| `ha1bb7f91…` | Shatter description |
| `hca0d6f4b…` | Shatter tooltip |
| `h0011a0ab…` | Steel Claw |
| `h26d44774…` | Piercing Cold |
| `hd526e1de…` | Armour Break |
| `h66008c7c…` | bludgeoning vulnerability text |

If you add a new entry, add its handle to the loca XML **in the same commit**, and re-run
the loca build — a stat entry without text still loads, it just reads `Not Found`.

---

## 8. Known limitations (read before "fixing")

* `Target_UnarmedAttack` is a **global** override: a character holding any weapon now adds
  that weapon's damage when punching. Empty hands are unaffected because the term is
  `max(0, MainMeleeWeapon)`.
* Stat effects gated on `IsMeleeUnarmedAttack()` will not fire for these weapons — this is
  the cost of being a weapon attack.
* A single item cannot be held in both hands. `Twohanded` gives one visual with both hands
  but forces the two-handed grip pose; a second `_Off` item is rejected by the engine when
  the main hand is empty. Both approaches were tried and reverted (see `docs/` research
  notes).
* The attack animation is chosen engine-side from a 20-archetype table
  (`WeaponAnimationSetData.lsx`). There is **no hold-pose field**; the archetype names do
  not appear in any other data file.

---

## 9. How to extend

| Goal | Touch this |
|---|---|
| Retune damage / add a 4th weapon | `KD_1_Weapons.txt` + root template + `TreasureTable.txt` + loca handles |
| Change what a hit applies | `KD_8_BreakOnHit.txt` (stats functor, `StatsFunctorContext "OnDamage"`) |
| Make riders fire on more spells | `KD_9_UnarmedCoverage.txt` (idempotent injector — it only adds missing pieces) |
| Change the pose / scale | `tools/pack_gr2.py` (`_rot_mode`, `_tilt`, `_drop`, `_shift`) |
| Change the glow colour | `tools/wire_visuals.py` (`GLOW_RGB`) then repack |

After any change, run the checks in `AGENT_GUIDE.md §4` before packing.
