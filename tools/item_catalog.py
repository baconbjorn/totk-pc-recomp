#!/usr/bin/env python3
"""Build a read-only item/actor name catalog from the user's extracted TotK RomFS.

This tool identifies ActorInfo records and groups likely pickups for UI/search. It does NOT create actors, alter
inventory, or spawn items. Catalog output belongs in the ignored build/ work tree, never in the repository.
"""
import argparse
import json
import struct
import sys
import zlib
from pathlib import Path

TITLE = "0100F2C0115B6000"
MAX_RAW = 512 << 20


def sarc_members(data: bytes) -> dict[str, bytes]:
    """Read named members from a little-endian SARC archive."""
    if len(data) < 0x20 or data[:4] != b"SARC":
        raise ValueError("ZsDic archive is not SARC")
    header_size, bom = struct.unpack_from("<HH", data, 4)
    if bom != 0xFEFF:
        raise ValueError("unsupported SARC byte order")
    data_offset = struct.unpack_from("<I", data, 12)[0]
    sfat = header_size
    if data[sfat:sfat + 4] != b"SFAT":
        raise ValueError("SARC has no SFAT")
    count = struct.unpack_from("<H", data, sfat + 6)[0]
    nodes = sfat + 12
    sfnt = nodes + count * 16
    if sfnt + 8 > len(data) or data[sfnt:sfnt + 4] != b"SFNT":
        raise ValueError("SARC has no valid SFNT")
    names = sfnt + 8
    out = {}
    for i in range(count):
        _, attr, start, end = struct.unpack_from("<4I", data, nodes + i * 16)
        if start > end or data_offset + end > len(data):
            raise ValueError(f"SARC member {i} is out of bounds")
        if not attr & 0x01000000:
            continue
        at = names + (attr & 0x00FFFFFF) * 4
        stop = data.find(b"\0", at, data_offset)
        if stop < 0:
            raise ValueError(f"SARC member {i} has an unterminated name")
        name = data[at:stop].decode("utf-8")
        out[name] = data[data_offset + start:data_offset + end]
    return out


def read_romfs_file(romfs: Path, manifest: dict, wanted: str) -> bytes:
    entries = manifest.get("files", [])
    found = next((e for e in entries if e.get("path") == wanted), None)
    if found is None:
        folded = [e for e in entries if str(e.get("path", "")).casefold() == wanted.casefold()]
        if len(folded) == 1:
            found = folded[0]
    if found is None:
        raise FileNotFoundError(wanted)
    offset, size = int(found["offset"]), int(found["size"])
    image = romfs / "romfs.bin"
    image_size = image.stat().st_size
    if offset < 0 or size <= 0 or offset > image_size or size > image_size - offset:
        raise ValueError(f"RomFS index entry out of bounds: {wanted}")
    with image.open("rb") as f:
        f.seek(offset)
        blob = f.read(size)
    if len(blob) != size:
        raise ValueError(f"short read of {wanted}")
    return blob


def unpack_zs(blob: bytes, dictionaries: dict[int, object]) -> bytes:
    try:
        import zstandard
    except ImportError as exc:
        raise RuntimeError("install tools/requirements.txt (zstandard) in the Python environment") from exc
    try:
        params = zstandard.get_frame_parameters(blob)
        dictionary_id = params.dict_id
        kwargs = {}
        if dictionary_id:
            dictionary = dictionaries.get(dictionary_id)
            if dictionary is None:
                raise ValueError(f"missing Zstandard dictionary {dictionary_id}")
            kwargs["dict_data"] = dictionary
        result = zstandard.ZstdDecompressor(**kwargs).decompress(blob, max_output_size=MAX_RAW)
    except Exception as exc:
        raise ValueError(f"Zstandard decompression failed: {exc}") from exc
    if len(result) > MAX_RAW:
        raise ValueError("decompressed ActorInfo exceeds size limit")
    return result


def dictionaries_for(romfs: Path, manifest: dict) -> dict[int, object]:
    """Read the game's own Zstandard dictionaries; contents remain in the local build tree."""
    try:
        import zstandard
    except ImportError as exc:
        raise RuntimeError("install tools/requirements.txt in the Python environment") from exc
    try:
        packed = read_romfs_file(romfs, manifest, "Pack/ZsDic.pack.zs")
        raw = unpack_zs(packed, {})
        return {d.dict_id: d for blob in sarc_members(raw).values()
                if (d := zstandard.ZstdCompressionDict(blob)).dict_id}
    except FileNotFoundError:
        return {}


