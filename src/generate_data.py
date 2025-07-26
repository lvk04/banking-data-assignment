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
from model import Session, Customer, BankAccount, Device, AuthLog, Transaction
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

Base.metadata.create_all(engine)

# Name generation
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

def generate_phone_number():
    prefix = random.choice(['032', '033', '034', '035', '036', '037', '038', '039'])
    suffix = f"{random.randint(0, 9999999):07d}"  # Zero-padded 7-digit number
    return f"{prefix}{suffix}"

# === Insertion Workflow ===
session = Session()
try:
    # 1. Insert Customers
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
            phone_number=generate_phone_number(),
            email=fake.email(),
        )
        session.add(cust)
        custs.append(cust)
    session.commit()
    try:
        session.commit()
        print(f"Inserted {len(custs)} customers")
    except Exception as e:
        session.rollback()
        print(f"Error inserting customers: {e}")


    # 2. Bank Accounts
    for c in custs:
        for _ in range(random.randint(1,2)):
            ba = BankAccount(
                customer_id=c.customer_id,
                account_id=uuid.uuid4(),
                account_number=''.join(str(random.randint(0,9)) for _ in range(13)),
                balance=round(random.uniform(0,100000000),3)
            )
            session.add(ba)
    try:
        session.commit()
        print(f"Inserted accounts")
    except Exception as e:
        session.rollback()
        print(f"Error inserting accounts: {e}")

    # 3. Devices 
    devices = []
    for c in custs:
        for _ in range(random.randint(1,3)):
            dv = Device(
                device_id=uuid.uuid4(),
                customer_id=c.customer_id,
                device_hash=uuid.uuid4().hex,
                device_name=fake.user_agent(),
                is_verified=random.choices([True,False],weights=[0.9,0.1])[0]
            )
            session.add(dv)
            devices.append(dv)
    try:
        session.commit()
        print(f"Inserted {len(devices)} devices")
    except Exception as e:
        session.rollback()
        print(f"Error inserting devices: {e}")

    # 4. Auth Logs
    auths = []
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

    # 5. Transactions 
    for al in auths:
        try:
            ba = session.query(BankAccount).filter_by(customer_id=al.customer_id).order_by(func.random()).first()
            if not ba:
                print(f"No bank account found for customer {al.customer_id}")
                continue
                
            device = session.get(Device, al.device_id)
            if not device:
                print(f"Device {al.device_id} not found")
                continue
                
            existing_tx = session.get(Transaction, al.log_id) 
            if existing_tx:
                print(f"Auth log {al.log_id} already used for transaction {existing_tx.transaction_id}")
                continue
                
            created_time = datetime.now() - timedelta(days=random.randint(0, 2))
            status = random.choices(['completed', 'cancelled', 'failed'], weights=[0.9, 0.09, 0.01])[0]
            
            tx = Transaction(
                transaction_id=uuid.uuid4(),
                account_id=ba.account_id,
                customer_id=al.customer_id,
                device_id=device.device_id,
                auth_log_id=al.log_id,
                amount=round(random.lognormvariate(15, 0.5), 3),
                recipient_account=''.join(str(random.randint(0,9)) for _ in range(13)),
                recipient_name=generate_vietnamese_name(),
                description=f"{cust.full_name} chuyen tien",
                transaction_type=random.choice(['1', '2', '3', '4']), #should be determined by application layer
                transaction_status=status,
                transaction_tag=random.choice(['A', 'B', 'C', 'D']), # should be determined by application layer
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
        
    print("Data insertion complete.")
except Exception as e:
    session.rollback()
    print("Error:", e)
finally:
    session.close()