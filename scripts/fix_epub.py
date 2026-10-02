#!/usr/bin/env python3
"""Make an EPUB openable on strict e-readers that reject anything with a
META-INF/encryption.xml — without touching any real DRM.

Two things get fixed, both of which are container-level, not content protection:

1. **IDPF font obfuscation** (`Algorithm="http://www.idpf.org/2008/embedding"`,
   the only entry type a normal publisher EPUB has) — reversible by spec: XOR the
   first 1040 bytes of each font with `SHA1(unique-identifier)` (urn:uuid: prefix
   and whitespace stripped). The fonts are restored and the encryption.xml entry
   is dropped, so no e-reader mistakes it for DRM. Text was never encrypted.

2. **Container defects**: a UTF-8 BOM before `<?xml` (invalid XML, strict parsers
   reject the package) and `mimetype` not being the first, stored, extension-less
   ZIP entry.

Refuses to touch anything that looks like real content protection (an encrypted
entry other than the IDPF embedding algorithm).

Usage: python3 fix_epub.py <input.epub> [output.epub]
"""
from __future__ import annotations

import hashlib
import re
import sys
import zipfile
from pathlib import Path

TEXT_EXT = (".opf", ".xhtml", ".html", ".ncx", ".xml", ".css", ".txt")
OBFUSCATION_NS = "http://www.idpf.org/2008/embedding"
FONT_EXT = (".ttf", ".otf", ".ttc", ".woff", ".woff2")
ENCRYPTION_ENTRY = "META-INF/encryption.xml"


def _unique_identifier(zin: zipfile.ZipFile, opf_path: str) -> str | None:
    opf = zin.read(opf_path).decode("utf-8-sig", "replace")
    m = re.search(r'unique-identifier="([^"]+)"', opf)
    if not m:
        return None
    ident_id = m.group(1)
    m2 = re.search(
        r"<dc:identifier[^>]*id=\"%s\"[^>]*>([^<]+)</dc:identifier>" % re.escape(ident_id),
        opf,
    )
    if not m2:
        m2 = re.search(r"<dc:identifier[^>]*>([^<]+)</dc:identifier>", opf)
    if not m2:
        return None
    value = re.sub(r"\s+", "", m2.group(1))
    return value[len("urn:uuid:"):] if value.lower().startswith("urn:uuid:") else value


def _deobfuscate(font_bytes: bytes, key: bytes) -> bytes:
    head = bytes(b ^ key[i % len(key)] for i, b in enumerate(font_bytes[:1040]))
    return head + font_bytes[1040:]


# A font that already carries one of these magics is NOT obfuscated, whatever
# encryption.xml claims — a repackaging tool stripped it and left the manifest
# entry behind, and XORing it would corrupt a perfectly good font.
FONT_MAGICS = (b"\x00\x01\x00\x00", b"OTTO", b"true", b"ttcf", b"wOFF", b"wOF2")


def _looks_plain(data: bytes) -> bool:
    return data[:4] in FONT_MAGICS


def fix(src: Path, dst: Path) -> dict:
    zin = zipfile.ZipFile(src)
    names = zin.namelist()
    report: dict = {"src": str(src), "drm_refused": False}

    # ---- inspect encryption.xml -------------------------------------------------
    obfuscated_fonts: list[str] = []
    if ENCRYPTION_ENTRY in names:
        enc = zin.read(ENCRYPTION_ENTRY).decode("utf-8", "replace")
        algs = set(re.findall(r'Algorithm="([^"]+)"', enc))
        uris = re.findall(r'CipherReference URI="([^"]+)"', enc)
        if algs - {OBFUSCATION_NS}:
            report["drm_refused"] = True
            report["algorithms"] = sorted(algs)
            return report
        obfuscated_fonts = uris
        report["obfuscated_fonts"] = len(uris)

    opf_path = next((n for n in names if n.endswith(".opf")), None)
    key = None
    if obfuscated_fonts:
        if not opf_path:
            report["drm_refused"] = True
            report["reason"] = "no OPF to source the identifier from"
            return report
        ident = _unique_identifier(zin, opf_path)
        if not ident:
            report["drm_refused"] = True
            report["reason"] = "no unique identifier in OPF"
            return report
        key = hashlib.sha1(ident.encode("utf-8")).digest()

    # ---- rebuild ----------------------------------------------------------------
    fixed_boms = 0
    deobfuscated = 0
    already_plain = 0
    items: list[tuple[str, bytes, int]] = []
    for n in names:
        if n == ENCRYPTION_ENTRY:
            continue  # dropped once its fonts are restored
        data = zin.read(n)
        is_dir = n.endswith("/")
        comp = zipfile.ZIP_STORED if is_dir else zipfile.ZIP_DEFLATED
        if key and n in obfuscated_fonts:
            if _looks_plain(data):
                already_plain += 1
            else:
                data = _deobfuscate(data, key)
                deobfuscated += 1
        if n.lower().endswith(TEXT_EXT) and data.startswith(b"\xef\xbb\xbf"):
            data = data[3:]
            fixed_boms += 1
        items.append((n, data, comp))

    ordered = [("mimetype", b"application/epub+zip", zipfile.ZIP_STORED)]
    ordered += [(n, d, c) for (n, d, c) in items if n != "mimetype"]

    with zipfile.ZipFile(dst, "w") as zout:
        for n, d, c in ordered:
            info = zipfile.ZipInfo(n)
            info.compress_type = c
            info.date_time = (1980, 1, 1, 0, 0, 0)
            if n == "mimetype":
                info.create_system = 0
                info.external_attr = 0
            zout.writestr(info, d)

    report.update(
        {
            "entries": len(ordered),
            "deobfuscated_fonts": deobfuscated,
            "fonts_already_plain": already_plain,
            "boms_stripped": fixed_boms,
            "encryption_xml_removed": ENCRYPTION_ENTRY in names,
        }
    )
    return report


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    src = Path(sys.argv[1]).expanduser()
    dst = (
        Path(sys.argv[2]).expanduser()
        if len(sys.argv) > 2
        else src.with_name(src.stem + "-fixed.epub")
    )
    if not src.exists():
        raise SystemExit(f"not found: {src}")
    out = fix(src, dst)
    print(out)
    if out.get("drm_refused"):
        raise SystemExit("REFUSED: real content protection found — not modifying.")
    print("wrote:", dst)
