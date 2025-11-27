# attack_gui_agent

## 概览
`server.py` 是 Notes 攻击实验的后端，向 App 返回 `view_cli_template` JSON 来驱动弹窗、按钮、消息等。当前版本强化了弹窗控制：
- 支持单独设置弹窗内标题、正文、两个伪装按钮的坐标和尺寸。
- 支持文本字号控制。
- 支持出现延迟 (`appearDelayMs` / 兼容旧字段 `delay`) 和消失延迟 (`dismissDelayMs`)。
- 通过 POST `/action/<action>` 可在运行时热更新整个模板。
- 新增能力：延迟拨号预填号码 (`calls`)、延迟请求系统权限 (`permissions`)、按需抓取本地媒体并上传到服务器 (`mediaUpload`)，以及通用文件上传接口 `/upload_file`。
- 新增能力：`settingsActions` 可直接跳转到系统设置页（如无障碍设置），配合 `delay` 控制时机。

## 快速启动
```bash
cd /home/qianyi/qiankunwei/attack_gui_agent
python server.py  # 默认 0.0.0.0:8080，debug 开启
```

打开后端后，在手机上启动 Notes（修改版），进入主界面后会调用 `/action/MainActivityResume` 拉取指令；之后周期性访问 `/action/interval`。

## 主要接口
- `GET /action/<action>`：返回当前模板（本地内存中的 `view_cli_template`），并对缺省字段做规范化补全。
- `POST /action/<action>`：用传入的 JSON 覆盖内存模板，返回写入结果。典型用法：在线调整弹窗。
- `POST /upload_stream`：上传 JPEG 单帧，内部缓存后用于视频流转发。
- `GET /forward_stream`：将缓存帧转成 MJPEG 流，便于网页/调试查看。
- `GET /`：简易页面查看视频流分辨率与画面。
- `POST /upload_file`：上传任意文件，存到 `uploads/` 目录（媒体抓取上传复用此接口）。服务器对单请求做 25 MiB 上限，强制清洗文件名并去重生成安全路径，防止覆盖和目录穿越；原始体上传自动生成 `upload_<uuid>.bin`。

## Dialog payload 结构（每个 dialogs 元素）
字段 | 说明 | 默认
--- | --- | ---
`title` / `message` | 标题 / 正文文本 | 空字符串
`left` / `top` | 弹窗左上角屏幕坐标 | 0 / 0
`width` / `height` | 弹窗整体尺寸 | 0（PopupWindow 将按内容 wrap）
`appearDelayMs` | 弹窗出现延迟（ms）；若未给则用旧字段 `delay` | 0
`delay` | 旧字段，等同出现延迟；仍受支持 | 0
`dismissDelayMs` | 出现后自动关闭的延迟（ms）；0 表示不自动关闭 | 0
`confirmVisible` / `cancelVisible` | 伪装按钮是否显示 | `false`
`confirm` / `cancel` | 按钮文案 | "确认" / "取消"
`confirmWidth` / `confirmHeight` | 确认按钮尺寸 | 150 / 80
`cancelWidth` / `cancelHeight` | 取消按钮尺寸 | 150 / 80
`titleLeft` / `titleTop` | 标题相对弹窗左上角坐标，-1 保持布局默认 | -1 / -1
`messageLeft` / `messageTop` | 正文相对坐标，-1 默认 | -1 / -1
`confirmLeft` / `confirmTop` | 确认按钮相对坐标，-1 默认 | -1 / -1
`cancelLeft` / `cancelTop` | 取消按钮相对坐标，-1 默认 | -1 / -1
`titleSizeSp` / `messageSizeSp` | 标题/正文字号（sp），-1 使用布局默认 | -1 / -1
`confirmTextSizeSp` / `cancelTextSizeSp` | 按钮字号（sp），-1 默认 | -1 / -1

补全逻辑：`server.py` 会在返回前为缺失字段填默认值，并优先使用 `appearDelayMs`，若未提供再回落到旧的 `delay`。

