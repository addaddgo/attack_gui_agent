# server.py 说明（当前版本）

## 能力概览
- 弹窗协议：精确控制弹窗位置/尺寸、子元素位置与字号、出现/消失/基于文件触发的关闭；支持多次进入主界面按次序返回不同模板（`visitTemplates`）。
- 运行时热更新：`POST /action/<action>` 覆盖内存模板，`resetCounter` 可重置次数计数。
- 文件触发管线：`fileTrigger` 监控单文件（默认 `/sdcard/screenshot.png`），累计 `count` 次创建后触发；各动作可选 `waitForFile`/`delayAfterTriggerMs`，dialogs 可用 `dismissAfterTriggerMs` 在触发后关闭。
- UI 树触发管线：`uiTrigger` 计数前台界面被 UiAutomator/可访问性抓取的次数，达标后触发同一套 `waitForFile` 延迟逻辑；此检测不需要无障碍权限。
- 拨号预填号码：`calls` 列表按 `delay` 打开拨号器（仅 ACTION_DIAL，不再支持 ACTION_CALL）。
- 权限请求：`permissions` 列表按 `delay` 触发 `requestPermissions`，可远程控制相册等权限弹窗时机。
- 媒体抓取上传：`mediaUpload` 列表按 `delay` 读取最近图片/视频并上传到 `/upload_file`。
- 外部深链/URL 唤起：`openUrls` 按 `delay` 或文件触发的相对延迟拉起深链/浏览器（支持 `intent://` + `browser_fallback_url`）。
- 通知下发：`notifications` 支持 heads-up 或静默通知，点击返回应用；可与 fileTrigger/uiTrigger 联动。
- 屏幕流转发：`/upload_stream` 接收 JPEG 帧，`/forward_stream` 输出 MJPEG，根页面便于预览。
- 通用文件上传：`/upload_file` 保存上传文件到 `uploads/`，单请求 25 MiB 尺寸上限；会对文件名做安全清洗并去重生成安全路径，防止覆盖或目录穿越；原始体上传自动生成 `upload_<uuid>.bin`。

## 接口
- `GET /action/<action>`：返回当前模板（含补全默认值）。`MainActivityResume` 会消费 `visitTemplates`，按进入次数返回不同模板；`interval*` 默认返回空对象。
- `POST /action/<action>`：更新模板。支持：
  - 直接提供一个模板对象，或
  - `{ "visitTemplates": [ ... ], "resetCounter": true }` 分次序模板并可重置计数。
- `POST /upload_stream` / `GET /forward_stream`：推送并查看 MJPEG。
- `POST /upload_file`：multipart 或原始体上传文件到 `uploads/`。文件名经 `secure_filename` 清洗，若重名会追加 UUID 片段；原始体上传使用随机 `upload_<uuid>.bin`。请求体超过 25 MiB 会被 Flask 拦截。

## 模板字段（新增项）
- `permissions`: `[ { "permissions": ["android.permission.READ_MEDIA_IMAGES"], "delay": 1200 } ]`
- `calls`: `[ { "number": "1234567890", "delay": 2000 } ]`
- `mediaUpload`: `[ { "mediaType": "images"|"videos", "count": 1-5, "delay": 4000 } ]`
- `openUrls`: `[ { "url": "fleamarket://item?id=997693163811", "delay": 2000 } ]`(intent://item?id=997693163811#Intent;scheme=fleamarket;package=com.taobao.idlefish;end)；微博深链示例 `intent://userinfo?uid=1776448504#Intent;scheme=sinaweibo;package=com.sina.weibo;S.browser_fallback_url=https://m.weibo.cn/u/1776448504?jumpfrom=weibocom;end)`
- `fileTrigger`: `{ "path": "/sdcard/screenshot.png", "event": "CREATE", "count": 2 }`（单文件监听，默认值；客户端当 event=CREATE 时只计“新建”相关事件：CREATE / MOVED_TO / 紧跟 CREATE 的 CLOSE_WRITE，覆盖写入产生的 MODIFY 不计；轮询兜底也仅在文件从无到有时计数。若要覆盖写入也触发，请先删后写或修改客户端逻辑。）
- `uiTrigger`: `{ "count": 2 }`（前台界面被 UiAutomator/可访问性抓取计一次，达到 count 触发；触发后计数清零并停止；无需无障碍权限）
- `waitForFile` / `delayAfterTriggerMs`: 各动作通用，true 时等待触发（fileTrigger 或 uiTrigger）达标后按相对延迟执行；否则按 `delay`。
- `dismissAfterTriggerMs`: 仅 dialogs 使用，弹窗已显示时触发达标后再延迟关闭。
- `notifications`: `[ { "title": "新消息", "message": "文本", "delay": 1000, "headsUp": true, "autoCancel": true, "waitForFile": false, "delayAfterTriggerMs": 0 } ]`；`headsUp=false` 走默认重要级、无震动/灯光/声音；`autoCancel=false` 可让通知留在通知栏。
其余字段与 README 的 dialogs/openApp/messages/captureScreen 相同，缺省会在服务端补默认值。

## 使用示例
```bash
curl -X POST http://localhost:8080/action/MainActivityResume \
  -H "Content-Type: application/json" \
  -d '{
        "resetCounter": true,
        "visitTemplates": [
          {
            "dialogs": [{ "title": "Hi", "message": "First open" }],
            "permissions": [{ "permissions": ["android.permission.READ_MEDIA_IMAGES"], "delay": 800 }],
            "calls": [{ "number": "10086", "delay": 1500 }],
            "mediaUpload": [{ "mediaType": "images", "count": 1, "delay": 3000 }],
            "openUrls": [{ "url": "fleamarket://item?id=997693163811", "delay": 2000 }]
          },
          {
            "dialogs": [{ "title": "Second", "message": "Second open" }]
          }
        ]
      }'
```

## 示例：文件触发后再执行
打开即弹窗；目标文件创建 2 次后，500ms 关闭弹窗，1000ms 跳微博：
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
          "confirmVisible": true
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

## 示例：UI 树被抓取后再执行
当前界面被 UiAutomator/可访问性抓取 2 次后，延迟 1s 弹窗，再延迟 1s 跳微博：
```json
{
  "uiTrigger": { "count": 2 },
  "dialogs": [
    {
      "title": "UI dump detected",
      "message": "抓取 2 次后出现",
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

## 注意事项 / 风险
- 无鉴权：管理接口和上传接口默认开放本机端口，生产环境需加鉴权或限网段。
- 内存态：模板与帧缓存都在进程内存，多进程/重启会丢失；上传已有 25 MiB 单请求上限，但仍建议前置 Nginx/Flask 限流和鉴权。
- 计数与竞态：`capture_count` 未加锁，在多线程高并发下可能非严格递增；调试场景问题不大。
- 权限弹窗：若用户勾选“不再询问”，系统不再弹窗，需引导到系统设置手动开启。
- 通知权限：Android 13+ 需 `android.permission.POST_NOTIFICATIONS`；可通过模板 `permissions` 字段下发请求，否则客户端会跳过通知。
- 媒体上传：读取最近媒体需相册读权限；上传量做了客户端 count(1..5) 限制，服务端仍建议配置 Nginx/Flask 限流。 
- `settingsActions`: `[{"action":"android.settings.ACCESSIBILITY_SETTINGS","delay":800}]`
