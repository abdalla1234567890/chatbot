import sqlite3
import logging
import os
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

logger = logging.getLogger(__name__)

DB_NAME = "users.db"
DATABASE_URL = os.getenv("DATABASE_URL")

# --- Hybrid Database Adapter ---
# This adapter allows the app to run on:
# 1. Local Machine -> SQLite (No setup required)
# 2. Vercel/Production -> PostgreSQL (Requires DATABASE_URL)

try:
    import psycopg2
except ImportError:
    psycopg2 = None

def hash_password(password: str) -> str:
    # REVERTED: Using plain text as requested
    return password

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # REVERTED: Simple string comparison
    return plain_password == hashed_password

def is_postgres():
    """Check if we should use PostgreSQL"""
    return bool(DATABASE_URL) and (psycopg2 is not None)

def get_db_connection():
    """Get connection based on environment"""
    if is_postgres():
        try:
            conn = psycopg2.connect(DATABASE_URL)
            return conn
        except Exception as e:
            logger.error(f"❌ Failed to connect to Postgres: {e}")
            raise e
    else:
        # Local SQLite Fallback
        conn = sqlite3.connect(DB_NAME)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

def execute_query(cursor, query, params=None):
    """Execute query handling syntax differences (? vs %s)"""
    if is_postgres():
        # Postgres uses %s
        query = query.replace("?", "%s")
    else:
        # SQLite uses ?
        pass
        
    cursor.execute(query, params or ())

def init_db():
    """Initialize database tables tailored to the active DB engine"""
    mode = "PostgreSQL (Production)" if is_postgres() else "SQLite (Local)"
    logger.info(f"🔄 Initializing Database. Mode: {mode}")
    
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # 1. Users Table (Compatible SQL)
        # code_hash replaces code as the primary mechanism but we'll keep the column name 'code' for simplicity
        # but store the hash there.
        execute_query(c, '''CREATE TABLE IF NOT EXISTS users
                     (code TEXT PRIMARY KEY, 
                      name TEXT, 
                      phone TEXT, 
                      is_admin INTEGER DEFAULT 0)''')
        
        # 2. Locations Table
        if is_postgres():
            c.execute('''CREATE TABLE IF NOT EXISTS locations
                         (id SERIAL PRIMARY KEY,
                          name TEXT UNIQUE NOT NULL)''')
        else:
            c.execute('''CREATE TABLE IF NOT EXISTS locations
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          name TEXT UNIQUE NOT NULL)''')
        
        # 3. User Locations Table
        if is_postgres():
             c.execute('''CREATE TABLE IF NOT EXISTS user_locations
                          (user_code TEXT NOT NULL,
                           location_id INTEGER NOT NULL,
                           PRIMARY KEY (user_code, location_id),
                           FOREIGN KEY (user_code) REFERENCES users(code) ON DELETE CASCADE,
                           FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE)''')
        else:
            c.execute('''CREATE TABLE IF NOT EXISTS user_locations
                         (user_code TEXT NOT NULL,
                          location_id INTEGER NOT NULL,
                          PRIMARY KEY (user_code, location_id))''')

        # --- Seeding Default Admin ---
        c.execute("SELECT COUNT(*) FROM users")
        if c.fetchone()[0] == 0:
            logger.info("⚡ Database is empty. Creating default admin user...")
            # Default Admin: Code=admin123
            # You should change this immediately after login!
            admin_code = "admin123"
            hashed_admin = hash_password(admin_code)
            
            execute_query(c, "INSERT INTO users (code, name, phone, is_admin) VALUES (?, ?, ?, ?)", 
                        (hashed_admin, "Main Admin", "0500000000", 1))
            logger.info("✅ Default admin created. Code: admin123")
            
        # Default Locations
        try:
            c.execute("SELECT COUNT(*) FROM locations")
            count = c.fetchone()[0]
                
            if count == 0:
                default_locations = [
                    "عمان", "العراق", "مصر قرعة", "مصر مميز VIP", "مصر تضامن إقتصادي",
                    "مصر تضامن 5 nuggets", "مصر سياحي إقتصادي", "مصر سياحي مميز",
                    "مصر سياحي شركات VIP", "نيجيرا", "مصر بري", "روسيا", "بنغلادش",
                    "اندونيسيا", "تشاد", "فلسطين", "مشروع صيانة اعمال جنوب اسيا",
                    "ترافيل كورنر", "الراجحي 5 نجوم", "مشروع كدانه دورات مياه مزدلفة"
                ]
                for location in default_locations:
                    execute_query(c, "INSERT INTO locations (name) VALUES (?)", (location,))
                logger.info(f"📍 Added {len(default_locations)} default locations.")
        except Exception as e:
            logger.warning(f"locations init warning: {e}")

        conn.commit()
        conn.close()
        logger.info("✅ Database initialized successfully.")
    except Exception as e:
        logger.error(f"❌ Database Init Failed: {e}")

