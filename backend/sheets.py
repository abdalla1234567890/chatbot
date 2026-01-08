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
            logger.info("Using GOOGLE_CREDENTIALS_JSON from environment")
            creds_dict = json.loads(creds_json)
        else:
            # التحميل من الملف المحلي (للتطوير)
            logger.info(f"Using local file: {CREDENTIALS_FILE}")
            with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
                creds_dict = json.load(f)
        
        # تصحيح مفتاح التشفير إذا كان يحتوي على escaped newlines
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

        gc = gspread.service_account_from_dict(creds_dict)
            
        sh = gc.open(GOOGLE_SHEET_NAME)
        try: worksheet = sh.worksheet("Sheet1")
        except: worksheet = sh.sheet1
        logger.info("✅ تم الاتصال بـ Google Sheets بنجاح")
    except Exception as e:
        logger.error(f"❌ خطأ Sheets: {e}")


def get_next_order_number():
    """الحصول على رقم الطلب التالي بناءً على آخر رقم في الشيت"""
    global worksheet
    if not worksheet:
        return 1
    try:
        all_values = worksheet.col_values(1)  # عمود رقم الطلب (العمود الأول)
        # تجاهل الصف الأول (العناوين) والبحث عن أرقام صالحة
        order_nums = []
        for v in all_values[1:]:
            try:
                order_nums.append(int(v))
            except (ValueError, TypeError):
                continue
        return max(order_nums) + 1 if order_nums else 1
    except Exception as e:
        logger.error(f"Error getting order number: {e}")
        return 1


def get_order_color(order_num):
    """إرجاع لون بناءً على رقم الطلب (تدوير بين ألوان محددة)"""
    colors = [
        {"red": 0.85, "green": 0.92, "blue": 0.95},  # أزرق فاتح
        {"red": 0.95, "green": 0.85, "blue": 0.85},  # وردي فاتح
        {"red": 0.85, "green": 0.95, "blue": 0.85},  # أخضر فاتح
        {"red": 0.95, "green": 0.95, "blue": 0.85},  # أصفر فاتح
        {"red": 0.92, "green": 0.85, "blue": 0.95},  # بنفسجي فاتح
        {"red": 0.95, "green": 0.9, "blue": 0.85},   # برتقالي فاتح
    ]
    return colors[order_num % len(colors)]


def save_to_sheet(data, summary, user_info):
    """حفظ الطلب في جوجل شيت باستخدام بيانات المستخدم من SQLite
    ملاحظة: لا يتم تضمين كود المستخدم السري في أسماء الملفات أو الأعمدة.
    يُرجع رقم الطلب في حالة النجاح، أو None في حالة الفشل.
    """
    global worksheet
    if not worksheet:
        init_google_sheets()
        if not worksheet:
            return None

    try:
        # الحصول على رقم الطلب التالي
        order_num = get_next_order_number()
        
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
                order_num,  # رقم الطلب (عمود جديد)
                timestamp,
                customer_name,
                customer_phone,
                item.get('cat', ''),
                desc,
                item.get('qty', ''),
                item.get('unit', ''),
                summary,
                "جديد",
                customer_address
                # Removed last two columns as requested
            ]
            rows.append(row)

        if rows:
            # الحصول على آخر صف قبل الإضافة
            current_row_count = len(worksheet.get_all_values())
            start_row = current_row_count + 1
            
            # إضافة الصفوف
            worksheet.append_rows(rows)
            
            # تطبيق اللون على الصفوف الجديدة
            end_row = start_row + len(rows) - 1
            color = get_order_color(order_num)
            
            # تنسيق الخلايا بلون الخلفية
            try:
                # Updated range to K (11 columns)
                cell_range = f"A{start_row}:K{end_row}"
                worksheet.format(cell_range, {
                    "backgroundColor": color
                })
                logger.info(f"✅ تم تطبيق اللون على الصفوف {start_row} إلى {end_row}")
            except Exception as format_error:
                logger.warning(f"⚠️ تعذر تطبيق اللون: {format_error}")
            
        logger.info(f"✅ تم حفظ الطلب #{order_num} بواسطة {customer_name}")
        return order_num
    except Exception as e:
        logger.error(f"Sheet error: {e}")
        print(f"DEBUG: Sheet Error Detailed: {e}")
        return None
