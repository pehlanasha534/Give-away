import sqlite3, re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = "8788292264:AAHS3MwgkrCp6MeXd9AUzl_wLIumGrgEt8k"
OWNER_ID = 2125181132
SUPPORT = "@Hey_shiva"

WELCOME_TEXT = """📜 BOT RULES & GUIDELINES 📜

1️⃣ Payment Policy
- Payment refundable नहीं होगा
- Payment करने के बाद ही आगे process होगा

2️⃣ Automatic Link System
- Bot आपको automatically एक invite link generate करके देगा
- Link केवल 24 hours तक ही valid रहेगा
- 24 hours के बाद link expire हो जाएगा

3️⃣ Link Usage
- एक link से सिर्फ 1 user ही join कर सकता है
- Link को किसी के साथ share न करें

4️⃣ Group Access Rules
- Join होने के बाद group को leave न करें
- अगर आप group leave करते हैं, तो दुबारा join करने के लिए ₹20 pay करना होगा
- Payment के बाद ही group access दोबारा मिलेगा

5️⃣ Group Backup
- अगर कोई group ban हो जाता है
- तो उसका नया link आपको bot पर ही मिल जाएगा

6️⃣ Support
- अगर आपको कोई भी समस्या होती है
- तो @hey_shiva DM
- आपको 48 hours के अंदर reply मिल जाएगा

⚠️ Rules violate करने पर बिना warning के ban किया जा सकता है!
📌 Support: Bot पर message करें
❤️ Thank you for choosing us!"""

conn = sqlite3.connect("premium.db", check_same_thread=False)
conn.execute("CREATE TABLE IF NOT EXISTS channels (channel_id TEXT PRIMARY KEY, title TEXT)")
conn.execute("CREATE TABLE IF NOT EXISTS plans (period TEXT PRIMARY KEY, price TEXT, days INTEGER)")
conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER, channel_id TEXT, expire_at TEXT, PRIMARY KEY(user_id, channel_id))")
conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
conn.commit()
conn.execute("INSERT OR IGNORE INTO plans VALUES ('1m','99',30)")
conn.execute("INSERT OR IGNORE INTO plans VALUES ('3m','199',90)")
conn.execute("INSERT OR IGNORE INTO plans VALUES ('life','499',3650)")
conn.commit()

def is_owner(uid): return uid == OWNER_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("💳 Buy Premium", callback_data="buy_plans")]])
    msg = await update.message.reply_text(WELCOME_TEXT, reply_markup=kb)
    try: await context.bot.pin_chat_message(update.effective_chat.id, msg.message_id, disable_notification=True)
    except: pass

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    if not context.args: return await update.message.reply_text("Use: /add -100xxx")
    cid = context.args[0]
    try:
        chat = await context.bot.get_chat(cid)
        conn.execute("INSERT OR REPLACE INTO channels VALUES (?,?)", (cid, chat.title))
        conn.commit()
        await update.message.reply_text(f"✅ Added: {chat.title}")
    except Exception as e: await update.message.reply_text(f"Error: Admin banao\n{e}")

async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    cur = conn.execute("SELECT * FROM channels")
    rows = cur.fetchall()
    if not rows: return await update.message.reply_text("No channels")
    txt = "📋 Channels:\n\n"
    for cid, t in rows: txt+=f"• {t}\n`{cid}`\n\n"
    await update.message.reply_text(txt, parse_mode="Markdown")

async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    conn.execute("DELETE FROM channels WHERE channel_id=?", (context.args[0],))
    conn.commit()
    await update.message.reply_text("✅ Removed")

async def set_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    if update.message.photo:
        fid = update.message.photo[-1].file_id
        conn.execute("INSERT OR REPLACE INTO settings VALUES ('qr',?)", (fid,))
        conn.commit()
        await update.message.reply_text("✅ QR Set ho gaya! Ab user ko yahi jayega.")
        context.user_data["await_qr"]=False
    else:
        context.user_data["await_qr"]=True
        await update.message.reply_text("Ab QR ki photo bhej do, set kar dunga.")

