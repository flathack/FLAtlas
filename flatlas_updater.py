from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from pathlib import Path
from queue import Empty, Queue
from urllib import request as urlrequest
import ssl


CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
DETACHED_PROCESS = getattr(subprocess, "DETACHED_PROCESS", 0)


def _wait_for_pid(pid: int, timeout_seconds: float) -> None:
    if pid <= 0:
        return
    deadline = time.time() + max(1.0, float(timeout_seconds))
    while time.time() < deadline:
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {int(pid)}"],
                capture_output=True,
                text=True,
                creationflags=CREATE_NO_WINDOW,
                timeout=5,
            )
            output = (result.stdout or "") + "\n" + (result.stderr or "")
            if f" {int(pid)} " not in output and f",{int(pid)}" not in output:
                return
        except Exception:
            pass
        time.sleep(0.4)


def _resolve_source_root(extract_root: Path) -> Path:
    entries = [p for p in extract_root.iterdir()]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return extract_root


def _downloaded_file_looks_like_html(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            head = fh.read(512).lstrip()
    except Exception:
        return False
    lowered = head.lower()
    return lowered.startswith(b"<!doctype html") or lowered.startswith(b"<html") or lowered.startswith(b"<?xml")


def _download_url_to_file(url: str, dest: Path, *, progress_cb=None, chunk_size: int = 1024 * 256) -> None:
    req = urlrequest.Request(url, headers={"User-Agent": "FLAtlas-Updater"})
    try:
        resp = urlrequest.urlopen(req, timeout=120.0)
    except Exception:
        insecure_ctx = ssl._create_unverified_context()
        resp = urlrequest.urlopen(req, timeout=120.0, context=insecure_ctx)
    with resp, dest.open("wb") as fh:
        total = -1
        try:
            total = int(resp.headers.get("Content-Length", "") or "-1")
        except Exception:
            total = -1
        written = 0
        while True:
            chunk = resp.read(max(4096, int(chunk_size)))
            if not chunk:
                break
            fh.write(chunk)
            written += len(chunk)
            if callable(progress_cb):
                progress_cb(written, total)
        if callable(progress_cb):
            progress_cb(written, total)


def _extract_zip_with_progress(archive_path: Path, extract_root: Path, *, progress_cb=None) -> None:
    with zipfile.ZipFile(archive_path, "r") as zf:
        members = [m for m in zf.infolist() if not m.is_dir()]
        total = max(1, len(members))
        for idx, member in enumerate(members, start=1):
            zf.extract(member, extract_root)
            if callable(progress_cb):
                progress_cb(idx, total)


def _iter_source_files(source_root: Path) -> list[Path]:
    return [p for p in source_root.rglob("*") if p.is_file()]


def _copy_tree_contents(src: Path, dst: Path, *, skip_names: set[str] | None = None, progress_cb=None) -> Path | None:
    skip = {str(x).strip().lower() for x in (skip_names or set()) if str(x).strip()}
    dst.mkdir(parents=True, exist_ok=True)
    files = _iter_source_files(src)
    total = max(1, len(files))
    pending_updater: Path | None = None
    for idx, child in enumerate(files, start=1):
        rel = child.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if child.name.lower() in skip:
            pending_name = f"{child.name}.new"
            pending_updater = dst / pending_name
            shutil.copy2(child, pending_updater)
        else:
            shutil.copy2(child, target)
        if callable(progress_cb):
            progress_cb(idx, total, str(rel).replace("\\", "/"))
    return pending_updater


def _schedule_self_replace(current_updater: Path, pending_updater: Path) -> None:
    if not current_updater.exists() or not pending_updater.exists():
        return
    cmd_script = (
        "@echo off\r\n"
        "setlocal\r\n"
        "ping 127.0.0.1 -n 3 >nul\r\n"
        f"move /Y \"{pending_updater}\" \"{current_updater}\" >nul 2>&1\r\n"
        "del \"%~f0\" >nul 2>&1\r\n"
    )
    script_path = Path(tempfile.gettempdir()) / f"flatlas_updater_replace_{int(time.time())}.cmd"
    script_path.write_text(cmd_script, encoding="utf-8")
    subprocess.Popen(
        ["cmd.exe", "/c", str(script_path)],
        creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
        close_fds=True,
    )


def _launch_exe(exe_path: Path, workdir: Path) -> bool:
    if not exe_path.exists():
        return False
    try:
        subprocess.Popen(
            [str(exe_path)],
            cwd=str(workdir),
            creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
            close_fds=True,
        )
        return True
    except Exception:
        return False


def _cleanup(paths: list[Path]) -> None:
    for path in paths:
        try:
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            elif path.exists():
                path.unlink()
        except Exception:
            pass


def _build_updater_args(
    *,
    mode: str,
    wait_pid: int,
    install_root: str,
    exe_path: str,
    version: str = "",
    download_url: str = "",
    asset_name: str = "",
    source_zip: str = "",
) -> list[str]:
    args = [
        "--mode",
        str(mode),
        "--wait-pid",
        str(int(wait_pid)),
        "--install-root",
        str(install_root),
        "--exe-path",
        str(exe_path),
    ]
    if version:
        args.extend(["--version", str(version)])
    if download_url:
        args.extend(["--download-url", str(download_url)])
    if asset_name:
        args.extend(["--asset-name", str(asset_name)])
    if source_zip:
        args.extend(["--source-zip", str(source_zip)])
    return args


class UpdaterRuntime:
    def __init__(
        self,
        *,
        mode: str,
        wait_pid: int,
        install_root: Path,
        exe_path: Path,
        version: str,
        download_url: str,
        asset_name: str,
        source_zip: Path | None,
        current_updater_path: Path,
        emit,
    ):
        self.mode = mode
        self.wait_pid = int(wait_pid)
        self.install_root = install_root
        self.exe_path = exe_path
        self.version = str(version or "").strip() or "update"
        self.download_url = str(download_url or "").strip()
        self.asset_name = str(asset_name or "").strip() or "FLAtlas-update.zip"
        self.source_zip = source_zip
        self.current_updater_path = current_updater_path
        self.emit = emit

    def run(self) -> int:
        stamp = str(int(time.time()))
        archive_path = Path(tempfile.gettempdir()) / f"flatlas_update_{stamp}_{Path(self.asset_name).name}"
        extract_root = Path(tempfile.gettempdir()) / f"flatlas_update_extract_{stamp}"
        try:
            self.emit("status", "Waiting for FL Atlas to close...")
            self.emit("progress", 4)
            _wait_for_pid(self.wait_pid, 90.0)
            time.sleep(0.4)

            self.emit("status", f"Downloading {self.version}...")
            self.emit("progress", 8)
            if self.mode == "local-zip":
                if self.source_zip is None or not self.source_zip.exists():
                    raise RuntimeError("Local test ZIP file was not found.")
                shutil.copy2(self.source_zip, archive_path)
                self.emit("progress", 28)
            else:
                if not self.download_url:
                    raise RuntimeError("Update URL is missing.")

                def _dl_progress(written: int, total: int) -> None:
                    if total and total > 0:
                        pct = int(round((max(0, int(written)) / max(1, int(total))) * 40.0))
                    else:
                        pct = 20
                    self.emit("progress", min(48, 8 + pct))

                _download_url_to_file(self.download_url, archive_path, progress_cb=_dl_progress)
            if (not zipfile.is_zipfile(archive_path)) or _downloaded_file_looks_like_html(archive_path):
                raise RuntimeError("Downloaded update package is not a valid FL Atlas ZIP archive.")

            self.emit("status", "Extracting update package...")
            extract_root.mkdir(parents=True, exist_ok=True)

            def _extract_progress(done: int, total: int) -> None:
                pct = int(round((max(0, int(done)) / max(1, int(total))) * 22.0))
                self.emit("progress", min(72, 50 + pct))

            _extract_zip_with_progress(archive_path, extract_root, progress_cb=_extract_progress)

            self.emit("status", "Applying update files...")
            source_root = _resolve_source_root(extract_root)

            def _copy_progress(done: int, total: int, rel: str) -> None:
                pct = int(round((max(0, int(done)) / max(1, int(total))) * 24.0))
                self.emit("status", f"Updating {rel}...")
                self.emit("progress", min(96, 72 + pct))

            pending_updater = _copy_tree_contents(
                source_root,
                self.install_root,
                skip_names={"FLAtlasUpdater.exe"},
                progress_cb=_copy_progress,
            )
            if pending_updater is not None:
                _schedule_self_replace(self.current_updater_path, pending_updater)

            self.emit("status", "Restarting FL Atlas...")
            self.emit("progress", 100)
            time.sleep(0.4)
            if not _launch_exe(self.exe_path, self.install_root):
                raise RuntimeError("FL Atlas was updated, but the application could not be restarted automatically.")
            self.emit("done", "Update completed successfully. FL Atlas is restarting...")
            return 0
        finally:
            _cleanup([archive_path, extract_root])


def _run_gui(args) -> int:
    import tkinter as tk
    from tkinter import ttk

    queue: Queue[tuple[str, object]] = Queue()

    def _emit(kind: str, payload) -> None:
        queue.put((kind, payload))

    root = tk.Tk()
    root.title("FL Atlas Updater")
    root.geometry("520x180")
    root.resizable(False, False)

    frame = ttk.Frame(root, padding=16)
    frame.pack(fill="both", expand=True)

    title_lbl = ttk.Label(frame, text="FL Atlas Updater", font=("Segoe UI", 13, "bold"))
    title_lbl.pack(anchor="w")

    subtitle = "Testing local ZIP update..." if args.mode == "local-zip" else f"Updating to {args.version or 'latest'}..."
    subtitle_lbl = ttk.Label(frame, text=subtitle)
    subtitle_lbl.pack(anchor="w", pady=(6, 10))

    status_var = tk.StringVar(value="Preparing updater...")
    status_lbl = ttk.Label(frame, textvariable=status_var, wraplength=470)
    status_lbl.pack(anchor="w", fill="x")

    progress = ttk.Progressbar(frame, orient="horizontal", mode="determinate", maximum=100)
    progress.pack(fill="x", pady=(14, 8))

    close_btn = ttk.Button(frame, text="Close")
    close_btn.state(["disabled"])
    close_btn.pack(anchor="e")

    state = {"running": True, "exit_code": 0}

    def _on_close():
        if state["running"]:
            return
        root.destroy()

    def _finish(exit_code: int):
        state["running"] = False
        state["exit_code"] = int(exit_code)
        close_btn.state(["!disabled"])
        close_btn.configure(command=_on_close)
        root.after(900 if exit_code == 0 else 0, _on_close)

    def _poll_queue():
        try:
            while True:
                kind, payload = queue.get_nowait()
                if kind == "status":
                    status_var.set(str(payload))
                elif kind == "progress":
                    progress["value"] = max(0, min(int(payload), 100))
                elif kind == "done":
                    status_var.set(str(payload))
                    progress["value"] = 100
                    _finish(0)
                elif kind == "error":
                    status_var.set(str(payload))
                    _finish(1)
        except Empty:
            pass
        if state["running"]:
            root.after(120, _poll_queue)

    runtime = UpdaterRuntime(
        mode=args.mode,
        wait_pid=int(args.wait_pid),
        install_root=Path(args.install_root).resolve(),
        exe_path=Path(args.exe_path).resolve(),
        version=str(args.version or "").strip(),
        download_url=str(args.download_url or "").strip(),
        asset_name=str(args.asset_name or "").strip(),
        source_zip=Path(args.source_zip).resolve() if args.source_zip else None,
        current_updater_path=Path(sys.executable).resolve() if getattr(sys, "frozen", False) else Path(__file__).resolve(),
        emit=_emit,
    )

    def _worker():
        try:
            exit_code = runtime.run()
            if exit_code != 0:
                _emit("error", "Update failed.")
        except Exception as exc:
            _emit("error", f"Update failed.\n\n{exc}")

    threading.Thread(target=_worker, daemon=True).start()
    root.protocol("WM_DELETE_WINDOW", _on_close)
    root.after(120, _poll_queue)
    root.mainloop()
    return int(state["exit_code"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("download-zip", "local-zip"), required=True)
    parser.add_argument("--wait-pid", type=int, default=0)
    parser.add_argument("--install-root", required=True)
    parser.add_argument("--exe-path", required=True)
    parser.add_argument("--version", default="")
    parser.add_argument("--download-url", default="")
    parser.add_argument("--asset-name", default="")
    parser.add_argument("--source-zip", default="")
    args = parser.parse_args(argv)
    return _run_gui(args)


if __name__ == "__main__":
    sys.exit(main())
