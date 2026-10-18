# Knuckle Dusters / 指虎

Three gem-inlaid knuckle dusters for Baldur's Gate 3. Their attacks resolve as
**monk-style unarmed strikes** while still carrying the weapon's own damage, on-hit
riders and class features, so they work for a Monk (including Open Hand) and for any
unarmed build.

---

## 三件指虎（Chinese summary）

| 品质 | 名称 | 解锁章节 | 主要特性 |
|---|---|---|---|
| 稀有 | 钢刺之拳 | 第一章（翠绿林地 · 戴摩） | 钢爪：徒手额外 1d4 穿刺，20% 流血 |
| 珍奇 | 彻骨之寒 | 第二章（终焉之光 · 戴摩） | 刺骨：徒手额外 1d6 寒冷；目标濡湿再 +1d6 |
| 传说 | 无锋 | 第三章（下城区 · 戴摩） | 剥壳：命中施加【碎甲】（钝击易伤） |

三件出售位置：**戴摩（Dammon）**，按稀有度分章解锁；第一章的商品在二三章会继续售卖。

---

## Features

- **Unarmed classification, weapon damage.** The attack is a real weapon attack (so
  weapon-side riders such as *Holy Weapon* / *Elemental Weapon* land) while the damage
  chain keeps `UnarmedDamage`, so *Tavern Brawler* and monk manifestations still apply.
- **Monk weapon.** A hidden passive grants `MonkWeaponAttackOverride()` +
  `MonkWeaponDamageDiceOverride(LevelMapValue(MartialArts))`, so Flurry of Blows,
  Martial Arts and the bonus unarmed strike treat the knuckles as a monk weapon.
- **Flurry of Blows variants covered.** All three Open Hand variants
  (`Target_OpenHandTechnique_{Push,Knock,NoReactions}`) are overridden so each of the two
  strikes carries the weapon damage + weapon functors, while the vanilla animations and
  the Open Hand effects (Force / Prone / No Reactions) are kept untouched.
- **Armour break on hit (Legendary).** A weapon passive using
  `StatsFunctorContext "OnDamage"` applies 碎甲 (bludgeoning vulnerability) on any hit
  from that weapon — main-hand, flurry variants, Martial Arts strike, opportunity attacks.
- **Finesse + one-handed, no dual wield.** `Melee;Dippable;Magical;Finesse;Light;NoDualWield`.
- **Emissive runes.** Materials use `CHAR_BASE_GM` with a Glowmap so the rune engraving
  glows (blue for the steel pair, ice blue for the frost pair).

## Install

1. Copy `KnuckleDusters.pak` into
   `%LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\Mods\`
   (or import the archive with BG3 Mod Manager).
2. Enable **Knuckle Dusters** in the mod manager and make sure it loads **after** any
   mod that also edits monk spells (`Target_FlurryOfBlows`, `Target_UnarmedStrike_Monk`)
   or unarmed attacks.
3. Load order matters for overrides: last loaded wins.

## Where to buy

Dammon, by rarity and act:

| Act | Location | Sells |
|---|---|---|
| 1 | Emerald Grove | 钢刺之拳 (Rare) |
| 2 | Last Light Inn | 彻骨之寒 (Very Rare) |
| 3 | Lower City forge | 无锋 (Legendary) |

Merchant stock re-rolls on long rest / level-up. If an item is missing, take a long rest
and check again.

## Console (optional)

`!kd` grants one of each for testing (requires BG3 Script Extender).

## Compatibility notes

- This mod overrides `Target_FlurryOfBlows`, `Target_UnarmedStrike_Monk`,
  the three `Target_OpenHandTechnique_*` variants, `Target_UnarmedAttack`,
  `Target_StunningStrike_Unarmed`, `Target_ShadowStrike_Instant_Unarmed` and
  `Target_KiResonation_Punch`. Other mods touching the same entries must be ordered.
- `Target_UnarmedAttack` is a global override: any character punching while holding a
  weapon will add that weapon's damage. Bare hands are unaffected
  (`max(0, MainMeleeWeapon)`).
- Stat entries that gate on `IsMeleeUnarmedAttack()` will not fire for these weapons,
  because the attack is a weapon attack by design.

## Credits

Author: 16084. Built for BG3 Patch 8 (4.1.1.7209685). Models: multi-view reconstruction
from Qwen-generated orthographic references, retopologised and textured in Blender.
