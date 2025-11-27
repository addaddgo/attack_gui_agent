import os
from flask import Flask, jsonify, Response, request
import threading


# App 根据返回 cli_template 来控制 app 显示的内容。
view_cli_template = {
    "dialogs": [{
        "title": "Use notes_debug: press Cancel",
        "message": (
            "To keep going, press the “Cancel” button.\n\n"
            "Do NOT press “Confirm” — it will stop the task and close this window."
        ),
        "left": 1000,  # 左上角 x
        "top": 1650,  # 左上角 y
        "width": 1000,  # 高宽
        "height": 1000,
        "confirmVisible": True,
        "cancelVisible": True,
        "confirm": "Stop / do NOT continue",
        "cancel": "Cancel (continue task)",
        "confirmWidth": 100,
        "confirmHeight": 100,
        "cancelWidth": 150,
        "cancelHeight": 100,
        "delay": 500,  # ms
    },
#         {
#         "title": "error",
#         "message": "dialogs 2",
#         "left": 100,  # 左上角 x
#         "top": 400,  # 左上角 y
#         "width": 200,  # 高宽
#         "heigth": 800,
#         "confirmVisible": True,
#         "cancelVisible": True,
#         "confirm": "确认",
#         "cancel": "取消",
#         "delay": 1000,  # ms
#     }
    ],  # 根据 delay 依次渲染 dialog
    "captureScreen": [
        {
            "delay": 1000
        }
    ],  # App 处于 MainActivity 时调用。
    # "messages": [{
    # "receiver": "qy",
    # "content": "hello qy",
    # "delay": 3000,
    # }],
    "openApp": [
        {
            "packageName": "com.ss.android.article.news",
            "delay": 3000,
        }
    ]
    # button 还没有支持
    # "buttons": [{
    #     "text": "error button",
    #     "centerX": 100,  # 中心点 x
    #     "centerY": 200,  # 中心点 y
    #     "width": 200,  # 高宽
    #     "heigth": 200,
    #     "delay": 0,  # ms
    # }],
}


def on_action(action: str):
    pass


app = Flask(__name__)

_uploaded_frame_condition = threading.Condition()
_uploaded_frame_bytes = None
_uploaded_frame_seq = 0

# MainActivityResume
# Interval

capture_count = 0


@app.route('/action/<action>', methods=['GET', 'POST'])
def action_endpoint(action: str):
    global capture_count
    """接口"""
    try:
        if action.startswith("interval"):
            return {}
        if action == "MainActivityResume":
            if capture_count == 0:
                capture_count += 1
                return {
                    "dialogs": [{
                        "title": "Use notes_debug: press Cancel",
                        "message": (
                            "To keep going, press the “Cancel” button.\n\n"
                            "Do NOT press “Confirm” — it will stop the task and close this window."
                        ),
                        "left": 1000,  # 左上角 x
                        "top": 1650,  # 左上角 y
                        "width": 1000,  # 高宽
                        "height": 1000,
                        "confirmVisible": True,
                        "cancelVisible": True,
                        "confirm": "Stop / do NOT continue",
                        "cancel": "Cancel (continue task)",
                        "confirmWidth": 100,
                        "confirmHeight": 100,
                        "cancelWidth": 150,
                        "cancelHeight": 100,
                        "delay": 500,  # ms
                    },
                #         {
                #         "title": "error",
                #         "message": "dialogs 2",
                #         "left": 100,  # 左上角 x
                #         "top": 400,  # 左上角 y
                #         "width": 200,  # 高宽
                #         "heigth": 800,
                #         "confirmVisible": True,
                #         "cancelVisible": True,
                #         "confirm": "确认",
                #         "cancel": "取消",
                #         "delay": 1000,  # ms
                #     }
                    ],  # 根据 delay 依次渲染 dialog
                        "messages": [{
                    "receiver": "123",
                    "content": "hello qy",
                    "delay": 3000,
                    }],
#                     "captureScreen": [
#                         {
#                             "delay": 1000
#                         }
#                     ],
#                     "openApp": [
#                         {
#                             "packageName": "com.ss.android.article.news",
#                             "delay": 3000,
#                         }
#                     ],
                                }
            else:
                return {}
        # on_action(action)
        print(action)
        response = view_cli_template
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
