import psycopg2
from faker import Faker
import random
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
load_dotenv()
# === Custom Vietnamese name generator ===
family_names = ['Nguyen', 'Tran', 'Le', 'Pham', 'Hoang', 'Vo', 'Dang', 'Bui', 'Do', 'Ngo']
middle_names = ['Van', 'Thi']
first_names = ['An','Anh', 'Binh','Chau', 'Dung', 'Giang', 'Hanh','Lan', 'My', 'Nam', 'Phuong', "Thuan"]

def generate_vietnamese_name():
    return f"{random.choice(family_names)} {random.choice(middle_names)} {random.choice(first_names)}"

# === CCCD Generator ===
province_codes = ['001', '002', '004', '008', '011', '014', '017', '019', '020', '021']

def generate_national_id(dob, gender='male'):
    province = random.choice(province_codes)
    year = dob.year
    century = 0 if year < 2000 else 2
    gender_digit = century + (0 if gender == 'male' else 1)
    yy = str(year)[-2:]
    serial = f"{random.randint(0, 999999):06d}"
    return f"{province}{gender_digit}{yy}{serial}"

def guess_gender(name):
    return 'female' if 'Thi' in name else 'male'

# === Faker setup ===
fake = Faker('vi_VN')

# === DB Config ===
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}

def insert_customers(cur, n=10):
    customer_ids = []
    for _ in range(n):
        full_name = generate_vietnamese_name()
        dob = fake.date_of_birth(minimum_age=18, maximum_age=70)
        gender = guess_gender(full_name)
        national_id = generate_national_id(dob, gender)
        passport_number = None
        phone = fake.phone_number()
        email = fake.email()
        cur.execute("""
            INSERT INTO customers (
                citizen_id, passport_number, full_name, dob,
                phone_number, email
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING customer_id
        """, (national_id, passport_number, full_name, dob, phone, email))
        customer_ids.append(cur.fetchone()[0])
    print(f"Inserted {n} customers.")
    return customer_ids

def insert_bank_accounts(cur, customer_ids, min_accounts=1, max_accounts=2):
    account_mappings = []
    for cid in customer_ids:
        num_accounts = random.randint(min_accounts, max_accounts)
        for _ in range(num_accounts):
            account_number = ''.join(str(random.randint(0, 9)) for _ in range(12))
            balance = round(random.uniform(0, 100000000), 3)
            cur.execute("""
                INSERT INTO bank_accounts (
                    customer_id, account_number, balance
                ) VALUES (%s, %s, %s)
                RETURNING account_id
            """, (cid, account_number, balance))
            account_id = cur.fetchone()[0]
            account_mappings.append((account_id, cid))
    print(f"Inserted {len(account_mappings)} bank accounts.")
    return account_mappings

def insert_devices(cur, customer_ids):
    device_ids = []
    for cid in customer_ids:
        num_devices = random.randint(1, 3)
        for _ in range(num_devices):
            device_hash = uuid.uuid4().hex
            device_name = fake.user_agent()
            is_verified = random.choices([True, False], weights=[0.9, 0.1])[0]
            cur.execute("""
                INSERT INTO devices (
                    customer_id, device_hash, device_name, is_verified
                ) VALUES (%s, %s, %s, %s)
                RETURNING device_id
            """, (cid, device_hash, device_name, is_verified))
            device_ids.append((cid, cur.fetchone()[0], is_verified))
    print(f"Inserted devices.")
    return device_ids

def insert_auth_logs(cur, device_ids):
    auth_log_ids = []
    for cid, did, is_verified in device_ids:
        num_logs = random.randint(1, 5)
        for _ in range(num_logs):
            method = random.choice(['otp', 'soft_otp', 'advanced_soft_otp','token_otp', 'advanced_token_otp', '2FA', 'biometric'])
            status = random.choices(['success', 'failed'], weights=[0.95, 0.05])[0]
            session_id = uuid.uuid4().hex
            cur.execute("""
                INSERT INTO auth_logs(
                    customer_id, device_id, method_type,
                    session_id, auth_status
                ) VALUES (%s, %s, %s, %s, %s)
                RETURNING log_id
            """, (cid, did, method, session_id, status))
            auth_log_ids.append(cur.fetchone()[0])
    print(f"Inserted auth logs.")
    return auth_log_ids

def insert_transactions(cur, auth_log_ids):
    # Fetch auth log data (customer_id and device_id) for the given auth_log_ids
    cur.execute("""
        SELECT al.customer_id, al.device_id
        FROM auth_logs al
        WHERE al.log_id = ANY(%s)
    """, (auth_log_ids,))
    auth_pairs = cur.fetchall()  # list of (customer_id, device_id)

    for cid, did in auth_pairs:
        # Get one of the customer's bank accounts
        cur.execute("""
            SELECT account_id FROM bank_accounts
            WHERE customer_id = %s
        """, (cid,))
        accounts = cur.fetchall()
        if not accounts:
            continue
        acc_id = random.choice(accounts)[0]

        num_tx = random.randint(1, 3)
        for _ in range(num_tx):
            amount = round(random.lognormvariate(14, 0.7), 3)
            tag = random.choice(['A', 'B', 'C', 'D'])
            status = random.choices(['completed', 'cancelled', 'failed'], weights=[0.9, 0.09, 0.01])[0]
            description = fake.sentence(nb_words=6)
            tx_time = datetime.now() - timedelta(days=random.randint(0, 2))
            cur.execute("""
                INSERT INTO transactions (
                    account_id, customer_id, device_id, amount,
                    description, transaction_type, transaction_status,
                    transaction_tag, created_at, completed_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                acc_id, cid, did, amount, description,
                random.choice(['1', '2', '3', '4']), status,
                tag, tx_time, tx_time if status == 'completed' else None
            ))

    print("Inserted transactions based on auth_log_ids.")


# === MAIN EXECUTION ===
if __name__ == "__main__":
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        cust_ids = insert_customers(cur, n=10)
        acct_ids = insert_bank_accounts(cur, cust_ids)
        dev_ids = insert_devices(cur, cust_ids)
        log_ids = insert_auth_logs(cur, dev_ids)
        insert_transactions(cur, log_ids)
        conn.commit()
        print("All data inserted successfully.")
    except Exception as e:
        conn.rollback()
        print("Error occurred:", e)
    finally:
        cur.close()
        conn.close()