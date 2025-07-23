import os
import random
import uuid
from datetime import datetime, timedelta, timezone, date
from faker import Faker
from sqlalchemy import (
    create_engine, Column, Integer, String, Date, DateTime, DECIMAL, Boolean,
    ForeignKey, Enum, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.sql import func
from dotenv import load_dotenv

# Load .env
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
    customer_id = Column(UUID, primary_key=True)
    citizen_id = Column(String(12), unique=True)
    passport_number = Column(String(20), unique=True)
    full_name = Column(String(100), nullable=False)
    dob = Column('dob', Date, nullable=False)
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
    account_id = Column(UUID, primary_key=True)
    customer_id = Column(UUID, ForeignKey('customers.customer_id', ondelete='CASCADE'))
    account_number = Column(String(13), unique=True, nullable=False)
    balance = Column(DECIMAL(15,3), default=0.000)
    status = Column(Enum('active','suspended','closed', name='account_status_enum'), default='active')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)
    customer = relationship('Customer', back_populates='accounts')
    transactions = relationship('Transaction', back_populates='account')

class Device(Base):
    __tablename__ = 'devices'
    device_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.customer_id', ondelete='CASCADE'))
    device_hash = Column(String(64), unique=True, nullable=False)
    device_name = Column(String(200))
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    customer = relationship('Customer', back_populates='devices')
    auth_logs = relationship('AuthLog', back_populates='device')

class AuthLog(Base):
    __tablename__ = 'auth_logs'
    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.customer_id', ondelete='CASCADE'))
    device_id = Column(UUID(as_uuid=True), ForeignKey('devices.device_id', ondelete='SET NULL'))
    method_type = Column(Enum('password','otp','soft_otp','advanced_soft_otp','token_otp','advanced_token_otp','2FA','biometric','esign', name='auth_method_enum'), nullable=False)
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
    account_id = Column(UUID(as_uuid=True), ForeignKey('bank_accounts.account_id', ondelete='CASCADE'))
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.customer_id', ondelete='CASCADE'))
    device_id = Column(UUID(as_uuid=True), ForeignKey('devices.device_id', ondelete='SET NULL'))
    auth_log_id = Column(UUID(as_uuid=True), ForeignKey('auth_logs.log_id', ondelete='SET NULL'))
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
    auth_log = relationship('AuthLog')
# Create tables if not exist
Base.metadata.create_all(engine)

# === Generators ===
family_names = ['Nguyen', 'Tran', 'Le', 'Pham', 'Hoang', 'Vo', 'Dang', 'Bui', 'Do', 'Ngo']
middle_names = ['Van', 'Thi']
first_names = ['An','Anh', 'Binh','Chau', 'Dung', 'Giang', 'Hanh','Lan', 'My', 'Nam', 'Phuong', "Thuan"]
def generate_vietnamese_name(): return f"{random.choice(family_names)} {random.choice(middle_names)} {random.choice(first_names)}"
# CCCD
province_codes = ['001','002','004','008','011','014','017','019','020','021']
def generate_national_id(dob,gender='male'):
    province,year = random.choice(province_codes), dob.year
    century = 0 if year<2000 else 2
    digit = century + (0 if gender=='male' else 1)
    return f"{province}{digit}{str(year)[-2:]}{random.randint(0,999999):06d}"
def guess_gender(name): return 'female' if 'Thi' in name else 'male'

def random_date_of_birth(min_age=18, max_age=70):
    today = date.today()
    max_birth_date = today - timedelta(days=min_age*365)
    min_birth_date = today - timedelta(days=max_age*365)
    
    random_days = random.randint(0, (max_birth_date - min_birth_date).days)
    return min_birth_date + timedelta(days=random_days)

