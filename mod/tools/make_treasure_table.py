# -*- coding: utf-8 -*-
"""Put the three knuckles into Dammon's (戴摩) stock.

How BG3 vendor stock works here (verified against vanilla):

  * Vendor inventories live in `Stats/Generated/TreasureTable.txt` as
    `new treasuretable "<name>"` + `new subtable` + `object category "I_<template>",...`
  * Vanilla has exactly ONE weaponsmith table: `DEN_Weaponsmith_Trade`
    (Public/Gustav/Stats/Generated/TreasureTable.txt) -- that is Dammon's stock in the
    Emerald Grove. There is no separate Act 2 / Act 3 smith table in vanilla, so his
    later stock either reuses this table or the generic EquipmentTrader_* tables.
  * `CanMerge` does not exist in this game's TreasureTable format (0 occurrences in
    957 vanilla tables), so a mod cannot "append" to a vanilla table. The supported way
    is a SAME-NAME override: the mod's `new treasuretable "DEN_Weaponsmith_Trade"`
    replaces the vanilla one, so it must reproduce every vanilla row verbatim and then
    add ours.

The vanilla rows are read straight out of the extracted Gustav pak, so nothing is
hand-typed and nothing of the original stock can be lost.

Run: python make_treasure_table.py
"""
import io
import os
import re

VANILLA = r"D:\DSH\knuckle_tools\vgust\Public\Gustav\Stats\Generated\TreasureTable.txt"
OUT_DIR = r"D:\DSH\knuckle_mod\Public\KnuckleDusters\Stats\Generated"
OUT = os.path.join(OUT_DIR, "TreasureTable.txt")

TABLE = "DEN_Weaponsmith_Trade"

# object category strings are "I_" + the RootTemplate name
OUR_ITEMS = [
    "I_KD_SteelSpikeFist",
    "I_KD_BoneChill",
    "I_KD_Unsharpened",
]

HEADER = """// ============================================================================
// 戴摩（武器商 Dammon）的商品表：把三件指虎加进库存
//
// 做法说明（重要）：本作的 TreasureTable 没有 CanMerge 之类"追加"语法（957 张原版表
// 里 0 次出现），所以 mod 只能**同名覆盖**。下面这张 DEN_Weaponsmith_Trade 是原版
// Public/Gustav/Stats/Generated/TreasureTable.txt 里的内容**逐行复制**，只是在末尾
// 追加了我们的三件；没有删改任何原版行，Dammon 原有库存不会丢。
//
// 章节说明：原版只有这一张武器商表，没有第二章（终焉之光）、第三章（下城区）的独立
// 武器商表，因此戴摩在后两章要么沿用这张表、要么走通用的 EquipmentTrader_*。
// 若进游戏发现二三章没有上架，下一步就把三件也加进 EquipmentTrader_Melee_Magic。
// ============================================================================

"""


def main():
    t = io.open(VANILLA, encoding="utf-8-sig", errors="replace").read()
    m = re.search(r'(?m)^new treasuretable "%s"\r?\n' % re.escape(TABLE), t)
    if not m:
        raise SystemExit("vanilla table not found: %s" % TABLE)
    rest = t[m.end():]
    nxt = re.search(r'(?m)^new treasuretable "', rest)
    body = rest[:nxt.start()] if nxt else rest
    body = body.rstrip() + "\n"

    add = ["\n// ---- 指虎三件（本 mod 追加） ----\n"]
    for it in OUR_ITEMS:
        add.append('new subtable "-1"\n')
        add.append('object category "%s",1,0,0,0,0,0,0,0\n' % it)

    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        HEADER + 'new treasuretable "%s"\n' % TABLE + body + "".join(add))
    print("wrote %s (%d B)" % (os.path.basename(OUT), os.path.getsize(OUT)))
    print("  vanilla rows kept: %d" % len(re.findall(r'(?m)^new subtable', body)))
    print("  ours appended   : %d" % len(OUR_ITEMS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
