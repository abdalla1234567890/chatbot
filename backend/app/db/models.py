from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.db.session import Base

# Association table for many-to-many relationship
user_locations = Table(
    "user_locations",
    Base.metadata,
    Column("user_code", String, ForeignKey("users.code", ondelete="CASCADE"), primary_key=True),
    Column("location_id", Integer, ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True),
)

class User(Base):
    __tablename__ = "users"

    code = Column(String, primary_key=True, index=True)
    secret_hash = Column(String, nullable=True)
    name = Column(String)
    phone = Column(String)
    is_admin = Column(Integer, default=0) # SQLite fallback for Boolean

    locations = relationship("Location", secondary=user_locations, back_populates="users")

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)

    users = relationship("User", secondary=user_locations, back_populates="locations")