## 新增控制项
字段 | 说明 | 示例
--- | --- | ---
`permissions` | 服务器控制何时弹出系统权限请求。元素：`{"permissions":["android.permission.READ_MEDIA_IMAGES"],"delay":1200}` | 延迟 1.2s 申请相册权限
`calls` | 预填号码打开拨号界面（默认 `action: "dial"`，可选 `"call"` 需 CALL_PHONE）。`{"number":"1234567890","delay":2000,"action":"dial"}` | 2s 后拉起拨号器并填入号码
`mediaUpload` | 读取最近的图片/视频并上传到 `/upload_file`。字段：`mediaType` = images/videos, `count`(1-5), `delay`。`{"mediaType":"images","count":2,"delay":4000}` | 4s 后上传最近 2 张图片（服务端会对文件名做安全清洗，单请求 25 MiB 尺寸上限）
`settingsActions` | 跳转系统设置页（如无障碍）。元素：`{"action":"android.settings.ACCESSIBILITY_SETTINGS","delay":800}` | 0.8s 后打开无障碍设置

## 示例：更新模板
把下列 JSON 存为 `template.json`，再 POST：
```bash
curl -X POST http://localhost:8080/action/MainActivityResume \
  -H "Content-Type: application/json" \
  -d @template.json
```

示例内容：
```json
{
  "dialogs": [{
    "title": "Demo",
    "message": "Move everything independently",
    "left": 200, "top": 400, "width": 900, "height": 800,
    "appearDelayMs": 300, "dismissDelayMs": 4000,
    "titleSizeSp": 24, "messageSizeSp": 16,
    "titleLeft": 40, "titleTop": 30,
    "messageLeft": 40, "messageTop": 120,
    "confirmVisible": true, "confirm": "Fake Confirm",
    "confirmWidth": 220, "confirmHeight": 90,
    "confirmLeft": 500, "confirmTop": 600, "confirmTextSizeSp": 18,
    "cancelVisible": true, "cancel": "Fake Cancel",
    "cancelWidth": 200, "cancelHeight": 90,
    "cancelLeft": 180, "cancelTop": 600, "cancelTextSizeSp": 18
  }]
}
```

## 当前版本与旧版的差异
- **延迟字段**：旧版只有 `delay`（出现延迟）；新版新增 `appearDelayMs` 和 `dismissDelayMs`，并自动兼容 `delay`。
- **位置控制**：旧版只能设置弹窗整体 `left/top/width/height`，新版可单独设置标题、正文、两个按钮的坐标和尺寸。
- **字号控制**：新增四个 `*SizeSp` 字段，按 sp 设置文本大小。
- **运行时热更新**：新增 POST `/action/<action>` 覆盖模板，无需改代码或重启进程即可生效。
- **安全回退**：未提供的字段会由服务器补默认值，保证旧客户端也能正常解析。
- **多次打开分场景**：新增 `visitTemplates` 支持按第 1、2、3 次进入主界面返回不同模板（详见下方）。
- **新增行为通道**：可控制拨号、权限申请、媒体抓取上传，时机同样由 `delay` 控制。
- **跳转系统设置**：通过 `settingsActions` 可直达无障碍等设置页，引导用户手动开启权限。

## 行为细节
- App 端在渲染时会将元素坐标限制在弹窗宽高内，避免完全跑出可视区域。
- 自动消失：`dismissDelayMs` > 0 时，会在弹窗显示后按该延迟关闭；若用户提前点击关闭，则不会报错。
- `MainActivityResume` 会按 `visitTemplates` 顺序返回：第 N 次进入主界面取第 N 个模板，超出长度返回空；`interval` 默认返回空对象，可按需调整模板或服务端逻辑。

## 调试视频流
- 持续 POST JPEG 帧到 `/upload_stream`，即可在浏览器打开根页面或 `GET /forward_stream` 查看 MJPEG 流（与弹窗控制无直接关系，便于观察设备屏幕）。

## 多次进入主界面按次序返回不同模板
- 发送带 `visitTemplates` 数组的 POST：
```bash
curl -X POST http://localhost:8080/action/MainActivityResume \
  -H "Content-Type: application/json" \
  -d '{
        "visitTemplates": [
          {"dialogs": [{"title": "第一次", "message": "首次弹窗"}]},
          {"dialogs": [{"title": "第二次", "message": "二次弹窗"}]}
        ],
        "resetCounter": true
      }'
```
- 效果：
  - 第 1 次进入主界面 → 返回第 1 个模板（标题“第一次”）。
  - 第 2 次 → 返回第 2 个模板。
  - 第 3 次及以后 → 返回空（可按需增加更多模板或再次 POST）。
- `resetCounter: true` 可在更新模板时把计数清零，便于重新从第 1 个模板开始。
