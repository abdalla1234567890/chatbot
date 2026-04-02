# دليل النشر على Vercel و Neon.tech 🚀

هذا الدليل يشرح كيفية نقل مشروعك من النسخة المحلية إلى النسخة السحابية ليعمل بشكل دائم.

---

## 1️⃣ الخطوة الأولى: إعداد قاعدة البيانات (Neon.tech)

بما أن Vercel لا يدعم حفظ ملفات `sqlite` بشكل دائم، سنستخدم Neon:

1. أنشئ حساباً على [Neon.tech](https://neon.tech).
2. أنشئ مشروعاً جديداً (مثلاً باسم `chatbot`).
3. في لوحة التحكم، ابحث عن الـ **Connection String**.
4. تأكد من اختيار **Transaction Mode** (عادة ما يكون مفعل تلقائياً).
5. سيكون الرابط بهذا الشكل:
   `postgresql://alex:AbC123dEf@ep-cool-darkness-123.eu-central-1.aws.neon.tech/neondb?sslmode=require`
6. **احفظ هذا الرابط جانباً.**

---

## 2️⃣ الخطوة الثانية: نشر الـ Backend

1. افتح الـ Terminal في مجلد المشروع الرئيسي.
2. ادخل لمجلد الـ backend:
   ```bash
   cd backend
   ```
3. قم بتثبيت Vercel CLI (إذا لم يكن لديك):
   ```bash
   npm install -g vercel
   ```
4. ابدأ عملية النشر:
   ```bash
   vercel
   ```
5. اتبع التعليمات في الـ Terminal:
   - سجل دخول إذا طلب منك.
   - Set up and deploy? **Yes**
   - Which scope? **اختر حسابك**
   - Link to existing project? **No**
   - Project name? **chatbot-backend** (أو أي اسم تفضله)
   - In which directory is your code located? **./**
6. **إضافة متغيرات البيئة (Environment Variables):**
   بعد الانتهاء من أول عملية نشر (حتى لو فشلت)، اذهب للوحة تحكم Vercel وأضف المتغيرات التالية:
   - `DATABASE_URL`: الرابط الذي حصلت عليه من Neon.
   - `GEMINI_API_KEY`: مفتاح Gemini الخاص بك.
   - `GOOGLE_CREDENTIALS_JSON`: محتوى ملف `credentials.json` بالكامل (اجعله في سطر واحد).
7. قم بالنشر النهائي:
   ```bash
   vercel --prod
   ```
8. **انسخ رابط الـ Backend المنشور** (مثلاً: `https://chatbot-backend.vercel.app`).

---

## 3️⃣ الخطوة الثالثة: نشر الـ Frontend

1. ارجع للمجلد الرئيسي ثم ادخل لمجلد الـ frontend:
   ```bash
   cd ../frontend
   ```
2. ابدأ عملية النشر:
   ```bash
   vercel
   ```
3. اتبع التعليمات (اسم المشروع: `chatbot-ui`).
4. **إضافة متغيرات البيئة:**
   في لوحة تحكم Vercel لمشروع الـ Frontend، أضف المتغير التالي:
   - `NEXT_PUBLIC_API_URL`: الرابط الذي حصلت عليه من الـ Backend في الخطوة السابقة.
5. قم بالنشر النهائي:
   ```bash
   vercel --prod
   ```

---

## 💡 ملاحظات هامة

- **CORS**: الكود مبرمج الآن للسماح بجميع الروابط (`*`) مؤقتاً لتسهيل النشر. يمكنك تضييقها لاحقاً من ملف `config.py`.
- **Google Sheets**: لا تنسَ مشاركة الشيت مع البريد الإلكتروني (client_email) الموجود داخل ملف `credentials.json` وأعطِه صلاحية **Editor**.
- **ملف main.py**: قمنا بإنشاء ملف `backend/main.py` خصيصاً ليعمل كـ Entry Point لخدمات Vercel.

---

### الأوامر السريعة للتحديث لاحقاً:
عند رغبتك في تحديث الكود في المستقبل، فقط اكتب في المجلد المعني:
```bash
vercel --prod
```
