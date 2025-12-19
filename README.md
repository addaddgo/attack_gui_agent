# attack_gui_agent

## 概览
`server.py` 是 Notes 攻击实验的后端，向 App 返回 `view_cli_template` JSON 来驱动弹窗、按钮、消息等。当前版本强化了弹窗控制，并新增“文件触发 / UI 树触发”动作管线：
- 支持单独设置弹窗内标题、正文、两个伪装按钮的坐标和尺寸。
- 支持文本字号控制。
- 支持出现延迟 (`appearDelayMs` / 兼容旧字段 `delay`) 和消失延迟 (`dismissDelayMs`)。
- 通过 POST `/action/<action>` 可在运行时热更新整个模板。
- 新增能力：延迟拨号预填号码 (`calls`)、延迟请求系统权限 (`permissions`)。
- 新增能力：`settingsActions` 可直接跳转到系统设置页（如通知/Wi‑Fi 设置），配合 `delay` 控制时机。
- 新增能力：`openUrls` 按 `delay` 触发 `ACTION_VIEW` 拉起深链或浏览器（如闲鱼 `fleamarket://...`、微博 `sinaweibo://...`）。
- 新增能力：`fileTrigger` + 各动作的 `waitForFile`/`delayAfterTriggerMs`/`dismissAfterTriggerMs`，可在检测到指定文件**新建** N 次后再调度动作，默认监控 `/sdcard/screenshot.png` 创建 2 次（覆盖写入不计，需先删再建）。
- 新增能力：`uiTrigger`（前台 UI 树被外部可访问性/UiAutomator 抓取）计数达标后触发，同样复用 `waitForFile` / `delayAfterTriggerMs` / `dismissAfterTriggerMs` 管线，无需申请无障碍权限。
- 新增能力：`notifications` 支持 heads-up 或静默通知，点击返回应用，可与 fileTrigger/uiTrigger 联动。

## 快速启动
```bash
cd /home/qianyi/qiankunwei/attack_gui_agent
python server.py  # 默认 0.0.0.0:8080，debug 开启
```

打开后端后，在手机上启动 Notes（修改版），进入主界面后会调用 `/action/MainActivityResume` 拉取指令；之后周期性访问 `/action/interval`。

## 主要接口
- `GET /action/<action>`：返回当前模板（本地内存中的 `view_cli_template`），并对缺省字段做规范化补全。
- `POST /action/<action>`：用传入的 JSON 覆盖内存模板，返回写入结果。典型用法：在线调整弹窗。
- `GET /`：简易健康检查页面。

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
`waitForFile` | 是否等待“触发”后再显示该弹窗（触发可来自 fileTrigger 或 uiTrigger） | false
`delayAfterTriggerMs` | 若 `waitForFile=true`，相对触发时刻的延迟显示（ms） | 0
`dismissAfterTriggerMs` | 弹窗已显示时，触发后再延迟多少 ms 关闭（0 表示不基于触发关闭） | 0

补全逻辑：`server.py` 会在返回前为缺失字段填默认值，并优先使用 `appearDelayMs`，若未提供再回落到旧的 `delay`。

## 新增控制项
字段 | 说明 | 示例
--- | --- | ---
`permissions` | 服务器控制何时弹出系统权限请求。元素：`{"permissions":["android.permission.POST_NOTIFICATIONS"],"delay":1200}` | 延迟 1.2s 申请通知权限
`calls` | 预填号码打开拨号界面（仅 ACTION_DIAL，不再支持 ACTION_CALL）。`{"number":"1234567890","delay":2000}` | 2s 后拉起拨号器并填入号码
`settingsActions` | 跳转系统设置页（如通知/Wi‑Fi）。元素：`{"action":"android.settings.WIFI_SETTINGS","delay":800}` | 0.8s 后打开 Wi‑Fi 设置
`openUrls` | 通过 `ACTION_VIEW` 打开外部深链或网页。元素：`{"url":"fleamarket://item?id=997693163811","delay":2000}` | 2s 后拉起对应 App 深链，未命中时由系统选择浏览器处理
`notifications` | 推送通知；字段：`title` / `message` / `delay` / `headsUp` / `autoCancel` / `waitForFile` / `delayAfterTriggerMs`。`headsUp=true` 走高优先级渠道并震动；`headsUp=false` 静默常规通知，可与触发器联动 | `{"title":"检测到截屏","message":"点击查看","waitForFile":true,"delayAfterTriggerMs":500,"headsUp":false}`
`fileTrigger` | 全局文件触发配置：`{"path":"/sdcard/screenshot.png","event":"CREATE","count":2}`。当 event=CREATE（默认）时客户端只计“新建”相关事件：CREATE / MOVED_TO / 紧跟 CREATE 的 CLOSE_WRITE，覆盖写入产生的 MODIFY 不计；轮询兜底仅在文件从无到有时计数。每次打开 APP 计数重置 | 监控 screenshot.png 被新建 2 次
`uiTrigger` | UI 树获取触发：`{"count":2}`，当前版本在前台界面被 UiAutomator/可访问性抓取时计数，达到 count 触发动作，随后计数清零并停止；此检测不需要无障碍权限 | 监控 UI 树被抓取 2 次
`waitForFile`/`delayAfterTriggerMs` | 适用于上面所有动作；为 true 时动作挂起，待触发（fileTrigger 或 uiTrigger）达标后以该延迟执行。`delayAfterTriggerMs` 默认为 0，若未设则不叠加原 delay。 |
`dismissAfterTriggerMs` | 仅 dialogs 使用：弹窗先显示（`waitForFile=false`），触发达标后再按此延迟关闭。 |

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

