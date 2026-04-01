
import gspread
import json
import os
import sys
import codecs

sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

CREDENTIALS_FILE = "credentials.json"
SHEET_NAME = "الشات والتصنيفات"

# Target Sheet Names
SHEET_CHAT = "الشات"
SHEET_CLASS = "التصنيفات"
SHEET_TAXONOMY_NEW = "Taxonomy_New"

# Columns
HEADERS_CHAT = [
    "رقم الطلب", "التاريخ", "اسم العميل", "رقم الجوال", 
    "الفئة", "الوصف", "الكمية", "الوحدة", 
    "ملخص الطلب", "الحالة", "العنوان", "الوصف الكامل"
]

HEADERS_CLASS = [
    "رقم الطلب", 
    "الطلب الأصلي", 
    "التصنيف الأساسي (AR)", "Basic Category (EN)",
    "التصنيف الرئيسي (AR)", "Main Category (EN)",
    "التصنيف الفرعي (AR)", "Sub Category (EN)",
    "اسم المواصفة 1", "قيمتها",
    "اسم المواصفة 2", "قيمتها",
    "كود التصنيف",
    "وقت التصنيف"
]

HEADERS_TAXONOMY = [
    "Basic (Ar)", "Basic (En)", "Main (Ar)", "Main (En)", "Sub (Ar)", "Sub (En)", "Code",
    "اسم المواصفة 1", "اسم المواصفة 2"
]

def setup_headers():
    if not os.path.exists(CREDENTIALS_FILE):
        print("❌ Credentials file missing.")
        return

    try:
        with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
             creds = json.load(f)
        
        gc = gspread.service_account_from_dict(creds)
        sh = gc.open(SHEET_NAME)
        
        print(f"🔧 Update Headers for: {SHEET_NAME}")

        # 1. Setup Chat Sheet
        try:
            ws_chat = sh.worksheet(SHEET_CHAT)
            current_headers = ws_chat.row_values(1)
            if not current_headers:
                print(f"   Writing headers to '{SHEET_CHAT}'...")
                ws_chat.update(range_name="A1:L1", values=[HEADERS_CHAT])
                ws_chat.format("A1:L1", {"textFormat": {"bold": True}})
                print("   ✅ Done.")
            else:
                print(f"   ℹ️ '{SHEET_CHAT}' already has headers.")
        except gspread.exceptions.WorksheetNotFound:
            print(f"   ⚠️ Sheet '{SHEET_CHAT}' not found. Creating it...")
            ws_chat = sh.add_worksheet(title=SHEET_CHAT, rows=1000, cols=12)
            ws_chat.update(range_name="A1:L1", values=[HEADERS_CHAT])
            print("   ✅ Created and initialized.")

        # 2. Setup Classifications Sheet
        try:
            ws_class = sh.worksheet(SHEET_CLASS)
            current_headers = ws_class.row_values(1)
            # Always ensure we have enough columns and correct headers for the new system
            if len(current_headers) < len(HEADERS_CLASS):
                print(f"   Updating headers for '{SHEET_CLASS}'...")
                ws_class.update(range_name=f"A1:{chr(64+len(HEADERS_CLASS))}1", values=[HEADERS_CLASS])
                ws_class.format(f"A1:{chr(64+len(HEADERS_CLASS))}1", {"textFormat": {"bold": True}})
                print("   ✅ Updated.")
            else:
                print(f"   ℹ️ '{SHEET_CLASS}' headers are up to date.")
        except gspread.exceptions.WorksheetNotFound:
            print(f"   ⚠️ Sheet '{SHEET_CLASS}' not found. Creating it...")
            ws_class = sh.add_worksheet(title=SHEET_CLASS, rows=1000, cols=len(HEADERS_CLASS))
            ws_class.update(range_name=f"A1:{chr(64+len(HEADERS_CLASS))}1", values=[HEADERS_CLASS])
            print("   ✅ Created and initialized.")

        # 3. Update Taxonomy_New Headers if necessary
        try:
            ws_tax = sh.worksheet(SHEET_TAXONOMY_NEW)
            current_tax_headers = ws_tax.row_values(1)
            if len(current_tax_headers) < len(HEADERS_TAXONOMY):
                 print(f"   Updating headers for '{SHEET_TAXONOMY_NEW}'...")
                 ws_tax.update(range_name=f"A1:{chr(64+len(HEADERS_TAXONOMY))}1", values=[HEADERS_TAXONOMY])
                 ws_tax.format(f"A1:{chr(64+len(HEADERS_TAXONOMY))}1", {"textFormat": {"bold": True}})
                 print("   ✅ Updated taxonomy headers.")
        except gspread.exceptions.WorksheetNotFound:
            print(f"   ⚠️ Sheet '{SHEET_TAXONOMY_NEW}' not found.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    setup_headers()
