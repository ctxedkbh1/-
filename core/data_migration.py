import datetime
import hashlib
import json
import os
import shutil


REPORT_FILE = "migration_report.json"
BACKUP_DIR = "migration_backups"


def _file_hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _same_file(left, right):
    try:
        if os.path.getsize(left) != os.path.getsize(right):
            return False
        return _file_hash(left) == _file_hash(right)
    except OSError:
        return False


def _copy_atomic(source, destination):
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    temporary = destination + ".migration_tmp"
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            try:
                os.remove(temporary)
            except OSError:
                pass


def _merge_missing(target, incoming):
    merged = 0
    for key, value in incoming.items():
        if key not in target or target[key] in (None, "", [], {}):
            target[key] = value
            merged += 1
        elif isinstance(target[key], dict) and isinstance(value, dict):
            merged += _merge_missing(target[key], value)
    return merged


def _merge_config(source, destination):
    try:
        with open(source, encoding="utf-8") as handle:
            incoming = json.load(handle)
        with open(destination, encoding="utf-8") as handle:
            target = json.load(handle)
        if not isinstance(incoming, dict) or not isinstance(target, dict):
            return 0
        merged = _merge_missing(target, incoming)
        if merged:
            temporary = destination + ".migration_tmp"
            with open(temporary, "w", encoding="utf-8") as handle:
                json.dump(target, handle, ensure_ascii=False, indent=2)
            os.replace(temporary, destination)
        return merged
    except (OSError, ValueError, TypeError):
        return 0


def _source_label(source):
    base = os.path.basename(os.path.dirname(source)) or os.path.basename(source) or "legacy"
    digest = hashlib.sha256(os.path.normcase(source).encode("utf-8")).hexdigest()[:8]
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in base)
    return f"{safe}-{digest}"


def _conflict_backup(source, source_dir, target_dir, relative_path):
    root = os.path.join(target_dir, BACKUP_DIR, _source_label(source_dir))
    destination = os.path.join(root, relative_path)
    if not os.path.exists(destination):
        _copy_atomic(source, destination)
        return destination
    if _same_file(source, destination):
        return destination
    stem, extension = os.path.splitext(destination)
    destination = f"{stem}.{_file_hash(source)[:10]}{extension}"
    if not os.path.exists(destination):
        _copy_atomic(source, destination)
    return destination


def merge_legacy_data(target_dir, source_dirs):
    """Copy legacy data into a stable directory without deleting source data."""
    target_dir = os.path.abspath(target_dir)
    os.makedirs(target_dir, exist_ok=True)
    report = {
        "at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sources": [],
        "copied_files": 0,
        "conflicts_backed_up": 0,
        "config_fields_merged": 0,
        "errors": [],
    }
    seen = set()
    for source_dir in source_dirs:
        if not source_dir:
            continue
        source_dir = os.path.abspath(source_dir)
        normalized = os.path.normcase(os.path.realpath(source_dir))
        if normalized in seen or normalized == os.path.normcase(os.path.realpath(target_dir)):
            continue
        seen.add(normalized)
        if not os.path.isdir(source_dir):
            continue
        report["sources"].append(source_dir)
        for root, dirnames, filenames in os.walk(source_dir, followlinks=False):
            dirnames[:] = [name for name in dirnames
                           if name != BACKUP_DIR and not os.path.islink(os.path.join(root, name))]
            for filename in filenames:
                source = os.path.join(root, filename)
                if os.path.islink(source) or filename == REPORT_FILE:
                    continue
                relative = os.path.relpath(source, source_dir)
                destination = os.path.join(target_dir, relative)
                try:
                    if not os.path.exists(destination):
                        _copy_atomic(source, destination)
                        report["copied_files"] += 1
                        continue
                    if _same_file(source, destination):
                        continue
                    _conflict_backup(source, source_dir, target_dir, relative)
                    report["conflicts_backed_up"] += 1
                    if relative.replace("\\", "/") == "config.json":
                        report["config_fields_merged"] += _merge_config(source, destination)
                except OSError as exc:
                    report["errors"].append({"file": relative, "error": str(exc)})

    changed = (report["copied_files"] or report["conflicts_backed_up"] or
               report["config_fields_merged"] or report["errors"])
    if changed:
        report_path = os.path.join(target_dir, REPORT_FILE)
        temporary = report_path + ".tmp"
        try:
            with open(temporary, "w", encoding="utf-8") as handle:
                json.dump(report, handle, ensure_ascii=False, indent=2)
            os.replace(temporary, report_path)
        finally:
            if os.path.exists(temporary):
                try:
                    os.remove(temporary)
                except OSError:
                    pass
    return report


# Version: v2.3.0 (2026-08-19) Update: lossless legacy data migration
