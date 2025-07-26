from model import Session, Transaction, AuthLog, Device, DailyTransactionSummary, RiskEvent
from sqlalchemy import or_, and_, func

STRONG_AUTH_METHODS = [
    'biometric', 'advanced_soft_otp', 'advanced_token_otp', 'FIDO', 'esign'
]

def check_high_value_strong_auth(session):
    print("\n[CHECK] Transactions >10M VND must use strong auth (biometric or OTP)")
    results = (
        session.query(Transaction.transaction_id, Transaction.amount, AuthLog.method_type, AuthLog.auth_status, Transaction.customer_id)
        .outerjoin(AuthLog, Transaction.auth_log_id == AuthLog.log_id)
        .filter(
            Transaction.amount > 10000000,
            or_(AuthLog.method_type == None, AuthLog.method_type.notin_(STRONG_AUTH_METHODS))
        )
        .all()
    )
    for row in results:
        print(f"  Violation: Transaction {row[0]} (amount: {row[1]}) - Auth method: {row[2]}")
        # Add to risk_events table
        risk_event = RiskEvent(
            customer_id=row[4],
            transaction_id=row[0],
            event_type='high_value_transaction',
            description=f"Violation: Transaction {row[0]} (amount: {row[1]}) - Auth method: {row[2]}"
        )
        session.add(risk_event)
    print(f"  Total violations: {len(results)}")
    if results:
        session.commit()

def check_device_verified(session):
    print("\n[CHECK] Device must be verified if new or untrusted (used in transaction)")
    results = (
        session.query(Transaction.transaction_id, Transaction.device_id, Device.is_verified, Transaction.customer_id)
        .join(Device, Transaction.device_id == Device.device_id)
        .filter(Device.is_verified == False)
        .all()
    )
    for row in results:
        print(f"  Violation: Transaction {row[0]} used unverified device {row[1]}")
        # Add to risk_events table
        risk_event = RiskEvent(
            customer_id=row[3],
            transaction_id=row[0],
            event_type='device_change',
            description=f"Violation: Transaction {row[0]} used unverified device {row[1]}"
        )
        session.add(risk_event)
    print(f"  Total violations: {len(results)}")
    if results:
        session.commit()

def check_daily_total_strong_auth(session):
    print("\n[CHECK] Total transaction amount per customer >20M VND in a day must have at least one strong auth")
    results = (
        session.query(DailyTransactionSummary.customer_id, DailyTransactionSummary.summary_date, DailyTransactionSummary.total_amount, DailyTransactionSummary.strong_auth_used)
        .filter(DailyTransactionSummary.total_amount > 20000000, DailyTransactionSummary.strong_auth_used == False)
        .all()
    )
    for row in results:
        print(f"  Violation: Customer {row[0]} on {row[1]} total {row[2]} - No strong auth used")
        # Add to risk_events table
        risk_event = RiskEvent(
            customer_id=row[0],
            transaction_id=None,
            event_type='high_value_transaction',
            description=f"Violation: Customer {row[0]} on {row[1]} total {row[2]} - No strong auth used"
        )
        session.add(risk_event)
    print(f"  Total violations: {len(results)}")
    if results:
        session.commit()

def assign_tag_type2(G, T):
    if G + T <= 5_000_000:
        return 'A'
    elif G + T > 5_000_000 and G + T <= 100_000_000:
        return 'B'
    elif G + T > 100_000_000 and G + T <= 1_500_000_000:
        return 'C'
    else:
        return 'D'

def assign_tag_type3(G, T, Tksth):
    # 3A: (i) G ≤ 10tr, (ii) G + Tksth ≤ 20tr
    if G <= 10_000_000 and G + Tksth <= 20_000_000:
        return 'B'
    # 3B: Trường hợp 1
    if G <= 10_000_000 and G + Tksth > 20_000_000 and G + T <= 1_500_000_000:
        return 'C'
    # 3B: Trường hợp 2
    if G > 10_000_000 and G <= 500_000_000 and G + T <= 1_500_000_000:
        return 'C'
    # 3C: Trường hợp 1
    if G <= 10_000_000 and G + Tksth > 20_000_000 and G + T > 1_500_000_000:
        return 'D'
    # 3C: Trường hợp 2
    if G > 10_000_000 and G <= 500_000_000 and G + T > 1_500_000_000:
        return 'D'
    # 3C: Trường hợp 3
    if G > 500_000_000:
        return 'D'
    return None

def assign_tag_type4(G, T):
    if G <= 200_000_000 and G + T <= 1_000_000_000:
        return 'C'
    elif (G <= 200_000_000 and G + T > 1_000_000_000) or (G > 200_000_000):
        return 'D'
    return None

def check_policy(session):
    print('\n[CHECK] Policy-based transaction tag assignment and validation')
    # Lấy tất cả giao dịch completed trong ngày
    transactions = session.query(Transaction).filter(Transaction.transaction_status == 'completed').all()

    for tx in transactions:
        G = float(tx.amount)
        # Tổng giao dịch trong ngày của khách hàng (T)
        T = session.query(func.sum(Transaction.amount)).filter(
            Transaction.customer_id == tx.customer_id,
            func.date(Transaction.created_at) == tx.created_at.date(),
            Transaction.transaction_status == 'completed'
        ).scalar() or 0

        # Tổng giao dịch cùng loại trong ngày (Tksth)
        Tksth = session.query(func.sum(Transaction.amount)).filter(
            Transaction.customer_id == tx.customer_id,
            func.date(Transaction.created_at) == tx.created_at.date(),
            Transaction.transaction_type == tx.transaction_type,
            Transaction.transaction_status == 'completed'
        ).scalar() or 0

        tag = None
        if tx.transaction_type == '1':
            tag = 'A'
        elif tx.transaction_type == '2':
            tag = assign_tag_type2(G, T)
        elif tx.transaction_type == '3':
            tag = assign_tag_type3(G, T, Tksth)
        elif tx.transaction_type == '4':
            tag = assign_tag_type4(G, T)

        # Nếu tag khác với tag hiện tại, log ra hoặc cập nhật
        if tag and tag != tx.transaction_tag:
            print(f'  Violation: Transaction {tx.transaction_id} should be tag {tag} but is {tx.transaction_tag}')
            risk_event = RiskEvent(
                customer_id=tx.customer_id,
                transaction_id=tx.transaction_id,
                event_type='unusual_pattern',
                description=f'Transaction {tx.transaction_id}: expected tag {tag}, found {tx.transaction_tag}'
            )
            session.add(risk_event)
    session.commit()


def main():
    session = Session()
    check_high_value_strong_auth(session)
    check_device_verified(session)
    check_daily_total_strong_auth(session)
    check_policy(session)
    session.close()

if __name__ == '__main__':
    main() 