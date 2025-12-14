import gspread
import logging
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
import base64
import io
from PIL import Image

logger = logging.getLogger(__name__)

GOOGLE_SHEET_NAME = "طلبات"
CREDENTIALS_FILE = "credentials.json"

worksheet = None
drive_service = None

import os
import json

def init_google_sheets():
    """تهيئة الاتصال بجوجل شيت والـ Drive"""
    global worksheet, drive_service
    try:
        # محاولة التحميل من متغير البيئة أولاً (للإنتاج)
        creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
        if creds_json:
            creds_dict = json.loads(creds_json)
            gc = gspread.service_account_from_dict(creds_dict)
        else:
            # التحميل من الملف المحلي (للتطوير)
            gc = gspread.service_account(filename=CREDENTIALS_FILE)
            
        sh = gc.open(GOOGLE_SHEET_NAME)
        try: worksheet = sh.worksheet("Sheet1")
        except: worksheet = sh.sheet1
        logger.info("✅ تم الاتصال بـ Google Sheets")
    except Exception as e:
        logger.error(f"❌ خطأ Sheets: {e}")



def save_to_sheet(data, summary, user_info):
    """حفظ الطلب في جوجل شيت باستخدام بيانات المستخدم من SQLite
    ملاحظة: لا يتم تضمين كود المستخدم السري في أسماء الملفات أو الأعمدة.
    """
    if not worksheet:
        init_google_sheets()
        if not worksheet:
            return False

    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        rows = []

        # بيانات العميل (آمنة: لا نستخدم الكود السري هنا)
        customer_name = user_info.get('name', '')
        customer_phone = user_info.get('phone', '')
        customer_address = data.get('c', {}).get('a', '')

        for item in data.get('items', []):
            desc_parts = [item.get(k, '') for k in ('item', 's1', 's2', 's3')]
            desc = " ".join([p for p in desc_parts if p]).strip()

            row = [
                timestamp,
                customer_name,
                customer_phone,
                item.get('cat', ''),
                desc,
                item.get('qty', ''),
                item.get('unit', ''),
                summary,
                "جديد",
                customer_address,
                "", # Image URL column left empty
                customer_name  # عمود إضافي للاسم فقط، بدون كود سري
            ]
            rows.append(row)

        if rows:
            worksheet.append_rows(rows)
        logger.info(f"✅ تم حفظ الطلب بواسطة {customer_name}")
        return True
    except Exception as e:
        logger.error(f"Sheet error: {e}")
        print(f"DEBUG: Sheet Error Detailed: {e}")
        return False
