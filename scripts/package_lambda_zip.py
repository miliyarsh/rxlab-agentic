#!/usr/bin/env python3
"""Build a Lambda zip: service/ package + pydantic (boto3 is in the runtime)."""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path


def rmtree_safe(path: Path, retries: int = 5) -> None:
    if not path.exists():
        return
    for attempt in range(retries):
        try:
            shutil.rmtree(path)
            return
        except OSError:
            if attempt == retries - 1:
                raise
            time.sleep(0.25 * (attempt + 1))


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: package_lambda_zip.py OUTPUT.zip", file=sys.stderr)
        return 1

    out = Path(sys.argv[1]).resolve()
    root = Path(__file__).resolve().parent.parent
    # One staging dir per output zip so parallel Terraform module builds do not race.
    staging = root / ".build" / "lambda-package" / out.stem

    rmtree_safe(staging)
    staging.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--quiet",
            "--disable-pip-version-check",
            "--target",
            str(staging),
            "--platform",
            "manylinux2014_x86_64",
            "--implementation",
            "cp",
            "--python-version",
            "3.11",
            "--only-binary",
            ":all:",
            "pydantic>=2.6,<3",
        ],
        check=True,
    )

    service_src = root / "service"
    service_dst = staging / "service"
    shutil.copytree(
        service_src,
        service_dst,
        ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc"),
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in staging.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(staging).as_posix())

    rmtree_safe(staging)

    print(f"Packaged {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
