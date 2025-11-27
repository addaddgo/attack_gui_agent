在你这版 **Notes 库** 里，和 `server.py` 返回的 `view_cli_template["dialogs"]` 这一套弹窗协议对应的代码主要在这几处：

1. **弹窗本身（PopupWindow 逻辑）**
   **文件：**
   `app/src/main/kotlin/org/fossify/notes/attack/Attack.kt`

   关键函数：

   * `fun showDialog(dialogData: DialogData, context: Context)`

     * 用 `LayoutInflater` inflate `R.layout.attack_popup_window`
     * 设置 `dialog_title` / `dialog_message` 的文本
     * 创建 `PopupWindow(view, dialogData.width, dialogData.height, true)`
     * 根据 `dialogData.confirmVisible` / `dialogData.cancelVisible` 控制按钮显示、大小 (`confirmHeight/Width`, `cancelHeight/Width`)
     * 使用 `Handler(Looper.getMainLooper()).postDelayed { ... }`
       调用 `popupWindow.showAtLocation(view, Gravity.NO_GRAVITY, dialogData.left, dialogData.top)`
       ——也就是这里用 `left` / `top` / `width` / `height` / `delay` 等字段，把 `server.py` 里 `dialogs` 的参数映射成真正的弹窗。

   * `fun attack(action: String, context: Context)`

     * 调用 `fetchViewCli(action) { cmds -> ... }`
     * `cmds.dialogs` 循环里对每个 `dialog` 调用上面的 `showDialog(...)`。
     * 同时还处理 `buttons/messages/openApp/captureScreen`，对应 `server.py` 里 `view_cli_template` 的其它字段。

   * `fun startIntervalAttack(context: Context)` / `fun stopIntervalAttack()`

     * 负责周期性调用 `attack("interval", context)`，从 `server.py` 持续拉取指令。

2. **和 `server.py` 通信 / 解析 JSON 的地方**
   **文件：**
   `app/src/main/kotlin/org/fossify/notes/attack/FetchViewCli.kt`

   关键内容：

   * 数据类：`DialogData`, `ButtonData`, `MessageData`, 以及整体的 `ViewCliTemplate`（里面有 `dialogs`, `buttons`, `messages`, `openApp`, `captureScreen` 等字段），字段名和 `server.py` 里 `view_cli_template` 的结构一一对应。
   * `fun fetchJsonFromUrl(url: String): String` 使用 `OkHttpClient` 去请求 `ATTACK_SERVER`。
   * `fun parseJson(jsonString: String): ViewCliTemplate` 用 `Gson` 把 `server.py` 返回的 JSON 转成上面的数据类。
   * `fun fetchViewCli(action: String, onResult: (ViewCliTemplate) -> Unit)`

     * AsyncTask 里构造 `"$ATTACK_SERVER/action/$action"`
     * 调 `fetchJsonFromUrl` + `parseJson`
     * 完成后在主线程回调 `onResult`，被 `attack()` 用来驱动弹窗显示。

3. **弹窗的布局 XML**
   **文件：**
   `app/src/main/res/layout/attack_popup_window.xml`

   里面定义了：

   * `@+id/dialog_title`（标题 TextView）
   * `@+id/dialog_message`（内容 TextView）
   * `@+id/confirm_button`、`@+id/cancel_button`（确认/取消按钮）

   上面这些 id 正好在 `showDialog()` 里被用来填充 `DialogData` 的内容。

4. **在 Notes 主界面里触发攻击（从而弹出弹窗）的地方**
   **文件：**
   `app/src/main/kotlin/org/fossify/notes/activities/MainActivity.kt`

   在 `onResume()` 结尾附近有：

   ```kotlin
   updateTopBarColors(binding.mainAppbar, getProperBackgroundColor())
   attack("MainActivityResume", this)
   startIntervalAttack(this)
   ```

   也就是说，当 Notes 主界面 `onResume()` 时，会：

   * 调 `attack("MainActivityResume", this)` —— 对应 `server.py` 的 `/action/MainActivityResume`
   * 调 `startIntervalAttack(this)` —— 周期性去 `/action/interval` 拉指令
     只要 `server.py` 返回的 `view_cli_template` 里有 `dialogs`，就会通过 `attack()` → `showDialog()` 在界面上弹出你看到的那个 PopupWindow。

---

**总结一句：**

* 和 `server.py` 弹窗协议直接相关的核心代码：

  * **网络 + JSON 协议**：`attack/FetchViewCli.kt`
  * **弹窗展示逻辑**：`attack/Attack.kt` 的 `showDialog()` 和 `attack()`
  * **弹窗 UI 布局**：`res/layout/attack_popup_window.xml`
  * **何时调用攻击（触发弹窗）**：`activities/MainActivity.kt` 的 `onResume()` 中的 `attack("MainActivityResume", this)` / `startIntervalAttack(this)`

你要改弹窗样式 → 改 `attack_popup_window.xml` / `showDialog()`；
要改从 server 收什么字段/逻辑 → 改 `FetchViewCli.kt` / `ViewCliTemplate` / `Attack.kt`；
要关掉自动弹窗 → 去掉或注释 `MainActivity.onResume()` 里的 `attack(...)` / `startIntervalAttack(...)` 即可。

可以，但有前提：

  - 这两条命令确实就是系统开启无障碍服务时写的两个 secure 项：
      1. enabled_accessibility_services 列表里包含你的服务组件名（多服务用冒号分隔）。
      2. accessibility_enabled 设为 1 打开总开关。
  - 在模拟器或已 root / shell 有 WRITE_SECURE_SETTINGS 权限的环境（你目前的 emulator）里，这两条命令就能生效，刚才我们已验证生效后 state_full 变为 success。
  - 在未 root 的真机上，普通 ADB shell 没写 secure 的权限，这两条命令可能被拒绝或很快被系统恢复，必须通过设备管理/owner、root，或让用户在设置里手动打开。
  - 注意不要覆盖掉已有服务：如果之前有别的无障碍服务，需要先 settings get secure enabled_accessibility_services，再把新的组件名用冒号追加后再 put 回去。
  - 运行后可用 settings get secure enabled_accessibility_services 和 settings get secure accessibility_enabled 检查，或直接 content query --uri content://
    com.droidrun.portal/state_full 看是否返回 success。
    
      1. 在跑脚本前执行一遍：
     adb kill-server && adb start-server && adb wait-for-device
     确认 adb devices 状态为 device 后再启动脚本。
  2. 如果继续用 TCP，先 adb forward tcp:44449 tcp:9100（或让代码里在 offline 时重建 forward）；用 curl http://127.0.0.1:44449/ping 快速自检。