"""Validate, stage and deterministically package the public prompt catalog."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=unique_pairs)


def validator():
    schema = read_json(ROOT / "catalog/prompt.schema.json")
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate(directory):
    check = validator()
    records = []
    ids = set()
    errors = []
    directory = Path(directory).resolve()
    for path in sorted(directory.rglob("*.json")):
        try:
            if path.is_symlink() or not path.resolve().is_relative_to(directory):
                raise ValueError("Catalog cannot contain linked files")
            document = read_json(path)
            check.validate(document)
            relative = path.relative_to(directory)
            if len(relative.parts) != 2 or relative.parts[0] != document["category"]:
                raise ValueError("Expected category/id.json matching category")
            if path.stem != document["id"]:
                raise ValueError("Filename must match id")
            if document["id"] in ids:
                raise ValueError(f"Duplicate ID: {document['id']}")
            if not any(text.strip() for text in document["content"].values()):
                raise ValueError("Prompt content is empty")
            ids.add(document["id"])
            records.append((path, document))
        except Exception as error:
            errors.append(f"{path.relative_to(directory)}: {error.message if hasattr(error, 'message') else error}")
    if not records and not errors:
        errors.append("Catalog is empty")
    if errors:
        raise ValueError("\n".join(errors))
    return records


def package(directory, destination, source_commit):
    records = validate(directory)
    payloads = []
    entries = []
    for path, doc in records:
        data = path.read_bytes()
        name = "prompts/" + path.relative_to(directory).as_posix()
        payloads.append((name, data))
        entries.append({"id": doc["id"], "path": name, "sha256": hashlib.sha256(data).hexdigest()})
    deleted = read_json(ROOT / "catalog/deleted-ids.json")
    if not isinstance(deleted, list) or any(not isinstance(value, str) or not value or not all(c.isascii() and (c.isalnum() or c in "_-") for c in value) for value in deleted):
        raise ValueError("Invalid deletion ledger")
    if len(set(deleted)) != len(deleted) or set(deleted) & {entry["id"] for entry in entries}:
        raise ValueError("Duplicate tombstones or live ID marked deleted")
    snapshot = hashlib.sha256(json.dumps({"entries": entries, "deleted_ids": deleted}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    manifest = {"schema_version": 1, "snapshot_id": snapshot, "source_commit": source_commit,
                "count": len(entries), "entries": entries, "deleted_ids": deleted}
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    manifest_data = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    # Fixed entry timestamps/order make the same source reproducible.
    temporary = destination / "prompts.zip.tmp"
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in payloads + [("catalog.manifest", manifest_data)]:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    os.replace(temporary, destination / "prompts.zip")
    (destination / "catalog-manifest.json").write_bytes(manifest_data)
    checksum = hashlib.sha256((destination / "prompts.zip").read_bytes()).hexdigest()
    (destination / "checksums.sha256").write_text(f"{checksum}  prompts.zip\n", encoding="utf-8")
    return manifest


def stage(source, directory):
    """Copy an explicit export to review staging. Never edits the live catalog."""
    document = read_json(source)
    if document.get("is_local") or document.get("is_favorite") or document.get("isLocal") or document.get("isFavorite"):
        raise ValueError("Personal export: review privacy before creating a public candidate")
    validator().validate(document)
    directory = Path(directory).resolve()
    target = directory / document["category"] / f"{document['id']}.json"
    if not target.resolve().is_relative_to(directory):
        raise ValueError("Unsafe destination")
    target.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents silently overwriting a reviewed candidate.
    with target.open("x", encoding="utf-8") as output:
        json.dump(document, output, ensure_ascii=False, indent=2)
        output.write("\n")
    return target


def candidate(source, directory, prompt_id=None):
    """Explicitly prepare a public candidate; retain content for human review."""
    document = read_json(source)
    if isinstance(document, list):
        selected = [item for item in document if isinstance(item, dict) and item.get("id") == prompt_id]
        if len(selected) != 1:
            raise ValueError("Select exactly one prompt from a personal export using --id")
        document = selected[0]
    if not isinstance(document, dict):
        raise ValueError("Expected a prompt document")
    document = copy.deepcopy(document)
    for old, new in {"compatibleModels": "compatible_models", "createdAt": "created_at", "modifiedAt": "updated_at"}.items():
        if old in document:
            document.setdefault(new, document.pop(old))
    document.pop("isLocal", None)
    document.pop("isFavorite", None)
    document["is_local"] = False
    document["is_favorite"] = False
    if isinstance(document.get("metadata"), dict):
        document["metadata"].pop("notes", None)
    for variant in document.get("prompt_variants", []):
        if "variantId" in variant:
            variant.setdefault("variant_id", variant.pop("variantId"))
        identity = variant.get("variant_id")
        if isinstance(identity, dict):
            identity.setdefault("priority", variant.pop("priority", 1))
    validator().validate(document)
    directory = Path(directory).resolve()
    target = directory / document["category"] / f"{document['id']}.json"
    if not target.resolve().is_relative_to(directory):
        raise ValueError("Unsafe destination")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as output:
        json.dump(document, output, ensure_ascii=False, indent=2)
        output.write("\n")
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate", "package", "stage", "candidate"])
    parser.add_argument("--prompts", type=Path, default=ROOT / "prompts")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--commit")
    parser.add_argument("--id")
    args = parser.parse_args()
    try:
        if args.command == "validate":
            print(f"Validated {len(validate(args.prompts))} prompts")
        elif args.command in ("stage", "candidate"):
            if args.source is None:
                parser.error("stage requires --source")
            print(candidate(args.source, args.output, args.id) if args.command == "candidate" else stage(args.source, args.output))
        else:
            commit = args.commit or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
            manifest = package(args.prompts.resolve(), args.output, commit)
            print(f"Packaged {manifest['count']} prompts, snapshot {manifest['snapshot_id']}")
    except (ValueError, OSError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
