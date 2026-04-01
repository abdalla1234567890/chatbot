"""
سكريبت لتنسيق شيتات Google Sheets كجداول احترافية
- حدود (borders) لجميع الخلايا
- تنسيق الهيدر (خلفية ملونة، خط عريض، وسط)
- تجميد الصف الأول
- Auto-filter
"""

import json
import gspread
import os
import time

CREDENTIALS_FILE = "credentials.json"
SHEET_NAME = "الشات والتصنيفات"

# ألوان الهيدر لكل شيت
HEADER_COLORS = {
    "الشات": {"red": 0.2, "green": 0.46, "blue": 0.73},      # أزرق داكن
    "الاساسي": {"red": 0.15, "green": 0.5, "blue": 0.25},     # أخضر داكن
    "التصنيفات": {"red": 0.55, "green": 0.27, "blue": 0.52},  # بنفسجي
}

# عناوين الأعمدة لكل شيت
HEADERS = {
    "الشات": [
        "رقم الطلب", "التاريخ", "الاسم", "الجوال",
        "الفئة", "الوصف المختصر", "الكمية", "الوحدة",
        "ملخص المحادثة", "الموقع", "الوصف الفني"
    ],
    "الاساسي": [
        "الفئة الأساسية (عربي)", "الفئة الأساسية (إنجليزي)",
        "الفئة الرئيسية (عربي)", "الفئة الرئيسية (إنجليزي)",
        "الفئة الفرعية (عربي)", "الفئة الفرعية (إنجليزي)",
        "مواصفة 1", "مواصفة 2", "مواصفة 3"
    ],
    "التصنيفات": [
        "رقم الطلب", "الوصف الأصلي",
        "الفئة الأساسية (عربي)", "الفئة الأساسية (إنجليزي)",
        "الفئة الرئيسية (عربي)", "الفئة الرئيسية (إنجليزي)",
        "الفئة الفرعية (عربي)", "الفئة الفرعية (إنجليزي)",
        "مواصفة 1 (اسم)", "مواصفة 1 (قيمة)",
        "مواصفة 2 (اسم)", "مواصفة 2 (قيمة)",
        "مواصفة 3 (اسم)", "مواصفة 3 (قيمة)",
        "الكود", "التاريخ"
    ],
}

# Column letter helper
def col_letter(n):
    result = ""
    while n > 0:
        n -= 1
        result = chr(65 + n % 26) + result
        n //= 26
    return result


def format_sheet_as_table(ws, sheet_name):
    """Apply table formatting to a worksheet using batch_update for efficiency"""
    
    all_data = ws.get_all_values()
    if not all_data:
        print(f"  ⚠️ الشيت '{sheet_name}' فارغ")
        return
    
    num_rows = len(all_data)
    num_cols = len(all_data[0])
    
    headers = HEADERS.get(sheet_name)
    header_color = HEADER_COLORS.get(sheet_name, {"red": 0.2, "green": 0.4, "blue": 0.7})
    
    print(f"  📊 الصفوف: {num_rows}, الأعمدة: {num_cols}")
    
    # 1. Set headers if defined
    if headers:
        actual_cols = max(num_cols, len(headers))
        end_col = col_letter(actual_cols)
        header_range = f"A1:{end_col}1"
        ws.update(header_range, [headers[:actual_cols]])
        num_cols = actual_cols
        print(f"  ✅ تم تحديث العناوين")
    
    time.sleep(1)  # Rate limit
    
    end_col = col_letter(num_cols)
    sheet_id = ws.id
    spreadsheet = ws.spreadsheet
    
    # Build batch requests for efficiency
    requests = []
    
    # 2. Header formatting - bold, white text, colored background, centered
    requests.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": 0,
                "endColumnIndex": num_cols
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": header_color,
                    "textFormat": {
                        "bold": True,
                        "foregroundColorStyle": {"rgbColor": {"red": 1, "green": 1, "blue": 1}},
                        "fontSize": 11
                    },
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE",
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
        }
    })
    
    # 3. Borders for ALL data cells
    border_style = {
        "style": "SOLID",
        "colorStyle": {"rgbColor": {"red": 0.75, "green": 0.75, "blue": 0.75}}
    }
    requests.append({
        "updateBorders": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": num_rows,
                "startColumnIndex": 0,
                "endColumnIndex": num_cols
            },
            "top": border_style,
            "bottom": border_style,
            "left": border_style,
            "right": border_style,
            "innerHorizontal": border_style,
            "innerVertical": border_style,
        }
    })
    
    # 4. Freeze header row
    requests.append({
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {
                    "frozenRowCount": 1
                }
            },
            "fields": "gridProperties.frozenRowCount"
        }
    })
    
    # 5. Banded (alternating) row colors via API
    # First clear any existing banding
    try:
        # Get existing bandings
        sheet_meta = None
        for s in spreadsheet.fetch_sheet_metadata()['sheets']:
            if s['properties']['sheetId'] == sheet_id:
                sheet_meta = s
                break
        
        if sheet_meta and 'bandedRanges' in sheet_meta:
            for banded in sheet_meta['bandedRanges']:
                requests.append({
                    "deleteBandedRange": {
                        "bandedRangeId": banded['bandedRangeId']
                    }
                })
    except:
        pass
    
    # Add banding
    requests.append({
        "addBanding": {
            "bandedRange": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": num_rows,
                    "startColumnIndex": 0,
                    "endColumnIndex": num_cols
                },
                "rowProperties": {
                    "firstBandColorStyle": {"rgbColor": {"red": 1, "green": 1, "blue": 1}},
                    "secondBandColorStyle": {"rgbColor": {"red": 0.94, "green": 0.94, "blue": 0.96}},
                }
            }
        }
    })
    
    # 6. Auto-filter — clear any existing, then add new
    requests.append({
        "clearBasicFilter": {
            "sheetId": sheet_id
        }
    })
    requests.append({
        "setBasicFilter": {
            "filter": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "startColumnIndex": 0,
                    "endColumnIndex": num_cols
                }
            }
        }
    })
    
    # Execute all requests in one batch
    try:
        spreadsheet.batch_update({"requests": requests})
        print(f"  ✅ تم تنسيق الهيدر + الحدود + التجميد + الفلتر + ألوان متبادلة")
    except Exception as e:
        print(f"  ⚠️ خطأ أثناء التنسيق: {e}")
        # Try without banding and filter
        try:
            fallback = requests[:4]  # header, borders, freeze
            spreadsheet.batch_update({"requests": fallback})
            print(f"  ✅ تم تنسيق الهيدر + الحدود + التجميد (بدون فلتر)")
        except Exception as e2:
            print(f"  ❌ فشل التنسيق: {e2}")
    
    print(f"  🎉 تم تنسيق '{sheet_name}' بنجاح!\n")


def run_formatting():
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ لم يتم العثور على ملف {CREDENTIALS_FILE}")
        return
    
    with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
        creds = json.load(f)
    
    gc = gspread.service_account_from_dict(creds)
    sh = gc.open(SHEET_NAME)
    
    sheets_to_format = ["الشات", "الاساسي", "التصنيفات"]
    
    for sheet_name in sheets_to_format:
        print(f"\n📋 تنسيق شيت: {sheet_name}")
        try:
            ws = sh.worksheet(sheet_name)
            format_sheet_as_table(ws, sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            print(f"  ⚠️ الشيت '{sheet_name}' غير موجود — تخطي")
        except Exception as e:
            print(f"  ❌ خطأ: {e}")
        
        time.sleep(2)  # Rate limit between sheets
    
    print("\n✅ انتهى التنسيق بنجاح!")


if __name__ == "__main__":
    run_formatting()
