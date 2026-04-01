from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db import session, crud, models
from app.schemas import location as loc_schema
from app.api import deps

router = APIRouter()

@router.get("/", response_model=List[loc_schema.Location])
def read_locations(
    db: Session = Depends(session.get_db),
    current_admin: models.User = Depends(deps.get_current_active_admin)
):
    return crud.get_locations(db)

@router.post("/", response_model=loc_schema.Location)
def create_location(
    loc_in: loc_schema.LocationCreate,
    db: Session = Depends(session.get_db),
    current_admin: models.User = Depends(deps.get_current_active_admin)
):
    return crud.create_location(db, **loc_in.dict())

@router.delete("/{location_id}")
def delete_location(
    location_id: int,
    db: Session = Depends(session.get_db),
    current_admin: models.User = Depends(deps.get_current_active_admin)
):
    if crud.delete_location(db, location_id):
        return {"msg": "Location deleted"}
    raise HTTPException(status_code=404, detail="Location not found")

@router.post("/user/{user_code}", response_model=bool)
def set_user_locations(
    user_code: str,
    loc_data: loc_schema.UserLocationsUpdate,
    db: Session = Depends(session.get_db),
    current_admin: models.User = Depends(deps.get_current_active_admin)
):
    return crud.set_user_locations(db, user_code, loc_data.location_ids)

@router.get("/my-locations", response_model=List[loc_schema.Location])
def get_my_locations(
    current_user: models.User = Depends(deps.get_current_user)
):
    return current_user.locations
