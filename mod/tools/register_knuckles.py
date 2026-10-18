# -*- coding: utf-8 -*-
"""把 KnuckleDusters 注册进 modsettings.lsx 的最后一位（加载顺序最后 = 压过其它模组）。"""
import datetime
import hashlib
import io
import os
import re
import shutil
import sys

LOCAL = os.path.join(os.environ["LOCALAPPDATA"], "Larian Studios", "Baldur's Gate 3")
MODS = os.path.join(LOCAL, "Mods")
PAK = os.path.join(MODS, "KnuckleDusters.pak")
MS = os.path.join(LOCAL, "PlayerProfiles", "Public", "modsettings.lsx")
LIB = r"D:\Tools\BG3Mods"
BACKUP = r"D:\DSH\knuckle_backup"

FOLDER = "KnuckleDusters"
NAME = "Knuckle Dusters (Probe)"
UUID = "b0b86379-2d63-4fb9-8ef8-665c09281874"
VERSION64 = "72057594037927936"


def read(p):
    return io.open(p, encoding="utf-8", errors="replace").read()


def write(p, t):
    io.open(p, "w", encoding="utf-8", newline="\n").write(t)


def main():
    if not os.path.isfile(PAK):
        raise SystemExit("找不到 pak：%s" % PAK)
    md5 = hashlib.md5(open(PAK, "rb").read()).hexdigest()
    print("pak : %s" % PAK)
    print("md5 : %s" % md5)

    t = read(MS)
    if ('value="%s" />' % FOLDER) in t:
        print("已注册：更新 MD5")
        t = re.sub(
            r'(<attribute id="Folder" type="LSString" value="%s" />\s*\n\s*<attribute id="MD5" type="LSString" value=")[^"]*(")'
            % re.escape(FOLDER), lambda m: m.group(1) + md5 + m.group(2), t)
        write(MS, t)
        report(t)
        sync_lib()
        return 0

    os.makedirs(BACKUP, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = os.path.join(BACKUP, "modsettings-before-knuckles-%s.lsx" % stamp)
    shutil.copy2(MS, dst)
    print("备份 : %s" % dst)

    m = re.search(r'\n(\s*)<node id="ModuleShortDesc">', t)
    if not m:
        raise SystemExit("modsettings.lsx 里找不到 ModuleShortDesc")
    ind = m.group(1)
    entry = "\n".join([
        '%s<node id="ModuleShortDesc">' % ind,
        '%s  <attribute id="Folder" type="LSString" value="%s" />' % (ind, FOLDER),
        '%s  <attribute id="MD5" type="LSString" value="%s" />' % (ind, md5),
        '%s  <attribute id="Name" type="LSString" value="%s" />' % (ind, NAME),
        '%s  <attribute id="PublishHandle" type="uint64" value="0" />' % ind,
        '%s  <attribute id="UUID" type="guid" value="%s" />' % (ind, UUID),
        '%s  <attribute id="Version64" type="int64" value="%s" />' % (ind, VERSION64),
        '%s</node>' % ind,
    ])
    i = t.index('<node id="Mods">')
    j = t.index("</children>", i)
    k = t.rfind("\n", 0, j)
    t = t[:k] + "\n" + entry + t[k:]
    write(MS, t)

    report(t)
    sync_lib()
    return 0


def sync_lib():
    if not os.path.isdir(LIB):
        print("BG3MM 库不存在，跳过：%s" % LIB)
        return
    dst = os.path.join(LIB, os.path.basename(PAK))
    shutil.copy2(PAK, dst)
    print("已同步到 BG3MM 库：%s (%d B)" % (dst, os.path.getsize(dst)))


def report(t):
    order = re.findall(r'id="Folder" type="LSString" value="([^"]*)"', t)
    n = len(re.findall(r'<node id="ModuleShortDesc">', t))
    ok = (FOLDER in t) and (UUID in t)
    print("注册 : %s   模块总数 %d" % ("成功" if ok else "失败", n))
    for i, f in enumerate(order):
        mark = "   <== 本模组（最后加载）" if f == FOLDER else ""
        print("   %2d. %s%s" % (i + 1, f, mark))


if __name__ == "__main__":
    sys.exit(main())
