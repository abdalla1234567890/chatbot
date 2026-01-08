# خطوات النشر على Vercel - دليل سريع

## المتطلبات الأساسية

قبل البدء، تأكد من توفر:
- ✅ حساب على [Vercel](https://vercel.com)
- ✅ حساب على [Neon.tech](https://neon.tech) لقاعدة البيانات
- ✅ Google Sheets API Credentials
- ✅ Gemini API Key

---

## الخطوة 1: إعداد قاعدة البيانات PostgreSQL

### استخدام Neon.tech (مجاني)

1. اذهب إلى https://neon.tech وسجل دخول
2. اضغط "Create Project"
3. اختر اسم للمشروع والمنطقة (يفضل EU Central 1)
4. انسخ `DATABASE_URL` من لوحة التحكم
5. احفظه للاستخدام لاحقًا

الصيغة:
```
postgresql://user:password@host/database?sslmode=require
```

---

## الخطوة 2: إعداد Google Sheets API

### إنشاء Service Account

1. اذهب إلى https://console.cloud.google.com
2. أنشئ مشروع جديد أو اختر مشروع موجود
3. من القائمة الجانبية: **APIs & Services** > **Enable APIs and Services**
4. ابحث عن "Google Sheets API" وفعّله
5. اذهب إلى **Credentials** > **Create Credentials** > **Service Account**
6. أدخل اسم للـ Service Account واضغط Create
7. اضغط على Service Account المُنشأ
8. اذهب إلى تبويب **Keys** > **Add Key** > **Create New Key**
9. اختر JSON وحمّل الملف
10. افتح الملف وانسخ **كل** المحتوى

### مشاركة Google Sheet

1. افتح Google Sheet الذي تريد استخدامه (اسمه: "طلبات")
2. اضغط "Share"
3. الصق البريد الإلكتروني من ملف JSON (حقل `client_email`)
4. أعطه صلاحية "Editor"

---

## الخطوة 3: نشر Backend على Vercel

### من Terminal

```bash
cd backend
vercel
```

### إعداد المتغيرات

عند السؤال، أدخل:

1. **DATABASE_URL**
   ```
   postgresql://user:password@host/database?sslmode=require
   ```

2. **GEMINI_API_KEY**
   ```
   AIzaSy...
   ```

3. **GOOGLE_CREDENTIALS_JSON**
   ```json
   {"type":"service_account","project_id":"...","private_key_id":"...","private_key":"...","client_email":"...","client_id":"...","auth_uri":"...","token_uri":"...","auth_provider_x509_cert_url":"...","client_x509_cert_url":"..."}
   ```
   > ⚠️ **مهم**: انسخ المحتوى كاملاً في سطر واحد بدون مسافات أو أسطر جديدة

### بعد النشر

- احفظ رابط Backend (مثال: `https://your-backend.vercel.app`)
- جرب الوصول إلى `https://your-backend.vercel.app/` للتأكد من عمله

---

## الخطوة 4: نشر Frontend على Vercel

### من Terminal

```bash
cd frontend
vercel
```

### إعداد المتغيرات

عند السؤال، أدخل:

**NEXT_PUBLIC_API_URL**
```
https://your-backend.vercel.app
```
> استبدل `your-backend.vercel.app` برابط Backend من الخطوة السابقة

### بعد النشر

- احفظ رابط Frontend (مثال: `https://your-frontend.vercel.app`)

---

## الخطوة 5: التحقق من النشر

### اختبار كامل

1. افتح رابط Frontend في المتصفح
2. سجل دخول بحساب Admin:
   - الكود: `admin123`
3. جرب إنشاء طلب جديد
4. تحقق من ظهور الطلب في Google Sheets

### في حالة وجود مشاكل

#### Backend لا يعمل
- تحقق من Logs في Vercel Dashboard
- تأكد من صحة `DATABASE_URL`
- تأكد من صحة `GOOGLE_CREDENTIALS_JSON`

#### Frontend لا يتصل بـ Backend
- تأكد من `NEXT_PUBLIC_API_URL` يشير لرابط Backend الصحيح
- تحقق من CORS في Backend (يجب أن يكون `allow_origins=["*"]`)

#### Google Sheets لا يحفظ
- تأكد من مشاركة Sheet مع Service Account Email
- تأكد من اسم Sheet هو "طلبات" بالضبط
- تحقق من صحة `GOOGLE_CREDENTIALS_JSON`

---

## إضافة/تعديل متغيرات البيئة بعد النشر

### من Vercel Dashboard

1. اذهب إلى https://vercel.com/dashboard
2. اختر المشروع (Backend أو Frontend)
3. اذهب إلى **Settings** > **Environment Variables**
4. أضف أو عدّل المتغيرات
5. اضغط **Save**
6. أعد نشر المشروع من تبويب **Deployments** > **Redeploy**

---

## نصائح مهمة

- 🔒 **لا تشارك** متغيرات البيئة مع أحد
- 📝 احفظ نسخة احتياطية من `credentials.json`
- 🔄 عند تعديل الكود، استخدم `vercel --prod` للنشر المباشر
- 📊 راقب Logs في Vercel Dashboard لمتابعة الأخطاء
- 💾 قاعدة البيانات على Neon.tech لها حد مجاني، راقب الاستخدام

---

## الأوامر المفيدة

```bash
# نشر تجريبي (Preview)
vercel

# نشر إنتاجي (Production)
vercel --prod

# عرض Logs
vercel logs

# ربط مشروع موجود
vercel link
```

---

## الدعم

إذا واجهت أي مشكلة:
1. تحقق من Logs في Vercel
2. راجع متغيرات البيئة
3. تأكد من صحة جميع الإعدادات
