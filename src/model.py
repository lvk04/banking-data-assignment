import os
import random
import uuid
from datetime import datetime, timedelta, timezone, date
from faker import Faker
from sqlalchemy import (
    create_engine, Column, Integer, String, Date, DateTime, DECIMAL, Boolean,
    ForeignKey, Enum, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.sql import func
from dotenv import load_dotenv

load_dotenv()

# DB connection
DATABASE_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base = declarative_base()
fake = Faker('vi_VN')

# === ORM Models ===
class Customer(Base):
    __tablename__ = 'customers'
    customer_id = Column(UUID(as_uuid=True), primary_key=True)
    citizen_id = Column(String(12), unique=True)
    passport_number = Column(String(20), unique=True)
    full_name = Column(String(100), nullable=False)
    dob = Column('DOB', Date, nullable=False)  
    phone_number = Column(String(15), nullable=False)
    email = Column(String(100))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)
    __table_args__ = (
        CheckConstraint('citizen_id IS NOT NULL OR passport_number IS NOT NULL'),
        CheckConstraint("citizen_id IS NULL OR LENGTH(citizen_id) = 12"),
        CheckConstraint("citizen_id IS NULL OR citizen_id ~ '^\\d{12}$'"),
        CheckConstraint("passport_number IS NULL OR LENGTH(passport_number) >= 6"),
    )
    accounts = relationship('BankAccount', back_populates='customer')
    devices = relationship('Device', back_populates='customer')

class BankAccount(Base):
    __tablename__ = 'bank_accounts'
    account_id = Column(UUID(as_uuid=True), primary_key=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.customer_id', ondelete='CASCADE'), nullable=False)
    account_number = Column(String(13), unique=True, nullable=False)
    balance = Column(DECIMAL(15,3), default=0.000)
    status = Column(Enum('active','suspended','closed', name='account_status_enum'), default='active')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)
    risk_level = Column(Enum('low', 'medium', 'high', name='risk_level_enum'), default='low') 
    customer = relationship('Customer', back_populates='accounts')
    transactions = relationship('Transaction', back_populates='account')
    __table_args__ = (
        CheckConstraint('balance >= 0'),
        CheckConstraint('LENGTH(account_number) = 13'),
    )

class Device(Base):
    __tablename__ = 'devices'
    device_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.customer_id', ondelete='CASCADE'), nullable=False)
    device_hash = Column(String(64), unique=True, nullable=False)
    device_name = Column(String(200))
    is_verified = Column(Boolean, default=False)
    last_used = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)
    customer = relationship('Customer', back_populates='devices')
    auth_logs = relationship('AuthLog', back_populates='device')

class AuthLog(Base):
    __tablename__ = 'auth_logs'
    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.customer_id', ondelete='CASCADE'), nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey('devices.device_id', ondelete='SET NULL'), nullable=False)
    method_type = Column(Enum('password','otp','soft_otp','advanced_soft_otp','token_otp','advanced_token_otp','2FA','biometric','FIDO','esign', name='auth_method_enum'), nullable=False)  # ✅ Fixed: added 'FIDO', fixed 'esign'
    session_id = Column(String(64))
    auth_status = Column(Enum('success','failed','expired', name='auth_status_enum'), nullable=False)
    ip_address = Column(String(45))
    user_agent = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    customer = relationship('Customer')
    device = relationship('Device', back_populates='auth_logs')

class Transaction(Base):
    __tablename__ = 'transactions'
    transaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey('bank_accounts.account_id', ondelete='CASCADE'), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.customer_id', ondelete='CASCADE'), nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey('devices.device_id', ondelete='SET NULL'))
    auth_log_id = Column(UUID(as_uuid=True), ForeignKey('auth_logs.log_id', ondelete='SET NULL'), unique=True)  # ✅ Added: unique constraint
    amount = Column(DECIMAL(15,3), nullable=False)
    description = Column(String)
    recipient_account = Column(String(20))
    recipient_name = Column(String(100))
    risk_score = Column(DECIMAL(3,2), default=0.00)
    transaction_type = Column(Enum('1','2','3','4', name='transaction_type_enum'), nullable=False)
    transaction_status = Column(Enum('pending','completed','failed','cancelled', name='transaction_status_enum'), default='pending')
    transaction_tag = Column(Enum('A','B','C','D', name='transaction_tag_enum'), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime)
    account = relationship('BankAccount', back_populates='transactions')
    auth_log = relationship('AuthLog')
    __table_args__ = (
        CheckConstraint('amount > 0'),
        CheckConstraint('risk_score >= 0 AND risk_score <= 1'),
    )

class DailyTransactionSummary(Base):
    __tablename__ = 'daily_transaction_summary'
    summary_id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.customer_id', ondelete='CASCADE'), nullable=False)
    summary_date = Column(Date, nullable=False)
    total_amount = Column(DECIMAL(15, 3), default=0.000)
    transaction_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)
    strong_auth_used = Column(Boolean, default=False)
    __table_args__ = (
        UniqueConstraint('customer_id', 'summary_date'), 
    )

class RiskEvent(Base):
    __tablename__ = 'risk_events'
    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.customer_id', ondelete='CASCADE'), nullable=False)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey('transactions.transaction_id', ondelete='SET NULL'))
    event_type = Column(Enum('high_value_transaction', 'unusual_pattern', 'device_change', 'location_mismatch', 'failed_auth', name='risk_event_enum'), nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    resolved_at = Column(DateTime)