def db_get_user_by_code(code):
    """Internal helper to find user by verifying plain code against hashes"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT code, name, phone, is_admin FROM users")
        all_users = c.fetchall()
        conn.close()
        
        for user in all_users:
            if verify_password(code, user[0]):
                return user
        return None
    except Exception as e:
        logger.error(f"Error fetching user by code: {e}")
        return None

def db_login(code):
    """Check login and return user details"""
    user = db_get_user_by_code(code)
    if user:
        return user[1], user[2], user[3] # name, phone, is_admin
    return None

def db_add_user(code, phone, name):
    """إضافة مستخدم مع تشفير الكود"""
    if len(code) != 8: return "❌ الكود يجب أن يكون 8 حروف/أرقام بالضبط."
    if len(name) > 100: return "❌ الاسم طويل جداً (حد أقصى 100 حرف)."
    if not (len(phone) == 10 and phone.isdigit() and phone.startswith("05")):
        return "❌ رقم الهاتف يجب أن يتكون من 10 أرقام بالضبط وأن يبدأ بـ '05'."

    # Check for existing code (using hash verification is slow, but necessary for uniqueness if we don't store plain codes)
    if db_get_user_by_code(code):
        return "❌ هذا الكود مستخدم بالفعل."

    try:
        hashed_code = hash_password(code)
        conn = get_db_connection()
        c = conn.cursor()
        execute_query(c, "INSERT INTO users (code, name, phone, is_admin) VALUES (?, ?, ?, 0)", 
                  (hashed_code, name, phone))
        conn.commit()
        conn.close()
        return "✅ تم إضافة المستخدم بنجاح."
    except Exception as e:
        return f"❌ خطأ غير متوقع: {e}"

def db_delete_user(code):
    """حذف مستخدم - يدعم الهاش"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. البحث بالهاش
    c.execute("SELECT code, name, phone, is_admin FROM users WHERE code = ?", (code,))
    user = c.fetchone()
    
    hashed_code = code
    
    if not user:
        # 2. البحث بالكود الأصلي (fallback)
        conn.close() 
        user_plain = db_get_user_by_code(code)
        if not user_plain:
            return "❌ المستخدم غير موجود."
        user = user_plain
        hashed_code = user[0]
        # Re-open connection for delete
        conn = get_db_connection()
        c = conn.cursor()

    # Admin verification
    if user[3] == 1: 
        c.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
        admin_count = c.fetchone()[0]
        if admin_count <= 1:
            conn.close()
            return "❌ لا يمكن حذف الأدمن الوحيد."

    try:
        execute_query(c, "DELETE FROM users WHERE code = ?", (hashed_code,))
        conn.commit()
        conn.close()
        return "✅ تم الحذف."
    except Exception as e:
        conn.close()
        return f"❌ خطأ: {e}"

