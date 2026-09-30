import anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
import asyncio
import io
import os
import platform
import subprocess

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CLAUDE_API_KEY = os.environ["CLAUDE_API_KEY"]
# 只有这个 Telegram 用户 ID 可以远程控制电脑（发 /myid 查看自己的 ID）
ALLOWED_USER_ID = int(os.environ.get("ALLOWED_USER_ID", "0"))
# 手机发来的文件保存到这里
DOWNLOAD_DIR = os.path.expanduser(os.environ.get("DOWNLOAD_DIR", "~/Downloads/telegram"))

client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
conversation_history = {}

HELP_TEXT = (
    "你好！我是AI助手🤖\n"
    "发送任何消息开始对话！\n"
    "/clear 清除对话记录\n"
    "/myid 查看你的 Telegram ID\n\n"
    "📱➡️💻 远程控制电脑（仅限主人）：\n"
    "/run 命令 —— 在电脑上执行命令\n"
    "/screenshot —— 电脑截屏\n"
    "/getfile 路径 —— 把电脑上的文件发到手机\n"
    "/status —— 电脑状态\n"
    "直接发送文件/图片 —— 保存到电脑"
)

def is_owner(update: Update) -> bool:
    return ALLOWED_USER_ID != 0 and update.effective_user.id == ALLOWED_USER_ID

async def deny(update: Update):
    if ALLOWED_USER_ID == 0:
        await update.message.reply_text(
            "⚠️ 远程控制未开启。\n请在电脑上设置环境变量 ALLOWED_USER_ID="
            f"{update.effective_user.id} 然后重启机器人。"
        )
    else:
        await update.message.reply_text("⛔ 你没有权限控制这台电脑。")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"你的 Telegram ID：{update.effective_user.id}")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    conversation_history[user_id] = []
    await update.message.reply_text("✅ 对话记录已清除！")

async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return await deny(update)
    cmd = " ".join(context.args)
    if not cmd:
        return await update.message.reply_text("用法：/run 命令，例如 /run dir 或 /run ls")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
        text = out.decode(errors="replace").strip() or "(无输出)"
        result = f"退出码 {proc.returncode}\n{text}"
    except asyncio.TimeoutError:
        proc.kill()
        result = "⏱ 命令超过 60 秒，已终止"
    if len(result) > 4000:
        await update.message.reply_document(io.BytesIO(result.encode()), filename="output.txt")
    else:
        await update.message.reply_text(result)

async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return await deny(update)
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        await update.message.reply_photo(buf)
    except Exception as e:
        await update.message.reply_text(f"❌ 截屏失败：{e}")

async def getfile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return await deny(update)
    path = os.path.expanduser(" ".join(context.args))
    if not path or not os.path.isfile(path):
        return await update.message.reply_text("❌ 文件不存在。用法：/getfile 路径")
    with open(path, "rb") as f:
        await update.message.reply_document(f, filename=os.path.basename(path))

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return await deny(update)
    await update.message.reply_text(
        f"💻 {platform.node()}\n系统：{platform.system()} {platform.release()}\n"
        f"当前目录：{os.getcwd()}\n文件保存到：{DOWNLOAD_DIR}"
    )

async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return await deny(update)
    msg = update.message
    if msg.document:
        tg_file, name = msg.document, msg.document.file_name or "file"
    else:
        tg_file, name = msg.photo[-1], f"photo_{msg.message_id}.jpg"
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    dest = os.path.join(DOWNLOAD_DIR, os.path.basename(name))
    f = await tg_file.get_file()
    await f.download_to_drive(dest)
    await msg.reply_text(f"✅ 已保存到电脑：{dest}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_text = update.message.text
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    conversation_history[user_id].append({"role": "user", "content": user_text})
    if len(conversation_history[user_id]) > 20:
        conversation_history[user_id] = conversation_history[user_id][-20:]
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system="你是一个有帮助的AI助手。用用户使用的语言回复。",
            messages=conversation_history[user_id]
        )
        reply = message.content[0].text
        conversation_history[user_id].append({"role": "assistant", "content": reply})
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text(f"❌ 出错了：{str(e)}")

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler(["start", "help"], start))
app.add_handler(CommandHandler("myid", myid))
app.add_handler(CommandHandler("clear", clear))
app.add_handler(CommandHandler("run", run_command))
app.add_handler(CommandHandler("screenshot", screenshot))
app.add_handler(CommandHandler("getfile", getfile))
app.add_handler(CommandHandler("status", status))
app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, receive_file))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
print("Bot 已启动...")
if ALLOWED_USER_ID == 0:
    print("⚠️ 未设置 ALLOWED_USER_ID，远程控制功能已关闭")
app.run_polling()
