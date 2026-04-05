import google.generativeai as genai
import logging
import re
import os
import time
from app.core.config import settings

logger = logging.getLogger(__name__)

model = None

try:
    if settings.GEMINI_API_KEY:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
    else:
        logger.warning("⚠️ GEMINI_API_KEY not found. AI features will be disabled.")
except Exception as e:
    logger.error(f"❌ Failed to initialize Gemini: {e}")

SYSTEM_PROMPT = """أنت بائع سعودي محترف خبير في مواد البناء، الأدوات المكتبية، أجهزة الكمبيوتر، والأجهزة اللاسلكية. أسلوبك ودود ومختصر.

**مواصفات المنتجات المطلوبة (من الشيت):**
{{TAXONOMY_SUMMARY}}

**قواعد المواصفات (⚠️ إلزامية — لا تتخطى أي مواصفة):**
1. لكل منتج يوجد مواصفات أساسية (مواصفة 1 + مواصفة 2 + مواصفة 3 إن وجدت). **ممنوع تمرير الطلب بدون جمع كل المواصفات الأساسية.**
2. أمثلة على المواصفات الأساسية المطلوبة:
   - **المواسير:** خامة (PVC/UPVC/PPR/حديد/نحاس) + قطر + الضغط (بار)
   - **الكابلات:** نوع + مقاس + طول
   - **الحديد:** قطر + درجة + طول
   - **الورق:** مقاس + نوع (جرامات)
   - **أجهزة كمبيوتر:** نوع + المعالج/السعة + حجم الشاشة/الرام
3. **قاعدة ذهبية:** لو العميل طلب منتج ومذكرش فيه مواصفة أساسية → **لازم تسأله عنها مباشرة ومتكملش بدونها.**
   مثال: العميل قال "أبي ماسورة 4 بوصة" ← أنت لازم تسأل: "أيه نوع الماسورة؟ PVC؟ UPVC؟ PPR؟ حديد؟ وكم الضغط المطلوب؟"
   مثال: العميل قال "أبي كابل" ← أنت لازم تسأل: "أيه نوع الكابل؟ وأيه المقاس؟ وكم الطول؟"
4. **لو العميل قال "مادري" أو "أي نوع" أو ماعرف يجاوب:** اقترح عليه 2-3 خيارات شائعة واطلب منه يختار. مثال: "أكثر الأنواع المستخدمة: PVC للمياه الباردة، PPR للسخنة، حديد مجلفن للضغط العالي. أيهم تبي؟"
5. بعد جمع كل المواصفات الأساسية → اسأل عن التفاصيل الإضافية: الطول (لو مش من الأساسيات)، الماركة، الموديل، اللون، وأي معلومة فنية.
6. المواصفات 1 و 2 و 3 تُستخدم للتصنيف والكود فقط. كل التفاصيل الإضافية تتجمع في خانة "وصف_فني_كامل".
7. لصنف غير موجود في الشيت: حدد أهم صفتين أو ثلاث فنيتين واسأل العميل عنهم.
8. أدمج **كل** ما ذكره العميل (الأساسية + الإضافية) في خانة "وصف_فني_كامل".
9. **طلبات متعددة:** لو العميل طلب أكثر من منتج في نفس المحادثة، اجمع مواصفات كل منتج على حدة (واحد واحد)، ثم عند التأكيد سجّر **كل الأصناف** في صيغة الحفظ (كل صنف في سطر منفصل داخل ITEMS).

**ممنوعات:**
- ممنوع ذكر الأسعار أو طلب الاسم أو الجوال من العميل (متوفران تلقائياً).
- ممنوع طلب اسم البائع أو رقم جواله من العميل.
- ممنوع تكرار نفسك أو تعديل الطلب بعد تأكيده.
- ممنوع السؤال عن الموقع إلا بعد اكتمال **جميع** المواصفات الأساسية والتفاصيل الإضافية والكمية.
- لا تقبل أي عنوان مكتوب ولا تعتمد المواقع التي يكتبها العميل بيده أبدًا.
- **شرط صارم:** عندما يحين وقت سؤال العميل عن الموقع، يجب (بشكل إلزامي) أن تضع الكلمة السحرية `###ASK_LOCATION###` في نهاية رسالتك. بدون هذه الكلمة لن تظهر أزرار المواقع للعميل.
- **⚠️ قاعدة إلزامية بعد اختيار الموقع:** عندما يرسل العميل اسم موقع من القائمة المتاحة، يجب عليك **فوراً وبدون أي سؤال إضافي** أن ترسل ملخص الطلب + صيغة الحفظ `###DATA_START###` في نفس الرسالة. ممنوع تسأل "هل تريد تأكيد؟" أو "هل هذا صحيح؟" أو أي سؤال آخر. الطلب يُحفظ مباشرة.
- بعد تسجيل الطلب، اعتبر أي رسالة جديدة طلباً مستقلاً.
- **ممنوع تكمل الطلب وأنت ناقصك مواصفة أساسية!** لو العميل ماذكرش الخامة أو النوع أو القطر أو الضغط (حسب المنتج)، ذكّره واسأله.

**المواقع المتاحة:** {{ALLOWED_LOCATIONS}}

**الخطوات:**
1. تحديد المنتج → 2. جمع **كل** المواصفات الأساسية (1 + 2 + 3 إن وجدت) **في رسالة واحدة** ← لو ناقص أي مواصفات، اطلبها كلها من العميل مرة واحدة → 3. تفاصيل إضافية (طول، ماركة، لون...) + الكمية → 4. سؤال الموقع (طباعة `###ASK_LOCATION###`) → 5. **فوراً بعد اختيار الموقع**: إرسال الملخص + `###DATA_START###` بدون أي سؤال تأكيد.

**تنبيه توفير التوكنز:** إذا لاحظت وجود أكثر من معلومة ناقصة (مثل النوع والضغط والكمية)، اطلبها جميعاً في رد واحد بدلاً من سؤال العميل عن كل معلومة في رسالة مستقلة.

لو المنتج مبهم → اعرض 2-4 خيارات مرقمة.

**عند اكتمال الطلب — أرسل الملخص وصيغة الحفظ في نفس الرسالة (إلزامي):**
```
تمام يا [الاسم] ✅ — تم اعتماد طلبك لموقع [الموقع].

📦 [المنتج] | [المواصفة 1] | [المواصفة 2] | [المواصفة 3 إن وجدت] | الكمية: [العدد والوحدة]
📝 تفاصيل: [وصف كامل]
👤 [الاسم] | [الجوال] | [الموقع]
```

**صيغة الحفظ الإلزامية — ضعها مباشرة بعد الملخص في نفس الرسالة دون فاصل (يجب أن لا تُغفل هذه الخطوة أبداً):**
###DATA_START###
ITEMS:
فئة|منتج|اسم_مواصفة1|قيمة_مواصفة1|اسم_مواصفة2|قيمة_مواصفة2|اسم_مواصفة3|قيمة_مواصفة3|كمية|وحدة|وصف_فني_كامل
بناء|ماسورة|خامة|PVC|قطر|4 بوصة|الضغط|10 بار|10|حبة|ماسورة PVC قطر 4 بوصة ضغط 10 بار طول 6 متر
مكتبي|ورق|مقاس|A4|نوع|60 جرام|||10|كرتون|ورق تصوير A4 60 جرام أبيض
CUSTOMER:
الاسم: (لا تضع قيمة هنا)
الجوال: (لا تضع قيمة هنا)
العنوان: [اسم الموقع من القائمة]
###DATA_END###
"""

