
import logging
import os
import google.generativeai as genai
import gspread
import time
import json
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Constants
CREDENTIALS_FILE = "credentials.json"
SHEET_NAME = "الشات والتصنيفات"
WORKSHEET_TAXONOMY = "الاساسي" # Source of truth (Knowledge Base)
WORKSHEET_RESULTS = "التصنيفات" # Where we save results

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Global Cache
_TAXONOMY_CACHE = None
_TAXONOMY_SUMMARY_CACHE = None
_EXISTING_SUBS_CACHE = None
_SPECS_BY_SUB_CACHE = None  # sub_en -> (spec1_name, spec2_name, spec3_name)
_CODES_BY_SUB_CACHE = None  # sub_en -> existing code from taxonomy sheet
_LAST_CACHE_UPDATE = 0
_LAST_SUMMARY_CACHE_UPDATE = 0
_LAST_SUBS_CACHE_UPDATE = 0
CACHE_TTL = 300 # Refresh every 5 minutes

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # Using gemini-2.5-flash-lite per user request
    model = genai.GenerativeModel('gemini-2.5-flash') 
else:
    model = None
    logger.warning("GEMINI_API_KEY not found in classifier.")

def get_google_sheet_client():
    if not os.path.exists(CREDENTIALS_FILE):
        logger.error("Credentials file missing.")
        return None
    try:
        with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
             creds = json.load(f)
        gc = gspread.service_account_from_dict(creds)
        return gc
    except Exception as e:
        logger.error(f"GSpread Connect Error: {e}")
        return None

def get_taxonomy(force_refresh=False):
    global _TAXONOMY_CACHE, _LAST_CACHE_UPDATE
    
    # Check Cache
    if _TAXONOMY_CACHE and not force_refresh and (time.time() - _LAST_CACHE_UPDATE < CACHE_TTL):
        return _TAXONOMY_CACHE

    logger.info("Loading taxonomy from Google Sheets...")
    gc = get_google_sheet_client()
    if not gc: return None

    try:
        sh = gc.open(SHEET_NAME)
        ws = sh.worksheet(WORKSHEET_TAXONOMY)
        rows = ws.get_all_values()
        
        if len(rows) < 2:
            return ""

        data_rows = rows[1:] # Skip header
        
        taxonomy_text = ""
        for row in data_rows:
            try:
                if len(row) >= 7:
                    b_ar, b_en = row[0], row[1]
                    m_ar, m_en = row[2], row[3]
                    s_ar, s_en = row[4], row[5]
                    code = row[6]
                    
                    # Load Spec Names if they exist (up to 3)
                    spec1_name = row[7] if len(row) > 7 else ""
                    spec2_name = row[8] if len(row) > 8 else ""
                    spec3_name = row[9] if len(row) > 9 else ""

                    if code and code != "Code": # verify not header
                        # Include both languages and SPEC NAMES for AI context
                        line = f"[{code}] {b_ar} ({b_en}) > {m_ar} ({m_en}) > {s_ar} ({s_en})"
                        if spec1_name: line += f" | Needs: {spec1_name}"
                        if spec2_name: line += f" & {spec2_name}"
                        if spec3_name: line += f" & {spec3_name}"
                        taxonomy_text += line + "\n"
            except IndexError:
                continue
        
        _TAXONOMY_CACHE = taxonomy_text
        _LAST_CACHE_UPDATE = time.time()
        logger.info(f"Taxonomy loaded ({len(data_rows)} items).")
        return taxonomy_text
    except Exception as e:
        logger.error(f"Failed to load taxonomy: {e}")
        return ""