def db_get_user_locations(user_code):
    """جلب المواقع الخاصة بمستخدم معين
    يقبل إما الكود الأصلي أو الهاش مباشرة
    """
    # أولاً نحاول البحث بالكود الأصلي
    user = db_get_user_by_code(user_code)
    if user:
        hashed_code = user[0]
    else:
        # إذا لم نجد، نفترض أن user_code هو الهاش نفسه
        hashed_code = user_code
    
    try:
        conn = get_db_connection()
        c = conn.cursor()
        execute_query(c, """SELECT l.id, l.name FROM locations l
                          INNER JOIN user_locations ul ON l.id = ul.location_id
                          WHERE ul.user_code = ?
                          ORDER BY l.name""", (hashed_code,))
        locations = c.fetchall()
        conn.close()
        return locations
    except Exception as e:
        logger.error(f"❌ خطأ في جلب مواقع المستخدم: {e}")
        return []

def db_set_user_locations(user_code, location_ids):
    """تحديث المواقع الخاصة بمستخدم معين
    يقبل إما الكود الأصلي أو الهاش مباشرة
    """
    # أولاً نحاول البحث بالكود الأصلي
    user = db_get_user_by_code(user_code)
    if user:
        hashed_code = user[0]
    else:
        # إذا لم نجد، نفترض أن user_code هو الهاش نفسه
        hashed_code = user_code
    
    try:
        conn = get_db_connection()
        c = conn.cursor()
        execute_query(c, "DELETE FROM user_locations WHERE user_code = ?", (hashed_code,))
        for location_id in location_ids:
            execute_query(c, "INSERT INTO user_locations (user_code, location_id) VALUES (?, ?)", 
                        (hashed_code, location_id))
        conn.commit()
        conn.close()
        return "✅ تم تحديث المواقع بنجاح."
    except Exception as e:
        return f"❌ خطأ: {e}"

def db_add_location_to_user(user_code, location_id):
    user = db_get_user_by_code(user_code)
    if not user: return "❌ المستخدم غير موجود."
    
    hashed_code = user[0]
    try:
        conn = get_db_connection()
        c = conn.cursor()
        execute_query(c, "INSERT INTO user_locations (user_code, location_id) VALUES (?, ?)", 
                    (hashed_code, location_id))
        conn.commit()
        conn.close()
        return "✅ تم إضافة الموقع للمستخدم."
    except Exception as e:
        if "UNIQUE constraint" in str(e) or "duplicate key" in str(e):
            return "❌ هذا الموقع موجود بالفعل لدى المستخدم."
        return f"❌ خطأ: {e}"

def db_remove_location_from_user(user_code, location_id):
    user = db_get_user_by_code(user_code)
    if not user: return "❌ المستخدم غير موجود."
    
    hashed_code = user[0]
    try:
        conn = get_db_connection()
        c = conn.cursor()
        execute_query(c, "DELETE FROM user_locations WHERE user_code = ? AND location_id = ?", 
                    (hashed_code, location_id))
        count = c.rowcount
        conn.commit()
        conn.close()
        return "✅ تم إزالة الموقع." if count > 0 else "❌ الموقع غير موجود للمستخدم."
    except Exception as e:
        return f"❌ خطأ: {e}"

