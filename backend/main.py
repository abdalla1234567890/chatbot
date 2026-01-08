from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional
import logging
import os
from datetime import datetime, timedelta
import jwt
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

load_dotenv()

from database import init_db, db_login, db_add_user, db_update_user, db_delete_user, db_get_all_users, db_get_all_locations, db_add_location, db_delete_location, db_get_user_locations, db_set_user_locations, db_add_location_to_user, db_remove_location_from_user
from sheets import save_to_sheet, init_google_sheets
from ai_agent import get_ai_response, extract_order_data

# --- Security Config ---
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-key-change-this-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# تهيئة اللوجر
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# تهيئة قاعدة البيانات عند البدء
try:
    init_db()
except Exception as e:
    logger.error(f"❌ بووم! خطأ أثناء تهيئة قاعدة البيانات: {e}")

# تهيئة Google Sheets عند البدء
try:
    init_google_sheets()
except Exception as e:
    logger.error(f"❌ أووبس! خطأ أثناء تهيئة Google Sheets: {e}")

app = FastAPI()

# --- Security Headers Middleware ---
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# إعداد CORS للسماح للفرونت إند بالاتصال
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Auth Helpers ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_code: str = payload.get("sub")
        if user_code is None:
            raise credentials_exception
        user = db_login(user_code) # db_login now handles hash verification internally
        if user is None:
            raise credentials_exception
        return {"code": user_code, "name": user[0], "phone": user[1], "is_admin": user[2]}
    except jwt.PyJWTError:
        raise credentials_exception

def get_admin_user(current_user: dict = Depends(get_current_user)):
    if current_user.get("is_admin") != 1:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user

# --- Routes ---

@app.get("/")
def home():
    return {"message": "Chatbot API is running! 🚀"}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = db_login(form_data.username) # Using 'username' field for the code
    if user:
        access_token = create_access_token(data={"sub": form_data.username})
        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "user": {"name": user[0], "phone": user[1], "is_admin": user[2]}
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect code",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Legacy login for backward compatibility (optional, but let's secure it too)
class LoginRequest(BaseModel):
    code: str

@app.post("/login_json")
def login_json(req: LoginRequest):
    user = db_login(req.code)
    if user:
        access_token = create_access_token(data={"sub": req.code})
        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "user": {"name": user[0], "phone": user[1], "is_admin": user[2]}
        }
    else:
        raise HTTPException(status_code=401, detail="Invalid code")

class ChatRequest(BaseModel):
    message: str
    history: List[str] = []

@app.post("/chat")
def chat(req: ChatRequest, current_user: dict = Depends(get_current_user)):
    user_code = current_user["code"]
    user_info = current_user
    
    # جلب المواقع الخاصة بالمستخدم فقط
    user_locations_data = db_get_user_locations(user_code)
    LOCATIONS = [loc[1] for loc in user_locations_data]
    
    # إضافة رسالة المستخدم للتاريخ
    history = req.history
    history.append(f"العميل: {req.message}")
    
    # الحصول على رد الذكاء الاصطناعي
    ai_reply = get_ai_response(history, user_info, LOCATIONS)
    
    # التحقق من وجود طلب
    order_data = extract_order_data(ai_reply, LOCATIONS)
    
    if order_data:
        summary = ai_reply.split("###DATA_START###")[0].strip()
        if save_to_sheet(order_data, summary, user_info):
            ai_reply = f"{summary}\n\n✅ تم تسجيل طلبك بنجاح! راح نتواصل معك قريب."
        else:
            ai_reply = "❌ حدث خطأ أثناء حفظ الطلب. يرجى المحاولة لاحقاً."

    if "###DATA_START###" in ai_reply:
         ai_reply = ai_reply.split("###DATA_START###")[0].strip()

    return {"reply": ai_reply, "order_placed": order_data is not None}

# --- Admin Routes ---

@app.get("/admin/users")
def get_users(admin: dict = Depends(get_admin_user)):
    users = db_get_all_users()
    return users # Database now returns sanitized dicts

class UserCreate(BaseModel):
    code: str
    name: str
    phone: str

@app.post("/admin/users")
def add_user(req: UserCreate, admin: dict = Depends(get_admin_user)):
    result = db_add_user(req.code, req.phone, req.name)
    if "✅" in result:
        return {"status": "success", "message": result}
    else:
        raise HTTPException(status_code=400, detail=result)

class UserUpdate(BaseModel):
    code: str
    field: str
    value: str

@app.put("/admin/users")
def update_user(req: UserUpdate, admin: dict = Depends(get_admin_user)):
    result = db_update_user(req.code, req.field, req.value)
    if "✅" in result:
        return {"status": "success", "message": result}
    else:
        raise HTTPException(status_code=400, detail=result)

@app.delete("/admin/users")
def delete_user(target_code: str, admin: dict = Depends(get_admin_user)):
    result = db_delete_user(target_code)
    if "✅" in result:
        return {"status": "success", "message": result}
    else:
        raise HTTPException(status_code=400, detail=result)

# --- Locations Routes ---

class LocationCreate(BaseModel):
    name: str

@app.get("/locations")
def get_locations():
    locations = db_get_all_locations()
    return [{"id": loc[0], "name": loc[1]} for loc in locations]

@app.get("/user-locations")
def get_user_locations_route(current_user: dict = Depends(get_current_user)):
    locations = db_get_user_locations(current_user["code"])
    return [{"id": loc[0], "name": loc[1]} for loc in locations]

@app.post("/admin/locations")
def add_location(req: LocationCreate, admin: dict = Depends(get_admin_user)):
    result = db_add_location(req.name)
    if "✅" in result:
        return {"status": "success", "message": result}
    else:
        raise HTTPException(status_code=400, detail=result)

@app.delete("/admin/locations/{location_id}")
def delete_location(location_id: int, admin: dict = Depends(get_admin_user)):
    result = db_delete_location(location_id)
    if "✅" in result:
        return {"status": "success", "message": result}
    else:
        raise HTTPException(status_code=400, detail=result)

# --- User Locations Management Routes ---

class UserLocationsUpdate(BaseModel):
    location_ids: List[int]

@app.get("/admin/user-locations")
def get_admin_user_locations(user_code: str, admin: dict = Depends(get_admin_user)):
    locations = db_get_user_locations(user_code)
    return [{"id": loc[0], "name": loc[1]} for loc in locations]

@app.put("/admin/user-locations")
def update_user_locations(user_code: str, req: UserLocationsUpdate, admin: dict = Depends(get_admin_user)):
    result = db_set_user_locations(user_code, req.location_ids)
    if "✅" in result:
        return {"status": "success", "message": result}
    else:
        raise HTTPException(status_code=400, detail=result)

@app.post("/admin/user-locations/add")
def add_location_to_user(user_code: str, location_id: int, admin: dict = Depends(get_admin_user)):
    result = db_add_location_to_user(user_code, location_id)
    if "✅" in result:
        return {"status": "success", "message": result}
    else:
        raise HTTPException(status_code=400, detail=result)

@app.delete("/admin/user-locations/remove")
def remove_location_from_user(user_code: str, location_id: int, admin: dict = Depends(get_admin_user)):
    result = db_remove_location_from_user(user_code, location_id)
    if "✅" in result:
        return {"status": "success", "message": result}
    else:
        raise HTTPException(status_code=400, detail=result)


