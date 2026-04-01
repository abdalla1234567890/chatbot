"""
سكريبت لإضافة مواصفة 3 للأصناف التي تحتاجها في شيت "الاساسي"
يتم تشغيله مرة واحدة فقط

الأصناف التي تحتاج مواصفة 3:
- المواسير (Pipes): خامة + قطر + الضغط
- كابلات الكهرباء (Electrical Cables): مقاس + نوع + طول  
- حديد التسليح (Rebar): قطر + درجة + طول
- خراطيم (Hoses): نوع + قطر + طول
- أنابيب (Tubes): خامة + قطر + طول
- أسلاك (Wires): مقاس + نوع + طول
- زوايا حديد (Steel Angles): مقاس + سمك + طول
- مواسير صرف (Drainage Pipes): خامة + قطر + طول
- قنوات كهربائية (Electrical Conduits): نوع + قطر + طول
- خشب (Lumber/Wood): نوع + سمك + طول
"""

import json
import gspread
import os

CREDENTIALS_FILE = "credentials.json"
SHEET_NAME = "الشات والتصنيفات"
WORKSHEET_TAXONOMY = "الاساسي"

# Map: sub_en (lowercase) -> spec3_name
# These are items where a 3rd specification is essential
SPEC3_MAP = {
    # Pipes & Tubes → الضغط (pressure rating) بدلاً من الطول
    "pipes": "الضغط",
    "pvc pipes": "الضغط",
    "ppr pipes": "الضغط",
    "steel pipes": "الضغط",
    "gi pipes": "الضغط",
    "upvc pipes": "الضغط",
    "drainage pipes": "الضغط",
    "water pipes": "الضغط",
    "tubes": "الضغط",
    "conduits": "طول",
    "electrical conduits": "طول",
    
    # Cables & Wires
    "cables": "طول",
    "electrical cables": "طول",
    "power cables": "طول",
    "network cables": "طول",
    "wires": "طول",
    "electrical wires": "طول",
    
    # Steel/Iron products
    "rebar": "طول",
    "steel angles": "طول",
    "steel sections": "طول",
    "steel bars": "طول",
    "iron bars": "طول",
    "channel steel": "طول",
    "flat bars": "طول",
    
    # Wood/Lumber
    "lumber": "طول",
    "wood": "طول",
    "timber": "طول",
    "plywood": "سمك",
    "mdf": "سمك",
    
    # Hoses
    "hoses": "طول",
    "garden hoses": "طول",
    "water hoses": "طول",
    "air hoses": "طول",
    
    # Chains & Ropes
    "chains": "طول",
    "ropes": "طول",
    "wire ropes": "طول",
}


def run_migration():
    """Add spec3_name column to taxonomy items that need it"""
    
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ لم يتم العثور على ملف {CREDENTIALS_FILE}")
        return
    
    with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
        creds = json.load(f)
    
    gc = gspread.service_account_from_dict(creds)
    sh = gc.open(SHEET_NAME)
    ws = sh.worksheet(WORKSHEET_TAXONOMY)
    
    rows = ws.get_all_values()
    
    if len(rows) < 2:
        print("⚠️ الشيت فارغ")
        return
    
    header = rows[0]
    print(f"📋 عدد الأعمدة الحالي: {len(header)}")
    print(f"📋 العناوين: {header}")
    
    # Check if spec3 column exists already (column J = index 9)
    if len(header) > 9 and header[9]:
        print(f"ℹ️ العمود J موجود بالفعل: '{header[9]}'")
    else:
        # Add header for spec3
        print("➕ إضافة عنوان 'مواصفة 3' في العمود J...")
        ws.update_cell(1, 10, "مواصفة 3")  # Column J = 10 (1-indexed)
    
    # Now scan all data rows and add spec3 where needed
    updated_count = 0
    data_rows = rows[1:]
    
    for i, row in enumerate(data_rows):
        row_num = i + 2  # 1-indexed, skip header
        
        if len(row) < 6:
            continue
        
        sub_en = row[5].strip().lower() if len(row) > 5 else ""
        sub_ar = row[4].strip().lower() if len(row) > 4 else ""
        
        # Check if this item already has spec3
        existing_spec3 = row[9].strip() if len(row) > 9 else ""
        
        # Look up what spec3 SHOULD be for this item
        spec3_val = SPEC3_MAP.get(sub_en)
        
        # Also check Arabic name
        if not spec3_val:
            arabic_map = {
                "مواسير": "الضغط",
                "ماسورة": "الضغط",
                "انابيب": "الضغط",
                "أنابيب": "الضغط",
                "كابلات": "طول",
                "كيبل": "طول",
                "كابل": "طول",
                "أسلاك": "طول",
                "سلك": "طول",
                "حديد تسليح": "طول",
                "حديد": "طول",
                "زوايا": "طول",
                "خراطيم": "طول",
                "خرطوم": "طول",
                "خشب": "طول",
                "قنوات": "طول",
                "سلاسل": "طول",
                "حبال": "طول",
            }
            for key, val in arabic_map.items():
                if key in sub_ar:
                    spec3_val = val
                    break
        
        if spec3_val:
            if existing_spec3 == spec3_val:
                continue  # Already correct, skip
            
            ws.update_cell(row_num, 10, spec3_val)  # Column J = 10
            item_name = sub_en or sub_ar
            action = "UPDATE" if existing_spec3 else "NEW"
            old_info = f" (كان: {existing_spec3})" if existing_spec3 else ""
            print(f"  ✅ [{action}] [{row_num}] {item_name} → مواصفة 3: {spec3_val}{old_info}")
            updated_count += 1
    
    print(f"\n🎉 تم تحديث {updated_count} صنف بمواصفة 3")
    print("✅ انتهى السكريبت بنجاح")


if __name__ == "__main__":
    run_migration()
