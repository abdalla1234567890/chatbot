
import gspread
import json
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CREDENTIALS_FILE = "credentials.json"
SHEET_NAME = "الشات والتصنيفات"
WORKSHEET_NAME = "الاساسي"

def clean_taxonomy():
    if not os.path.exists(CREDENTIALS_FILE):
        logger.error("Missing credentials.")
        return

    try:
        with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
             creds = json.load(f)
        gc = gspread.service_account_from_dict(creds)
        sh = gc.open(SHEET_NAME)
        ws = sh.worksheet(WORKSHEET_NAME)
        
        rows = ws.get_all_values()
        if not rows: return
        
        # Headers should be: [BasicAr, BasicEn, MainAr, MainEn, SubAr, SubEn, Code, Spec1Name, Spec2Name]
        headers = ["الأساسي (عربي)", "Basic (En)", "الرئيسي (عربي)", "Main (En)", "الفرعي (عربي)", "Sub (En)", "الكود", "اسم المواصفة 1", "اسم المواصفة 2"]
        
        # Ensure header row is correct (9 columns)
        ws.update("A1:I1", [headers])
        
        # Batch update logic for speed
        logger.info(f"Normalizing {len(rows)-1} rows...")
        new_rows = []
        for i, row in enumerate(rows):
            if i == 0: continue # Skip header
            
            # Normalize row length to 9
            while len(row) < 9: row.append("")
            row = row[:9] # slice to be sure
            
            b_ar = str(row[0])
            m_ar = str(row[2])
            s_ar = str(row[4])
            
            # Populate Defaults if empty
            if not row[7] or not row[8]:
                # Pipe Logic
                if any(x in b_ar or x in m_ar or x in s_ar for x in ["ماسورة", "مواسير", "Pipe"]):
                    row[7] = row[7] or "القطر"
                    row[8] = row[8] or "الضغط"
                
                # Wire Logic
                elif any(x in b_ar or x in m_ar or x in s_ar for x in ["سلك", "أسلاك", "Wire", "كهرباء"]):
                    row[7] = row[7] or "التخانة"
                    row[8] = row[8] or "النوع"
                
                # Paint Logic
                elif any(x in b_ar or x in m_ar or x in s_ar for x in ["دهان", "بوية", "Paint"]):
                    row[7] = row[7] or "السعة"
                    row[8] = row[8] or "اللون/اللمعة"

            new_rows.append(row)

        if new_rows:
            # Batch update the whole data block
            ws.update(f"A2:I{len(new_rows)+1}", new_rows)

        logger.info("Taxonomy cleaning completed.")

    except Exception as e:
        logger.error(f"Cleaning failed: {e}")

if __name__ == "__main__":
    clean_taxonomy()
