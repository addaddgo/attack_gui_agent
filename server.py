from flask import Flask, jsonify
import threading


# App 根据返回 cli_template 来控制 app 显示的内容。
view_cli_template = {
    "dialogs": [{
        "title": "error",
        "message": "errorxxxx asdfasdfsdsfdxxx",
        "left": 100,  # 左上角 x
        "top": 100,  # 左上角 y
        "width": 200,  # 高宽
        "heigth": 200,
        "confirmVisible": True,
        "cancelVisible": True,
        "confirm": "确认",
        "cancel": "取消",
        "delay": 3000,  # ms
    },
        {
        "title": "error",
        "message": "dialogs 2",
        "left": 100,  # 左上角 x
        "top": 400,  # 左上角 y
        "width": 200,  # 高宽
        "heigth": 200,
        "confirmVisible": True,
        "cancelVisible": True,
        "confirm": "确认",
        "cancel": "取消",
        "delay": 1000,  # ms
    }]  # 根据 delay 依次渲染 dialog
    # "messages": [{
    #     "receiver": "qy",
    #     "content": "hello qy",
    #     "delay": 3000,
    # }]
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


@app.route('/action/<action>', methods=['GET', 'POST'])
def action_endpoint(action: str):
    """截图接口"""
    try:
        on_action(action)
        print(action)
        response = view_cli_template
        return jsonify(response)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


def start_flask_server(host='0.0.0.0', port=8080, debug=True):
    """启动Flask服务器"""
    print(f"Flask server started at http://{host}:{port}")
    print("Available endpoints:")
    print("  GET/POST /action")
    app.run(host=host, port=port, debug=debug, use_reloader=True)


if __name__ == "__main__":
    # 启动Flask服务器
    start_flask_server()
