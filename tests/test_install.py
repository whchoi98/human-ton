"""Behavioral tests for the standalone installer; all installs use temp trees."""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


INSTALLER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "install.py"
INSTALL_PATHS = (
    ".agents/skills/human-ton",
    ".claude/skills/human-ton",
    ".kiro/skills/human-ton",
    ".kiro/agents/human-ton.json",
)
PROJECT_URI = "skill://.kiro/skills/human-ton/SKILL.md"
USER_URI = "skill://~/.kiro/skills/human-ton/SKILL.md"

installer = None
if INSTALLER_PATH.is_file():
    spec = importlib.util.spec_from_file_location("human_ton_installer", INSTALLER_PATH)
    installer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = installer
    spec.loader.exec_module(installer)


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    return path


def make_repo(repo):
    source = repo / "skills" / "human-ton"
    write(source / "SKILL.md", "# Human ton\n\n[Style](references/style.md)\n")
    write(source / "references" / "style.md", "자연스러운 문장\n")
    write(source / "references" / "nested" / "example.txt", "A local example.\n")
    write(source / "agents" / "openai.yaml", "display_name: Human ton\n")
    script = write(
        source / "scripts" / "read_style.py",
        "from pathlib import Path\n"
        "print((Path(__file__).resolve().parents[1] / 'references' / 'style.md')"
        ".read_text(encoding='utf-8'), end='')\n",
    )
    script.chmod(0o755)
    (source / "empty").mkdir()
    write(source / "__pycache__" / "cache.pyc", b"cache")
    write(source / "scripts" / "__pycache__" / "cache.pyc", b"cache")
    write(source / "references" / "stray.pyc", b"cache")
    write(repo / "not-in-the-package.txt", "Do not install this.\n")
    template = write(
        repo / "integrations" / "kiro" / "human-ton.json",
        json.dumps(
            {
                "name": "human-ton",
                "description": "Portable writing helper",
                "prompt": "Use the writing skill.",
                "resources": [PROJECT_URI],
                "tools": ["read"],
                "allowedTools": [],
            }
        ),
    )
    return source, template


