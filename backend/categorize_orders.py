
import pandas as pd
import gspread
import json
import os
import google.generativeai as genai
import logging
import time
from dotenv import load_dotenv

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load Env
load_dotenv()

# Check API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY is missing!")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash-lite')

# Constants
EXCEL_PATH = r"c:\Abdalla\chatbot\طلبات.xlsx"
EXCEL_SHEET = "التصنيفات الفرعية " # Note the space
GS_SHEET_NAME = "الشات والتصنيفات"
SOURCE_WORKSHEET = "Sheet1"
TARGET_WORKSHEET = "تصنيفات"
CREDENTIALS_FILE = "credentials.json"

def load_taxonomy():
    """Reads the Excel file and builds a taxonomy string for the AI."""
    logger.info("Loading taxonomy from Excel...")
    try:
        df = pd.read_excel(EXCEL_PATH, sheet_name=EXCEL_SHEET)
        
        # Explicit mapping by index (Safest for Arabic headers)
        cols = df.columns.tolist()
        basic_col = cols[0] if len(cols) > 0 else None
        main_col = cols[1] if len(cols) > 1 else None
        sub_col = cols[2] if len(cols) > 2 else None
        # Exclude Ex-col (index 3)
        ex_col = None 
        
        logger.info(f"Mapping Indices: Basic='{basic_col}', Main='{main_col}', Sub='{sub_col}'")

        taxonomy_text = ""
        current_basic = "General"
        current_main = "General"
        
        for _, row in df.iterrows():
            # Handle Basic Cat (Fill down if merged/nan)
            b = row.get(basic_col)
            if pd.notna(b): current_basic = b
            
            # Handle Main Cat (Fill down if merged/nan)
            m = row.get(main_col)
            if pd.notna(m): current_main = m
            
            # Sub Cat
            s = row.get(sub_col, '')
            if pd.isna(s): s = ""
            
            # Examples
            e = row.get(ex_col, '') if ex_col else ''
            if pd.isna(e): e = ""
            
            if s:
                taxonomy_text += f"- {current_basic} > {current_main} > {s} (Ex: {e})\n"
            
        # DEBUG: Print first 500 chars of taxonomy
        logger.info(f"Taxonomy Preview:\n{taxonomy_text[:500]}...")
        
        if not taxonomy_text:
            logger.error("❌ Taxonomy is empty! Check column names.")
            
        return taxonomy_text
    except Exception as e:
        logger.error(f"Error loading Excel: {e}")
        return None

def classify_item(item_desc, taxonomy):
    """Asks Gemini to classify the item based on the taxonomy."""
    prompt = f"""
    You are an expert construction material classifier.
    
    Task: Map the User Request to the most appropriate Standardized Classification Path.
    
    User Request: "{item_desc}"
    
    Taxonomy Format: Basic > Main > Sub
    Allowed Paths:
    {taxonomy}
    
    Instructions:
    1. Find the best matching path from the list.
    2. Do NOT use any examples or extra details. Match strictly against the provided paths.
    3. Return the full path in this format: "Basic Category - Main Category - Sub Category".
    4. Example Output: "السباكة - الأنابيب - أنابيب مياه".
    5. If no match found, return "Uncategorized".
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        # Print detailed traceback or error message
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}"

def main():
    # 1. Setup GSpread
    if not os.path.exists(CREDENTIALS_FILE):
        logger.error("Credentials file missing.")
        return

    try:
        with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
             creds = json.load(f)
        if "private_key" in creds:
             creds["private_key"] = creds["private_key"].replace("\\n", "\n")
             
        gc = gspread.service_account_from_dict(creds)
        sh = gc.open(GS_SHEET_NAME)
    except Exception as e:
        logger.error(f"GSpread Connect Error: {e}")
        return

    # 2. Get Source Data
    try:
        src_ws = sh.worksheet(SOURCE_WORKSHEET)
        # Assuming the LAST column (12th, or column L) has the full desc
        # Or better: Read all values and take the last element of each row
        all_rows = src_ws.get_all_values()
        if len(all_rows) < 2:
             logger.info("Source sheet is empty.")
             return
             
        headers = all_rows[0]
        data_rows = all_rows[1:]
    except Exception as e:
        logger.error(f"Error reading source sheet: {e}")
        return

    # 3. Setup Target Sheet
    try:
        try:
            target_ws = sh.worksheet(TARGET_WORKSHEET)
        except gspread.exceptions.WorksheetNotFound:
            target_ws = sh.add_worksheet(title=TARGET_WORKSHEET, rows=1000, cols=5)
            target_ws.append_row(["Order ID", "Original Request", "Standardized Classification", "Timestamp"])
            logger.info(f"Created new worksheet: {TARGET_WORKSHEET}")
            
        # Read existing IDs in target to avoid duplicates
        target_rows = target_ws.get_all_values()
        processed_ids = set()
        if len(target_rows) > 1:
            for r in target_rows[1:]:
                if r: processed_ids.add(r[0]) # Assuming Order ID is first col
    except Exception as e:
        logger.error(f"Error setup target sheet: {e}")
        return

    # 4. Load Taxonomy
    taxonomy = load_taxonomy()
    if not taxonomy:
        return

    # 5. Process Rows
    new_rows = []
    
    logger.info(f"Processing {len(data_rows)} rows...")
    
    for row in data_rows:
        if not row: continue
        
        # Adjust indices based on your sheet structure
        # In save_to_sheet: 
        # 0: OrderNum, 1: Time, 2:Name, 3:Phone, 4:Cat, 5:Desc, 6:Qty, 7:Unit, 8:Sum, 9:Stat, 10:Addr, 11: FULL_DESC
        
        # Check if row has enough columns. Since we just added col 12, old rows might not have it.
        # If row length is < 12, we might not have the full desc.
        # Fallback to column 5 (Desc) if 11 is missing
        
        order_id = row[0]
        
        if len(row) >= 12:
            full_desc = row[11]
        elif len(row) >= 6:
            full_desc = row[5] # Fallback to normal desc
        else:
            full_desc = "Unknown"
        
        if order_id in processed_ids and str(order_id) != "1000":
            continue
            
        logger.info(f"Classifying Order #{order_id}: {full_desc}")
        
        standardized_name = classify_item(full_desc, taxonomy)
        logger.info(f"-> Result: {standardized_name}")
        
        new_rows.append([
            order_id,
            full_desc,
            standardized_name,
            str(time.strftime("%Y-%m-%d %H:%M:%S"))
        ])
        
        # Sleep to avoid rate limits
        time.sleep(1)

    # 6. Write to Target
    if new_rows:
        # Check if we need to append or just write
        target_ws.append_rows(new_rows)
        logger.info(f"✅ Successfully added {len(new_rows)} categorized orders.")
    else:
        logger.info("No new orders to process.")

if __name__ == "__main__":
    main()