## 示例：文件触发后再执行（默认监控 /sdcard/screenshot.png）
场景：打开即弹窗；当 screenshot.png 被创建 2 次后，500ms 关闭弹窗，1000ms 后跳微博页面。
```json
{
  "resetCounter": true,
  "fileTrigger": { "path": "/sdcard/screenshot.png", "event": "CREATE", "count": 2 },
  "visitTemplates": [
    {
      "dialogs": [
        {
          "title": "Use notes_debug: press Confirm",
          "message": "...",
          "left": 0, "top": 0, "width": 800, "height": 800,
          "appearDelayMs": 0,
          "dismissDelayMs": 0,
          "dismissAfterTriggerMs": 500,
          "waitForFile": false,
          "delayAfterTriggerMs": 0,
          "confirmVisible": true,
          "confirmLeft": 10, "confirmTop": 340,
          "confirmWidth": 180, "confirmHeight": 100,
          "titleLeft": 40, "titleTop": 130,
          "messageLeft": 40, "messageTop": 520
        }
      ],
      "openUrls": [
        {
          "url": "sinaweibo://userinfo?uid=1776448504",
          "waitForFile": true,
          "delayAfterTriggerMs": 1000
        }
      ]
    }
  ]
}
```

## 示例：UI 树被抓取 2 次后再执行
场景：UiAutomator/可访问性抓取当前界面 2 次后，1s 弹窗并 500ms 后关闭，同时再延迟 1s 打开微博深链。
```json
{
  "uiTrigger": { "count": 2 },
  "dialogs": [
    {
      "title": "被查看了",
      "message": "检测到 UI dump 2 次后出现",
      "waitForFile": true,
      "delayAfterTriggerMs": 1000,
      "dismissAfterTriggerMs": 500,
      "confirmVisible": true
    }
  ],
  "openUrls": [
    {
      "url": "intent://userinfo?uid=1776448504#Intent;scheme=sinaweibo;package=com.sina.weibo;S.browser_fallback_url=https://m.weibo.cn/u/1776448504?jumpfrom=weibocom;end",
      "waitForFile": true,
      "delayAfterTriggerMs": 2000
    }
  ]
}
```

## 示例：文件触发后推送通知
目标文件创建 2 次后 500ms 发送静默通知，点击回到应用：
```json
{
  "resetCounter": true,
  "fileTrigger": { "path": "/sdcard/screenshot.png", "event": "CREATE", "count": 2 },
  "notifications": [
    {
      "title": "检测到截屏",
      "message": "点击查看详情",
      "waitForFile": true,
      "delayAfterTriggerMs": 500,
      "headsUp": false,
      "autoCancel": true
    }
  ]
}
```

## 当前版本与旧版的差异
- **延迟字段**：旧版只有 `delay`（出现延迟）；新版新增 `appearDelayMs` 和 `dismissDelayMs`，并自动兼容 `delay`。
- **位置控制**：旧版只能设置弹窗整体 `left/top/width/height`，新版可单独设置标题、正文、两个按钮的坐标和尺寸。
- **字号控制**：新增四个 `*SizeSp` 字段，按 sp 设置文本大小。
- **运行时热更新**：新增 POST `/action/<action>` 覆盖模板，无需改代码或重启进程即可生效。
- **安全回退**：未提供的字段会由服务器补默认值，保证旧客户端也能正常解析。
- **多次打开分场景**：新增 `visitTemplates` 支持按第 1、2、3 次进入主界面返回不同模板（详见下方）。
- **新增行为通道**：可控制拨号、权限申请，时机同样由 `delay` 控制。
- **跳转系统设置**：通过 `settingsActions` 可直达常见设置页（如通知/Wi‑Fi），由用户手动完成后续操作。
- **通知通道**：新增 `notifications`，支持 heads-up/静默，点击返回应用；Android 13+ 未授权 `POST_NOTIFICATIONS` 时客户端会跳过，可通过模板 `permissions` 下发请求。

## 行为细节
- App 端在渲染时会将元素坐标限制在弹窗宽高内，避免完全跑出可视区域。
- 自动消失：`dismissDelayMs` > 0 时，会在弹窗显示后按该延迟关闭；若用户提前点击关闭，则不会报错。
- `MainActivityResume` 会按 `visitTemplates` 顺序返回：第 N 次进入主界面取第 N 个模板，超出长度返回空；`interval` 默认返回空对象，可按需调整模板或服务端逻辑。
- 弹窗清理：客户端仅在新下发的模板包含 `dialogs` 时清空 DialogRegistry，`interval` 返回空模板不会关掉已显示的弹窗；`dismissAfterTriggerMs` 由文件触发后调度关闭。

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