# === Insertion Workflow ===
# === Insertion Workflow ===
session = Session()
try:
    # 1. Insert Customers (no changes needed here)
    custs = []
    for _ in range(10):
        name = generate_vietnamese_name()
        gender = guess_gender(name)
        dob = fake.date_of_birth(minimum_age=18, maximum_age=70)
        cust = Customer(
            customer_id=uuid.uuid4(),
            citizen_id=generate_national_id(dob,gender),
            passport_number=None,
            dob=dob,
            full_name=name,
            phone_number=fake.phone_number(),
            email=fake.email(),
        )
        session.add(cust)
        custs.append(cust)
    session.commit()

    # 2. Bank Accounts (no changes needed here)
    for c in custs:
        for _ in range(random.randint(1,2)):
            ba = BankAccount(
                customer_id=c.customer_id,
                account_id=uuid.uuid4(),
                account_number=''.join(str(random.randint(0,9)) for _ in range(13)),
                balance=round(random.uniform(0,100000000),3)
            )
            session.add(ba)
    session.commit()
    print(f"Inserted {len(custs)} customers and their bank accounts.")

    # 3. Devices (no changes needed here)
    devices = []
    for c in custs:
        for _ in range(random.randint(1,3)):
            dv = Device(
                device_id=uuid.uuid4(),
                customer_id=c.customer_id,
                device_hash=uuid.uuid4(),
                device_name=fake.user_agent(),
                is_verified=random.choices([True,False],weights=[0.9,0.1])[0]
            )
            session.add(dv)
            devices.append(dv)
    session.commit()
    print(f"Inserted {len(devices)} devices.")

    # 4. Auth Logs - Changed query to get for device verification
    auths = []
    # We can't replace this query with get() because we need to filter by is_verified
    verified_devices = session.query(Device).filter(Device.is_verified == True).all()
    for dv in verified_devices:
        for _ in range(random.randint(1,5)):
            al = AuthLog(
                log_id=uuid.uuid4(),
                customer_id=dv.customer_id,
                device_id=dv.device_id,
                method_type=random.choice(['otp','soft_otp','advanced_soft_otp',
                                          'token_otp','advanced_token_otp',
                                          '2FA','biometric','esign']),
                session_id=uuid.uuid4().hex,
                auth_status=random.choices(['success','failed'], weights=[0.95,0.05])[0],
                ip_address=fake.ipv4_public(),
                user_agent=fake.user_agent()
            )
            session.add(al)
            auths.append(al)
    try:
        session.commit()
        print(f"Inserted {len(auths)} auth logs")
    except Exception as e:
        session.rollback()
        print(f"Error inserting auth logs: {e}")

    # 5. Transactions - Changed queries to get where possible
    for al in auths:
        try:
            # Get random account for this customer - can't use get() here because we need random selection
            ba = session.query(BankAccount).filter_by(customer_id=al.customer_id).order_by(func.random()).first()
            if not ba:
                print(f"No bank account found for customer {al.customer_id}")
                continue
                
            # Changed to get() for device lookup
            device = session.get(Device, al.device_id)
            if not device:
                print(f"Device {al.device_id} not found")
                continue
                
            # Changed to get() for transaction check
            existing_tx = session.get(Transaction, al.log_id)  # Assuming log_id is the primary key
            if existing_tx:
                print(f"Auth log {al.log_id} already used for transaction {existing_tx.transaction_id}")
                continue
                
            # Prepare transaction data
            created_time = datetime.now() - timedelta(days=random.randint(0, 2))
            status = random.choices(['completed', 'cancelled', 'failed'], weights=[0.9, 0.09, 0.01])[0]
            
            tx = Transaction(
                transaction_id=uuid.uuid4(),
                account_id=ba.account_id,
                customer_id=al.customer_id,
                device_id=device.device_id,
                auth_log_id=al.log_id,
                amount=round(random.lognormvariate(14, 0.5), 3),
                recipient_account=fake.bban() if random.random() > 0.3 else None,
                recipient_name=fake.name() if random.random() > 0.3 else None,
                description=f"Payment via {al.method_type} auth",
                transaction_type=random.choice(['1', '2', '3', '4']),
                transaction_status=status,
                transaction_tag=random.choice(['A', 'B', 'C', 'D']),
                created_at=created_time,
                completed_at=created_time if status == 'completed' else None,
                risk_score=round(random.uniform(0, 1), 2)
            )
            session.add(tx)
            
        except Exception as e:
            print(f"Error processing auth log {al.log_id}: {str(e)}")
            session.rollback()
            continue

    session.commit()
    print(f"Successfully created {len(auths)} transactions")
        
    print("ORM data insertion complete.")
except Exception as e:
    session.rollback()
    print("Error:", e)
finally:
    session.close()