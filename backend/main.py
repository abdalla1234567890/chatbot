from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import List, Optional
import logging
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from database import init_db, db_login, db_add_user, db_update_user, db_delete_user, db_get_all_users, db_get_all_locations, db_add_location, db_delete_location, db_get_user_locations, db_set_user_locations, db_add_location_to_user, db_remove_location_from_user
from sheets import save_to_sheet, init_google_sheets
from ai_agent import get_ai_response, extract_order_data

# تهيئة اللوجر
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# تهيئة قاعدة البيانات عند البدء
init_db()

# تهيئة Google Sheets عند البدء
init_google_sheets()

app = FastAPI()

# إعداد CORS للسماح للفرونت إند بالاتصال
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # في الإنتاج يجب تحديد الدومين
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "Chatbot API is running! 🚀"}

# --- Models ---
class LoginRequest(BaseModel):
    code: str

class ChatRequest(BaseModel):
    code: str
    message: str
    history: List[str] = [] # قائمة الرسائل السابقة
    history: List[str] = [] # قائمة الرسائل السابقة

class UserCreate(BaseModel):
    code: str
    name: str
    phone: str

class UserUpdate(BaseModel):
    code: str
    field: str
    value: str

# --- Routes ---

@app.post("/login")
def login(req: LoginRequest):
    user = db_login(req.code)
    if user:
        return {"status": "success", "user": {"name": user[0], "phone": user[1], "is_admin": user[2]}}
    else:
        raise HTTPException(status_code=401, detail="Invalid code")

@app.post("/chat")
def chat(req: ChatRequest):
    # جلب المواقع الخاصة بالمستخدم فقط
    user_locations_data = db_get_user_locations(req.code)
    LOCATIONS = [loc[1] for loc in user_locations_data]  # استخراج أسماء المواقع فقط
    
    user = db_login(req.code)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_info = {"name": user[0], "phone": user[1], "code": req.code}
    
    # إضافة رسالة المستخدم للتاريخ
    history = req.history
    history.append(f"العميل: {req.message}")
    
    # الحصول على رد الذكاء الاصطناعي مع تمرير المواقع المسموحة
    ai_reply = get_ai_response(history, user_info, LOCATIONS)
    
    # التحقق من وجود طلب مع التحقق من صحة الموقع
    order_data = extract_order_data(ai_reply, LOCATIONS)
    order_summary = None
    
    if order_data:
        summary = ai_reply.split("###DATA_START###")[0].strip()
        if save_to_sheet(order_data, summary, user_info):
            order_summary = summary
            ai_reply = f"{summary}\n\n✅ تم تسجيل طلبك بنجاح! راح نتواصل معك قريب."
        else:
            ai_reply = "❌ حدث خطأ أثناء حفظ الطلب. يرجى المحاولة لاحقاً."

    # تنظيف الرد من التاجات الداخلية إذا لم يكن هناك طلب (أو إذا كان هناك طلب وتمت معالجته)
    if "###DATA_START###" in ai_reply:
         ai_reply = ai_reply.split("###DATA_START###")[0].strip()

    return {"reply": ai_reply, "order_placed": order_data is not None}

# --- Admin Routes ---

@app.get("/admin/users")
@app.get("/admin/users")
def get_users(x_admin_code: str = Header(...)):
    admin = db_login(x_admin_code)
    if not admin or admin[2] != 1:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    users = db_get_all_users()
    return [{"code": u[0], "name": u[1], "phone": u[2], "is_admin": u[3]} for u in users]

@app.post("/admin/users")
def add_user(req: UserCreate, x_admin_code: str = Header(...)):
    admin = db_login(x_admin_code)
    if not admin or admin[2] != 1:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    result = db_add_user(req.code, req.phone, req.name)
    if "✅" in result:
        return {"status": "success", "message": result}
    else:
        raise HTTPException(status_code=400, detail=result)

@app.put("/admin/users")
@app.put("/admin/users")
def update_user(req: UserUpdate, x_admin_code: str = Header(...)):
    admin = db_login(x_admin_code)
    if not admin or admin[2] != 1:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    result = db_update_user(req.code, req.field, req.value)
    if "✅" in result:
        return {"status": "success", "message": result}
    else:
        raise HTTPException(status_code=400, detail=result)

