import sqlite3
import logging
import os

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

        # Create Admin
        execute_query(c, "SELECT * FROM users WHERE code = ?", ('admin123',))
        if not c.fetchone():
            execute_query(c, "INSERT INTO users (code, name, phone, is_admin) VALUES (?, ?, ?, ?)", 
                      ('admin123', 'admin', '0500000000', 1))
            logger.info("👑 Admin account created: admin123")
            
        # Default Locations
        try:
            if is_postgres():
                c.execute("SELECT COUNT(*) FROM locations")
                count = c.fetchone()[0]
            else:
                c.execute("SELECT COUNT(*) FROM locations")
                count = c.fetchone()[0]
                
            if count == 0:
                default_locations = [
                    "عمان", "العراق", "مصر قرعة", "مصر مميز VIP", "مصر تضامن إقتصادي",
                    "مصر تضامن 5 نجوم", "مصر سياحي إقتصادي", "مصر سياحي مميز",
                    "مصر سياحي شركات VIP", "نيجيريا", "مصر بري", "روسيا", "بنغلادش",
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
        # We generally don't want to crash here in prod if it's just an ephemeral error, 
        # but for init_db it's usually critical. 
        # Main.py catches this now, so we are safe to just log.


def db_login(code):
    """Check login and return user details"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        execute_query(c, "SELECT name, phone, is_admin FROM users WHERE code = ?", (code,))
        result = c.fetchone()
        conn.close()
        
        # Normalize return to tuple (name, phone, is_admin)
        if result:
            return result 
        return None
    except Exception as e:
        logger.error(f"DB Login Error: {e}")
        return None

def db_add_user(code, phone, name):
    """إضافة مستخدم مع التحقق من شروط الإدخال الجديدة"""
    # 1. التحقق من الكود (8 حروف/أرقام بالضبط)
    if len(code) != 8: return "❌ الكود يجب أن يكون 8 حروف/أرقام بالضبط."
    
    # 2. التحقق من الاسم (حد أقصى 100 حرف)
    if len(name) > 100: return "❌ الاسم طويل جداً (حد أقصى 100 حرف)."
    
    # 3. التحقق من الهاتف (10 أرقام بالضبط ويبدأ بـ 05)
    if not (len(phone) == 10 and phone.isdigit() and phone.startswith("05")):
        return "❌ رقم الهاتف يجب أن يتكون من 10 أرقام بالضبط وأن يبدأ بـ '05'."

    try:
        conn = get_db_connection()
        c = conn.cursor()
        execute_query(c, "INSERT INTO users (code, name, phone, is_admin) VALUES (?, ?, ?, 0)", 
                  (code, name, phone))
        conn.commit()
        conn.close()
        return "✅ تم إضافة المستخدم بنجاح."
    except Exception as e:
        # Handle IntegrityError generically since it differs between libs
        if "UNIQUE constraint" in str(e) or "duplicate key" in str(e):
             return "❌ هذا الكود مستخدم بالفعل."
        return f"❌ خطأ غير متوقع: {e}"

def db_delete_user(code):
    if code == "admin123": return "❌ لا يمكن حذف الأدمن الرئيسي."
    try:
        conn = get_db_connection()
        c = conn.cursor()
        execute_query(c, "DELETE FROM users WHERE code = ?", (code,))
        count = c.rowcount
        conn.commit()
        conn.close()
        return "✅ تم الحذف." if count > 0 else "❌ المستخدم غير موجود."
    except Exception as e:
        return f"❌ خطأ: {e}"

def db_get_user_locations(user_code):
    """جلب المواقع الخاصة بمستخدم معين"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        execute_query(c, """SELECT l.id, l.name FROM locations l
                          INNER JOIN user_locations ul ON l.id = ul.location_id
                          WHERE ul.user_code = ?
                          ORDER BY l.name""", (user_code,))
        locations = c.fetchall()
        conn.close()
        return locations
    except Exception as e:
        logger.error(f"❌ خطأ في جلب مواقع المستخدم: {e}")
        return []

def db_set_user_locations(user_code, location_ids):
    """تعيين قائمة المواقع للمستخدم (استبدال القائمة القديمة)"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # حذف المواقع القديمة للمستخدم
        execute_query(c, "DELETE FROM user_locations WHERE user_code = ?", (user_code,))
        
        # إضافة المواقع الجديدة
        for location_id in location_ids:
            execute_query(c, "INSERT INTO user_locations (user_code, location_id) VALUES (?, ?)", 
                        (user_code, location_id))
        
        conn.commit()
        conn.close()
        return "✅ تم تحديث المواقع بنجاح."
    except Exception as e:
        return f"❌ خطأ: {e}"

def db_add_location_to_user(user_code, location_id):
    """إضافة موقع واحد للمستخدم"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        execute_query(c, "INSERT INTO user_locations (user_code, location_id) VALUES (?, ?)", 
                    (user_code, location_id))
        conn.commit()
        conn.close()
        return "✅ تم إضافة الموقع للمستخدم."
    except Exception as e:
        if "UNIQUE constraint" in str(e) or "duplicate key" in str(e):
            return "❌ هذا الموقع موجود بالفعل لدى المستخدم."
        return f"❌ خطأ: {e}"

def db_remove_location_from_user(user_code, location_id):
    """إزالة موقع من مواقع المستخدم"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        execute_query(c, "DELETE FROM user_locations WHERE user_code = ? AND location_id = ?", 
                    (user_code, location_id))
        count = c.rowcount
        conn.commit()
        conn.close()
        return "✅ تم إزالة الموقع." if count > 0 else "❌ الموقع غير موجود للمستخدم."
    except Exception as e:
        return f"❌ خطأ: {e}"

