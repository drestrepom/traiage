import requests as http_requests
from flask import Blueprint, request, jsonify
from fake_library.security import GITHUB_USER_RE, URL_CATALOG, validate_url

integrations_bp = Blueprint("integrations", __name__, url_prefix="/integrations")


@integrations_bp.route("/fetch", methods=["GET"])
def fetch():
    """Fetch a URL."""
    url = request.args.get("url", "")
    resp = http_requests.get(url, timeout=5)
    return jsonify({"status": resp.status_code, "body": resp.text[:500]})


@integrations_bp.route("/proxy", methods=["GET"])
def proxy():
    """Proxy a URL."""
    url = request.args.get("url", "")
    try:
        validated = validate_url(url)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    resp = http_requests.get(validated, timeout=5, allow_redirects=False)
    return jsonify({"status": resp.status_code, "body": resp.text[:500]})


@integrations_bp.route("/github_user", methods=["GET"])
def github_user():
    """Fetch GitHub user profile."""
    user = request.args.get("user", "")
    if user.startswith("http"):
        url = user
    else:
        url = f"https://api.github.com/users/{user}"
    resp = http_requests.get(url, timeout=5)
    return jsonify({"status": resp.status_code, "body": resp.text[:500]})


@integrations_bp.route("/github_profile", methods=["GET"])
def github_profile():
    """Fetch GitHub user profile."""
    user = request.args.get("user", "")
    if not GITHUB_USER_RE.match(user):
        return jsonify({"error": "invalid GitHub username"}), 400
    url = f"https://api.github.com/users/{user}"
    resp = http_requests.get(url, timeout=5, allow_redirects=False)
    return jsonify({"status": resp.status_code, "body": resp.text[:500]})


@integrations_bp.route("/catalog_fetch", methods=["GET"])
def catalog_fetch():
    """Fetch from catalog."""
    key = request.args.get("key", "")
    url = URL_CATALOG.get(key)
    if not url:
        return jsonify({"error": "unknown catalog key"}), 404
    resp = http_requests.get(url, timeout=5, allow_redirects=False)
    return jsonify({"status": resp.status_code, "body": resp.text[:500]})
