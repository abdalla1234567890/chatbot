import google.generativeai as genai
import logging
import re

logger = logging.getLogger(__name__)

import os
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

model = None

try:
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
    else:
        logger.warning("⚠️ GEMINI_API_KEY not found. AI features will be disabled.")
except Exception as e:
    logger.error(f"❌ Failed to initialize Gemini: {e}")

SYSTEM_PROMPT = """أنت بائع سعودي محترف لمواد البناء. أسلوبك ودود ومرن.

**مهمتك:** استقبال الطلبات.
**بيانات المتوفرة بالفعل:** اسم العميل ورقم جواله موجودان في ملفك الشخصي.

**قائمة المواقع المتاحة:**
{{ALLOWED_LOCATIONS}}

**القواعد الممنوعة (حتمي جداً):**
- ممنوع ذكر الأسعار.
- ممنوع تطلب الاسم أو رقم الجوال من العميل، هذه البيانات جاهزة.
- ممنوع تكرر نفسك.
- ممنوع الرد على أي طلب لمنتج لا يخص منتجات البناء إطلاقاً.
- ممنوع تطلب العميل اسم البائع أو رقم جوال البائع.
- ممنوع طلب تعديل الموقع من العميل بعد اختياره.
- ممنوع طلب تعديل أي بيانات في الطلب بعد تأكيده.
- ممنوع السؤال عن الموقع إلا عندما تكون جميع تفاصيل الطلب جاهزة.
- لا تقبل أي عنوان يكتبه المستخدم - إذا حاول أن يكتب عنواناً، ارفضه وأجبره على الاختيار من القائمة فقط.
- عندما ينهي العميل الطلب ويتم تسجيله، تعامل مع أي رسالة جديدة على أنها طلب جديد.

**حول الموقع (مهم جداً):**
- عندما تطلب الموقع باستخدام ###ASK_LOCATION###، لا تطلبه مرة أخرى أبداً.
- عندما يرد المستخدم بأي نص، افترض أنه اختار موقعاً وأكمل الطلب فوراً.
- لا تقل "هل هذا صحيح؟" أو "هل تريد تعديل الموقع؟" - فقط أكمل الطلب.

**القاعدة الذهبية:** لا تطلب من المستخدم أي شيء لم تطلبه منه بشكل صريح في هذا الـ prompt.

**العملية:**
1.  تلقي الطلب وتحديد مواصفات المنتجات.
2.  عندما يصبح الطلب جاهزًا للتأكيد، اطلب العنوان (الموقع) باستخدام التاج ###ASK_LOCATION###.
3.  **مهم:** عندما يرد العميل باسم موقع من القائمة أعلاه (مثل: عمان، العراق، إلخ)، اقبله فوراً واكمل الطلب. لا تطلب منه الاختيار مرة أخرى.

**طريقة العمل:**

1️⃣ **فهم الطلب والخيارات:**
    - لو العميل قال منتج عام/مبهم → **اعرض عليه خيارات واضحة**
    - استخدم أرقام للخيارات عشان يسهل على العميل الاختيار
    - الخيارات تكون من 2 إلى 4 خيارات

2️⃣ **التفاصيل المهمة:**
    - اسأل فقط عن التفاصيل المهمة للمنتج
    -في حالة العميل طلب ماسورة او اسلاك اسأله عن قوة الضغط في ادوات السباكه المطلوبه او شدة التحمل في الادوات الكهربيه
    - كن مرن ولا تفترض أي شي

4️⃣ **التأكيد والحفظ:**
    لما تكمل كل البيانات، اكتب **ملخص واضح** للطلب:

    ```
    تمام يا [الاسم] ✅
    
    📦 ملخص طلبك:
    ━━━━━━━━━━━━━━━━
    • [المنتج]: [التفاصيل] - الكمية: [X]
    
    👤 بيانات التوصيل:
    ━━━━━━━━━━━━━━━━
    الاسم: [الاسم الكامل]
    الجوال: [رقم الجوال]
    الموقع: [الموقع]
    ```
**الصيغة النهائية للطلب (يجب أن تحتوي على العنوان فقط):**
###DATA_START###
ITEMS:
فئة|منتج|مواصفة1|مواصفة2|مواصفة3|كمية|وحدة
كهرباء|سلك|...|...|...|5|لفة
CUSTOMER:
الاسم: (لا تضع قيمة هنا)
الجوال: (لا تضع قيمة هنا)
العنوان: ...
###DATA_END###
"""

