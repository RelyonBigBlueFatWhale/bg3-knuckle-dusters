# Changelog

## 1.0.0 - 2026-10-18

First public release.

**Weapons**
- Steel Spike Fist (Rare, Act 1), Bone Chill (Very Rare, Act 2),
  Unsharpened (Legendary, Act 3), sold by Dammon, one per act by rarity.
- Attack costs an Action and supports Extra Attack.
- Weapon-attached riders apply to the knuckles, Flurry of Blows, Martial Arts bonus
  strike and the other unarmed strikes.
- Unsharpened applies Shatter (bludgeoning vulnerability) from every hit path.

**Fixes made during development (all reflected in the code)**
- Bonus Action cost removed; Extra Attack restored via explicit `UseCosts`.
- Open Hand Flurry variants overridden separately (base-spell edits were ignored).
- Treasure tables append with `CanMerge 1` instead of replacing Dammon's stock.
- `ValueUUID` set to the vanilla rarity tables (self-made UUIDs priced at 15 gp).
- All DisplayName/Description handles resolved against the real loca entries.
- `wire_visuals.py` gated behind `KD_REGEN_STATS=1` (it used to revert stat edits).
- Off-hand twin-item and `Twohanded` experiments reverted: the engine refuses an
  off-hand weapon while the main hand is empty, and `Twohanded` forces the wrong pose.

**Art**
- Three knuckle duster meshes rebuilt from multi-view references; rigid 7-joint rig.
- BC7 DX10 texture sets with emissive Glowmap for the rune engraving.

### Added after first packaging
- Full localization: all 13 BG3 languages (English, Chinese, French, German, Spanish,
  Italian, Polish, Russian, Turkish, Ukrainian, Brazilian Portuguese, Japanese, Korean)
  compiled to .loca and shipped in both localization roots.
- mod/tools/gen_localization.py — the translation table plus XML/loca generation, so
  any line can be fixed and rebuilt in one command.