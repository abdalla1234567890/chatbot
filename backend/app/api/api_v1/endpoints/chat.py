from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from app.db import session, models
from app.schemas import chat as chat_schema
from app.services import ai_service, sheets_service, classifier
from app.api import deps # We'll create this to get current user

router = APIRouter()

@router.post("/", response_model=chat_schema.ChatResponse)
def chat(
    req: chat_schema.ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    # Determine locations for this user
    LOCATIONS = [loc.name for loc in current_user.locations]
    
    history = req.history
    history.append(f"العميل: {req.message}")
    
    # Trim history after last order
    last_order_idx = -1
    for i, msg in enumerate(history):
        if "تم تسجيل طلبك بنجاح" in msg or "رقم الطلب:" in msg:
            last_order_idx = i
    if last_order_idx >= 0:
        history = history[last_order_idx + 1:]
        
    # Get Taxonomy - simplified for now
    tax_summary = ""
    if sheets_service.worksheet:
        tax_summary = classifier.get_taxonomy_summary(sheets_service.worksheet.spreadsheet)
    
    ai_reply = ai_service.get_ai_response(history, current_user, LOCATIONS, tax_summary)
    
    order_data = ai_service.extract_order_data(ai_reply, LOCATIONS)
    
    order_placed = False
    if order_data:
        summary = ai_reply.split("###DATA_START###")[0].strip()
        order_num = sheets_service.save_to_sheet(order_data, summary, current_user, background_tasks)
        if order_num:
            ai_reply = f"{summary}\n\n✅ تم تسجيل طلبك بنجاح! رقم الطلب: **{order_num}**\nراح نتواصل معك قريب."
            order_placed = True
        else:
            ai_reply = "❌ حدث خطأ أثناء حفظ الطلب. يرجى المحاولة لاحقاً."

    # Remove data block before returning
    if "###DATA_START###" in ai_reply:
        ai_reply = ai_reply.split("###DATA_START###")[0].strip()

    return {"reply": ai_reply, "order_placed": order_placed}
