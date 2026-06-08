import os, logging, csv, io
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

from database import init_db, save_email, get_email, list_emails, update_status, report, clear_all
from ai_service import analyze_email

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED = os.getenv("ALLOWED_CHAT_IDS", "")
STATUSES = ["new", "triaged", "drafted", "answered", "archived"]


def ids():
    result=set()
    for x in ALLOWED.split(","):
        x=x.strip()
        if x:
            try: result.add(int(x))
            except: pass
    return result


def ok(chat_id):
    allowed=ids()
    return True if not allowed else chat_id in allowed


async def deny(update):
    if ok(update.effective_chat.id): return False
    if update.message: await update.message.reply_text("Доступ закритий 🔒")
    elif update.callback_query: await update.callback_query.answer("Доступ закритий", show_alert=True)
    return True


def kb():
    return ReplyKeyboardMarkup([["📥 Emails", "📊 Report"], ["➕ Help"]], resize_keyboard=True)


def buttons(email_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👁 View", callback_data=f"view:{email_id}"),
         InlineKeyboardButton("✅ Answered", callback_data=f"status:{email_id}:answered")],
        [InlineKeyboardButton("📁 Archived", callback_data=f"status:{email_id}:archived")]
    ])


def short(t, l=500):
    if not t: return "—"
    return t if len(str(t)) <= l else str(t)[:l] + "..."


def format_email(e):
    return (
        f"Email #{e['id']}\n\n"
        f"Status: {e.get('status')}\n"
        f"Category: {e.get('category')}\n"
        f"Priority: {e.get('priority')}\n"
        f"Sender: {e.get('sender_name') or '—'} <{e.get('sender_email') or '—'}>\n\n"
        f"Summary:\n{short(e.get('summary'), 800)}\n\n"
        f"Extracted data:\n{short(e.get('extracted_data'), 800)}\n\n"
        f"Draft subject:\n{e.get('draft_subject') or '—'}\n\n"
        f"Draft body:\n{short(e.get('draft_body'), 1200)}"
    )


def help_text():
    return (
        "AI Email/Ticket Triage Agent 🤖\n\n"
        "Встав текст email/заявки — бот класифікує, визначить пріоритет, витягне дані і створить draft відповіді.\n\n"
        "Команди:\n"
        "/triage text — обробити email\n"
        "/emails — список\n"
        "/email ID — деталі\n"
        "/status ID status — статус\n"
        "/report — звіт\n"
        "/export — CSV\n"
        "/clear — очистити\n"
        "/myid — chat_id"
    )


async def start(update, context):
    if await deny(update): return
    await update.message.reply_text("Привіт! Це AI Email/Ticket Triage Agent.\n\n" + help_text(), reply_markup=kb())


async def help_command(update, context):
    if await deny(update): return
    await update.message.reply_text(help_text(), reply_markup=kb())


async def myid(update, context):
    await update.message.reply_text(f"Твій chat_id:\n{update.effective_chat.id}")


async def process(update, raw_text):
    msg = await update.effective_message.reply_text("Аналізую email... 🔎")
    analysis = analyze_email(raw_text)
    email_id = save_email(update.effective_chat.id, raw_text, analysis)
    e = get_email(email_id, update.effective_chat.id)
    await msg.edit_text("Email triaged ✅\n\n" + format_email(e), reply_markup=buttons(email_id))


async def triage_command(update, context):
    if await deny(update): return
    if not context.args:
        await update.message.reply_text("Формат: /triage text")
        return
    await process(update, " ".join(context.args))


async def emails_command(update, context):
    if await deny(update): return
    rows = list_emails(update.effective_chat.id)
    if not rows:
        await update.message.reply_text("Email-ів поки немає.")
        return
    lines=["Emails:\n"]
    for e in rows:
        lines.append(f"{e['id']}. {e.get('category')} | {e.get('priority')} | {e.get('status')}\n   {short(e.get('summary'), 120)}")
    await update.message.reply_text("\n\n".join(lines))