@app.delete("/admin/users/{target_code}")
@app.delete("/admin/users/{target_code}")
def delete_user(target_code: str, x_admin_code: str = Header(...)):
    admin = db_login(x_admin_code)
    if not admin or admin[2] != 1:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    result = db_delete_user(target_code)
    if "✅" in result:
        return {"status": "success", "message": result}
    else:
        raise HTTPException(status_code=400, detail=result)

# --- Locations Routes ---

class LocationCreate(BaseModel):
    name: str

class UserLocationsUpdate(BaseModel):
    location_ids: List[int]

@app.get("/locations")
def get_locations():
    """جلب جميع المواقع - متاح للجميع"""
    locations = db_get_all_locations()
    return [{"id": loc[0], "name": loc[1]} for loc in locations]

@app.get("/user-locations")
def get_user_locations(code: str):
    """جلب المواقع الخاصة بالمستخدم"""
    user = db_login(code)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    locations = db_get_user_locations(code)
    return [{"id": loc[0], "name": loc[1]} for loc in locations]

@app.post("/admin/locations")
@app.post("/admin/locations")
def add_location(req: LocationCreate, x_admin_code: str = Header(...)):
    """إضافة موقع جديد - أدمن فقط"""
    admin = db_login(x_admin_code)
    if not admin or admin[2] != 1:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    result = db_add_location(req.name)
    if "✅" in result:
        return {"status": "success", "message": result}
    else:
        raise HTTPException(status_code=400, detail=result)

@app.delete("/admin/locations/{location_id}")
@app.delete("/admin/locations/{location_id}")
def delete_location(location_id: int, x_admin_code: str = Header(...)):
    """حذف موقع - أدمن فقط"""
    admin = db_login(x_admin_code)
    if not admin or admin[2] != 1:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    result = db_delete_location(location_id)
    if "✅" in result:
        return {"status": "success", "message": result}
    else:
        raise HTTPException(status_code=400, detail=result)

# --- User Locations Management Routes (Admin) ---

@app.get("/admin/user-locations/{user_code}")
def get_admin_user_locations(user_code: str, x_admin_code: str = Header(...)):
    """جلب مواقع المستخدم - أدمن فقط"""
    admin = db_login(x_admin_code)
    if not admin or admin[2] != 1:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    locations = db_get_user_locations(user_code)
    return [{"id": loc[0], "name": loc[1]} for loc in locations]

@app.put("/admin/user-locations/{user_code}")
def update_user_locations(user_code: str, req: UserLocationsUpdate, x_admin_code: str = Header(...)):
    """تحديث مواقع المستخدم - أدمن فقط"""
    admin = db_login(x_admin_code)
    if not admin or admin[2] != 1:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # التحقق من وجود المستخدم
    user = db_login(user_code)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    result = db_set_user_locations(user_code, req.location_ids)
    if "✅" in result:
        return {"status": "success", "message": result}
    else:
        raise HTTPException(status_code=400, detail=result)

@app.post("/admin/user-locations/{user_code}/{location_id}")
def add_location_to_user(user_code: str, location_id: int, x_admin_code: str = Header(...)):
    """إضافة موقع للمستخدم - أدمن فقط"""
    admin = db_login(x_admin_code)
    if not admin or admin[2] != 1:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    result = db_add_location_to_user(user_code, location_id)
    if "✅" in result:
        return {"status": "success", "message": result}
    else:
        raise HTTPException(status_code=400, detail=result)

@app.delete("/admin/user-locations/{user_code}/{location_id}")
def remove_location_from_user(user_code: str, location_id: int, x_admin_code: str = Header(...)):
    """إزالة موقع من المستخدم - أدمن فقط"""
    admin = db_login(x_admin_code)
    if not admin or admin[2] != 1:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    result = db_remove_location_from_user(user_code, location_id)
    if "✅" in result:
        return {"status": "success", "message": result}
    else:
        raise HTTPException(status_code=400, detail=result)


