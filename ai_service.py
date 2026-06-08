import os, json
from groq import Groq

MODEL = "llama-3.3-70b-versatile"


def client():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY не знайдено")
    return Groq(api_key=key)


def clean(text):
    text = text.strip()
    if text.startswith("```json"):
        text = text.replace("```json", "", 1).strip()
    if text.startswith("```"):
        text = text.replace("```", "", 1).strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    return text


def analyze_email(raw_text: str) -> dict:
    system = """
You are an AI email/ticket triage assistant.

Analyze the pasted email or customer message.
Return only valid JSON.

Categories:
sales, support, complaint, refund, invoice, partnership, spam, urgent, other

Priority:
low, normal, high, urgent

JSON:
{
  "sender_name": "string or null",
  "sender_email": "string or null",
  "category": "sales | support | complaint | refund | invoice | partnership | spam | urgent | other",
  "priority": "low | normal | high | urgent",
  "summary": "short internal summary",
  "extracted_data": "important details: order number, product, phone, deadline, etc.",
  "draft_subject": "subject for reply",
  "draft_body": "polite draft response"
}
"""
    response = client().chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": raw_text}],
        temperature=0.3,
    )
    raw = clean(response.choices[0].message.content)
    try:
        return json.loads(raw)
    except Exception:
        return {
            "sender_name": None,
            "sender_email": None,
            "category": "other",
            "priority": "normal",
            "summary": raw[:800],
            "extracted_data": "",
            "draft_subject": "Re: Your message",
            "draft_body": raw,
        }
