# -*- coding: utf-8 -*-
"""Write BG3-format .loca files (the format the shipped game actually loads).

Layout, verified against a working mod (5eSpellsCHS), OneTouchBuff and the vanilla
chinese.loca:

    "LOCA"                  char[4]
    uint32  entryCount
    uint32  textBlockOffset      (= 12 + entryCount * 70)
    entryCount x 70 bytes:
        char    key[64]          handle, null padded, WITHOUT the ";version" suffix
        uint16  unknown          always 1
        uint32  textLen          length of the UTF-8 text INCLUDING its trailing NUL
    text block: UTF-8 strings, back to back, each NUL terminated

The old `loca.py` in bg3-ascendant writes the DOS2-style inline UTF-16 layout
(key[64] + uint16 len + UTF-16). BG3 parses it as the layout above, finds garbage and
silently loads zero strings - which is exactly the "everything is Not Found" symptom.

Usage:
    python loca_bg3.py <input.xml> <output.loca>
    python loca_bg3.py --verify <file.loca>
    python loca_bg3.py --rebuild-all
"""
import io
import os
import re
import struct
import sys

XML_ROOTS = [
    r"D:\DSH\dist\src\KnuckleDusters\source\meta\Localization",
    r"D:\DSH\github\bg3-knuckle-dusters\mod\meta\Localization",
]
LOCA_ROOT = r"D:\DSH\knuckle_mod\Localization"
LANGS = ["English", "Chinese", "French", "German", "Spanish", "Italian", "Polish",
         "Russian", "Turkish", "Ukrainian", "BrazilianPortuguese", "Japanese", "Korean"]

ENTRY = re.compile(r'<content contentuid="([^"]+)"[^>]*>(.*?)</content>', re.S)


def unescape(s):
    return (s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
             .replace("&apos;", "'").replace("&amp;", "&"))


def read_xml(path):
    txt = io.open(path, encoding="utf-8-sig").read()
    out = []
    for uid, body in ENTRY.findall(txt):
        out.append((uid.strip(), unescape(body)))
    return out


def write_loca(entries, path):
    count = len(entries)
    text_off = 12 + count * 70
    entries_blob = bytearray()
    text_blob = bytearray()
    for key, text in entries:
        raw = text.encode("utf-8") + b"\x00"
        kb = key.encode("ascii")
        if len(kb) > 63:
            raise ValueError("handle too long: %s" % key)
        entries_blob += kb.ljust(64, b"\x00")
        entries_blob += struct.pack("<H", 1)
        entries_blob += struct.pack("<I", len(raw))
        text_blob += raw
    out = bytearray(b"LOCA")
    out += struct.pack("<I", count)
    out += struct.pack("<I", text_off)
    out += entries_blob
    out += text_blob
    assert len(out) == text_off + len(text_blob)
    with open(path, "wb") as f:
        f.write(out)
    return count, len(out)


def parse_loca(path):
    d = open(path, "rb").read()
    if d[:4] != b"LOCA":
        raise ValueError("bad magic")
    count, text_off = struct.unpack_from("<II", d, 4)
    ent = 12
    cur = text_off
    out = []
    for _ in range(count):
        key = d[ent:ent + 64].split(b"\x00")[0].decode("ascii", "ignore")
        u16, ln = struct.unpack_from("<HI", d, ent + 64)
        raw = d[cur:cur + ln]
        out.append((key, u16, raw.decode("utf-8", "replace").rstrip("\x00")))
        ent += 70
        cur += ln
    return count, text_off, out


def verify(path):
    count, text_off, entries = parse_loca(path)
    size = os.path.getsize(path)
    ok = (text_off == 12 + count * 70)
    print("  %-58s %d 条, 文本块@%d, %d B, %s" %
          (os.path.basename(path), count, text_off, size, "结构正确" if ok else "**结构异常**"))
    for key, u16, txt in entries[:2]:
        print("     %s -> %s" % (key[:20] + "…", txt[:36]))
    return ok


def rebuild_all():
    total = 0
    for lang in LANGS:
        xml = os.path.join(XML_ROOTS[0], lang, "KnuckleDusters.xml")
        if not os.path.isfile(xml):
            print("  缺少 XML: %s" % xml)
            continue
        entries = read_xml(xml)
        dst_dir = os.path.join(LOCA_ROOT, lang)
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, "KnuckleDusters.loca")
        n, size = write_loca(entries, dst)
        total += 1
        print("  %-22s %3d 条  %6d B" % (lang, n, size))
    print("  共生成 %d 个 .loca" % total)
    return 0


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    if argv[0] == "--rebuild-all":
        return rebuild_all()
    if argv[0] == "--verify":
        for p in argv[1:]:
            verify(p)
        return 0
    if len(argv) == 2:
        entries = read_xml(argv[0])
        n, size = write_loca(entries, argv[1])
        print("  wrote %d entries, %d B -> %s" % (n, size, argv[1]))
        return verify(argv[1]) and 0 or 1
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