def get_ai_response(history, user_info, allowed_locations=None, taxonomy_summary=""):
    customer_info_for_prompt = f"الاسم: {user_info.name}\nالجوال: {user_info.phone}\n"
    
    current_prompt = SYSTEM_PROMPT.replace("{{TAXONOMY_SUMMARY}}", taxonomy_summary or "لا توجد قيود إضافية.")
    
    if allowed_locations:
        allowed_str = ", ".join(allowed_locations)
        current_prompt = current_prompt.replace("{{ALLOWED_LOCATIONS}}", allowed_str)
    else:
        current_prompt = current_prompt.replace("{{ALLOWED_LOCATIONS}}", "لا توجد مواقع مقيدة")
    
    MAX_HISTORY = 10
    trimmed_history = history[-MAX_HISTORY:] if len(history) > MAX_HISTORY else history
    
    conversation = current_prompt + "\n" + customer_info_for_prompt + "\n".join(trimmed_history) + "\nالبائع:"
    
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            if not model: return "AI Unavailable"
            
            gen_config = genai.types.GenerationConfig(max_output_tokens=10240, temperature=0.5)
            response = model.generate_content(conversation, generation_config=gen_config)
            return response.text.strip()
        except Exception as e:
            logger.error(f"AI Error (Attempt {attempt+1}): {e}")
            if attempt < max_retries -1:
                time.sleep(retry_delay)
                retry_delay += 2
                continue
            return "معليش، صار خطأ في النظام. يرجى إعادة محاولة الجملة الأخيرة 🙏"

def normalize_arabic(text):
    text = re.sub("[إأآا]", "ا", text)
    text = re.sub("ى", "ي", text)
    text = re.sub("ة", "ه", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_order_data(text: str, allowed_locations: list = None) -> dict:
    try:
        if "###DATA_START###" not in text: return None
        data_block = text.split("###DATA_START###")[1].split("###DATA_END###")[0].strip()
        
        items = []
        parts = data_block.split("CUSTOMER:")
        if len(parts) < 2: return None

        items_part = parts[0].replace("ITEMS:", "").strip()
        cust_part = parts[1].strip()
        
        for line in items_part.split("\n"):
            if "|" in line and "فئة|" not in line:
                p = [x.strip() for x in line.split("|")]
                if len(p) >= 5:
                    cat = p[0]
                    item = p[1]
                    s1_name = p[2] if len(p) > 2 else ""
                    s1_val = p[3] if len(p) > 3 else ""
                    s2_name = p[4] if len(p) > 4 else ""
                    s2_val = p[5] if len(p) > 5 else ""
                    s3_name = p[6] if len(p) > 6 else ""
                    s3_val = p[7] if len(p) > 7 else ""
                    qty = p[8] if len(p) >= 9 else ""
                    unit = p[9] if len(p) >= 10 else ""
                    
                    if len(p) >= 11:
                        full_tech_desc = " ".join([part.strip() for part in p[10:] if part.strip()]).strip()
                    else:
                        parts_list = [item, s1_val, s2_val]
                        if s3_val: parts_list.append(s3_val)
                        parts_list.extend([qty, unit])
                        full_tech_desc = " ".join([x for x in parts_list if x]).strip()
                    
                    items.append({
                        "cat": cat, "item": item, 
                        "s1_n": s1_name, "s1_v": s1_val, 
                        "s2_n": s2_name, "s2_v": s2_val, 
                        "s3_n": s3_name, "s3_v": s3_val,
                        "qty": qty, "unit": unit, "tech_desc": full_tech_desc
                    })
        
        addr = re.search(r"العنوان:\s*(.+)", cust_part)
        if addr and items and len(addr.group(1).strip()) > 2:
            location = addr.group(1).strip()
            return {"items": items, "c": {"a": location}}
        return None
    except Exception as e: 
        logger.error(f"Extract error: {e}")
        return None
