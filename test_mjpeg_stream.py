import io
import time
import argparse
from datetime import datetime

import requests
from PIL import Image, ImageDraw, ImageFont


def build_frame(sequence: int, width: int, height: int) -> bytes:
    """生成带有时间戳/序列号的 JPEG 帧。"""
    img = Image.new("RGB", (width, height), color=(20, 20, 20))
    draw = ImageDraw.Draw(img)

    text = f"Frame #{sequence}\n{datetime.now().strftime('%H:%M:%S.%f')[:-3]}"
    draw.rectangle([(10, 10), (width - 10, height - 10)], outline=(0, 200, 255), width=3)
    draw.text((30, 40), text, fill=(255, 255, 255))

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def stream_frames(server: str, frame_interval: float, width: int, height: int):
    """不断构造 JPEG 帧并 POST 至 /upload_stream。"""
    url = f"{server.rstrip('/')}/upload_stream"
    sequence = 0

    print(f"开始推流: {url}")
    try:
        while True:
            frame_bytes = build_frame(sequence, width, height)
            resp = requests.post(
                url,
                data=frame_bytes,
                headers={"Content-Type": "application/octet-stream"},
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json()

            print(f"Sent frame {sequence}, server seq={data.get('seq')}")
            sequence += 1
            time.sleep(frame_interval)
    except KeyboardInterrupt:
        print("收到中断，停止推流。")


def main():
    parser = argparse.ArgumentParser(description="MJPEG 上传流测试脚本")
    parser.add_argument(
        "--server",
        default="http://127.0.0.1:8080",
        help="Flask 服务地址（默认: http://127.0.0.1:8080）",
    )
    parser.add_argument("--fps", type=float, default=5.0, help="推流帧率 (默认 5 FPS)")
    parser.add_argument("--width", type=int, default=640, help="帧宽度")
    parser.add_argument("--height", type=int, default=360, help="帧高度")
    args = parser.parse_args()

    frame_interval = 1.0 / max(args.fps, 0.1)
    stream_frames(args.server, frame_interval, args.width, args.height)


if __name__ == "__main__":
    main()

