#!/usr/bin/env python3
"""Install the portable human-ton package using only Python 3.9+ stdlib.

install(repo_root, ...) returns display lines or raises InstallError. Every
destination is checked before writing, and all copies are staged before any
replacement. Backups are retained outside skill discovery directories.

Renames are atomic per path, not a crash-proof multi-path transaction. Avoid
concurrent modifications of the source or installation directories while running.
"""

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
from typing import Dict, List, Optional


SKILL_PATHS = {
    "codex": Path(".agents/skills/human-ton"),
    "claude": Path(".claude/skills/human-ton"),
    "kiro": Path(".kiro/skills/human-ton"),
}
AGENT_PATH = Path(".kiro/agents/human-ton.json")
PROJECT_URI = "skill://.kiro/skills/human-ton/SKILL.md"
USER_URI = "skill://~/.kiro/skills/human-ton/SKILL.md"
Tree = Dict[Path, Optional[bytes]]


class InstallError(Exception):
    """A validation, conflict, or filesystem error suitable for CLI display."""


@dataclass
class _Item:
    destination: Path
    expected: Tree
    original: Optional[Tree]
    source: Optional[Path] = None
    staged: Optional[Path] = None
    backup: Optional[Path] = None
    promoted: bool = False


def _check_path(path: Path, directory: bool = False) -> None:
    """Use lstat on every component, including dangling links and ancestors."""
    for component in (*reversed(path.parents), path):
        try:
            mode = component.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise InstallError("Refusing symlink: {}".format(component))
        if (component != path or directory) and not stat.S_ISDIR(mode):
            raise InstallError("Not a directory: {}".format(component))


def _absolute(path: Path) -> Path:
    # Check before normalizing "..", so normalization cannot conceal a symlink.
    path = Path(path).expanduser().absolute()
    _check_path(path)
    return Path(os.path.abspath(path))


def _tree(path: Path, exclude_cache: bool = False) -> Tree:
    """Read regular files and directories without accepting links/special files."""
    mode = path.lstat().st_mode
    if stat.S_ISLNK(mode):
        raise InstallError("Refusing symlink: {}".format(path))
    if stat.S_ISREG(mode):
        return {Path("."): path.read_bytes()}
    if not stat.S_ISDIR(mode):
        raise InstallError("Not a regular file or directory: {}".format(path))
    result = {Path("."): None}
    for child in sorted(path.iterdir()):
        if exclude_cache and (child.name == "__pycache__" or child.name.endswith(".pyc")):
            continue
        for relative, contents in _tree(child, exclude_cache).items():
            result[Path(child.name) / relative] = contents
    return result


def _existing_tree(path: Path) -> Optional[Tree]:
    _check_path(path)
    return _tree(path) if os.path.lexists(path) else None


def _overlap(first: Path, second: Path) -> bool:
    return first == second or first in second.parents or second in first.parents


