import base64
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from email.message import EmailMessage

from django.utils import timezone


BILL_QUERY = '(bill OR invoice OR due OR payment OR subscription OR statement OR "amount due") newer_than:90d'
AMOUNT_RE = re.compile(r"(?:rs\.?|inr|₹)\s*([0-9][0-9,]*(?:\.\d{1,2})?)", re.IGNORECASE)
DATE_PATTERNS = [
    re.compile(r"(?:due date|pay by|before|on or before)[:\s-]*(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", re.IGNORECASE),
    re.compile(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", re.IGNORECASE),
]
SERVICE_HINTS = [
    "Netflix", "Spotify", "Amazon", "Electricity", "Rent", "EMI", "Water",
    "Airtel", "Jio", "Vi", "Credit Card", "Loan", "Insurance", "Broadband",
]


@dataclass
class SuggestedBill:
    message_id: str
    subject: str
    service: str
    amount: Decimal
    due_date: date
    category: str
    snippet: str


def gmail_dependencies_ready():
    try:
        import google_auth_oauthlib.flow  # noqa: F401
        import googleapiclient.discovery  # noqa: F401
    except ImportError:
        return False
    return True


def build_flow(settings):
    from google_auth_oauthlib.flow import Flow

    return Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            }
        },
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )


def service_from_credentials(credentials_dict):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    credentials = Credentials(**credentials_dict)
    return build("gmail", "v1", credentials=credentials)


def credentials_to_dict(credentials):
    return {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }


def extract_subject(payload):
    for header in payload.get("headers", []):
        if header.get("name", "").lower() == "subject":
            return header.get("value", "Bill reminder")
    return "Bill reminder"


def extract_text(payload):
    chunks = []
    for part in payload.get("parts", []) or []:
        body = part.get("body", {})
        data = body.get("data")
        mime = part.get("mimeType", "")
        if data and mime in {"text/plain", "text/html"}:
            decoded = base64.urlsafe_b64decode(data + "===")
            chunks.append(decoded.decode("utf-8", errors="ignore"))
    body_data = payload.get("body", {}).get("data")
    if body_data:
        decoded = base64.urlsafe_b64decode(body_data + "===")
        chunks.append(decoded.decode("utf-8", errors="ignore"))
    return " ".join(chunks)


def clean_amount(text):
    match = AMOUNT_RE.search(text)
    if not match:
        return None
    try:
        return Decimal(match.group(1).replace(",", "")).quantize(Decimal("1"))
    except InvalidOperation:
        return None


def clean_due_date(text):
    for pattern in DATE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        day, month, year = [int(value) for value in match.groups()]
        if year < 100:
            year += 2000
        try:
            return date(year, month, day)
        except ValueError:
            continue
    return timezone.localdate()


def guess_service(text, subject):
    combined = f"{subject} {text}"
    for hint in SERVICE_HINTS:
        if hint.lower() in combined.lower():
            return hint
    words = re.findall(r"[A-Z][A-Za-z]{2,}", subject)
    return words[0] if words else "Imported Bill"


def guess_category(service):
    service_lower = service.lower()
    if service_lower in {"netflix", "spotify", "amazon"}:
        return "Subscription"
    if service_lower in {"electricity", "water", "broadband", "airtel", "jio", "vi"}:
        return "Utilities"
    if "card" in service_lower or "loan" in service_lower or "emi" in service_lower:
        return "Finance"
    if "rent" in service_lower:
        return "Housing"
    return "Bills"


def fetch_suggested_bills(credentials_dict, existing_message_ids):
    service = service_from_credentials(credentials_dict)
    response = service.users().messages().list(userId="me", q=BILL_QUERY, maxResults=10).execute()
    suggestions = []
    for item in response.get("messages", []):
        message_id = item["id"]
        if message_id in existing_message_ids:
            continue
        message = service.users().messages().get(userId="me", id=message_id, format="full").execute()
        payload = message.get("payload", {})
        subject = extract_subject(payload)
        text = extract_text(payload) or message.get("snippet", "")
        amount = clean_amount(f"{subject} {text}")
        if amount is None:
            continue
        due_date = clean_due_date(f"{subject} {text}")
        service_name = guess_service(text, subject)
        suggestions.append(SuggestedBill(
            message_id=message_id,
            subject=subject[:255],
            service=service_name,
            amount=amount,
            due_date=due_date,
            category=guess_category(service_name),
            snippet=message.get("snippet", "")[:240],
        ))
    return suggestions