async def email_command(update, context):
    if await deny(update): return
    if not context.args:
        await update.message.reply_text("Формат: /email ID")
        return
    try:
        email_id=int(context.args[0])
        e=get_email(email_id, update.effective_chat.id)
        await update.message.reply_text(format_email(e), reply_markup=buttons(email_id))
    except Exception:
        await update.message.reply_text("Не знайшов email або ID неправильний.")


async def status_command(update, context):
    if await deny(update): return
    if len(context.args)<2:
        await update.message.reply_text("Формат: /status ID status")
        return
    try:
        email_id=int(context.args[0])
        status=context.args[1]
        if status not in STATUSES:
            await update.message.reply_text("Доступні: " + ", ".join(STATUSES))
            return
        updated=update_status(email_id, update.effective_chat.id, status)
        await update.message.reply_text("Статус оновлено ✅" if updated else "Email не знайдено.")
    except ValueError:
        await update.message.reply_text("ID має бути числом.")


async def report_command(update, context):
    if await deny(update): return
    r=report(update.effective_chat.id)
    lines=["Email triage report 📊\n", "By category:"]
    for row in r["by_category"]:
        lines.append(f"- {row['category']}: {row['count']}")
    lines.append("\nBy priority:")
    for row in r["by_priority"]:
        lines.append(f"- {row['priority']}: {row['count']}")
    await update.message.reply_text("\n".join(lines))


async def export_command(update, context):
    if await deny(update): return
    rows=list_emails(update.effective_chat.id, limit=1000)
    if not rows:
        await update.message.reply_text("Немає даних для export.")
        return
    output=io.StringIO()
    fields=["id","status","category","priority","sender_name","sender_email","summary","extracted_data","draft_subject","draft_body","created_at"]
    writer=csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for r in rows: writer.writerow({f:r.get(f) for f in fields})
    bio=io.BytesIO(output.getvalue().encode("utf-8-sig"))
    bio.name="triaged_emails.csv"
    await update.message.reply_document(InputFile(bio, filename="triaged_emails.csv"), caption="Export готовий ✅")


async def clear_command(update, context):
    if await deny(update): return
    clear_all(update.effective_chat.id)
    await update.message.reply_text("Очищено ✅")


async def handle_keyboard(update):
    if update.message.text=="📥 Emails":
        class C: args=[]
        await emails_command(update, C())
        return True
    if update.message.text=="📊 Report":
        class C: args=[]
        await report_command(update, C())
        return True
    if update.message.text=="➕ Help":
        await update.message.reply_text(help_text(), reply_markup=kb())
        return True
    return False


async def handle_message(update, context):
    if await deny(update): return
    if await handle_keyboard(update): return
    await process(update, update.message.text)


async def button(update, context):
    q=update.callback_query
    if not q: return
    await q.answer()
    if not ok(q.message.chat_id):
        await q.message.reply_text("Доступ закритий 🔒")
        return
    try:
        parts=q.data.split(":")
        action=parts[0]
        email_id=int(parts[1])
        if action=="view":
            e=get_email(email_id, q.message.chat_id)
            await q.message.reply_text(format_email(e), reply_markup=buttons(email_id))
        elif action=="status":
            status=parts[2]
            update_status(email_id, q.message.chat_id, status)
            await q.message.reply_text(f"Email {email_id} status → {status} ✅")
    except Exception as e:
        await q.message.reply_text(f"Помилка: {type(e).__name__}: {e}")


def main():
    if not TOKEN: raise RuntimeError("TELEGRAM_BOT_TOKEN не знайдено")
    init_db()
    app=ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("triage", triage_command))
    app.add_handler(CommandHandler("emails", emails_command))
    app.add_handler(CommandHandler("email", email_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(CommandHandler("export", export_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Email Triage Agent is running...")
    app.run_polling()


if __name__=="__main__":
    main()