def _kiro_config(template: Path, scope: str) -> bytes:
    _check_path(template)
    if not template.is_file():
        raise InstallError("Missing Kiro template file: {}".format(template))
    try:
        config = json.loads(template.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as error:
        raise InstallError("Invalid Kiro template {}: {}".format(template, error)) from error
    if not isinstance(config, dict) or config.get("resources") != [PROJECT_URI]:
        raise InstallError(
            "Invalid Kiro template {}: resources must be [{}]".format(
                template, json.dumps(PROJECT_URI)
            )
        )
    if scope == "user":
        config["resources"] = [USER_URI]
    return (json.dumps(config, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _mkdir(path: Path, created: List[Path]) -> None:
    _check_path(path, directory=True)
    missing = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    for directory in reversed(missing):
        _check_path(directory, directory=True)
        try:
            directory.mkdir()
        except FileExistsError:
            _check_path(directory, directory=True)
        else:
            created.append(directory)


def _rollback(items: List[_Item]) -> List[str]:
    errors = []
    for item in reversed(items):
        if not item.promoted and item.backup is None:
            continue
        try:
            if item.promoted:
                current = _existing_tree(item.destination)
                if current is not None:
                    if current != item.expected:
                        raise InstallError("Destination changed during rollback")
                    _check_path(item.staged)
                    if os.path.lexists(item.staged):
                        raise InstallError("Staging path is occupied during rollback")
                    os.replace(item.destination, item.staged)
            if item.backup is not None:
                _check_path(item.destination)
                _check_path(item.backup)
                if os.path.lexists(item.destination):
                    raise InstallError("Destination is occupied during rollback")
                os.replace(item.backup, item.destination)
        except (OSError, InstallError) as error:
            errors.append("{}: {}".format(item.destination, error))
    return errors


def _apply(items: List[_Item], base: Path, work: Path) -> List[str]:
    changes = [item for item in items if item.original != item.expected]
    created = []
    staging = None
    backup_run = None
    failure = None
    rollback_errors = []
    warnings = []
    try:
        _mkdir(work, created)
        staging = Path(tempfile.mkdtemp(prefix=".stage-", dir=str(work)))
        for item in changes:
            item.staged = staging / item.destination.relative_to(base)
            _mkdir(item.staged.parent, created)
            if item.source is not None:
                # Preserve script permissions; links are copied as links, then
                # rejected below, so a changing source cannot install a link.
                shutil.copytree(
                    item.source,
                    item.staged,
                    symlinks=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                    copy_function=shutil.copy2,
                )
            else:
                item.staged.write_bytes(item.expected[Path(".")])
            if _tree(item.staged) != item.expected:
                raise InstallError("Source changed while staging: {}".format(item.source))

        # Check all selected paths again, including those originally unchanged.
        for item in items:
            if _existing_tree(item.destination) != item.original:
                raise InstallError("Destination changed during staging: {}".format(item.destination))

        if any(item.original is not None for item in changes):
            backup_parent = work / "backups"
            _mkdir(backup_parent, created)
            backup_run = Path(tempfile.mkdtemp(prefix="", dir=str(backup_parent)))
            created.append(backup_run)

        for item in changes:
            _mkdir(item.destination.parent, created)
            if _existing_tree(item.destination) != item.original:
                raise InstallError("Destination changed before replacement: {}".format(item.destination))
            if item.original is not None:
                backup = backup_run / item.destination.relative_to(base)
                _mkdir(backup.parent, created)
                _check_path(backup)
                if os.path.lexists(backup):
                    raise InstallError("Backup path already exists: {}".format(backup))
                os.replace(item.destination, backup)
                item.backup = backup
            _check_path(item.destination)
            if os.path.lexists(item.destination):
                raise InstallError("Destination appeared before installation: {}".format(item.destination))
            os.replace(item.staged, item.destination)
            item.promoted = True
    except (OSError, InstallError) as error:
        failure = error
        rollback_errors = _rollback(changes)
    finally:
        if staging is not None:
            try:
                _check_path(staging)
                shutil.rmtree(staging)
            except (OSError, InstallError) as error:
                warnings.append("Could not remove staging directory {}: {}".format(staging, error))
        # Only empty directories created by this run can be removed here.
        # Previous contents live in destinations or backups, never in staging.
        for directory in reversed(created):
            try:
                _check_path(directory, directory=True)
                directory.rmdir()
            except (OSError, InstallError):
                pass

    if failure is not None:
        details = [str(failure)]
        if rollback_errors:
            details.append(
                "Rollback incomplete; previous content is retained in backups at {}:\n{}".format(
                    backup_run, "\n".join(rollback_errors)
                )
            )
        details.extend(warnings)
        raise InstallError("\n".join(details)) from failure
    return warnings


def install(
    repo_root: Path,
    *,
    target: str = "all",
    scope: str = "project",
    project_dir: Optional[Path] = None,
    dry_run: bool = False,
    replace: bool = False,
) -> List[str]:
    """Preflight and install; user scope rejects the project-only directory flag."""
    if target not in (*SKILL_PATHS, "all"):
        raise InstallError("Unknown target: {}".format(target))
    if scope not in ("project", "user"):
        raise InstallError("Unknown scope: {}".format(scope))
    if scope == "user" and project_dir is not None:
        raise InstallError("--project-dir is only meaningful with --scope project")

    try:
        repo = _absolute(repo_root)
        base = _absolute(Path.home() if scope == "user" else (
            project_dir if project_dir is not None else Path.cwd()
        ))
        _check_path(base, directory=True)
        source = repo / "skills" / "human-ton"
        _check_path(source, directory=True)
        if not source.is_dir():
            raise InstallError("Missing source package: {}".format(source))
        expected = _tree(source, exclude_cache=True)
        if expected.get(Path("SKILL.md")) is None:
            raise InstallError("Missing source SKILL.md file: {}".format(source / "SKILL.md"))

        targets = tuple(SKILL_PATHS) if target == "all" else (target,)
        inputs = [source]
        candidates = [(base / SKILL_PATHS[name], expected, source) for name in targets]
        if "kiro" in targets:
            template = repo / "integrations" / "kiro" / "human-ton.json"
            contents = _kiro_config(template, scope)
            inputs.append(template)
            candidates.append((base / AGENT_PATH, {Path("."): contents}, None))

        work = base / ".human-ton"
        for destination in [item[0] for item in candidates] + [work]:
            for input_path in inputs:
                if _overlap(input_path, destination):
                    raise InstallError(
                        "Source and destination overlap: {} and {}".format(input_path, destination)
                    )

        items = [
            _Item(destination, wanted, _existing_tree(destination), origin)
            for destination, wanted, origin in candidates
        ]
        changes = [item for item in items if item.original != item.expected]
        conflicts = [item.destination for item in changes if item.original is not None]
        if conflicts and not replace:
            raise InstallError(
                "Existing content differs; use --replace to back up and replace:\n"
                + "\n".join(str(path) for path in conflicts)
            )
        if changes:
            _check_path(work, directory=True)
            if conflicts:
                _check_path(work / "backups", directory=True)

        warnings = _apply(items, base, work) if changes and not dry_run else []
        messages = []
        for item in items:
            if item.original == item.expected:
                messages.append("unchanged: {}".format(item.destination))
            elif dry_run:
                action = "replace" if item.original is not None else "install"
                backup = " (backup under {})".format(work / "backups") if item.original is not None else ""
                messages.append("would {}: {}{}".format(action, item.destination, backup))
            elif item.backup is not None:
                messages.append("replaced: {} (backup: {})".format(item.destination, item.backup))
            else:
                messages.append("installed: {}".format(item.destination))
        return messages + warnings
    except OSError as error:
        raise InstallError(str(error)) from error


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Install the portable human-ton writing skill.")
    parser.add_argument("--target", choices=("codex", "claude", "kiro", "all"), default="all")
    parser.add_argument("--scope", choices=("project", "user"), default="project")
    parser.add_argument("--project-dir", type=Path, help="Project base directory (default: cwd)")
    parser.add_argument("--dry-run", action="store_true", help="Preflight and report without writing")
    parser.add_argument("--replace", action="store_true", help="Back up and replace differing installs")
    args = parser.parse_args(argv)
    if args.scope == "user" and args.project_dir is not None:
        parser.error("--project-dir is only meaningful with --scope project")
    try:
        messages = install(Path(__file__).resolve().parents[1], **vars(args))
    except InstallError as error:
        print("error: {}".format(error), file=sys.stderr)
        return 1
    for message in messages:
        print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
