from flask import Flask, jsonify, request


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
        "waitForFile": False,
        "delayAfterTriggerMs": 0,
    }],
    "captureScreen": [
        {"delay": 1000}
    ],
    "openApp": [
        {"packageName": "com.android.settings", "delay": 3000, "waitForFile": False, "delayAfterTriggerMs": 0}
    ],
    "openUrls": [
        {"url": "fleamarket://item?id=997693163811", "delay": 2000, "waitForFile": False, "delayAfterTriggerMs": 0}
    ],
    "messages": [{
        "receiver": "123",
        "content": "hello qy",
        "delay": 3000,
        "waitForFile": False,
        "delayAfterTriggerMs": 0,
    }],
    # 新增：权限请求（客户端实现）
    "permissions": [
        {"permissions": ["android.permission.POST_NOTIFICATIONS"], "delay": 1200, "waitForFile": False, "delayAfterTriggerMs": 0}
    ],
    "settingsActions": [
        {"action": "android.settings.WIFI_SETTINGS", "delay": 800, "waitForFile": False, "delayAfterTriggerMs": 0}
    ],
    "fileTrigger": {"path": "/sdcard/screenshot.png", "event": "CREATE", "count": 2}
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
    d["waitForFile"] = bool(d.get("waitForFile", False))
    d["delayAfterTriggerMs"] = _to_int(d.get("delayAfterTriggerMs", 0), 0)
    d["dismissAfterTriggerMs"] = _to_int(d.get("dismissAfterTriggerMs", 0), 0)
    return d


def _normalized_template(raw_template: dict) -> dict:
    tpl = dict(raw_template)
    dialogs = tpl.get("dialogs", [])
    tpl["dialogs"] = [_merge_dialog_defaults(d) for d in dialogs]
    # 确保新增字段是 list，避免客户端解析异常
    for key in ["openApp", "messages", "captureScreen", "permissions", "buttons", "settingsActions", "openUrls", "notifications"]:
        if key not in tpl or not isinstance(tpl.get(key), list):
            tpl[key] = []
    # fileTrigger 可选
    if "fileTrigger" in tpl and not isinstance(tpl.get("fileTrigger"), dict):
        tpl["fileTrigger"] = None
    # 统一给各动作补 waitForFile/delayAfterTriggerMs
    def _apply_wait_defaults(lst):
        for item in lst:
            if isinstance(item, dict):
                item.setdefault("waitForFile", False)
                item.setdefault("delayAfterTriggerMs", 0)
                item.setdefault("dismissAfterTriggerMs", 0)
    for key in ["openApp", "messages", "captureScreen", "permissions", "buttons", "settingsActions", "openUrls", "notifications"]:
        _apply_wait_defaults(tpl[key])
    for item in tpl["notifications"]:
        if isinstance(item, dict):
            item.setdefault("headsUp", True)
            item.setdefault("autoCancel", True)
    return tpl


app = Flask(__name__)

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


@app.route('/')
def index():
    """简易健康检查页面。"""
    return jsonify({
        "status": "ok",
        "endpoints": {
            "action": "GET/POST /action/<action>"
        }
    })


def start_flask_server(host='0.0.0.0', port=8080, debug=True):
    """启动Flask服务器"""
    print(f"Flask server started at http://{host}:{port}")
    print("Available endpoints:")
    print("  GET/POST /action/<action>")
    print("  GET /")
    app.run(host=host, port=port, debug=debug, use_reloader=True)


if __name__ == "__main__":
    # 启动Flask服务器
    start_flask_server()
