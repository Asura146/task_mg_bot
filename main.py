import os
from dotenv import load_dotenv
import discord
from discord.ext import commands,tasks
from datetime import datetime,timedelta
import json
import os
import uuid

TASK_FILE = "tasks.json"


def load_tasks():
    if os.path.exists(TASK_FILE):
        with open(TASK_FILE,"r",encoding="utf-8") as f:
            return json.load(f)
    return []

def save_tasks(tasks):
    with open(TASK_FILE,"w",encoding="utf-8") as f:
        json.dump(tasks,f,indent=2,ensure_ascii=False)

task_list = load_tasks()

# トークンを.envから読み込む
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Botの初期設定（メッセージ内容を取得するintentが必要）
intents = discord.Intents.default()
intents.message_content = True  # これを忘れるとBotがメッセージに反応しない

# !で始まるコマンドを処理
bot = commands.Bot(command_prefix='!', intents=intents)

# Botが起動したときに呼ばれる
@bot.event
async def on_ready():
    print(f'✅ ログイン完了: {bot.user}')
    daily_summary.start()

# !hello とチャットすると反応する
@bot.command()
async def hello(ctx):
    await ctx.send("こんにちは！")

@bot.command()
async def add(ctx,date:str,*,content:str):
    task_list = load_tasks()
    try :
        now = datetime.now()
        month ,day = map(int, date.split("/"))
        notify_date = now.replace(month=month,day=day,hour=9,minute=0,second=0,microsecond=0)

        if notify_date < now :
            ctx.send("日にちが過去になっています！")
            return
    except Exception:
        await ctx.send("日付は/区切りで入力してください")
        return

    task = {
        "id":str(uuid.uuid4()),
        "date": notify_date.strftime("%Y-%m-%d %H:%M:%S"),
        "channel_id":ctx.channel.id,
        "content":content
    }

    task_list.append(task)
    save_tasks(task_list)
    
@bot.command()
async def list(ctx):
    current_tasks = load_tasks()
    if not current_tasks:
        await ctx.send("📭 現在、登録されているタスクはありません。")
        return

    user_tasks = [
        t for t in current_tasks
        if str(ctx.channel.id) == str(t.get("channel_id"))
    ]
    if not user_tasks:
        await ctx.send("📭 このチャンネルにはタスクが登録されていません。")
        return

    # 並び替え（日付順）
    sorted_tasks = sorted(
        user_tasks,
        key=lambda t: datetime.strptime(t["date"], "%Y-%m-%d %H:%M:%S")
    )

    message_lines = [f"📋 タスク一覧（全{len(user_tasks)}件）:"]
    for idx, task in enumerate(sorted_tasks, 1):
        date_str = task["date"][:16]  # "YYYY-MM-DD HH:MM"
        message_lines.append(f"{idx}. 🕒 {date_str} - {task['content']}")

    await ctx.send("\n".join(message_lines))

@bot.command()
async def remove(ctx,index:int):
    current_tasks = load_tasks()

    user_tasks = [
        t for t in current_tasks
        if str(t.get("channel_id"))==str(ctx.channel.id)
    ]    

    if not user_tasks:
        await ctx.send("📭 このチャンネルには削除できるタスクがありません。")
        return
    
    # インデックスの範囲チェック（1始まり）
    if index < 1 or index > len(user_tasks):
        await ctx.send(f"⚠ 番号が無効です。1〜{len(user_tasks)}の範囲で指定してください。")
        return
    
    task_to_remove = user_tasks[index - 1]

    updated_tasks = [t for t in current_tasks if t["id"] != task_to_remove["id"]]

    save_tasks(updated_tasks)

    await ctx.send(f"🗑 タスク削除完了: {task_to_remove['content']}")



@tasks.loop(minutes=1)
async def daily_summary():
    now = datetime.now()
    if now.hour != 9 or now.minute != 0:
        return
    current_tasks = load_tasks()

    if not current_tasks:
        return  # タスクが空なら何もしない
    
    channels = set(t["channel_id"] for t in current_tasks)

    for channel_id in channels:
        channel_tasks = [
            t for t in current_tasks
            if t["channel_id"] == channel_id
            and datetime.strptime(t["date"], "%Y-%m-%d %H:%M:%S") >= now
        ]

        if not channel_tasks:
            continue

        sorted_tasks = sorted(
            channel_tasks,
            key=lambda t: t["date"]
        )

        lines = [f"📅 現在のタスク一覧 ({len(sorted_tasks)} 件):"]
        for idx, task in enumerate(sorted_tasks, 1):
            date_str = task["date"][:16]  # YYYY-MM-DD HH:MM
            lines.append(f"{idx}. 🕒 {date_str} - {task['content']}")

        channel = bot.get_channel(int(channel_id))
        if channel:
            await channel.send("\n".join(lines))


# Bot起動
bot.run(TOKEN)