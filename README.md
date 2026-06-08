# AI Email / Ticket Triage Agent

Telegram-based AI agent for classifying customer emails, support tickets, and business messages.

## What problem it solves

Support teams and small businesses often receive mixed messages: sales inquiries, complaints, refund requests, invoices, spam, and urgent issues.  
This agent helps classify messages, extract key information, set priority, and generate a draft reply.

## Main features

- Accepts pasted email or ticket text
- Classifies message category:
  - sales
  - support
  - complaint
  - refund
  - invoice
  - partnership
  - spam
  - urgent
  - other
- Assigns priority:
  - low
  - normal
  - high
  - urgent
- Extracts sender name and email when available
- Creates an internal summary
- Extracts important details
- Generates a draft reply
- Tracks message status
- CSV export
- PostgreSQL database
- Optional private access with `ALLOWED_CHAT_IDS`

## Example use case

User pastes:

> Hello, my order arrived damaged and I want a refund. Order number #12345.

The agent returns:

- category: refund / complaint
- priority: high
- summary of the issue
- extracted order number
- draft response for the support team

## Commands

```text
/start — start the bot
/triage text — analyze email or ticket
/emails — show all triaged messages
/email ID — show message details
/status ID status — update status
/report — show statistics
/export — export CSV
/clear — clear all data
/myid — show Telegram chat ID
```

## Statuses

```text
new
triaged
drafted
answered
archived
```

## Tech stack

- Python
- python-telegram-bot
- Groq API
- PostgreSQL
- Railway-compatible deployment

## Environment variables

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GROQ_API_KEY=your_groq_api_key
DATABASE_URL=your_postgres_database_url
ALLOWED_CHAT_IDS=
```

`ALLOWED_CHAT_IDS` is optional. If empty, the bot is open to everyone.

## How to run locally

```bash
pip install -r requirements.txt
python main.py
```

## How to deploy

The project includes a `Procfile`:

```text
worker: python main.py
```

It can be deployed to Railway or any service that supports Python workers.

## Portfolio value

This project demonstrates:

- AI ticket triage
- message classification
- priority scoring
- structured information extraction
- AI-generated draft replies
- support workflow automation
- CSV export
- database integration