def get_taxonomy_summary():
    """Returns a concise list of categories and their required specs for the Chat AI. Cached."""
    global _TAXONOMY_SUMMARY_CACHE, _LAST_SUMMARY_CACHE_UPDATE
    
    # Return cached version if still fresh
    if _TAXONOMY_SUMMARY_CACHE and (time.time() - _LAST_SUMMARY_CACHE_UPDATE < CACHE_TTL):
        return _TAXONOMY_SUMMARY_CACHE
    
    gc = get_google_sheet_client()
    if not gc: return _TAXONOMY_SUMMARY_CACHE or ""
    try:
        sh = gc.open(SHEET_NAME)
        ws = sh.worksheet(WORKSHEET_TAXONOMY)
        rows = ws.get_all_values()
        if len(rows) < 2: return ""
        
        categories = {}
        for row in rows[1:]:
            if len(row) >= 7:
                cat_key = row[4] or row[2] # SubAr or MainAr
                spec1 = row[6] if len(row) > 6 else ""
                spec2 = row[7] if len(row) > 7 else ""
                spec3 = row[8] if len(row) > 8 else ""
                if cat_key and (spec1 or spec2):
                    specs_str = spec1
                    if spec2: specs_str += f" و {spec2}"
                    if spec3: specs_str += f" و {spec3}"
                    categories[cat_key] = specs_str
        
        summary = "مواصفات المنتجات المطلوبة:\n"
        for cat, specs in categories.items():
            summary += f"- {cat}: اطلب من العميل ({specs})\n"
        
        _TAXONOMY_SUMMARY_CACHE = summary
        _LAST_SUMMARY_CACHE_UPDATE = time.time()
        logger.info("Taxonomy summary cache refreshed.")
        return summary
    except Exception as e:
        logger.error(f"Error getting taxonomy summary: {e}")
        return _TAXONOMY_SUMMARY_CACHE or ""

# Helper for code generation
def generate_base_code(b_sh, m_sh, s_sh):
    """Generate base code from category shorthands (without specs)."""
    parts = [str(p).strip().upper() for p in [b_sh, m_sh, s_sh] if p]
    return "-".join(parts)

def generate_code(b_sh, m_sh, s_sh, spec1_sh=None, spec2_sh=None, spec3_sh=None):
    """Legacy function kept for compatibility."""
    base = generate_base_code(b_sh, m_sh, s_sh)
    return build_final_code(base, spec1_sh, spec2_sh, spec3_sh)

def normalize_spec_shorthand(val):
    """Normalize a spec value into a consistent, deterministic shorthand code."""
    if not val:
        return ""
    val = str(val).strip()
    number_match = re.match(r'^(\d+[\.\d]*)\s*(.*)$', val)
    if number_match:
        number = number_match.group(1)
        if '.' in number and number.endswith('0'):
            try:
                num_float = float(number)
                if num_float == int(num_float):
                    number = str(int(num_float))
            except ValueError:
                pass
        unit = number_match.group(2).strip().upper()
    else:
        number = ""
        unit = val.upper()
    
    unit_map = {
        "بوصة": "IN", "بوصه": "IN", "انش": "IN", "إنش": "IN",
        "INCH": "IN", "INCHES": "IN",
        "متر": "M", "م": "M", "METER": "M", "METERS": "M", "MTR": "M",
        "ملم": "MM", "ملي": "MM", "مم": "MM", "MILLIMETER": "MM",
        "سم": "CM", "سنتيمتر": "CM", "CENTIMETER": "CM",
        "بار": "BAR", "BARS": "BAR",
        "واط": "W", "وات": "W", "WATT": "W", "WATTS": "W",
        "كيلو": "KG", "كجم": "KG", "KILOGRAM": "KG",
        "جرام": "G", "GRAM": "G", "GRAMS": "G",
        "لتر": "L", "LITER": "L", "LITRE": "L",
    }
    
    normalized_unit = unit
    for ar_unit, en_code in unit_map.items():
        if unit == ar_unit.upper() or unit == en_code:
            normalized_unit = en_code
            break
    
    result = f"{number}{normalized_unit}".replace(" ", "")
    if not result:
        result = val.strip().upper().replace(" ", "")
    return result

def normalize_spec_value(val):
    """Normalize a spec value for comparison."""
    if not val:
        return ""
    val = str(val).strip().lower()
    val = re.sub("[إأآا]", "ا", val)
    val = re.sub("ى", "ي", val)
    val = re.sub("ة", "ه", val)
    val = re.sub(r"\s+", " ", val).strip()
    return val

def build_final_code(base_code, spec1_sh=None, spec2_sh=None, spec3_sh=None):
    """Build the final product code from base code + normalized spec shorthands."""
    parts = [base_code]
    for ssh in [spec1_sh, spec2_sh, spec3_sh]:
        normalized = normalize_spec_shorthand(ssh) if ssh else ""
        if normalized:
            parts.append(normalized)
    return "-".join(parts)

