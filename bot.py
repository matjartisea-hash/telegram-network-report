from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
import sqlite3
import re
from datetime import datetime, date, time
from reportlab.pdfgen import canvas

TOKEN="8583886234:AAEPcKBCyH0823cO4WYXc9dx0CObYfbo2Zs"
CHAT_ID=1995981496

db = sqlite3.connect("events.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS events(
ip TEXT,
status TEXT,
time TEXT
)
""")

def get_ip(text):
    m = re.search(r'IP:\s*(\d+\.\d+\.\d+\.\d+)', text)
    if m:
        return m.group(1)

async def save(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.chat_id != CHAT_ID:
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

    cursor.execute("INSERT INTO events VALUES(?,?,?)",(ip,status,now))
    db.commit()

def build_pdf(rows, filename):

    devices = {}

    for ip,status,t in rows:
        devices.setdefault(ip,[]).append((status,t))

    c = canvas.Canvas(filename)
    y = 800

    for ip,events in devices.items():

        c.drawString(50,y,f"Device: {ip}")
        y-=20

        last=None
        count=0

        for s,t in events:

            t=datetime.fromisoformat(t)

            if s=="down":
                last=t

            elif s=="up" and last:

                duration=t-last

                c.drawString(60,y,f"Down: {last.strftime('%H:%M')}")
                y-=15
                c.drawString(60,y,f"Up: {t.strftime('%H:%M')}")
                y-=15
                c.drawString(60,y,f"Duration: {duration}")
                y-=20

                count+=1
                last=None

        c.drawString(60,y,f"Total outages: {count}")
        y-=40

    c.save()

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):

    today=str(date.today())

    cursor.execute("SELECT * FROM events WHERE time LIKE ?",(f"{today}%",))
    rows=cursor.fetchall()

    file="report_today.pdf"

    build_pdf(rows,file)

    await update.message.reply_document(open(file,"rb"))

async def report_range(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args)!=2:
        await update.message.reply_text("اكتب: /report_range 2026-03-01 2026-03-09")
        return

    start=context.args[0]
    end=context.args[1]

    cursor.execute("""
    SELECT * FROM events
    WHERE date(time) BETWEEN ? AND ?
    """,(start,end))

    rows=cursor.fetchall()

    file="report_range.pdf"

    build_pdf(rows,file)

    await update.message.reply_document(open(file,"rb"))

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):

    cursor.execute("""
    SELECT ip,COUNT(*)
    FROM events
    WHERE status='down'
    GROUP BY ip
    ORDER BY COUNT(*) DESC
    LIMIT 10
    """)

    rows=cursor.fetchall()

    text="الأجهزة الأكثر انقطاعاً:\n\n"

    for ip,count in rows:
        text+=f"{ip} : {count} مرات\n"

    await update.message.reply_text(text)

async def nightly_report(context: ContextTypes.DEFAULT_TYPE):

    today=str(date.today())

    cursor.execute("SELECT * FROM events WHERE time LIKE ?",(f"{today}%",))
    rows=cursor.fetchall()

    file="night_report.pdf"

    build_pdf(rows,file)

    await context.bot.send_document(chat_id=CHAT_ID,document=open(file,"rb"))

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT,save))
app.add_handler(CommandHandler("report",report))
app.add_handler(CommandHandler("report_range",report_range))
app.add_handler(CommandHandler("top",top))

app.job_queue.run_daily(nightly_report,time(hour=0,minute=0))

app.run_polling()
