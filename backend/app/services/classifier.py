import google.generativeai as genai
import json
import logging
import re
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global variable for cached summary
_SUMMARY_CACHE = ""
_SUMMARY_CACHE_TIME = 0

def get_taxonomy(sh=None):
    """Fetch taxonomy rows from 'الاساسي'"""
    if not sh: return []
    try:
        ws = sh.worksheet("الاساسي")
        rows = ws.get_all_values()
        if len(rows) < 2: return []
        return rows[1:] # skip header
    except Exception as e:
        logger.error(f"Error getting taxonomy: {e}")
        return []

def get_taxonomy_summary(sh=None):
    global _SUMMARY_CACHE, _SUMMARY_CACHE_TIME
    import time
    if _SUMMARY_CACHE and (time.time() - _SUMMARY_CACHE_TIME < 300):
        return _SUMMARY_CACHE

    rows = get_taxonomy(sh)
    summary = []
    for row in rows:
        if len(row) >= 6:
            # Format: BasicAr (BasicEn) > MainAr (MainEn) > SubAr (SubEn)
            line = f"{row[0]} ({row[1]}) > {row[2]} ({row[3]}) > {row[4]} ({row[5]})"
            needs = []
            if len(row) > 6 and row[6]: needs.append(row[6].strip())
            if len(row) > 7 and row[7]: needs.append(row[7].strip())
            if len(row) > 8 and row[8]: needs.append(row[8].strip())
            if needs:
                line += f" | Needs: {' & '.join(needs)}"
            summary.append(line)
    
    _SUMMARY_CACHE = "\n".join(summary)
    _SUMMARY_CACHE_TIME = time.time()
    return _SUMMARY_CACHE

def generate_base_code(b_sh, m_sh, s_sh):
    """Generate base code from category shorthands (without specs)."""
    parts = [str(p).strip().upper() for p in [b_sh, m_sh, s_sh] if p]
    return "-".join(parts)

def normalize_spec_shorthand(val):
    """Normalize a spec value into a consistent, deterministic shorthand code.
    
    This ensures the SAME spec value always produces the SAME shorthand,
    regardless of how the AI generates it.
    
    Examples:
        "5 بوصة" -> "5IN"
        "10 متر" -> "10M"
        "16 بار" -> "16BAR"
        "PVC"    -> "PVC"
        "12W"    -> "12W"
    """
    if not val:
        return ""
    
    val = str(val).strip()
    
    # Extract number prefix and unit suffix
    # Match patterns like "5 بوصة", "10 متر", "16 بار", "12W", "50MM"
    number_match = re.match(r'^(\d+[\.\d]*)\s*(.*)$', val)
    
    if number_match:
        number = number_match.group(1)
        # Remove trailing .0 if it's a whole number
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
    
    # Standardize Arabic and English unit names to short codes
    unit_map = {
        # Length
        "بوصة": "IN", "بوصه": "IN", "انش": "IN", "إنش": "IN",
        "INCH": "IN", "INCHES": "IN", "\"": "IN",
        "متر": "M", "م": "M", "METER": "M", "METERS": "M", "MTR": "M",
        "ملم": "MM", "ملي": "MM", "مم": "MM", "MILLIMETER": "MM", "MILLIMETERS": "MM",
        "سم": "CM", "سنتيمتر": "CM", "CENTIMETER": "CM", "CENTIMETERS": "CM",
        # Pressure
        "بار": "BAR", "BARS": "BAR",
        # Power
        "واط": "W", "وات": "W", "WATT": "W", "WATTS": "W",
        "كيلو واط": "KW", "KILOWATT": "KW",
        # Weight
        "كيلو": "KG", "كجم": "KG", "KILOGRAM": "KG", "KILOGRAMS": "KG",
        "جرام": "G", "GRAM": "G", "GRAMS": "G",
        "طن": "TON", "TONS": "TON",
        # Volume
        "لتر": "L", "LITER": "L", "LITRE": "L", "LITERS": "L",
        "جالون": "GAL", "GALLON": "GAL",
        # Electrical
        "أمبير": "AMP", "امبير": "AMP", "AMPERE": "AMP", "AMP": "AMP",
        "فولت": "V", "VOLT": "V", "VOLTS": "V",
        # Speed
        "ميجا": "MEGA", "MEGA": "MEGA",
        "جيجا": "GB", "GB": "GB",
    }
    
    # Try to match and replace unit
    normalized_unit = unit
    for ar_unit, en_code in unit_map.items():
        if unit == ar_unit.upper() or unit == en_code:
            normalized_unit = en_code
            break
    
    # Remove spaces from the final result
    result = f"{number}{normalized_unit}".replace(" ", "")
    
    # If result is empty, return the original cleaned up
    if not result:
        result = val.strip().upper().replace(" ", "")
    
    return result


