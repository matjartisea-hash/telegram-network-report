from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
import sqlite3
import re
from datetime import datetime, date
from reportlab.pdfgen import canvas

TOKEN="8583886234:AAEPcKBCyH0823cO4WYXc9dx0CObYfbo2Zs"
CHAT_ID="1995981496"

db = sqlite3.connect("events.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS events(ip TEXT,status TEXT,time TEXT)")

def get_ip(text):
    m = re.search(r'IP:\s*(\d+\.\d+\.\d+\.\d+)', text)
    if m:
        return m.group(1)

async def save(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if str(update.message.chat_id) != CHAT_ID:
        return

    text = update.message.text
    ip = get_ip(text)

    if not ip:
        return

    now = datetime.now().isoformat()

    if "🔴" in text:
        status = "down"
    elif "🟢" in text:
        status = "up"
    else:
        return

    cursor.execute("INSERT INTO events VALUES(?,?,?)", (ip, status, now))
    db.commit()

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if str(update.message.chat_id) != CHAT_ID:
        return

    today = str(date.today())

    cursor.execute("SELECT * FROM events WHERE time LIKE ?", (f"{today}%",))
    rows = cursor.fetchall()

    devices = {}

    for ip, status, time in rows:
        devices.setdefault(ip, []).append((status, time))

    file = "report.pdf"
    c = canvas.Canvas(file)

    y = 800

    for ip, events in devices.items():

        c.drawString(50, y, f"Device: {ip}")
        y -= 20

        last = None

        for s, t in events:

            t = datetime.fromisoformat(t)

            if s == "down":
                last = t

            if s == "up" and last:

                duration = t - last

                c.drawString(60, y, f"Down {last.strftime('%H:%M')}")
                y -= 15
                c.drawString(60, y, f"Up {t.strftime('%H:%M')}")
                y -= 15
                c.drawString(60, y, f"Duration {duration}")
                y -= 20

                last = None

        y -= 30

    c.save()

    await update.message.reply_document(open(file, "rb"))

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT, save))
app.add_handler(CommandHandler("report", report))

app.run_polling()
