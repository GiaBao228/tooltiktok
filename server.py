"""
TikDown - Backend Flask Server
Xử lý toàn bộ logic: gọi API, lấy link CDN, proxy stream video xuống client
"""

import os
import re
import requests  # type: ignore
from flask import Flask, request, jsonify, Response, send_from_directory  # type: ignore

# ─── Cấu hình ────────────────────────────────────────────────────────────────
TIKWM_API   = "https://www.tikwm.com/api/"
HOST        = "0.0.0.0"
PORT        = 5000
DEBUG_MODE  = True

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ─── App Flask ────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=".", static_url_path="")


# ─── Helpers ──────────────────────────────────────────────────────────────────
def sanitize_filename(name: str) -> str:
    """Loại bỏ ký tự không hợp lệ trong tên file."""
    if not name or not isinstance(name, str):
        return "tiktok_video"
        
    # Loại bỏ ký tự đặc biệt
    clean_name = re.sub(r'[\\/:*?"<>|]', '_', name)
    clean_str = str(clean_name.strip())
    
    # Sử dụng vòng lặp thay vì slicing để tránh lỗi linter Pyre2 (không cho phép slice)
    res_list = []
    max_len = len(clean_str)
    if max_len > 80:
        max_len = 80
        
    for i in range(max_len):
        res_list.append(clean_str[i])
        
    return "".join(res_list)


def validate_tiktok_url(url: str) -> bool:
    """Kiểm tra URL có phải TikTok không."""
    patterns = [
        r"tiktok\.com/@[\w.]+/video/\d+",
        r"vm\.tiktok\.com/\w+",
        r"vt\.tiktok\.com/\w+",
    ]
    return any(re.search(p, url) for p in patterns)


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Phục vụ giao diện web (index.html)."""
    return send_from_directory(".", "index.html")


@app.route("/api/info", methods=["GET"])
def get_video_info():
    """
    Lấy thông tin video TikTok (không watermark).
    Query param: ?url=<tiktok_url>
    """
    tiktok_url = request.args.get("url", "").strip()

    if not tiktok_url:
        return jsonify({"ok": False, "message": "Thiếu tham số 'url'"}), 400

    if not validate_tiktok_url(tiktok_url):
        return jsonify({"ok": False, "message": "URL không hợp lệ. Vui lòng dán đúng link TikTok"}), 400

    try:
        resp = requests.get(TIKWM_API, params={"url": tiktok_url}, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        return jsonify({"ok": False, "message": "API timeout. Vui lòng thử lại sau"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"ok": False, "message": f"Lỗi kết nối API: {str(e)}"}), 502

    if data.get("code") != 0 or not data.get("data"):
        msg = data.get("msg", "Không thể phân tích video")
        return jsonify({"ok": False, "message": msg}), 422

    v = data["data"]
    result = {
        "ok": True,
        "id":         v.get("id"),
        "title":      v.get("title", ""),
        "cover":      v.get("cover", ""),
        "duration":   v.get("duration", 0),
        "play_count": v.get("play_count", 0),
        "like_count":  v.get("digg_count", 0),
        "comment_count": v.get("comment_count", 0),
        "share_count": v.get("share_count", 0),
        "author": {
            "nickname": v.get("author", {}).get("nickname", ""),
            "avatar":   v.get("author", {}).get("avatar", ""),
        },
        # Link CDN không watermark
        "play_url":    v.get("play"),
        "hd_play_url": v.get("hdplay"), # Thêm Full HD
        # Nhạc nền
        "music_url":   v.get("music"),
        "music_title": v.get("music_info", {}).get("title", ""),
    }
    return jsonify(result)


@app.route("/api/download", methods=["GET"])
def download_video():
    """
    Proxy tải video từ CDN TikTok về máy client.
    Server làm trung gian để tránh bị chặn CORS.
    Query params: ?url=<cdn_url>&filename=<tên file>
    """
    cdn_url  = request.args.get("url", "").strip()
    filename = sanitize_filename(request.args.get("filename", "tiktok_video")) + ".mp4"

    if not cdn_url:
        return jsonify({"ok": False, "message": "Thiếu tham số 'url'"}), 400

    # Chỉ cho phép tải từ domain CDN của TikTok
    allowed_hosts = ("v19", "v16", "v17", "v26", "api16", "api19")
    try:
        from urllib.parse import urlparse
        host = urlparse(cdn_url).hostname or ""
        # ok nếu host chứa tiktok hoặc bắt đầu bằng v1x.tiktokcdn
        if "tiktok" not in host and "akamaized" not in host:
            return jsonify({"ok": False, "message": "URL nguồn không được phép"}), 403
    except Exception:
        return jsonify({"ok": False, "message": "URL không hợp lệ"}), 400

    try:
        upstream = requests.get(cdn_url, headers=HEADERS, stream=True, timeout=60)
        upstream.raise_for_status()

        def generate():
            for chunk in upstream.iter_content(chunk_size=1024 * 64):  # 64 KB mỗi chunk
                if chunk:
                    yield chunk

        response = Response(
            generate(),
            status=200,
            mimetype="video/mp4",
        )
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.headers["Content-Length"]      = upstream.headers.get("Content-Length", "")
        response.headers["Cache-Control"]       = "no-cache"
        return response

    except requests.exceptions.Timeout:
        return jsonify({"ok": False, "message": "Hết thời gian chờ khi tải video"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"ok": False, "message": f"Lỗi khi tải video: {str(e)}"}), 502


# ─── Xử lý lỗi toàn cục ─────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return jsonify({"ok": False, "message": "Không tìm thấy endpoint"}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"ok": False, "message": "Lỗi server nội bộ"}), 500


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("  TikDown - Server đang khởi động...")
    print(f"  URL: http://localhost:{PORT}")
    print("=" * 50)
    app.run(host=HOST, port=PORT, debug=DEBUG_MODE)


if __name__ == "__main__":
    main()
