from sqlalchemy.orm import Session
from app.db import models
from app.core.security import get_password_hash
from app.core.config import settings
import logging
import secrets

logger = logging.getLogger(__name__)

def get_user_by_code(db: Session, code: str):
    return db.query(models.User).filter(models.User.code == code).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, code: str, name: str, phone: str, is_admin: int = 0):
    db_user = models.User(
        code=code,
        secret_hash=get_password_hash(code),
        name=name, 
        phone=phone, 
        is_admin=is_admin
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_field(db: Session, user_code: str, field: str, value: str):
    user = get_user_by_code(db, user_code)
    if not user:
        return None
    
    if field == "code":
        # Changing primary key requires careful cascading updates; disallow for safety.
        return None
    elif hasattr(user, field):
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user

def update_user(db: Session, user_code: str, updates: dict):
    user = get_user_by_code(db, user_code)
    if not user:
        return None

    allowed_fields = {"name", "phone"}
    applied = False

    for field, value in updates.items():
        if field not in allowed_fields:
            continue
        setattr(user, field, value)
        applied = True

    if not applied:
        return False

    db.commit()
    db.refresh(user)
    return user

def delete_user(db: Session, user_code: str):
    user = get_user_by_code(db, user_code)
    if user:
        db.delete(user)
        db.commit()
        return True
    return False

def reset_user_secret(db: Session, user_code: str, new_secret: str):
    user = get_user_by_code(db, user_code)
    if not user:
        return None
    
    if user_code == new_secret:
        return user
        
    old_name = user.name
    old_phone = user.phone
    old_is_admin = user.is_admin
    loc_ids = [loc.id for loc in user.locations]
    
    # Safely clear foreign key references before delete in case of schema limitations
    user.locations = []
    db.commit()
    
    # Delete old user first to avoid any conflicts (Neon/SQLite on delete cascade handling)
    delete_user(db, user_code)
    
    existing = get_user_by_code(db, new_secret)
    if existing:
        existing.locations = []
        db.commit()
        delete_user(db, new_secret)
        
    new_user = create_user(
        db,
        code=new_secret,
        name=old_name,
        phone=old_phone,
        is_admin=old_is_admin
    )
    
    if loc_ids:
        set_user_locations(db, new_secret, loc_ids)
        
    return new_user

# Locations
def get_locations(db: Session):
    return db.query(models.Location).all()

def create_location(db: Session, name: str):
    db_loc = models.Location(name=name)
    db.add(db_loc)
    db.commit()
    db.refresh(db_loc)
    return db_loc

def delete_location(db: Session, location_id: int):
    loc = db.query(models.Location).filter(models.Location.id == location_id).first()
    if loc:
        db.delete(loc)
        db.commit()
        return True
    return False

# User-Locations association
def set_user_locations(db: Session, user_code: str, location_ids: list):
    user = get_user_by_code(db, user_code)
    if not user: return False
    
    # Clear existing
    user.locations = []
    
    # Add new
    new_locs = db.query(models.Location).filter(models.Location.id.in_(location_ids)).all()
    user.locations = new_locs
    
    db.commit()
    return True

def init_db_data(db: Session):
    """Seed default admin if empty"""
    if db.query(models.User).count() == 0:
        admin_code = settings.ADMIN_BOOTSTRAP_CODE or secrets.token_urlsafe(12)
        create_user(db, admin_code, "Main Admin", "0500000000", is_admin=1)
        logger.info(f"✅ Created default admin with code: {admin_code}")
