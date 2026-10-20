"""Preserve the user-accepted v0.3 release without invoking Unreal or Blender."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil


PROJECT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "AnomalyLab_RC_20261011T225958"
DEFAULT_ARCHIVE = PROJECT / "Saved/Releases/v0.3_ScenePolish_Accepted_20261011"


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def files_in(folder: Path):
    for path in sorted(folder.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            yield path


def verify(archive: Path) -> dict:
    manifest = json.loads((archive / "release_manifest.json").read_text(encoding="utf-8"))
    failures = []
    total_bytes = 0
    for item in manifest["files"]:
        file = archive / item["path"]
        if not file.is_file() or file.stat().st_size != item["bytes"] or digest(file) != item["sha256"]:
            failures.append(item["path"])
        total_bytes += item["bytes"]
    result = {
        "status": "PASS" if not failures else "FAIL",
        "verified_at": datetime.now().astimezone().isoformat(),
        "files_checked": len(manifest["files"]),
        "bytes_checked": total_bytes,
        "failures": failures,
        "scope": "Archived files against SHA-256 manifest; no engine or gameplay tests rerun.",
    }
    write_json(archive / "verification_report.json", result)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    if failures:
        raise RuntimeError("Archive verification failed")
    return result


def create_archive() -> None:
    archive = DEFAULT_ARCHIVE
    if archive.exists():
        raise FileExistsError(f"Preserving existing archive; use --verify instead: {archive}")
    source_manifest = PROJECT / "Saved/V03/package_source_20261011T225958.json"
    expected = json.loads(source_manifest.read_text(encoding="utf-8-sig"))
    mismatches = [name for name, sha in expected.items()
                  if not (PROJECT / name).is_file() or digest(PROJECT / name) != sha]
    if mismatches:
        raise RuntimeError(f"Project differs from accepted package source manifest: {mismatches}")
    package = PROJECT / "Builds/v0.3" / PACKAGE_NAME
    game_hashes = {p.relative_to(package).as_posix(): digest(p) for p in files_in(package / "Windows")}
    archive.mkdir(parents=True)
    records = []

    def copy_file(source: Path, relative: Path) -> None:
        target = archive / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        sha = digest(source)
        shutil.copy2(source, target)
        records.append({"path": relative.as_posix(), "bytes": source.stat().st_size,
                        "sha256": sha, "original": str(source)})

    def copy_tree(source: Path, relative: Path) -> None:
        for file in files_in(source):
            copy_file(file, relative / file.relative_to(source))
        print(f"Copied {relative}", flush=True)

    for name in ("Content", "Source", "Config", "Scripts", "Docs", "LowPolyLabPrototype",
                 "LowPolyCharacterPrototype", "T11EAssets", "GameAudio", "MenuAudio", "ScenePolishAssets"):
        copy_tree(PROJECT / name, Path("Project") / name)
    for file in sorted(PROJECT.iterdir()):
        if file.is_file() and file.suffix.lower() in (".uproject", ".md"):
            copy_file(file, Path("Project") / file.name)
    copy_tree(package, Path("Package") / PACKAGE_NAME)
    for folder in ("ScenePolish", "V03"):
        for file in sorted((PROJECT / "Saved" / folder).iterdir()):
            if file.is_file():
                copy_file(file, Path("Evidence/Saved") / folder / file.name)
    copy_tree(PROJECT / "Saved/ScenePolish/Views_20261011T225916",
              Path("Evidence/Saved/ScenePolish/Views_20261011T225916"))
    copy_tree(PROJECT / "Saved/V03/Runs", Path("Evidence/Saved/V03/Runs"))
    copy_tree(PROJECT / "Saved/CppMigration/20260929T083920372566Z",
              Path("Evidence/Saved/CppMigration/20260929T083920372566Z"))
    for name, sha in expected.items():
        if digest(archive / "Project" / name) != sha:
            raise RuntimeError(f"Source changed during archive: {name}")
    for name, sha in game_hashes.items():
        if digest(package / name) != sha or digest(archive / "Package" / PACKAGE_NAME / name) != sha:
            raise RuntimeError(f"Game package changed during archive: {name}")
    readme = archive / "README_RESTORE.md"
    readme.write_text("""# v0.3 场景细节版已验收归档

用户于 2026-10-11 确认最新场景细节版测试完成并要求保留。版本 RC_20261011T225958。

- `Project/`：完整工程源码、配置、Content 资产、脚本、文档及模型/音频制作源。
- `Package/AnomalyLab_RC_20261011T225958/Windows/`：完整独立程序；双击 AnomalyLab.exe，无需测试参数。复制交付时须带整个 Windows 目录。
- `Evidence/Saved/`：原始自动报告、构建日志、实景截图与用户总体人工确认；历史失败日志仍保留，不代表最终失败。
- `release_manifest.json`：所有归档文件的 SHA-256 与大小；不包含清单自身和可重写的 verification_report.json。
- `verification_report.json`：逐文件归档校验结果，不是新一轮玩法测试。

恢复工程时将整个 Project 目录复制到一个新工作目录，使用 UE 5.8 打开 uproject；不必覆盖当前工程。Editor Binaries、Intermediate 与 DerivedDataCache 未归档，需按 Scripts/cpp_migration.py 和 Docs/CPP_MIGRATION.md 重新生成；中文路径的 MSVC PCH 仍需使用 ASCII 构建副本。

复核命令：`python Scripts/archive_v03_accepted.py --verify <本归档目录>`。归档中的 Project/Scripts 也保存了该脚本。

工作报告：`Project/Docs/V03_WORK_REPORT_2026-10-11.md`。此归档为同盘保留副本，不是异地备份；后续开发在工作工程进行，保留归档原件。
""", encoding="utf-8")
    records.append({"path": "README_RESTORE.md", "bytes": readme.stat().st_size,
                    "sha256": digest(readme), "original": None})
    write_json(archive / "release_manifest.json", {
        "release": PACKAGE_NAME,
        "status": "USER_ACCEPTED_ARCHIVED",
        "created_at": datetime.now().astimezone().isoformat(),
        "original_project": str(PROJECT),
        "user_confirmation": "测试完成，你可以保留一下这一版然后记录工作报告了",
        "acceptance_scope": "User overall manual testing completion; no itemized human measurements supplied.",
        "package_source_files_verified": len(expected),
        "unchanged_windows_package_files": len(game_hashes),
        "excluded": ["Intermediate", "DerivedDataCache", "Editor Binaries", "nested historical checkpoints"],
        "files": records,
    })
    verify(archive)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path, help="Verify an existing archive; never overwrite its files.")
    args = parser.parse_args()
    if args.verify:
        verify(args.verify.resolve())
    else:
        create_archive()
