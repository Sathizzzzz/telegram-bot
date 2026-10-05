from datetime import datetime, date
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Date,
    DateTime,
    Float,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    user_id = Column(BigInteger, primary_key=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(150), nullable=True)
    last_name = Column(String(150), nullable=True)
    phone = Column(String(20), nullable=True)
    language = Column(String(10), default="en")
    plan_tier = Column(String(20), default="free")
    vault_limit = Column(Integer, default=5)
    created_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("ProductWarranty", back_populates="user", cascade="all, delete-orphan")


class ProductWarranty(Base):
    __tablename__ = "product_warranties"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    product_name = Column(String(200), nullable=False)
    category = Column(String(80), nullable=False)
    brand = Column(String(100), nullable=False)
    model_no = Column(String(100), nullable=True)
    serial_no = Column(String(100), nullable=True)
    purchase_platform = Column(String(100), nullable=True)
    purchase_date = Column(Date, nullable=False)
    warranty_months = Column(Integer, nullable=False, default=12)
    expiry_date = Column(Date, nullable=False)
    price_paid = Column(Float, nullable=True)
    room_location = Column(String(50), nullable=True)
    return_window_days = Column(Integer, default=7)
    invoice_file_id = Column(String(255), nullable=True)
    invoice_file_type = Column(String(20), nullable=True)
    local_invoice_path = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(30), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="products")
    reminder_logs = relationship("ReminderLog", back_populates="product", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_user_expiry", "user_id", "expiry_date"),
    )

    @property
    def is_expired(self) -> bool:
        return date.today() > self.expiry_date

    @property
    def days_remaining(self) -> int:
        delta = self.expiry_date - date.today()
        return delta.days


class ReminderLog(Base):
    __tablename__ = "reminder_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("product_warranties.id"), nullable=False)
    reminder_type = Column(String(30), nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("ProductWarranty", back_populates="reminder_logs")


class LeadRequest(Base):
    __tablename__ = "lead_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    product_id = Column(Integer, ForeignKey("product_warranties.id"), nullable=True)
    service_type = Column(String(50), nullable=False)
    provider = Column(String(50), nullable=False)
    status = Column(String(30), default="pending")
    contact_phone = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)