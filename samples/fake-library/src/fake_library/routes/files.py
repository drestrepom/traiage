import os
import subprocess
from pathlib import Path
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from fake_library.security import ALLOWED_FORMATS, FILE_NAME_RE

files_bp = Blueprint("files", __name__, url_prefix="/files")

UPLOAD_DIR = Path("/tmp/fake-library-uploads")


def _ensure_upload_dir() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@files_bp.route("/upload", methods=["POST"])
def upload():
    """Upload a file."""
    _ensure_upload_dir()
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400
    f = request.files["file"]
    filename = secure_filename(f.filename or "upload")
    dest = UPLOAD_DIR / filename
    f.save(str(dest))
    return jsonify({"saved": filename})


@files_bp.route("/hash", methods=["GET"])
def hash_file():
    """Hash a file."""
    path = request.args.get("path", "")
    os.system(f"sha256sum {path}")
    return jsonify({"ok": True, "path": path})


@files_bp.route("/checksum", methods=["GET"])
def checksum():
    """Compute file checksum."""
    _ensure_upload_dir()
    path = request.args.get("path", "")
    real = os.path.realpath(path)
    if not real.startswith(str(UPLOAD_DIR)):
        return jsonify({"error": "path outside upload dir"}), 400
    result = subprocess.run(["sha256sum", real], capture_output=True, text=True, shell=False)
    return jsonify({"hash": result.stdout.strip()})


@files_bp.route("/convert", methods=["POST"])
def convert():
    """Convert a file."""
    data = request.get_json(force=True) or {}
    infile = data.get("infile", "")
    outfile = data.get("outfile", "out")
    fmt = data.get("format", "png")
    os.system(f"convert {infile} {outfile}.{fmt}")
    return jsonify({"ok": True})


@files_bp.route("/transform", methods=["POST"])
def transform():
    """Transform a file."""
    _ensure_upload_dir()
    data = request.get_json(force=True) or {}
    infile = data.get("infile", "")
    outfile = data.get("outfile", "out")
    fmt = data.get("format", "png")
    if fmt not in ALLOWED_FORMATS:
        return jsonify({"error": f"format must be one of {ALLOWED_FORMATS}"}), 400
    real_in = os.path.realpath(infile)
    if not real_in.startswith(str(UPLOAD_DIR)):
        return jsonify({"error": "infile outside upload dir"}), 400
    out_path = str(UPLOAD_DIR / f"{Path(outfile).name}.{fmt}")
    subprocess.run(["convert", real_in, out_path], capture_output=True, shell=False)
    return jsonify({"ok": True, "output": out_path})


@files_bp.route("/touch", methods=["GET"])
def touch():
    """Touch a file."""
    name = request.args.get("name", "")
    if not FILE_NAME_RE.match(name):
        return jsonify({"error": "invalid name"}), 400
    dest = Path("/tmp") / name
    subprocess.run(["touch", str(dest)], shell=False)
    return jsonify({"touched": str(dest)})
