# Web Chatbot - Next.js + FastAPI

مشروع شات بوت ذكي لاستقبال طلبات مواد البناء باستخدام Next.js للواجهة الأمامية و FastAPI للخادم.

## المتطلبات

- Python 3.9+
- Node.js 18+
- PostgreSQL Database (Neon.tech للإنتاج)
- Google Sheets API Credentials

## متغيرات البيئة المطلوبة

### Backend (.env)

```env
DATABASE_URL=postgresql://user:password@host/database?sslmode=require
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_CREDENTIALS_JSON={"type":"service_account",...}
```

### Frontend (.env.local)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## التشغيل المحلي

### Backend (FastAPI)
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev
```

## الوصول للتطبيق محليًا

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## بيانات الدخول الافتراضية

- Admin: `admin123`

---

## نشر المشروع على Vercel

### 1. إعداد قاعدة البيانات (Neon.tech)

1. سجل حساب على [Neon.tech](https://neon.tech)
2. أنشئ مشروع جديد
3. احصل على `DATABASE_URL` من لوحة التحكم
4. قاعدة البيانات ستُنشأ تلقائيًا عند أول تشغيل

### 2. إعداد Google Sheets API

1. اذهب إلى [Google Cloud Console](https://console.cloud.google.com)
2. أنشئ مشروع جديد
3. فعّل Google Sheets API
4. أنشئ Service Account وحمّل ملف JSON
5. شارك Google Sheet مع البريد الإلكتروني للـ Service Account
6. انسخ محتوى ملف JSON كاملاً (سيُستخدم كمتغير بيئة)

### 3. نشر Backend

```bash
cd backend
vercel
```

عند السؤال عن المتغيرات، أضف:
- `DATABASE_URL`: من Neon.tech
- `GEMINI_API_KEY`: من Google AI Studio
- `GOOGLE_CREDENTIALS_JSON`: محتوى ملف credentials.json كاملاً

### 4. نشر Frontend

```bash
cd frontend
vercel
```

عند السؤال عن المتغيرات، أضف:
- `NEXT_PUBLIC_API_URL`: رابط Backend من الخطوة السابقة (مثال: https://your-backend.vercel.app)

### 5. التحقق من النشر

1. افتح رابط Frontend
2. سجل دخول بحساب admin: `admin123`
3. جرب إنشاء طلب جديد
4. تحقق من حفظ الطلب في Google Sheets

---

## الهيكل العام للمشروع

```
Web-chatboot-next/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── database.py          # Database operations
│   ├── ai_agent.py          # Gemini AI integration
│   ├── sheets.py            # Google Sheets integration
│   ├── requirements.txt     # Python dependencies
│   ├── vercel.json          # Vercel deployment config
│   └── .env                 # Environment variables (local)
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx         # Login page
│   │   ├── chat/            # Chat interface
│   │   └── admin/           # Admin panel
│   ├── package.json         # Node dependencies
│   ├── vercel.json          # Vercel deployment config
│   └── .env.local           # Environment variables (local)
│
└── credentials.json         # Google Sheets credentials (local only)
```

## الميزات

- ✅ تسجيل دخول بالكود
- ✅ شات بوت ذكي باستخدام Gemini AI
- ✅ حفظ الطلبات في Google Sheets
- ✅ لوحة تحكم للأدمن
- ✅ إدارة المستخدمين
- ✅ إدارة المواقع
- ✅ قاعدة بيانات PostgreSQL

## الدعم الفني

للمشاكل والاستفسارات، يرجى فتح Issue في المستودع.