def get_ai_response(history, user_info, allowed_locations=None):
    """
    history: List of strings (User: ..., Seller: ...)
    user_info: Dict with name and phone
    allowed_locations: List of allowed location names
    """
    customer_info_for_prompt = f"الاسم: {user_info['name']}\nالجوال: {user_info['phone']}\n"
    
    # إضافة المواقع المسموحة للـ prompt إن وجدت
    # إضافة المواقع المسموحة للـ prompt إن وجدت
    if allowed_locations:
        allowed_str = ", ".join(allowed_locations)
        SYSTEM_PROMPT_MODIFIED = SYSTEM_PROMPT.replace("{{ALLOWED_LOCATIONS}}", allowed_str)
    else:
        SYSTEM_PROMPT_MODIFIED = SYSTEM_PROMPT.replace("{{ALLOWED_LOCATIONS}}", "لا توجد مواقع مقيدة")
    
    conversation = SYSTEM_PROMPT_MODIFIED + "\n" + customer_info_for_prompt + "\n".join(history) + "\nالبائع:"
    
    try:
        if not model:
            return "عذراً، نظام الذكاء الاصطناعي غير متصل حالياً (Missing API Key)."
            
        response = model.generate_content(conversation)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        print(f"DEBUG: Gemini API Error: {e}") # Debug print
        return "معليش، صار خطأ في النظام. يرجى إعادة محاولة الجملة الأخيرة 🙏"

def normalize_arabic(text):
    text = re.sub("[إأآا]", "ا", text)
    text = re.sub("ى", "ي", text)
    text = re.sub("ة", "ه", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_order_data(text: str, allowed_locations: list = None) -> dict:
    """استخراج بيانات الطلب، ونبحث فقط عن العنوان"""
    try:
        if "###DATA_START###" not in text: return None
        data_block = text.split("###DATA_START###")[1].split("###DATA_END###")[0].strip()
        
        items = []
        # استخدام التقطيع الصحيح (split)
        parts = data_block.split("CUSTOMER:")
        if len(parts) < 2: return None

        items_part = parts[0].replace("ITEMS:", "").strip()
        cust_part = parts[1].strip()
        
        for line in items_part.split("\n"):
            if "|" in line and "فئة|" not in line:
                p = [x.strip() for x in line.split("|")]
                if len(p) >= 5: # Relaxed condition, at least Cat, Item, Qty, Unit required
                    # Robust parsing:
                    # p[0] = Cat
                    # p[1] = Item
                    # p[-1] = Unit (if len >= 7 usually, but sometimes AI misses it? No, usually Qty, Unit are last)
                    # Let's assume standard prompt structure but missing specs.
                    
                    # Try to map based on standard expectation but handle missing
                    cat = p[0]
                    item = p[1]
                    
                    # Assume last two are Qty and Unit if valid
                    # If len is 6: Cat, Item, S1, S2, Qty, Unit
                    # If len is 7: Cat, Item, S1, S2, S3, Qty, Unit
                    
                    # Safe mapping
                    unit = p[-1] if len(p) >= 4 else ""
                    qty = p[-2] if len(p) >= 5 else ""
                    
                    # Specs are everything in between
                    specs = p[2:-2]
                    s1 = specs[0] if len(specs) > 0 else ""
                    s2 = specs[1] if len(specs) > 1 else ""
                    s3 = specs[2] if len(specs) > 2 else ""
                    
                    items.append({"cat": cat, "item": item, "s1": s1, "s2": s2, "s3": s3, "qty": qty, "unit": unit})
        
        # استخراج العنوان فقط (الاسم والجوال سيتم سحبها من DB)
        addr = re.search(r"العنوان:\s*(.+)", cust_part)
        
        if addr and items and len(addr.group(1).strip()) > 2:
            location = addr.group(1).strip()
            
            # التحقق من أن الموقع من القائمة المسموحة
            if allowed_locations:
                # تطبيع الموقع (إزالة التشكيل والمسافات الزائدة)
                normalized_location = normalize_arabic(location).lower()
                
                # البحث عن موقع مطابق (مع تطبيع)
                location_found = False
                for allowed_loc in allowed_locations:
                    if normalized_location == normalize_arabic(allowed_loc).lower():
                        location = allowed_loc  # استخدام الموقع الصحيح من القائمة
                        location_found = True
                        break
                
                if not location_found:
                    logger.warning(f"❌ موقع غير مسموح: '{location}' (normalized: {normalized_location}). المواقع المتاحة: {allowed_locations}")
                    return None
            
            return {"items": items, "c": {"a": location}}
        return None
    except Exception as e: 
        logger.error(f"Extract error: {e}")
        return None