def actor_info_path(files: list[dict], game_version: str) -> str:
    """Prefer the versioned runtime RSDB, with ActorInfo's legacy path as a compatibility fallback."""
    paths = {str(f.get("path", "")) for f in files}
    version = game_version.replace(".", "")
    candidates = [
        f"RSDB/ActorInfo.Product.{version}.rstbl.byml.zs",
        f"RSDB/ActorInfo.Product.{version}.byml.zs",
        "Actor/ActorInfo.product.sbyml",
        "Actor/ActorInfo.product.byml.zs",
    ]
    for candidate in candidates:
        if candidate in paths:
            return candidate
    folded = {p.casefold(): p for p in paths}
    for candidate in candidates:
        if candidate.casefold() in folded:
            return folded[candidate.casefold()]
    matches = sorted(p for p in paths if p.casefold().endswith("actorinfo.product.sbyml"))
    if len(matches) == 1:
        return matches[0]
    raise FileNotFoundError("no supported ActorInfo path found for update " + game_version)


def as_int(value) -> int:
    return int(getattr(value, "v", value))


def catalog_rows(document) -> list[dict]:
    """Validate ActorInfo's CRC/name table and extract display/search metadata."""
    hashes = document.get("Hashes")
    actors = document.get("Actors")
    if hashes is None or actors is None or len(hashes) != len(actors):
        raise ValueError("ActorInfo has no matching Hashes and Actors arrays")
    rows = []
    seen = set()
    for index, (raw_hash, actor) in enumerate(zip(hashes, actors)):
        if not hasattr(actor, "get"):
            raise ValueError(f"ActorInfo Actors[{index}] is not a map")
        name = str(actor.get("name", ""))
        if not name or name in seen:
            raise ValueError(f"ActorInfo Actors[{index}] has a missing or duplicate name")
        seen.add(name)
        stored = as_int(raw_hash) & 0xFFFFFFFF
        calculated = zlib.crc32(name.encode("utf-8")) & 0xFFFFFFFF
        if stored != calculated:
            raise ValueError(f"ActorInfo CRC mismatch for {name}: stored {stored:08X}, computed {calculated:08X}")
        profile = str(actor.get("profile", ""))
        lower_profile = profile.casefold()
        if name.startswith(("Weapon_Sword", "Weapon_Lsword", "Weapon_Spear", "Weapon_Bow", "Weapon_Shield")):
            category = "Weapons"
        elif name.startswith("Armor_") or lower_profile == "armor":
            category = "Armor"
        elif lower_profile in {"weapon", "bow", "arrow", "shield"} or name.startswith("Weapon_"):
            category = "Weapons"
        elif lower_profile in {"item", "cookitem", "bullet"} or name.startswith(("Item_", "Obj_Arrow", "Obj_Bomb", "Obj_Cook")):
            category = "Items"
        else:
            category = "Other"
        rows.append({"name": name, "hash": f"{stored:08X}", "profile": profile,
                     "category": category, "item_candidate": category != "Other"})
    return sorted(rows, key=lambda row: (row["category"], row["name"]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--romfs", type=Path, required=True, help="verified build/extracted/<version>/romfs directory")
    parser.add_argument("--version", choices=("1.1.0", "1.2.1", "1.4.3"), required=True,
                        help="installed game's update version; selects its versioned RSDB ActorInfo first")
    parser.add_argument("--out", type=Path, help="JSON output (default: <romfs parent>/item-catalog.json)")
    parser.add_argument("--query", default="", help="case-insensitive substring in actor name or profile")
    parser.add_argument("--items-only", action="store_true", help="limit results to likely weapon/item actors")
    args = parser.parse_args()
    try:
        import oead
        romfs = args.romfs.resolve()
        manifest = json.loads((romfs / "index.json").read_text(encoding="utf-8"))
        if manifest.get("status") != "pass":
            raise ValueError("RomFS index does not record a verified extraction")
        path = actor_info_path(manifest.get("files", []), args.version)
        blob = read_romfs_file(romfs, manifest, path)
        dictionaries = dictionaries_for(romfs, manifest)
        raw = unpack_zs(blob, dictionaries) if path.endswith(".zs") else blob
        if raw.startswith(b"Yaz0"):
            raw = bytes(oead.yaz0.decompress(raw))
        document = oead.byml.from_binary(raw)
        rows = catalog_rows(document)
        catalog = {"format": 1, "game_version": args.version, "source": path,
                   "lookup": "CRC32(actor name)", "actors": rows}
        out = args.out.resolve() if args.out else romfs.parent / "item-catalog.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        query = args.query.casefold()
        shown = [r for r in rows if (not args.items_only or r["item_candidate"])
                 and (not query or query in r["name"].casefold() or query in r["profile"].casefold())]
        for row in shown:
            print(f"{row['category']}\t{row['name']}\t{row['hash']}\t{row['profile']}")
        print(f"item_catalog: source={path}; {len(rows)} actors; {sum(r['item_candidate'] for r in rows)} item candidates; "
              f"{len(shown)} matched; wrote {out}", file=sys.stderr)
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"item_catalog: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