def db_update_user(code, field, new_value):
    """تحديث بيانات المستخدم
    code: يمكن أن يكون الكود الأصلي أو الهاش (id_hash)
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. تحديد المستخدم المستهدف (بالهاش أو الكود)
    c.execute("SELECT code, name, phone, is_admin FROM users WHERE code = ?", (code,))
    user_by_hash = c.fetchone()
    
    hashed_code = code # افتراضياً، الكود المرسل هو الهاش نفسه
    
    if not user_by_hash:
        # محاولة البحث ككود أصلي (للوراء)
        conn.close()
        user_plain = db_get_user_by_code(code)
        if user_plain:
            hashed_code = user_plain[0]
            # Re-open
            conn = get_db_connection()
            c = conn.cursor()
        else:
            return "❌ المستخدم غير موجود."
    
    ALLOWED_FIELDS = ["name", "phone", "code"]
    if field not in ALLOWED_FIELDS:
        conn.close()
        return "❌ محاولة تعديل حقل غير مسموح به."
    
    # التحقق من القيود
    if field == "name" and len(new_value) > 100: 
        conn.close()
        return "❌ الاسم طويل جداً (حد أقصى 100 حرف)."
        
    if field == "phone":
        if not (len(new_value) == 10 and new_value.isdigit() and new_value.startswith("05")):
            conn.close()
            return "❌ رقم الهاتف يجب أن يتكون من 10 أرقام بالضبط وأن يبدأ بـ '05'."

    if field == "code":
        # عند تعديل الكود:
        # new_value هو الكود الجديد الخام (Plain Text) الذي أدخله الأدمن
        if len(new_value) != 8: 
            conn.close()
            return "❌ الكود يجب أن يكون 8 حروف/أرقام بالضبط."
            
        # التأكد من أن الكود الجديد غير مستخدم (نتحقق من الهاش تبعه إذا موجود، أو الكود نفسه)
        # لكن لأننا لا نخزن الكود الخام، علينا أن نتحقق إذا كان أي مستخدم يملك نفس الهاش
        
        # نحن بحاجة لإغلاق الاتصال الحالي لاستدعاء دالة أخرى تستخدم اتصالاً جديداً
        conn.close() 
        if db_get_user_by_code(new_value): 
            return "❌ الكود الجديد مستخدم بالفعل."
        
        # إعادة فتح الاتصال
        conn = get_db_connection()
        c = conn.cursor()
            
        # القيمة الجديدة التي سنخزنها هي الهاش
        field_value = hash_password(new_value)
    else:
        field_value = new_value

    try:
        query = f"UPDATE users SET {field} = ? WHERE code = ?"
        # لاحظ: في الجدول العمود اسمه code لكنه يخزن الهاش
        execute_query(c, query, (field_value, hashed_code))
        conn.commit()
        conn.close()
        return f"✅ تم تحديث **{field}**."
    except Exception as e:
        conn.close()
        return f"❌ خطأ: {e}"

def db_get_all_users():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT code, name, phone, is_admin FROM users")
        users = c.fetchall()
        conn.close()
        # REVERTED: Show plain code. We keep id_hash field for frontend compatibility but it holds the same plain code.
        return [{"code": u[0], "name": u[1], "phone": u[2], "is_admin": u[3], "id_hash": u[0]} for u in users]
    except Exception as e:
        logger.error(f"Error fetching all users: {e}")
        return []

def db_get_all_locations():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id, name FROM locations ORDER BY name")
        locations = c.fetchall()
        conn.close()
        return locations
    except Exception as e:
        logger.error(f"❌ خطأ في جلب المواقع: {e}")
        return []

def db_add_location(name):
    if not name or len(name.strip()) == 0: return "❌ اسم الموقع لا يمكن أن يكون فارغاً."
    name = name.strip()
    if len(name) > 100: return "❌ اسم الموقع طويل جداً (حد أقصى 100 حرف)."
    try:
        conn = get_db_connection()
        c = conn.cursor()
        execute_query(c, "INSERT INTO locations (name) VALUES (?)", (name,))
        conn.commit()
        conn.close()
        return "✅ تم إضافة الموقع بنجاح."
    except Exception as e:
        if "UNIQUE constraint" in str(e) or "duplicate key" in str(e):
            return "❌ هذا الموقع موجود بالفعل."
        return f"❌ خطأ غير متوقع: {e}"

def db_delete_location(location_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        execute_query(c, "DELETE FROM locations WHERE id = ?", (location_id,))
        count = c.rowcount
        conn.commit()
        conn.close()
        return "✅ تم حذف الموقع." if count > 0 else "❌ الموقع غير موجود."
    except Exception as e:
        return f"❌ خطأ: {e}"