def db_update_user(code, field, new_value):
    """تعديل بيانات مستخدم مع التحقق من شروط الإدخال الجديدة"""
    if code == "admin123" and field == "code": return "❌ لا يمكن تغيير كود الأدمن الرئيسي."
    
    # Whitelist allowed fields to prevent SQL Injection
    ALLOWED_FIELDS = ["name", "phone", "code"]
    if field not in ALLOWED_FIELDS:
        return "❌ محاولة تعديل حقل غير مسموح به."
    
    # التحقق من القيود
    if field == "name" and len(new_value) > 100: return "❌ الاسم طويل جداً (حد أقصى 100 حرف)."
    
    if field == "phone":
        if not (len(new_value) == 10 and new_value.isdigit() and new_value.startswith("05")):
            return "❌ رقم الهاتف يجب أن يتكون من 10 أرقام بالضبط وأن يبدأ بـ '05'."
            
    if field == "code":
        if len(new_value) != 8:
            return "❌ الكود يجب أن يكون 8 حروف/أرقام بالضبط."

    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        query = f"UPDATE users SET {field} = ? WHERE code = ?"
        execute_query(c, query, (new_value, code))
        
        count = c.rowcount
        conn.commit()
        conn.close()
        return f"✅ تم تحديث **{field}** للمستخدم `{code}`." if count > 0 else "❌ المستخدم غير موجود."
    except Exception as e:
        if "UNIQUE constraint" in str(e) or "duplicate key" in str(e):
            return "❌ الكود الجديد مستخدم بالفعل."
        return f"❌ خطأ: {e}"

def db_get_all_users():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT code, name, phone, is_admin FROM users")
    users = c.fetchall()
    conn.close()
    return users

# --- Locations Management ---

def db_get_all_locations():
    """جلب جميع المواقع من قاعدة البيانات"""
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
    """إضافة موقع جديد"""
    if not name or len(name.strip()) == 0:
        return "❌ اسم الموقع لا يمكن أن يكون فارغاً."
    
    name = name.strip()
    if len(name) > 100:
        return "❌ اسم الموقع طويل جداً (حد أقصى 100 حرف)."
    
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
    """حذف موقع"""
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
