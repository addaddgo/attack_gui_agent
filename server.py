from flask import Flask, jsonify
import threading


# App 根据返回 cli_template 来控制 app 显示的内容。
view_cli_template = {
    "dialog": [{
        "text": "error",
        "center_x": 100,  # 中心点 x
        "center_y": 200,  # 中心点 y
        "width": 200,  # 高宽
        "heigth": 200,
        "delay": 0,
    }],  # 根据 delay 依次渲染 dialog
    "button": [{
        "text": "error",
        "center_x": 100,  # 中心点 x
        "center_y": 200,  # 中心点 y
        "width": 200,  # 高宽
        "heigth": 200,
        "delay": 0,
    }]
}


def on_screenshot():
    pass


def on_appplication_show():
    pass


app = Flask(__name__)


@app.route('/screenshot', methods=['GET', 'POST'])
def screenshot_endpoint():
    """截图接口"""
    try:
        result = on_screenshot()
        response = {
            "status": "success",
            "data": view_cli_template,
            "message": "Screenshot processed successfully"
        }
        return jsonify(response)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/application_show', methods=['GET', 'POST'])
def application_show_endpoint():
    """应用显示接口"""
    try:
        result = on_appplication_show()
        response = {
            "status": "success",
            "data": view_cli_template,
            "message": "Application show processed successfully"
        }
        return jsonify(response)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


def start_flask_server(host='0.0.0.0', port=8080, debug=False):
    """启动Flask服务器"""
    print(f"Flask server started at http://{host}:{port}")
    print("Available endpoints:")
    print("  GET/POST /screenshot")
    print("  GET/POST /application_show")
    app.run(host=host, port=port, debug=debug, use_reloader=False)


if __name__ == "__main__":
    # 启动Flask服务器
    start_flask_server()