def snapshot(root):
    """Include identities/mtimes so copying identical bytes is not a no-op."""
    result = {}

    def visit(path):
        try:
            info = path.lstat()
        except FileNotFoundError:
            return
        relative = str(path.relative_to(root))
        metadata = (stat.S_IMODE(info.st_mode), info.st_ino, info.st_mtime_ns)
        if stat.S_ISLNK(info.st_mode):
            result[relative] = ("link", os.readlink(path), metadata)
        elif stat.S_ISDIR(info.st_mode):
            result[relative] = ("dir", metadata)
            for child in sorted(path.iterdir()):
                visit(child)
        elif stat.S_ISREG(info.st_mode):
            result[relative] = ("file", path.read_bytes(), metadata)
        else:
            result[relative] = ("special", metadata)

    visit(root)
    return result


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(installer, "scripts/install.py has not been implemented")
        temporary = tempfile.TemporaryDirectory(prefix="human ton test ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.repo = self.root / "source repo"
        self.source, self.template = make_repo(self.repo)
        self.project = self.root / "project with spaces"
        self.home = self.root / "temporary home"

    def install(self, **kwargs):
        kwargs.setdefault("project_dir", self.project)
        return installer.install(self.repo, **kwargs)

    def assert_package(self, destination):
        self.assertEqual(
            (destination / "SKILL.md").read_bytes(), (self.source / "SKILL.md").read_bytes()
        )
        self.assertEqual(
            (destination / "references" / "style.md").read_text(encoding="utf-8"),
            "자연스러운 문장\n",
        )
        self.assertEqual(
            (destination / "references" / "nested" / "example.txt").read_text(),
            "A local example.\n",
        )
        self.assertTrue((destination / "agents" / "openai.yaml").is_file())
        self.assertTrue((destination / "scripts" / "read_style.py").is_file())
        self.assertTrue((destination / "empty").is_dir())
        self.assertEqual(list(destination.rglob("__pycache__")), [])
        self.assertEqual(list(destination.rglob("*.pyc")), [])
        self.assertFalse((destination / "not-in-the-package.txt").exists())
        self.assertFalse(any(path.is_symlink() for path in destination.rglob("*")))
        if os.name != "nt":
            self.assertTrue((destination / "scripts" / "read_style.py").stat().st_mode & 0o100)

    def symlink(self, path, target, directory=False):
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError) as error:
            self.skipTest("Symlinks unavailable: {}".format(error))

    def make_changed_install(self):
        self.install()
        for relative in INSTALL_PATHS[:3]:
            write(self.project / relative / "SKILL.md", "User's previous " + relative)
        write(self.project / INSTALL_PATHS[3], '{"name": "previous user agent"}\n')
        return {relative: snapshot(self.project / relative) for relative in INSTALL_PATHS}

    def assert_previous(self, previous):
        for relative, contents in previous.items():
            self.assertEqual(snapshot(self.project / relative), contents, relative)

    def backup_runs(self):
        backups = self.project / ".human-ton" / "backups"
        return sorted(backups.iterdir()) if backups.exists() else []

    def cli(self, *args, cwd=None):
        script = self.repo / "scripts" / "install.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(INSTALLER_PATH, script)
        return subprocess.run(
            [sys.executable, "-B", str(script), *map(str, args)],
            cwd=str(cwd or self.root),
            capture_output=True,
            text=True,
            timeout=15,
        )

    def test_installs_all_package_files_and_only_selected_owned_paths(self):
        messages = self.install()
        for relative in INSTALL_PATHS[:3]:
            self.assert_package(self.project / relative)
        self.assertTrue((self.project / INSTALL_PATHS[3]).is_file())
        for relative in INSTALL_PATHS:
            self.assertIn(str(self.project / relative), "\n".join(messages))
        self.assertEqual(self.backup_runs(), [])

    def test_each_single_target_is_independent(self):
        expected = {
            "codex": {INSTALL_PATHS[0]},
            "claude": {INSTALL_PATHS[1]},
            "kiro": {INSTALL_PATHS[2], INSTALL_PATHS[3]},
        }
        for target, paths in expected.items():
            with self.subTest(target=target):
                base = self.root / target
                self.install(target=target, project_dir=base)
                actual = {path for path in INSTALL_PATHS if (base / path).exists()}
                self.assertEqual(actual, paths)

    def test_project_kiro_uri_and_other_template_fields_are_preserved(self):
        before = snapshot(self.template)
        self.install(target="kiro")
        config = json.loads((self.project / INSTALL_PATHS[3]).read_text())
        self.assertEqual(config["resources"], [PROJECT_URI])
        self.assertEqual(config, json.loads(self.template.read_text()))
        self.assertEqual(snapshot(self.template), before)

    def test_user_scope_uses_path_home_and_user_uri(self):
        before = snapshot(self.repo)
        with mock.patch.object(installer.Path, "home", return_value=self.home):
            installer.install(self.repo, scope="user")
        for relative in INSTALL_PATHS[:3]:
            self.assert_package(self.home / relative)
        config = json.loads((self.home / INSTALL_PATHS[3]).read_text())
        expected = json.loads(self.template.read_text())
        expected["resources"] = [USER_URI]
        self.assertEqual(config, expected)
        self.assertFalse(self.project.exists())
        self.assertEqual(snapshot(self.repo), before)

    def test_project_dir_is_rejected_for_user_scope_without_writing(self):
        before = snapshot(self.root)
        with mock.patch.object(installer.Path, "home", return_value=self.home):
            with self.assertRaises(installer.InstallError):
                self.install(scope="user")
        self.assertEqual(snapshot(self.root), before)

    def test_dry_run_with_missing_base_creates_nothing(self):
        before = snapshot(self.root)
        messages = self.install(dry_run=True, project_dir=self.project / "new nested base")
        self.assertIn("would", "\n".join(messages).lower())
        self.assertEqual(snapshot(self.root), before)

    def test_dry_run_still_refuses_conflicts(self):
        write(self.project / INSTALL_PATHS[3], "Existing agent")
        before = snapshot(self.root)
        with self.assertRaises(installer.InstallError) as caught:
            self.install(dry_run=True)
        self.assertIn(str(self.project / INSTALL_PATHS[3]), str(caught.exception))
        self.assertEqual(snapshot(self.root), before)

    def test_dry_run_replace_reports_backups_without_mutating(self):
        self.make_changed_install()
        before = snapshot(self.root)
        messages = self.install(dry_run=True, replace=True)
        self.assertIn("replace", "\n".join(messages).lower())
        self.assertIn("backup", "\n".join(messages).lower())
        self.assertEqual(snapshot(self.root), before)

    def test_matching_install_is_noop_including_with_replace(self):
        self.install()
        before = snapshot(self.project)
        for replace in (False, True):
            with self.subTest(replace=replace):
                messages = self.install(replace=replace)
                self.assertIn("unchanged", "\n".join(messages).lower())
                self.assertEqual(snapshot(self.project), before)
        self.assertEqual(self.backup_runs(), [])

    def test_last_destination_conflict_prevents_every_install(self):
        write(self.project / INSTALL_PATHS[3], "My existing agent")
        before = snapshot(self.root)
        with self.assertRaises(installer.InstallError):
            self.install()
        self.assertEqual(snapshot(self.root), before)
        for relative in INSTALL_PATHS[:3]:
            self.assertFalse((self.project / relative).exists())

    def test_extra_existing_file_is_a_conflict_even_when_skill_matches(self):
        self.install(target="codex")
        write(self.project / INSTALL_PATHS[0] / "personal-notes.txt", "Keep this")
        before = snapshot(self.root)
        with self.assertRaises(installer.InstallError):
            self.install()
        self.assertEqual(snapshot(self.root), before)

    def test_replace_backs_up_owned_paths_and_preserves_unrelated_files(self):
        previous = self.make_changed_install()
        unrelated = (
            ".agents/skills/another-skill/SKILL.md",
            ".claude/settings.json",
            ".kiro/agents/default.json",
            ".kiro/settings/trust.json",
            ".human-ton/notes.txt",
        )
        for relative in unrelated:
            write(self.project / relative, "User content: " + relative)
        untouched = {path: snapshot(self.project / path) for path in unrelated}
        messages = self.install(replace=True)
        runs = self.backup_runs()
        self.assertEqual(len(runs), 1)
        for relative in INSTALL_PATHS:
            self.assertEqual(snapshot(runs[0] / relative), previous[relative], relative)
        for relative in INSTALL_PATHS[:3]:
            self.assert_package(self.project / relative)
        config = json.loads((self.project / INSTALL_PATHS[3]).read_text())
        self.assertEqual(config["resources"], [PROJECT_URI])
        for relative in unrelated:
            self.assertEqual(snapshot(self.project / relative), untouched[relative])
        self.assertIn(str(runs[0]), "\n".join(messages))
        self.assertEqual(list((self.project / ".human-ton").glob(".stage-*")), [])

    def test_replace_only_changes_differing_paths(self):
        self.install()
        write(self.project / INSTALL_PATHS[1] / "SKILL.md", "Old Claude skill")
        unchanged = {
            path: snapshot(self.project / path)
            for path in (INSTALL_PATHS[0], INSTALL_PATHS[2], INSTALL_PATHS[3])
        }
        self.install(replace=True)
        self.assert_previous(unchanged)
        runs = self.backup_runs()
        self.assertEqual(len(runs), 1)
        self.assertEqual(
            (runs[0] / INSTALL_PATHS[1] / "SKILL.md").read_text(), "Old Claude skill"
        )
        for relative in unchanged:
            self.assertFalse((runs[0] / relative).exists())

    def test_repeated_replacements_keep_distinct_backups(self):
        self.install(target="codex")
        for old_content in ("First edit", "Second edit"):
            write(self.project / INSTALL_PATHS[0] / "SKILL.md", old_content)
            self.install(target="codex", replace=True)
        runs = self.backup_runs()
        self.assertEqual(len(runs), 2)
        self.assertEqual(
            {(run / INSTALL_PATHS[0] / "SKILL.md").read_text() for run in runs},
            {"First edit", "Second edit"},
        )

    def test_replace_handles_file_directory_type_conflicts(self):
        write(self.project / INSTALL_PATHS[0], "A user's file at the skill path")
        write(self.project / INSTALL_PATHS[3] / "keep.txt", "A user's directory")
        previous = {
            path: snapshot(self.project / path)
            for path in (INSTALL_PATHS[0], INSTALL_PATHS[3])
        }
        self.install(replace=True)
        self.assert_package(self.project / INSTALL_PATHS[0])
        self.assertTrue((self.project / INSTALL_PATHS[3]).is_file())
        runs = self.backup_runs()
        self.assertEqual(len(runs), 1)
        for relative, contents in previous.items():
            self.assertEqual(snapshot(runs[0] / relative), contents)

    def test_copied_packages_work_after_original_repository_is_removed(self):
        self.install()
        shutil.rmtree(self.repo)
        for relative in INSTALL_PATHS[:3]:
            destination = self.project / relative
            result = subprocess.run(
                [sys.executable, "-B", str(destination / "scripts" / "read_style.py")],
                cwd=str(self.root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=15,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "자연스러운 문장\n")
            self.assertTrue((destination / "references" / "style.md").is_file())

    def test_rejects_live_and_dangling_destination_symlinks_at_all_levels(self):
        outside = self.root / "outside"
        write(outside / "keep.txt", "Never follow or modify this")
        cases = (
            ".",
            ".agents",
            ".agents/skills",
            ".agents/skills/human-ton",
            ".claude/skills/human-ton",
            ".kiro/skills/human-ton",
            ".kiro/agents",
            ".kiro/agents/human-ton.json",
            ".human-ton",
            ".human-ton/backups",
        )
        for dangling in (False, True):
            for index, relative in enumerate(cases):
                with self.subTest(path=relative, dangling=dangling):
                    base = self.root / "links {} {}".format(dangling, index)
                    target = self.root / "absent outside" if dangling else outside
                    self.symlink(base / relative, target, directory=True)
                    if relative == ".human-ton/backups":
                        write(base / INSTALL_PATHS[0] / "SKILL.md", "Old install")
                    before = snapshot(self.root)
                    with self.assertRaises(installer.InstallError) as caught:
                        self.install(project_dir=base, replace=True)
                    self.assertIn("symlink", str(caught.exception).lower())
                    self.assertEqual(snapshot(self.root), before)

    def test_rejects_symlinks_inside_an_existing_install_even_with_replace(self):
        outside = write(self.root / "private.txt", "User's private contents")
        for dangling in (False, True):
            with self.subTest(dangling=dangling):
                base = self.root / "nested link {}".format(dangling)
                write(base / INSTALL_PATHS[0] / "SKILL.md", "Old skill")
                target = self.root / "missing.txt" if dangling else outside
                self.symlink(base / INSTALL_PATHS[0] / "references" / "link.md", target)
                before = snapshot(self.root)
                with self.assertRaises(installer.InstallError):
                    self.install(project_dir=base, replace=True)
                self.assertEqual(snapshot(self.root), before)

    def test_rejects_source_symlinks_including_dangling_links(self):
        outside = write(self.root / "external-reference.md", "Outside the package")
        for index, relative in enumerate((".", "SKILL.md", "references/style.md", "dangling")):
            with self.subTest(path=relative):
                repo = self.root / "linked source {}".format(index)
                source, _ = make_repo(repo)
                path = source / relative
                if path.is_dir():
                    shutil.rmtree(path)
                elif path.exists():
                    path.unlink()
                target = self.source if relative == "." else outside
                if relative == "dangling":
                    target = self.root / "absent"
                self.symlink(path, target, directory=relative == ".")
                before = snapshot(self.root)
                with self.assertRaises(installer.InstallError):
                    installer.install(repo, project_dir=self.project)
                self.assertEqual(snapshot(self.root), before)

    def test_rejects_a_symlinked_kiro_template(self):
        target = write(self.root / "outside-template.json", self.template.read_bytes())
        self.template.unlink()
        self.symlink(self.template, target)
        before = snapshot(self.root)
        with self.assertRaises(installer.InstallError):
            self.install()
        self.assertEqual(snapshot(self.root), before)

    def test_rejects_source_destination_overlap_in_both_directions(self):
        with self.subTest(direction="destination inside source"):
            before = snapshot(self.root)
            with self.assertRaises(installer.InstallError) as caught:
                self.install(project_dir=self.source)
            self.assertIn("overlap", str(caught.exception).lower())
            self.assertEqual(snapshot(self.root), before)
        with self.subTest(direction="source inside destination"):
            nested_repo = self.project / INSTALL_PATHS[0]
            make_repo(nested_repo)
            before = snapshot(self.root)
            with self.assertRaises(installer.InstallError) as caught:
                installer.install(nested_repo, project_dir=self.project)
            self.assertIn("overlap", str(caught.exception).lower())
            self.assertEqual(snapshot(self.root), before)

    def test_rejects_file_in_a_destination_ancestor_without_replacing_it(self):
        write(self.project / ".kiro" / "agents", "This is not our path to replace")
        before = snapshot(self.root)
        with self.assertRaises(installer.InstallError):
            self.install(replace=True)
        self.assertEqual(snapshot(self.root), before)

    def test_missing_source_and_missing_skill_are_validated_before_writing(self):
        for case in ("missing source", "source is file", "missing SKILL", "SKILL is dir"):
            with self.subTest(case=case):
                repo = self.root / case
                source, _ = make_repo(repo)
                if case in ("missing source", "source is file"):
                    shutil.rmtree(source)
                    if case == "source is file":
                        write(source, "Not a package")
                else:
                    (source / "SKILL.md").unlink()
                    if case == "SKILL is dir":
                        (source / "SKILL.md").mkdir()
                before = snapshot(self.root)
                with self.assertRaises(installer.InstallError):
                    installer.install(repo, project_dir=self.project)
                self.assertEqual(snapshot(self.root), before)

    def test_missing_kiro_template_prevents_all_selected_writes(self):
        self.template.unlink()
        before = snapshot(self.root)
        for target in ("kiro", "all"):
            with self.subTest(target=target):
                with self.assertRaises(installer.InstallError) as caught:
                    self.install(target=target)
                self.assertIn(str(self.template), str(caught.exception))
                self.assertEqual(snapshot(self.root), before)

    def test_non_kiro_targets_do_not_require_a_template(self):
        self.template.unlink()
        self.install(target="codex")
        self.install(target="claude")
        self.assert_package(self.project / INSTALL_PATHS[0])
        self.assert_package(self.project / INSTALL_PATHS[1])
        self.assertFalse((self.project / ".kiro").exists())

    def test_invalid_kiro_template_is_rejected_without_mutation(self):
        for content in (
            "not json",
            "[]",
            "{}",
            '{"resources": "skill://wrong"}',
            '{"resources": ["skill://elsewhere/SKILL.md"]}',
        ):
            with self.subTest(content=content):
                self.template.write_text(content)
                before = snapshot(self.root)
                with self.assertRaises(installer.InstallError) as caught:
                    self.install()
                self.assertIn(str(self.template), str(caught.exception))
                self.assertEqual(snapshot(self.root), before)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "Requires FIFO support")
    def test_special_source_and_destination_files_are_rejected_without_reading(self):
        for location in ("source", "destination"):
            with self.subTest(location=location):
                path = (
                    self.source / "references" / "pipe"
                    if location == "source"
                    else self.project / INSTALL_PATHS[0] / "pipe"
                )
                path.parent.mkdir(parents=True, exist_ok=True)
                os.mkfifo(path)
                before = snapshot(self.root)
                with self.assertRaises(installer.InstallError):
                    self.install(replace=True)
                self.assertEqual(snapshot(self.root), before)
                path.unlink()

    def test_copy_failure_leaves_all_previous_installs_intact(self):
        previous = self.make_changed_install()
        real_copy = shutil.copy2

        def fail_on_reference(source, destination, *args, **kwargs):
            if Path(source).name == "style.md":
                raise OSError("simulated unreadable source")
            return real_copy(source, destination, *args, **kwargs)

        with mock.patch.object(installer.shutil, "copy2", side_effect=fail_on_reference):
            with self.assertRaises(installer.InstallError) as caught:
                self.install(replace=True)
        self.assertIn("simulated unreadable source", str(caught.exception))
        self.assert_previous(previous)
        self.assertEqual(self.backup_runs(), [])
        self.assertEqual(list((self.project / ".human-ton").glob(".stage-*")), [])

    def test_replacement_failure_rolls_back_every_previous_install(self):
        previous = self.make_changed_install()
        real_replace = os.replace
        failed = False

        def fail_last_promotion(source, destination, *args, **kwargs):
            nonlocal failed
            if Path(destination) == self.project / INSTALL_PATHS[3] and not failed:
                failed = True
                raise OSError("simulated final promotion failure")
            return real_replace(source, destination, *args, **kwargs)

        with mock.patch.object(installer.os, "replace", side_effect=fail_last_promotion):
            with self.assertRaises(installer.InstallError) as caught:
                self.install(replace=True)
        self.assertIn("simulated final promotion failure", str(caught.exception))
        self.assert_previous(previous)
        self.assertEqual(list((self.project / ".human-ton").glob(".stage-*")), [])

    def test_failed_fresh_install_removes_already_promoted_packages(self):
        real_replace = os.replace

        def fail_kiro(source, destination, *args, **kwargs):
            if Path(destination) == self.project / INSTALL_PATHS[2]:
                raise OSError("simulated new install failure")
            return real_replace(source, destination, *args, **kwargs)

        with mock.patch.object(installer.os, "replace", side_effect=fail_kiro):
            with self.assertRaises(installer.InstallError):
                self.install()
        for relative in INSTALL_PATHS:
            self.assertFalse((self.project / relative).exists())
        self.assertEqual(list(self.project.rglob("SKILL.md")), [])

    def test_backup_move_failure_restores_earlier_replacements(self):
        previous = self.make_changed_install()
        real_replace = os.replace

        def fail_backup(source, destination, *args, **kwargs):
            if Path(source) == self.project / INSTALL_PATHS[1]:
                raise OSError("simulated backup move failure")
            return real_replace(source, destination, *args, **kwargs)

        with mock.patch.object(installer.os, "replace", side_effect=fail_backup):
            with self.assertRaises(installer.InstallError):
                self.install(replace=True)
        self.assert_previous(previous)

    def test_rollback_failure_keeps_previous_content_in_reported_backup(self):
        previous = self.make_changed_install()
        real_replace = os.replace

        def fail_promotion_and_one_restore(source, destination, *args, **kwargs):
            source, destination = Path(source), Path(destination)
            if destination == self.project / INSTALL_PATHS[3] and "backups" not in source.parts:
                raise OSError("simulated promotion failure")
            if destination == self.project / INSTALL_PATHS[0] and "backups" in source.parts:
                raise OSError("simulated restoration failure")
            return real_replace(source, destination, *args, **kwargs)

        with mock.patch.object(
            installer.os, "replace", side_effect=fail_promotion_and_one_restore
        ):
            with self.assertRaises(installer.InstallError) as caught:
                self.install(replace=True)
        runs = self.backup_runs()
        self.assertEqual(len(runs), 1)
        self.assertEqual(snapshot(runs[0] / INSTALL_PATHS[0]), previous[INSTALL_PATHS[0]])
        self.assertIn(str(runs[0]), str(caught.exception))
        for relative in INSTALL_PATHS[1:]:
            self.assertEqual(snapshot(self.project / relative), previous[relative])

    def test_cli_defaults_to_all_and_current_working_directory(self):
        self.project.mkdir()
        result = self.cli(cwd=self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        for relative in INSTALL_PATHS:
            self.assertTrue((self.project / relative).exists())
            self.assertIn(str(self.project / relative), result.stdout)
        self.assertFalse((self.repo / ".agents").exists())

    def test_cli_accepts_paths_with_spaces_and_shell_metacharacters(self):
        base = self.root / "project with spaces & $HOME"
        result = self.cli("--target", "codex", "--project-dir", base)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_package(base / INSTALL_PATHS[0])
        self.assertFalse((self.root / "project").exists())

    def test_cli_conflict_returns_nonzero_and_simple_error_without_partial_install(self):
        path = write(self.project / INSTALL_PATHS[3], "Existing agent")
        before = snapshot(self.project)
        result = self.cli("--project-dir", self.project)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(path), result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(snapshot(self.project), before)

    def test_cli_dry_run_and_replace_flags_are_wired(self):
        path = write(self.project / INSTALL_PATHS[0] / "SKILL.md", "Existing skill")
        before = snapshot(self.project)
        result = self.cli(
            "--target", "codex", "--project-dir", self.project, "--dry-run", "--replace"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(path.parent), result.stdout)
        self.assertEqual(snapshot(self.project), before)
        result = self.cli("--target", "codex", "--project-dir", self.project, "--replace")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_package(path.parent)
        self.assertEqual(len(self.backup_runs()), 1)

    def test_cli_rejects_invalid_options(self):
        for args in (
            ("--target", "unknown"),
            ("--scope", "unknown"),
            ("--scope", "user", "--project-dir", str(self.project)),
        ):
            with self.subTest(args=args):
                result = self.cli(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse(self.project.exists())


if __name__ == "__main__":
    unittest.main()
