# Telegram Claude Bot：手机 ↔ 电脑

在电脑上运行这个机器人，然后在手机的 Telegram 里：和 Claude 聊天，或者远程控制电脑。

## 启动

```bash
pip install -r requirements.txt
```

Windows（PowerShell）：
```powershell
$env:TELEGRAM_TOKEN="你的BotToken"
$env:CLAUDE_API_KEY="你的ClaudeKey"
$env:ALLOWED_USER_ID="你的TelegramID"
python bot.py
```

Mac / Linux：
```bash
export TELEGRAM_TOKEN=你的BotToken
export CLAUDE_API_KEY=你的ClaudeKey
export ALLOWED_USER_ID=你的TelegramID
python bot.py
```

还不知道自己的 Telegram ID？先不设 `ALLOWED_USER_ID` 启动，在手机上给机器人发 `/myid`，把 ID 填进去后重启。

默认使用 `claude-opus-5-5` 模型。想换模型可以设置 `CLAUDE_MODEL`，例如 `claude-sonnet-5-5`（更便宜）。

## 手机上可用的命令

| 命令 | 作用 |
|---|---|
| 直接发文字 | 和 Claude 聊天 |
| `/run 命令` | 在电脑上执行命令（60 秒超时） |
| `/screenshot` | 电脑截屏发到手机 |
| `/getfile 路径` | 把电脑上的文件发到手机 |
| 发送文件或图片 | 保存到电脑的 `~/Downloads/telegram`（可用 `DOWNLOAD_DIR` 修改） |
| `/status` | 查看电脑信息 |
| `/clear` | 清除对话记录 |

⚠️ 只有 `ALLOWED_USER_ID` 对应的账号能使用远程控制命令。`/run` 可以执行任何命令，不要把这个 ID 设成别人的。
