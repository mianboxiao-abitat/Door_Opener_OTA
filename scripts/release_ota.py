#!/usr/bin/env python3
"""OTA release helper.

Usage example:
  python3 scripts/release_ota.py --Op --notes "启用振动传感器" --push
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

MAX_FW_SIZE = 0xE0020

DEVICE_CONFIG = {
    "op": {
        "flag": "--Op",
        "name": "Door Opener",
        "prefix": "Door_Opener_",
        "target_dir": "Door_Opener_OTA",
        "incoming_dir": "incoming/Door_Opener_OTA",
    },
    "lo": {
        "flag": "--Lo",
        "name": "Door Lock",
        "prefix": "Door_Lock_",
        "target_dir": "Door_Lock_OTA",
        "incoming_dir": "incoming/Door_Lock_OTA",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "自动 OTA 发布：选择设备 + notes，自动重命名 bin、生成 manifest，"
            "并可自动 git 提交推送。"
        )
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--Op", action="store_true", help="发布 Door Opener 固件")
    group.add_argument("--Lo", action="store_true", help="发布 Door Lock 固件")
    parser.add_argument("--notes", required=True, help="manifest notes 字段内容")
    parser.add_argument(
        "--bin",
        dest="bin_path",
        default=None,
        help="可选：手动指定 bin 文件路径；不指定则从 incoming/<device> 读取",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="自动执行 git add/commit/push 到 origin/main",
    )
    parser.add_argument(
        "--allow-empty-notes",
        action="store_true",
        help="允许 notes 为空字符串",
    )
    return parser.parse_args()


def fail(msg: str, exit_code: int = 1) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)
    raise SystemExit(exit_code)


def run_cmd(cmd: list[str], cwd: Path) -> None:
    completed = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        detail = stderr or stdout or "unknown error"
        fail(f"命令失败: {' '.join(cmd)}\n{detail}")


def pick_device(args: argparse.Namespace) -> dict:
    if args.Op:
        return DEVICE_CONFIG["op"]
    return DEVICE_CONFIG["lo"]


def parse_and_bump_version(current: str, prefix: str) -> str:
    pattern = rf"^{re.escape(prefix)}(\d+)\.(\d+)\.(\d+)$"
    match = re.match(pattern, current)
    if not match:
        fail(f"manifest.version 格式非法: {current}，期望前缀 {prefix}X.Y.Z")
    major, minor, patch = map(int, match.groups())
    return f"{prefix}{major}.{minor}.{patch + 1}"


def compute_sha256(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_source_bin(repo_root: Path, device_cfg: dict, explicit_path: str | None) -> Path:
    if explicit_path:
        src = Path(explicit_path)
        if not src.is_absolute():
            src = (repo_root / src).resolve()
        if not src.exists() or not src.is_file():
            fail(f"--bin 指定文件不存在: {src}")
        if src.suffix.lower() != ".bin":
            fail(f"--bin 必须是 .bin 文件: {src}")
        return src

    incoming_dir = repo_root / device_cfg["incoming_dir"]
    if not incoming_dir.exists():
        fail(f"未找到投放目录: {incoming_dir}")
    bins = sorted(p for p in incoming_dir.iterdir() if p.is_file() and p.suffix.lower() == ".bin")
    if not bins:
        fail(f"{incoming_dir} 下没有 .bin 文件")
    if len(bins) > 1:
        names = "\n".join(f"- {p.name}" for p in bins)
        fail(
            f"{incoming_dir} 下存在多个 .bin，请只保留一个或使用 --bin 指定:\n{names}"
        )
    return bins[0].resolve()


def purge_old_bins(target_dir: Path, keep_name: str) -> list[Path]:
    removed: list[Path] = []
    for fw in sorted(target_dir.iterdir()):
        if not fw.is_file():
            continue
        if fw.suffix.lower() != ".bin":
            continue
        if fw.name == keep_name:
            fail(f"目标固件文件已存在: {fw}")
        fw.unlink()
        removed.append(fw)
    return removed


def main() -> None:
    args = parse_args()
    notes = args.notes.strip()
    if not notes and not args.allow_empty_notes:
        fail("notes 不能为空；如需空字符串请添加 --allow-empty-notes")

    repo_root = Path(__file__).resolve().parent.parent
    device_cfg = pick_device(args)

    target_dir = repo_root / device_cfg["target_dir"]
    manifest_path = target_dir / "manifest.json"
    if not manifest_path.exists():
        fail(f"manifest 不存在: {manifest_path}")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"manifest JSON 解析失败: {exc}")

    current_version = str(manifest.get("version", "")).strip()
    next_version = parse_and_bump_version(current_version, device_cfg["prefix"])
    target_name = f"firmware_{next_version}.bin"
    target_file = target_dir / target_name

    source_file = resolve_source_bin(repo_root, device_cfg, args.bin_path)
    if target_dir.resolve() in source_file.resolve().parents:
        fail(
            "源 bin 文件不能放在发布目录中。请使用 incoming 目录或通过 --bin 指向其他路径。"
        )

    source_size = source_file.stat().st_size
    if source_size > MAX_FW_SIZE:
        fail(
            f"固件过大: {source_size} bytes，超过上限 {MAX_FW_SIZE} bytes (0x{MAX_FW_SIZE:X})"
        )

    removed_bins = purge_old_bins(target_dir, target_name)
    shutil.move(str(source_file), str(target_file))
    size = target_file.stat().st_size
    sha256 = compute_sha256(target_file)

    new_manifest = {
        "version": next_version,
        "file": target_name,
        "size": size,
        "sha256": sha256,
        "notes": notes,
    }
    manifest_path.write_text(
        json.dumps(new_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("[OK] 发布文件已生成")
    print(f"  device : {device_cfg['name']}")
    print(f"  source : {source_file}")
    print(f"  target : {target_file}")
    print(f"  version: {current_version} -> {next_version}")
    print(f"  size   : {size}")
    print(f"  sha256 : {sha256}")
    print(f"  notes  : {notes}")
    print(f"  purge  : removed {len(removed_bins)} old bin file(s)")

    if not args.push:
        print("\n[INFO] 未启用 --push，仅完成文件与 manifest 更新。")
        print(
            "[INFO] 如需自动推送，请执行: "
            f"python3 scripts/release_ota.py {device_cfg['flag']} --notes \"...\" --push"
        )
        return

    commit_message = f"OTA {next_version}"
    run_cmd(["git", "add", "-A", str(target_dir)], cwd=repo_root)
    run_cmd(["git", "commit", "-m", commit_message], cwd=repo_root)
    run_cmd(["git", "push", "origin", "main"], cwd=repo_root)
    print("\n[OK] 已完成 git add/commit/push")


if __name__ == "__main__":
    main()
