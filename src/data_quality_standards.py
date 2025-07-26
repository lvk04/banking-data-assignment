import re
from dotenv import load_dotenv
# Import ORM models and session from model.py
from model import Customer, BankAccount, Device, AuthLog, Transaction, Session
from sqlalchemy import func


CCCD_REGEX = r'^\d{12}$'
ACCOUNT_REGEX = r'^\d{13}$'

def check_nulls(session, model, columns):
    for col in columns:
        count = session.query(func.count()).filter(getattr(model, col) == None).scalar()
        print(f"[NULL CHECK] {model.__tablename__}.{col}: {count} nulls")

def check_uniqueness(session, model, column):
    total = session.query(func.count(getattr(model, column))).filter(getattr(model, column) != None).scalar()
    unique = session.query(func.count(func.distinct(getattr(model, column)))).filter(getattr(model, column) != None).scalar()
    print(f"[UNIQUENESS] {model.__tablename__}.{column}: {total-unique} duplicates")

def check_format_length(session, model, column, regex, desc):
    values = session.query(getattr(model, column)).filter(getattr(model, column) != None).all()
    bad = [val[0] for val in values if not re.match(regex, str(val[0]))]
    print(f"[FORMAT] {model.__tablename__}.{column} ({desc}): {len(bad)} bad values")
    if bad:
        print(f"  Examples: {bad[:3]}")

def check_foreign_key(session, child_model, child_col, parent_model, parent_col):
    child_values = session.query(getattr(child_model, child_col)).filter(getattr(child_model, child_col) != None).all()
    parent_values = set(val[0] for val in session.query(getattr(parent_model, parent_col)).all())
    broken = [val[0] for val in child_values if val[0] not in parent_values]
    print(f"[FK INTEGRITY] {child_model.__tablename__}.{child_col} -> {parent_model.__tablename__}.{parent_col}: {len(broken)} broken references")
    if broken:
        print(f"  Examples: {broken[:3]}")

def main():
    session = Session()
    # Null/missing value checks
    check_nulls(session, Customer, ['citizen_id', 'passport_number', 'full_name', 'dob', 'phone_number'])
    check_nulls(session, BankAccount, ['account_number', 'customer_id'])
    check_nulls(session, Device, ['device_hash', 'customer_id'])
    check_nulls(session, Transaction, ['account_id', 'customer_id', 'amount'])

    # Uniqueness checks
    check_uniqueness(session, Customer, 'citizen_id')
    check_uniqueness(session, Customer, 'passport_number')
    check_uniqueness(session, BankAccount, 'account_number')
    check_uniqueness(session, Device, 'device_hash')

    # Format/length validation
    check_format_length(session, Customer, 'citizen_id', CCCD_REGEX, '12 digits')
    check_format_length(session, BankAccount, 'account_number', ACCOUNT_REGEX, '13 digits')

    # Foreign key integrity
    check_foreign_key(session, BankAccount, 'customer_id', Customer, 'customer_id')
    check_foreign_key(session, Device, 'customer_id', Customer, 'customer_id')
    check_foreign_key(session, Transaction, 'account_id', BankAccount, 'account_id')
    check_foreign_key(session, Transaction, 'customer_id', Customer, 'customer_id')
    check_foreign_key(session, Transaction, 'device_id', Device, 'device_id')
    session.close()

if __name__ == '__main__':
    main() 