def find_existing_code_in_classifications(sh, sub_en, spec1_val, spec2_val, spec3_val):
    """Look up existing classifications to find if same product+specs already has a code.
    
    This ensures the SAME product with the SAME specs always gets the SAME code.
    Matching is done on sub_en (product type) + spec values (not shorthands).
    """
    try:
        ws = sh.worksheet("التصنيفات")
        rows = ws.get_all_values()
        
        # Column layout: [ID, Original, BasicAr, BasicEn, MainAr, MainEn, SubAr, SubEn, 
        #                  Spec1Name, Spec1Val, Spec2Name, Spec2Val, Spec3Name, Spec3Val, Code, Date]
        # Indices:         0    1        2        3        4        5       6      7
        #                  8          9          10         11         12         13       14   15
        
        target_sub = (sub_en or "").strip().lower()
        target_s1 = normalize_spec_value(spec1_val)
        target_s2 = normalize_spec_value(spec2_val)
        target_s3 = normalize_spec_value(spec3_val)
        
        for row in rows[1:]:  # skip header
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
                    logger.info(f"✅ Found existing code '{row_code}' for {sub_en} [{spec1_val}, {spec2_val}, {spec3_val}]")
                    return row_code
        
        return None
    except Exception as e:
        logger.error(f"Error looking up existing classification code: {e}")
        return None


def normalize_spec_value(val):
    """Normalize a spec value for comparison (case-insensitive, trimmed, unified Arabic)."""
    if not val:
        return ""
    val = str(val).strip().lower()
    # Normalize Arabic characters
    val = re.sub("[إأآا]", "ا", val)
    val = re.sub("ى", "ي", val)
    val = re.sub("ة", "ه", val)
    val = re.sub(r"\s+", " ", val).strip()
    return val


def build_final_code(base_code, spec1_sh, spec2_sh, spec3_sh):
    """Build the final product code from base code + normalized spec shorthands.
    
    Example: base_code="PLU-OUT-DRA", spec1_sh="5IN", spec2_sh="10M", spec3_sh="16BAR"
    Result: "PLU-OUT-DRA-5IN-10M-16BAR"
    """
    parts = [base_code]
    for ssh in [spec1_sh, spec2_sh, spec3_sh]:
        normalized = normalize_spec_shorthand(ssh) if ssh else ""
        if normalized:
            parts.append(normalized)
    return "-".join(parts)


def add_new_item_to_taxonomy(sh, res):
    """Add completely new category to 'الاساسي' sheet"""
    try:
        b_sh = res.get('basic_sh', '') or res.get('basic_en', '')[:3]
        m_sh = res.get('main_sh', '') or res.get('main_en', '')[:3]
        s_sh = res.get('sub_sh', '') or res.get('sub_en', '')[:4]
        code = generate_base_code(b_sh, m_sh, s_sh) # We don't save this in taxonomy sheet, but use it here to construct base
        
        ws = sh.worksheet("الاساسي")
        row = [
            res.get('basic_ar', ''), res.get('basic_en', ''),
            res.get('main_ar', ''), res.get('main_en', ''),
            res.get('sub_ar', ''), res.get('sub_en', ''),
            res.get('spec1_name', ''),
            res.get('spec2_name', ''),
            res.get('spec3_name', '')
        ]
        ws.append_row(row)
        
        # force clear cache
        global _SUMMARY_CACHE_TIME
        _SUMMARY_CACHE_TIME = 0
        
        logger.info(f"Learned new item and added to taxonomy: {res.get('sub_en')} without fixed base code")
        return code
    except Exception as e:
        logger.error(f"Failed to learn new item: {e}")
        return None

def classify_item_ai(item_desc, taxonomy_data_str):
    if not settings.GEMINI_API_KEY: return None
    
    prompt = f"""
    Task: Classify item: "{item_desc}"
    Taxonomy Reference: {taxonomy_data_str}
    
    Instructions:
    1. Match existing taxonomy strictly based on the reference above. 
    2. Code Generation (CRITICAL): Generate concise English shorthands (2-4 chars ONLY):
       - basic_sh, main_sh: use the category abbreviation (e.g., ELE, OFF, CON, PLU)
       - sub_sh: Use a unique short word for the sub-category (e.g., CAB, BULB, PEN, PIPE).
       - spec1_sh, spec2_sh, spec3_sh: MUST be from the SPEC VALUE, not the spec name.
         ✅ Diameter=5inches → spec1_sh="5IN" | Length=10M → spec2_sh="10M" | Pressure=16bar → spec3_sh="16BAR"
         ✅ Wattage=12W → spec1_sh="12W" | Thickness=3MM → spec1_sh="3MM"
         ❌ Diameter=50MM → spec1_sh="DIA" (this is the spec NAME, not the value!)
    3. IMPORTANT: spec shorthands must be DETERMINISTIC. Same value = same shorthand always.
       Use this format: [number][UNIT_CODE]. Unit codes: IN=inch, M=meter, MM=millimeter, CM=centimeter, BAR=bar, W=watt, KG=kilogram, V=volt, AMP=ampere, L=liter.
    4. If NOT found in taxonomy, invent new logical names and English 3-letter shorthands (_sh).
    
    JSON Schema:
    {{
        "found": boolean,
        "basic_ar": "string", "basic_en": "string", "basic_sh": "string",
        "main_ar": "string", "main_en": "string", "main_sh": "string",
        "sub_ar": "string", "sub_en": "string", "sub_sh": "string",
        "spec1_name": "string", "spec1_val": "string", "spec1_sh": "string",
        "spec2_name": "string", "spec2_val": "string", "spec2_sh": "string",
        "spec3_name": "string", "spec3_val": "string", "spec3_sh": "string"
    }}
    """
    
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt, generation_config={"temperature":0, "response_mime_type": "application/json"})
        text = response.text.strip()
        if text.startswith('```json'): text = text[7:]
        elif text.startswith('```'): text = text[3:]
        if text.endswith('```'): text = text[:-3]
        return json.loads(text.strip())
    except Exception as e:
        logger.error(f"Classification AI Error: {e}")
        return None