def find_existing_code_in_classifications(sh, sub_en, spec1_val, spec2_val, spec3_val):
    """Look up existing classifications to find if same product+specs already has a code."""
    try:
        ws = sh.worksheet(WORKSHEET_RESULTS)
        rows = ws.get_all_values()
        target_sub = (sub_en or "").strip().lower()
        target_s1 = normalize_spec_value(spec1_val)
        target_s2 = normalize_spec_value(spec2_val)
        target_s3 = normalize_spec_value(spec3_val)
        
        for row in rows[1:]:
            if len(row) >= 15:
                row_sub = (row[7] or "").strip().lower()
                row_s1 = normalize_spec_value(row[9] if len(row) > 9 else "")
                row_s2 = normalize_spec_value(row[11] if len(row) > 11 else "")
                row_s3 = normalize_spec_value(row[13] if len(row) > 13 else "")
                row_code = (row[14] or "").strip()
                
                if (row_sub == target_sub and 
                    row_s1 == target_s1 and 
                    row_s2 == target_s2 and 
                    row_s3 == target_s3 and
                    row_code):
                    logger.info(f"✅ Found existing code '{row_code}' for {sub_en}")
                    return row_code
        return None
    except Exception as e:
        logger.error(f"Error looking up existing classification code: {e}")
        return None