async def plans_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    text = update.message.text.replace("/plans","").strip()
    if text:
        for line in re.split(r'[\n,]+', text):
            m = re.search(r'(1\s*m|3\s*m|life|1\s*month|3\s*month|lifetime).*?(\d+)', line.lower())
            if m:
                raw, price = m.group(1), m.group(2)
                if '1' in raw: p,d='1m',30
                elif '3' in raw: p,d='3m',90
                else: p,d='life',3650
                conn.execute("INSERT OR REPLACE INTO plans VALUES (?,?,?)", (p, price, d))
        conn.commit()
        await update.message.reply_text("✅ Plans Set!")

    cur = conn.execute("SELECT period, price FROM plans ORDER BY days")
    mp = {'1m':'1 month','3m':'3 months','life':'Lifetime'}
    txt="💰 Current Plans:\n\n"
    for per, pr in cur.fetchall(): txt+=f"{mp.get(per,per)} - {pr} rs\n"
    txt+="\nSet: /plans\n1 month - 99 rs\n3 months - 199 rs\nLifetime - 499 rs\n\nReset: /planreset"
    await update.message.reply_text(txt)

async def reset_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    conn.execute("DELETE FROM plans")
    conn.commit()
    await update.message.reply_text("✅ Plans reset! Naya set karo /plans se")

async def members_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    cur = conn.execute("SELECT channel_id, title FROM channels")
    chans = cur.fetchall()
    kb = [[InlineKeyboardButton(t, callback_data=f"mem_{c}")] for c,t in chans]
    await update.message.reply_text("Group select karo:", reply_markup=InlineKeyboardMarkup(kb))

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    await context.bot.ban_chat_member(context.args[1], int(context.args[0]))
    await update.message.reply_text("✅ Banned")

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    await context.bot.unban_chat_member(context.args[1], int(context.args[0]))
    await update.message.reply_text("✅ Unbanned")

