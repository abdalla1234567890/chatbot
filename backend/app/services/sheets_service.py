import gspread
import logging
import json
import os
import time
import threading
from datetime import datetime
from google.oauth2.service_account import Credentials
from app.core.config import settings

logger = logging.getLogger(__name__)

worksheet = None
_sheets_lock = threading.Lock()  # Prevent concurrent writes
_gc_client = None  # Shared gspread client


def init_google_sheets():
    global worksheet, _gc_client
    try:
        if settings.GOOGLE_CREDENTIALS_JSON:
            creds_dict = json.loads(settings.GOOGLE_CREDENTIALS_JSON)
        else:
            with open("credentials.json", 'r', encoding='utf-8') as f:
                creds_dict = json.load(f)
        
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

        _gc_client = gspread.service_account_from_dict(creds_dict)
        sh = _gc_client.open(settings.GOOGLE_SHEET_NAME)
        worksheet = sh.worksheet("الشات")
    except Exception as e:
        logger.error(f"❌ Sheets Init Error: {e}")

def get_next_order_number():
    if not worksheet: return 1001
    try:
        # Use retry mechanism since we are hitting the API
        values = _sheets_request_with_retry(worksheet.col_values, 1)
        if not values or len(values) <= 1: return 1001
        return int(values[-1]) + 1
    except:
        return 1001

def _sheets_request_with_retry(func, *args, max_retries=4, **kwargs):
    """Execute a Google Sheets API call with exponential backoff for rate limiting."""
    delay = 2
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except gspread.exceptions.APIError as e:
            if '429' in str(e) or 'RATE_LIMIT' in str(e).upper() or 'Quota' in str(e):
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ Google Sheets rate limit hit. Retrying in {delay}s... (attempt {attempt+1})")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                    continue
            raise  # Re-raise non-rate-limit errors
    return None


def save_to_sheet(data, summary, user_info, background_tasks=None):
    global worksheet
    if not worksheet:
        init_google_sheets()
        if not worksheet: return None

    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        res = None

        # ✅ Lock ensures only one write happens at a time AND numbering is sequential
        with _sheets_lock:
            order_num = get_next_order_number()
            rows = []

            for item in data.get('items', []):
                short_desc = f"{item.get('item', '')} {item.get('s1_v', '')} {item.get('s2_v', '')} {item.get('s3_v', '')}".strip()
                row = [
                    order_num, timestamp, user_info.name, user_info.phone,
                    item.get('cat', ''), short_desc, item.get('qty', ''), item.get('unit', ''),
                    summary, data.get('c', {}).get('a', ''), item.get('tech_desc', summary)
                ]
                rows.append(row)

            if rows:
                res = _sheets_request_with_retry(worksheet.append_rows, rows)
            
            # Apply color to the appended rows based on order_num
            if res:
                try:
                    updated_range = res.get('updates', {}).get('updatedRange')
                    if updated_range:
                        colors = [
                            {"red": 0.95, "green": 0.98, "blue": 1.0},
                            {"red": 1.0, "green": 0.98, "blue": 0.95},
                            {"red": 0.95, "green": 1.0, "blue": 0.95},
                            {"red": 0.98, "green": 0.95, "blue": 1.0},
                            {"red": 1.0, "green": 0.95, "blue": 0.98},
                            {"red": 1.0, "green": 1.0, "blue": 1.0},
                        ]
                        color = colors[order_num % len(colors)]
                        clean_range = updated_range.split("!")[-1] if "!" in updated_range else updated_range
                        _sheets_request_with_retry(worksheet.format, clean_range, {"backgroundColor": color})
                except Exception as e:
                    logger.error(f"Error styling rows: {e}")

            # Classification in background (non-blocking)
            from app.services.classifier import process_and_save_classification
            for idx, row in enumerate(rows):
                item_id = f"{order_num}-{idx+1}" if len(rows) > 1 else order_num
                if background_tasks:
                    background_tasks.add_task(process_and_save_classification, worksheet.spreadsheet, item_id, row[10])
        
        return order_num
    except Exception as e:
        logger.error(f"Sheet error: {e}")
        return None