def add_new_item_to_taxonomy(data, item_name):
    """Appends a new verified classification to the Google Sheet (Bilingual + Code)"""
    logger.info(f"Learning new item: {item_name}")
    gc = get_google_sheet_client()
    if not gc: return False

    try:
        sh = gc.open(SHEET_NAME)
        ws = sh.worksheet(WORKSHEET_TAXONOMY)
        
        # Calculate BASE code only (without specs) for the taxonomy row
        b_sh = data.get('basic_sh', '') or data.get('basic_en', '')[:3]
        m_sh = data.get('main_sh', '') or data.get('main_en', '')[:3]
        s_sh = data.get('sub_sh', '') or data.get('sub_en', '')[:4]
        code = generate_base_code(b_sh, m_sh, s_sh)
        
        # Append [BasicAr, BasicEn, MainAr, MainEn, SubAr, SubEn, Spec1Name, Spec2Name, Spec3Name]
        b_en = data.get('basic_en', '')
        m_en = data.get('main_en', '')
        s_en = data.get('sub_en', '')
        row = [
            data.get('basic_ar', ''), b_en,
            data.get('main_ar', ''), m_en,
            data.get('sub_ar', ''), s_en,
            data.get('spec1_name', ''),
            data.get('spec2_name', ''),
            data.get('spec3_name', '')
        ]
        
        ws.append_row(row)
        
        # Apply table borders to the new taxonomy row
        try:
            new_row_num = len(ws.get_all_values())
            end_col_letter = chr(64 + len(row))
            cell_range = f"A{new_row_num}:{end_col_letter}{new_row_num}"
            ws.format(cell_range, {
                "borders": {
                    "top": {"style": "SOLID", "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                    "bottom": {"style": "SOLID", "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                    "left": {"style": "SOLID", "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                    "right": {"style": "SOLID", "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                }
            })
        except Exception as fmt_err:
            logger.warning(f"Failed to format taxonomy row: {fmt_err}")
        
        # Force cache refresh for ALL caches next time
        global _LAST_CACHE_UPDATE, _LAST_SUMMARY_CACHE_UPDATE, _LAST_SUBS_CACHE_UPDATE, _SPECS_BY_SUB_CACHE
        _LAST_CACHE_UPDATE = 0
        _LAST_SUMMARY_CACHE_UPDATE = 0
        _LAST_SUBS_CACHE_UPDATE = 0
        _SPECS_BY_SUB_CACHE = None  # Force rebuild of specs cache
        _CODES_BY_SUB_CACHE = None  # Force rebuild of codes cache
        logger.info(f"All taxonomy caches invalidated after adding new item.")
        return code
    except Exception as e:
        logger.error(f"Failed to learn new item: {e}")
        return "UNKNOWN"

def classify_item_ai(item_desc):
    if not model: return None
    
    taxonomy = get_taxonomy()
        
    prompt = f"""
    Task: Classify items into 3 levels (Basic, Main, Sub) for Construction Materials, Office Supplies (مكتبي), or IT/PCs and Wireless Devices (الكترونيات/كمبيوتر).
    Item: "{item_desc}"
    
    Taxonomy Reference (Current Known Items from Sheet):
    {taxonomy}
    
    Instructions:
    1. STRICTLY MATCH existing taxonomy items if they fit.
    2. Primary Specs: If a taxonomy item has "| Needs: Spec1 & Spec2 & Spec3", you MUST map the user's data to these specific names.
    3. spec3 is OPTIONAL — only include it if the taxonomy entry has 3 specs listed, or if the item genuinely needs a 3rd distinguishing attribute (e.g., pipes need material + diameter + pressure).
    4. Additional Specs beyond the defined ones go into the description, NOT as primary specs.
    5. New Categories: If NO match exists, define spec1_name and spec2_name as the two most important TECHNICAL attributes. Add spec3_name ONLY if a 3rd attribute is truly essential for this category.
    6. ⚠️ CRITICAL RULE — NEVER use these as specs: quantity (كمية), unit (وحدة), count (عدد), price (سعر), date (تاريخ).
       Valid specs are ONLY: type (نوع), color (لون), size (مقاس/حجم), material (خامة), capacity (سعة), speed (سرعة), brand (ماركة), weight (وزن), dimension (قطر/طول), pressure (الضغط).
       Example for Pens: spec1=نوع (حبر/رصاص/جاف), spec2=لون (أزرق/أسود/أحمر) ✅
       Example BAD:      spec1=كمية (10), spec2=لون ❌ (كمية is NEVER a spec)
    7. Code Generation: Generate concise English shorthands (2-4 chars):
       - basic_sh, main_sh: use the category name (e.g., ELE, OFF, CON | LIG, PC, WIRE)
       - sub_sh: MUST be different from basic_sh and main_sh. Use a unique word for the sub-category (e.g., BULB for Electric lamps, PEN for pens, ROUT for router — NOT "ELE" if basic is already "ELE")
       - spec1_sh, spec2_sh, spec3_sh: MUST be from the SPEC VALUE, not the spec name.
         ✅ Wattage=12W → spec1_sh="12W" | Color=Blue → spec1_sh="BLU" | RAM=16GB → spec1_sh="16GB"
         ❌ Wattage=12W → spec1_sh="WAT" (this is the spec NAME, not the value!)
    8. Return JSON ONLY.
    
    JSON Schema:
    {{
        "found": boolean,
        "basic_ar": "string", "basic_en": "string", "basic_sh": "string",
        "main_ar": "string", "main_en": "string", "main_sh": "string",
        "sub_ar": "string", "sub_en": "string", "sub_sh": "string",
        "spec1_name": "string", "spec1_val": "string", "spec1_sh": "string",
        "spec2_name": "string", "spec2_val": "string", "spec2_sh": "string",
        "spec3_name": "string or empty", "spec3_val": "string or empty", "spec3_sh": "string or empty"
    }}
    """
    
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            current_model = model
            if attempt > 0:
                 logger.info("Retrying with gemini-2.5-flash...")
                 current_model = genai.GenerativeModel('gemini-2.5-flash')

            response = current_model.generate_content(prompt, generation_config={"response_mime_type": "application/json", "temperature": 0})
            text_resp = response.text.strip()
            
            if text_resp.startswith("```"):
                text_resp = re.sub(r"^```json|^```", "", text_resp).strip()
                if text_resp.endswith("```"):
                    text_resp = text_resp[:-3].strip()

            try:
                result_json = json.loads(text_resp)
                logger.info(f"Classifier AI Response: {json.dumps(result_json, ensure_ascii=False)}")
            except json.JSONDecodeError:
                logger.error(f"JSON Parse Error. Raw: {text_resp}")
                continue

            # Generate UNIQUE code using AI-shorthands
            unique_code = generate_code(
                result_json.get('basic_sh', 'XXX'), 
                result_json.get('main_sh', 'XXX'), 
                result_json.get('sub_sh', 'XXX'),
                result_json.get('spec1_sh'),
                result_json.get('spec2_sh'),
                result_json.get('spec3_sh')
            )
            result_json['code'] = unique_code
            
            return result_json
            
        except Exception as e:
            if "429" in str(e):
                logger.warning(f"Classifier Quota Exceeded (Attempt {attempt+1}). Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.error(f"Gemini error in classifier: {e}")
                if attempt == max_retries - 1:
                    return None
    return None

def get_existing_sub_categories():
    """Returns a set of existing (sub_en) sub-category names. Cached for 5 minutes."""
    global _EXISTING_SUBS_CACHE, _LAST_SUBS_CACHE_UPDATE
    
    if _EXISTING_SUBS_CACHE is not None and (time.time() - _LAST_SUBS_CACHE_UPDATE < CACHE_TTL):
        return _EXISTING_SUBS_CACHE
    
    gc = get_google_sheet_client()
    if not gc: return _EXISTING_SUBS_CACHE or set()
    try:
        sh = gc.open(SHEET_NAME)
        ws = sh.worksheet(WORKSHEET_TAXONOMY)
        rows = ws.get_all_values()
        existing = set()
        for row in rows[1:]:  # skip header
            if len(row) >= 6 and row[5]:  # sub_en is col index 5
                existing.add(row[5].strip().lower())
        _EXISTING_SUBS_CACHE = existing
        _LAST_SUBS_CACHE_UPDATE = time.time()
        logger.info(f"Sub-categories cache refreshed ({len(existing)} items).")
        return existing
    except Exception as e:
        logger.error(f"Error fetching existing sub-categories: {e}")
        return _EXISTING_SUBS_CACHE or set()

def _build_taxonomy_lookup_caches():
    """Builds both specs and codes caches from the taxonomy sheet in ONE read."""
    global _SPECS_BY_SUB_CACHE, _CODES_BY_SUB_CACHE
    
    gc = get_google_sheet_client()
    if not gc: return
    try:
        sh = gc.open(SHEET_NAME)
        ws = sh.worksheet(WORKSHEET_TAXONOMY)
        rows = ws.get_all_values()
        specs_cache = {}
        codes_cache = {}
        for row in rows[1:]:
            if len(row) >= 6 and row[5]:  # sub_en in col 5
                key = row[5].strip().lower()
                spec1 = row[6].strip() if len(row) > 6 else ''
                spec2 = row[7].strip() if len(row) > 7 else ''
                spec3 = row[8].strip() if len(row) > 8 else ''
                if spec1 or spec2:
                    specs_cache[key] = (spec1, spec2, spec3)
        _SPECS_BY_SUB_CACHE = specs_cache
        _CODES_BY_SUB_CACHE = {} # Empty since code column is removed from Taxonomy
        logger.info(f"Taxonomy lookup caches built ({len(specs_cache)} specs).")
    except Exception as e:
        logger.error(f"Error building taxonomy caches: {e}")

def get_taxonomy_specs_for_sub(sub_en_key):
    """Returns (spec1_name, spec2_name, spec3_name) from the taxonomy sheet for a known sub-category. Cached."""
    global _SPECS_BY_SUB_CACHE
    
    if _SPECS_BY_SUB_CACHE is None:
        _build_taxonomy_lookup_caches()
    
    if _SPECS_BY_SUB_CACHE is None:
        return None, None, None
    
    key = (sub_en_key or '').strip().lower()
    entry = _SPECS_BY_SUB_CACHE.get(key)
    if entry:
        return entry[0], entry[1], entry[2]
    return None, None, None

def get_taxonomy_code_for_sub(sub_en_key):
    """Returns the existing code from the taxonomy sheet for a known sub-category. Cached."""
    global _CODES_BY_SUB_CACHE
    
    if _CODES_BY_SUB_CACHE is None:
        _build_taxonomy_lookup_caches()
    
    if _CODES_BY_SUB_CACHE is None:
        return None
    
    key = (sub_en_key or '').strip().lower()
    return _CODES_BY_SUB_CACHE.get(key)

def process_and_save_classification(sh, order_id, full_desc):
    try:
        # Classify
        result = classify_item_ai(full_desc)
        
        if not result:
            logger.warning(f"Could not classify order {order_id}")
            return False
            
        # --- Robust Learning Logic: Direct sheet lookup to check if truly new ---
        sub_en = (result.get('sub_en') or '').strip().lower()
        existing_subs = get_existing_sub_categories()
        
        is_truly_new = sub_en and (sub_en not in existing_subs)
            
        if is_truly_new:
            logger.info(f"Adding TRULY NEW category to taxonomy: {result.get('sub_ar')} ({sub_en})")
            new_code = add_new_item_to_taxonomy(result, full_desc)
            base_code = generate_base_code(
                result.get('basic_sh', 'XXX'), result.get('main_sh', 'XXX'), result.get('sub_sh', 'XXX')
            )
            # Invalidate specs cache too
            global _SPECS_BY_SUB_CACHE
            _SPECS_BY_SUB_CACHE = None
        else:
            logger.info(f"Category already exists in sheet, skipping add: {result.get('sub_ar')} ({sub_en})")
            # Override spec names with sheet-defined values for consistency
            sheet_spec1, sheet_spec2, sheet_spec3 = get_taxonomy_specs_for_sub(sub_en)
            if sheet_spec1:
                result['spec1_name'] = sheet_spec1
            if sheet_spec2:
                result['spec2_name'] = sheet_spec2
            if sheet_spec3:
                result['spec3_name'] = sheet_spec3
            
            # Get base code by AI generation since Code column is removed from Taxonomy sheet
            base_code = generate_base_code(
                result.get('basic_sh', 'XXX'), result.get('main_sh', 'XXX'), result.get('sub_sh', 'XXX')
            )
        
        # ========================================
        # CODE STANDARDIZATION LOGIC
        # ========================================
        
        spec1_val = result.get('spec1_val', '')
        spec2_val = result.get('spec2_val', '')
        spec3_val = result.get('spec3_val', '')
        
        # Step 1: Check if the SAME product with SAME specs already has a code
        existing_code = find_existing_code_in_classifications(
            sh, result.get('sub_en', ''), spec1_val, spec2_val, spec3_val
        )
        
        if existing_code:
            # REUSE the existing code (same product + same specs = same code)
            final_code = existing_code
            logger.info(f"♻️ Reusing existing code: {final_code}")
        else:
            # Step 2: Generate NEW code = base_code + normalized spec shorthands
            final_code = build_final_code(
                base_code,
                result.get('spec1_sh', ''),
                result.get('spec2_sh', ''),
                result.get('spec3_sh', '')
            )
            logger.info(f"🆕 Generated new code: {final_code} (base={base_code})")
        
        result['code'] = final_code
        
        # Save Result
        try:
            target_ws = sh.worksheet(WORKSHEET_RESULTS)
        except gspread.exceptions.WorksheetNotFound:
            target_ws = sh.add_worksheet(title=WORKSHEET_RESULTS, rows=1000, cols=14)
            
        # Columns: [ID, Original, BasicAr, BasicEn, MainAr, MainEn, SubAr, SubEn, Spec1Name, Spec1Val, Spec2Name, Spec2Val, Spec3Name, Spec3Val, Code, Date]
        row = [
            order_id,
            full_desc,
            result.get('basic_ar'), result.get('basic_en'),
            result.get('main_ar'), result.get('main_en'),
            result.get('sub_ar'), result.get('sub_en'),
            result.get('spec1_name'), result.get('spec1_val'),
            result.get('spec2_name'), result.get('spec2_val'),
            result.get('spec3_name', ''), result.get('spec3_val', ''),
            final_code,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ]
        
        target_ws.append_row(row)
        
        # Apply table borders to the new row
        try:
            new_row_num = len(target_ws.get_all_values())
            end_col_letter = chr(64 + len(row))  # Convert column count to letter
            cell_range = f"A{new_row_num}:{end_col_letter}{new_row_num}"
            target_ws.format(cell_range, {
                "borders": {
                    "top": {"style": "SOLID", "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                    "bottom": {"style": "SOLID", "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                    "left": {"style": "SOLID", "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                    "right": {"style": "SOLID", "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                }
            })
        except Exception as fmt_err:
            logger.warning(f"Failed to format classification row: {fmt_err}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to save classification: {e}")
        return False