async def check_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    cur = conn.execute("SELECT user_id, channel_id, expire_at FROM users")
    c=0
    for uid, cid, exp in cur.fetchall():
        if datetime.fromisoformat(exp) < datetime.now():
            try:
                await context.bot.ban_chat_member(cid, uid)
                await context.bot.unban_chat_member(cid, uid)
                await context.bot.send_message(uid, "⚠️ Apka plan khatam hua hai. Recharge /start se")
                c+=1
            except: pass
            conn.execute("DELETE FROM users WHERE user_id=? AND channel_id=?", (uid, cid))
    conn.commit()
    await update.message.reply_text(f"✅ {c} removed")

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    if data == "buy_plans":
        cur = conn.execute("SELECT period, price FROM plans ORDER BY days")
        kb=[]
        mp={'1m':'1 month','3m':'3 months','life':'Lifetime'}
        for per, pr in cur.fetchall(): kb.append([InlineKeyboardButton(f"{mp.get(per,per)} - {pr} rs", callback_data=f"sel_{per}")])
        await q.message.reply_text("Plan Select Karo:", reply_markup=InlineKeyboardMarkup(kb))
    elif data.startswith("sel_"):
        per = data.split("_")[1]
        price = conn.execute("SELECT price FROM plans WHERE period=?", (per,)).fetchone()[0]
        qr = conn.execute("SELECT value FROM settings WHERE key='qr'").fetchone()
        if not qr: return await q.message.reply_text("❌ QR set nahi hai! Owner pehle QR set karo.")
        context.user_data["buy_period"]=per
        context.user_data["await_ss"]=False
        mp={'1m':'1 month','3m':'3 months','life':'Lifetime'}
        kb=InlineKeyboardMarkup([[InlineKeyboardButton("✅ I have sent (मैंने भेजा है)", callback_data=f"sent_{per}")],[InlineKeyboardButton("❌ I have not sent (मैंने नहीं भेजा है)", callback_data="not_sent")]])
        await context.bot.send_photo(q.from_user.id, qr[0], caption=f"{mp.get(per,per)} - {price} rs\nPay karke screenshot bhejo to {SUPPORT}", reply_markup=kb)
    elif data.startswith("sent_"):
        context.user_data["await_ss"]=True
        await q.message.reply_text("Ab payment screenshot bhejo yaha.")
    elif data=="not_sent":
        await q.message.reply_text("Pehle pay karo")
    elif data.startswith("mem_"):
        cid=data.split("_",1)[1]
        rows=conn.execute("SELECT user_id, expire_at FROM users WHERE channel_id=?", (cid,)).fetchall()
        if not rows: return await q.message.reply_text("Koi premium member nahi")
        txt=f"Members {cid}:\n\n"
        for uid, exp in rows: txt+=f"👤 {uid} - Till {exp[:10]}\n"
        await q.message.reply_text(txt)
    elif data.startswith("approve_"):
        _, uid, per = data.split("_")
        uid=int(uid)
        for (cid,) in conn.execute("SELECT channel_id FROM channels").fetchall():
            try:
                link=await context.bot.create_chat_invite_link(chat_id=cid, member_limit=1, expire_date=datetime.now()+timedelta(hours=24))
                await context.bot.send_message(uid, f"✅ Approved!\nLink (24hr, 1-time):\n{link.invite_link}")
                days=conn.execute("SELECT days FROM plans WHERE period=?", (per,)).fetchone()[0]
                exp=datetime.now()+timedelta(days=days)
                conn.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (uid, cid, exp.isoformat()))
            except Exception as e: await q.message.reply_text(f"Error {cid}: {e}")
        conn.commit()
        await q.edit_message_text(f"✅ Approved {uid}")
    elif data.startswith("reject_"):
        uid=int(data.split("_")[1])
        await context.bot.send_message(uid, f"❌ Rejected {SUPPORT}")
        await q.edit_message_text("Rejected")

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # QR SET - Owner ke liye
    if is_owner(update.effective_user.id) and not context.user_data.get("await_ss"):
        fid = update.message.photo[-1].file_id
        conn.execute("INSERT OR REPLACE INTO settings VALUES ('qr',?)", (fid,))
        conn.commit()
        context.user_data["await_qr"]=False
        await update.message.reply_text("✅ QR Set ho gaya! Final wala.")
        return

    # User ka screenshot
    if not context.user_data.get("await_ss"): return
    per=context.user_data.get("buy_period","1m")
    uid=update.effective_user.id
    kb=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Approve", callback_data=f"approve_{uid}_{per}"), InlineKeyboardButton("❌ Reject", callback_data=f"reject_{uid}")]])
    await context.bot.send_photo(OWNER_ID, update.message.photo[-1].file_id, caption=f"🔔 Payment\nUser:{uid} @{update.effective_user.username}\nPlan:{per}", reply_markup=kb)
    await update.message.reply_text("✅ Screenshot owner ko bhej diya, link approve hote hi ayega.")
    context.user_data["await_ss"]=False

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add_channel))
app.add_handler(CommandHandler("list", list_channels))
app.add_handler(CommandHandler("remove", remove_channel))
app.add_handler(CommandHandler("qr", set_qr))
app.add_handler(CommandHandler("plans", plans_cmd))
app.add_handler(CommandHandler("planreset", reset_plans))
app.add_handler(CommandHandler("members", members_cmd))
app.add_handler(CommandHandler("ban", ban_cmd))
app.add_handler(CommandHandler("unban", unban_cmd))
app.add_handler(CommandHandler("check", check_cmd))
app.add_handler(CallbackQueryHandler(callbacks))
app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
print("Bot Running - QR Fixed Final")
app.run_polling()