def process_and_save_classification(sh, item_id, text):
    tax_rows = get_taxonomy(sh)
    tax_summary = get_taxonomy_summary(sh)
    
    # Simple retry block for the AI classification
    import time
    res = None
    for attempt in range(3):
        res = classify_item_ai(text, tax_summary)
        if res: break
        logger.warning(f"Classification retry {attempt+1}/3 for item {item_id}")
        time.sleep(2)
        
    if not res:
        logger.error(f"Failed to classifying item '{item_id}' after retries.")
        return False
    
    try:
        sub_en = (res.get('sub_en') or '').strip().lower()
        
        # Build map for override check from الاساسي sheet
        existing_map = {}
        for row in tax_rows:
            if len(row) >= 6 and row[5]:
                existing_map[row[5].strip().lower()] = row
                
        is_truly_new = sub_en and (sub_en not in existing_map)
        
        if is_truly_new:
            # New category - add to الاساسي
            logger.info("New sub-category detected. Adding to primary sheet.")
            base_code = add_new_item_to_taxonomy(sh, res)
            if not base_code:
                base_code = generate_base_code(
                    res.get('basic_sh', 'XXX'), res.get('main_sh', 'XXX'), res.get('sub_sh', 'XXX')
                )
        else:
            # Existing category - override AI details with sheet truth
            logger.info("Category exists, overriding AI data with Sheet facts.")
            r = existing_map[sub_en]
            
            res['basic_ar'] = r[0] if len(r) > 0 else res.get('basic_ar')
            res['basic_en'] = r[1] if len(r) > 1 else res.get('basic_en')
            res['main_ar'] = r[2] if len(r) > 2 else res.get('main_ar')
            res['main_en'] = r[3] if len(r) > 3 else res.get('main_en')
            res['sub_ar'] = r[4] if len(r) > 4 else res.get('sub_ar')
            res['sub_en'] = r[5] if len(r) > 5 else res.get('sub_en')
            
            # Get base code by combining the English strings or shorthands generated by AI
            base_code = generate_base_code(
                res.get('basic_sh', 'XXX'), res.get('main_sh', 'XXX'), res.get('sub_sh', 'XXX')
            )
            
            # Override Spec Names from sheet
            if len(r) > 6 and r[6]: res['spec1_name'] = r[6]
            if len(r) > 7 and r[7]: res['spec2_name'] = r[7]
            if len(r) > 8 and r[8]: res['spec3_name'] = r[8]

        # ========================================
        # CODE STANDARDIZATION LOGIC
        # ========================================
        
        spec1_val = res.get('spec1_val', '')
        spec2_val = res.get('spec2_val', '')
        spec3_val = res.get('spec3_val', '')
        
        # Step 1: Check if the SAME product with SAME specs already has a code in التصنيفات
        existing_code = find_existing_code_in_classifications(
            sh, res.get('sub_en', ''), spec1_val, spec2_val, spec3_val
        )
        
        if existing_code:
            # REUSE the existing code for consistency (same product + same specs = same code)
            code = existing_code
            logger.info(f"♻️ Reusing existing code: {code}")
        else:
            # Step 2: Generate NEW code = base_code + normalized spec shorthands
            code = build_final_code(
                base_code,
                res.get('spec1_sh', ''),
                res.get('spec2_sh', ''),
                res.get('spec3_sh', '')
            )
            logger.info(f"🆕 Generated new code: {code} (base={base_code})")
        
        # ========================================
        # SAVE TO التصنيفات SHEET
        # ========================================
        from datetime import datetime
        
        ws = sh.worksheet("التصنيفات")
        row = [
            item_id, text,
            res.get("basic_ar", ""), res.get("basic_en", ""),
            res.get("main_ar", ""), res.get("main_en", ""),
            res.get("sub_ar", ""), res.get("sub_en", ""),
            res.get("spec1_name", ""), res.get("spec1_val", ""),
            res.get("spec2_name", ""), res.get("spec2_val", ""),
            res.get("spec3_name", ""), res.get("spec3_val", ""),
            code,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ]
        ws.append_row(row)
        logger.info(f"✅ Successfully saved classification for item {item_id} with code: {code}")
        return True
    except Exception as e:
        logger.error(f"Error appending classification to sheet for item {item_id}: {e}")
        return False
        
def get_taxonomy_summary_static():
    return _SUMMARY_CACHE or "Taxonomy data loading from sheet..."
