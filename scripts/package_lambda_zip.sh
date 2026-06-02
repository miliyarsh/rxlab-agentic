#!/usr/bin/env bash
# Build a Lambda deployment zip: service/ package + pydantic (boto3 is in the runtime).
set -euo pipefail

OUT="${1:?usage: package_lambda_zip.sh OUTPUT.zip}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD="${ROOT}/.build/lambda-package"
STAGING="${BUILD}/staging"

rm -rf "${STAGING}"
mkdir -p "${STAGING}"

python3 -m pip install --quiet --disable-pip-version-check \
  --target "${STAGING}" \
  "pydantic>=2.6,<3"

cp -r "${ROOT}/service" "${STAGING}/service"
rm -rf "${STAGING}/service/tests"

mkdir -p "$(dirname "${OUT}")"
rm -f "${OUT}"

if command -v zip >/dev/null 2>&1; then
  (cd "${STAGING}" && zip -qr "${OUT}" . -x "*.pyc" -x "*__pycache__*")
else
  python3 - <<PY
import pathlib, zipfile
out = pathlib.Path(r"${OUT}")
staging = pathlib.Path(r"${STAGING}")
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    for path in staging.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts and not path.name.endswith(".pyc"):
            zf.write(path, path.relative_to(staging).as_posix())
PY
fi

echo "Packaged ${OUT}"
