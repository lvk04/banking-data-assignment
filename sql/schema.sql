-- Drop all tables
DROP TABLE IF EXISTS 
  daily_transaction_summary,
  risk_events, 
  transactions, 
  auth_logs, 
  devices, 
  bank_accounts, 
  customers 
  CASCADE;

-- Drop ENUMs (CASCADE handles references just in case)
DO $$ BEGIN
  PERFORM 1 FROM pg_type WHERE typname = 'risk_level_enum';
  IF FOUND THEN EXECUTE 'DROP TYPE risk_level_enum CASCADE'; END IF;

  PERFORM 1 FROM pg_type WHERE typname = 'account_status_enum';
  IF FOUND THEN EXECUTE 'DROP TYPE account_status_enum CASCADE'; END IF;

  PERFORM 1 FROM pg_type WHERE typname = 'auth_method_enum';
  IF FOUND THEN EXECUTE 'DROP TYPE auth_method_enum CASCADE'; END IF;

  PERFORM 1 FROM pg_type WHERE typname = 'auth_type_enum';
  IF FOUND THEN EXECUTE 'DROP TYPE auth_type_enum CASCADE'; END IF;

  PERFORM 1 FROM pg_type WHERE typname = 'auth_status_enum';
  IF FOUND THEN EXECUTE 'DROP TYPE auth_status_enum CASCADE'; END IF;

  PERFORM 1 FROM pg_type WHERE typname = 'transaction_status_enum';
  IF FOUND THEN EXECUTE 'DROP TYPE transaction_status_enum CASCADE'; END IF;

  PERFORM 1 FROM pg_type WHERE typname = 'transaction_type_enum';
  IF FOUND THEN EXECUTE 'DROP TYPE transaction_type_enum CASCADE'; END IF;

  PERFORM 1 FROM pg_type WHERE typname = 'transaction_tag_enum';
  IF FOUND THEN EXECUTE 'DROP TYPE transaction_tag_enum CASCADE'; END IF;

  PERFORM 1 FROM pg_type WHERE typname = 'risk_event_enum';
  IF FOUND THEN EXECUTE 'DROP TYPE risk_event_enum CASCADE'; END IF;
END $$;


-- Recreate ENUM types
CREATE TYPE risk_level_enum AS ENUM ('low', 'medium', 'high');
CREATE TYPE account_status_enum AS ENUM ('active', 'suspended', 'closed');
CREATE TYPE auth_method_enum AS ENUM ('password','otp', 'soft_otp', 'advanced_soft_otp','token_otp', 'advanced_token_otp', '2FA', 'biometric', 'FIDO', 'esign');
CREATE TYPE auth_type_enum AS ENUM ('login', 'transaction_auth', 'password_change');
CREATE TYPE auth_status_enum AS ENUM ('success', 'failed', 'expired');
CREATE TYPE transaction_type_enum AS ENUM ('1', '2', '3', '4');
CREATE TYPE transaction_status_enum AS ENUM ('pending', 'completed', 'failed', 'cancelled');
CREATE TYPE transaction_tag_enum AS ENUM ('A', 'B', 'C', 'D');
CREATE TYPE risk_event_enum AS ENUM ('high_value_transaction', 'unusual_pattern', 'device_change', 'location_mismatch', 'failed_auth');

-- Customers
CREATE TABLE customers (
    customer_id UUID PRIMARY KEY,
    citizen_id VARCHAR(12) UNIQUE,
    passport_number VARCHAR(20) UNIQUE,
    full_name VARCHAR(100) NOT NULL,
    DOB DATE NOT NULL,
    phone_number VARCHAR(15) NOT NULL,
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (citizen_id IS NOT NULL OR passport_number IS NOT NULL), --Either citizen ID or passport number must be provided
    CHECK (citizen_id IS NULL OR LENGTH(citizen_id) = 12),
    CHECK (citizen_id IS NULL OR citizen_id ~ '^\d{12}$'),  -- Citizen ID must be 12 digits
    CHECK (passport_number IS NULL OR LENGTH(passport_number) >= 6)
);

-- Bank Accounts
CREATE TABLE bank_accounts (
    account_id UUID PRIMARY KEY,
    customer_id UUID NOT NULL,
    account_number VARCHAR(13) UNIQUE NOT NULL, --timo account number is 13 digits
    balance DECIMAL(15,3) DEFAULT 0.000,
    status account_status_enum DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    risk_level risk_level_enum DEFAULT 'low',
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    CHECK (balance >= 0),
    CHECK (LENGTH(account_number) = 13)
);

-- Devices
CREATE TABLE devices (
    device_id UUID PRIMARY KEY,
    customer_id UUID NOT NULL,
    device_hash VARCHAR(64) UNIQUE NOT NULL,
    device_name VARCHAR(200),
    is_verified BOOLEAN DEFAULT FALSE,
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

-- Authentication log
CREATE TABLE auth_logs (
    log_id UUID PRIMARY KEY,
    customer_id UUID NOT NULL,
    device_id UUID NOT NULL,
    method_type auth_method_enum NOT NULL,
    session_id VARCHAR(64),
    auth_status auth_status_enum NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE SET NULL
);

-- Transactions
CREATE TABLE transactions (
    transaction_id UUID PRIMARY KEY,
    account_id UUID NOT NULL,
    customer_id UUID NOT NULL,
    device_id UUID,
    auth_log_id UUID UNIQUE, -- Unique to ensure one transaction per auth log
    amount DECIMAL(15,3) NOT NULL,
    description TEXT,
    transaction_type transaction_type_enum NOT NULL, -- Transaction type tag(?) (1.1,1.2,1.3,1.4) according to 2345/QĐ-NHNN 2023, should be determined by the application layer
    recipient_account VARCHAR(20),
    recipient_name VARCHAR(100),
    transaction_status transaction_status_enum DEFAULT 'pending',
    risk_score DECIMAL(3,2) DEFAULT 0.00, --risk score, 
    transaction_tag transaction_tag_enum NOT NULL, -- Transaction risk tag(?) (A,B,C,D) according to 2345/QĐ-NHNN 2023, should be determined by the application layer
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES bank_accounts(account_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE SET NULL,
    FOREIGN KEY (auth_log_id) REFERENCES auth_logs(log_id) ON DELETE SET NULL,
    CHECK (amount > 0),
    CHECK (risk_score >= 0 AND risk_score <= 1)
);

-- Risk Events: table to log risk events related to transactions or accounts
CREATE TABLE risk_events (
    event_id UUID PRIMARY KEY,
    customer_id UUID NOT NULL,
    transaction_id UUID,
    event_type risk_event_enum NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id) ON DELETE SET NULL
);

-- Daily Transaction Summary
CREATE TABLE daily_transaction_summary (
    summary_id SERIAL PRIMARY KEY,
    customer_id UUID NOT NULL,
    summary_date DATE NOT NULL,
    total_amount DECIMAL(15, 3) DEFAULT 0.000,
    transaction_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    strong_auth_used BOOLEAN DEFAULT FALSE,
    UNIQUE (customer_id, summary_date),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

-- Trigger to update daily transaction summary
-- This trigger will update the daily transaction summary table whenever a new transaction is inserted
CREATE OR REPLACE FUNCTION update_daily_transaction_summary()
RETURNS TRIGGER AS $$
DECLARE
  tx_date          DATE := NEW.created_at::date;
  used_strong_auth BOOLEAN;
BEGIN
  IF NEW.transaction_status = 'completed' THEN

    -- Check whether this customer performed a strong auth for a transaction today
    SELECT EXISTS (
      SELECT 1
      FROM auth_logs
      WHERE customer_id   = NEW.customer_id
        AND method_type IN (
          'advanced_soft_otp',
          'advanced_token_otp',
          'biometric'
        )
        AND created_at::date = tx_date
    ) INTO used_strong_auth;

    -- Upsert into daily summary
    INSERT INTO daily_transaction_summary (
      customer_id,
      summary_date,
      total_amount,
      transaction_count,
      strong_auth_used
    ) VALUES (
      NEW.customer_id,
      tx_date,
      NEW.amount,
      1,
      used_strong_auth
    )
    ON CONFLICT (customer_id, summary_date)
    DO UPDATE
      SET
        total_amount      = daily_transaction_summary.total_amount    + EXCLUDED.total_amount,
        transaction_count = daily_transaction_summary.transaction_count + 1,
        strong_auth_used  = daily_transaction_summary.strong_auth_used OR EXCLUDED.strong_auth_used,
        updated_at        = CURRENT_TIMESTAMP;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;


CREATE TRIGGER trg_update_daily_transaction_summary
  AFTER INSERT ON transactions
  FOR EACH ROW
  EXECUTE FUNCTION update_daily_transaction_summary();
-- Indexes
CREATE INDEX idx_transactions_customer ON transactions(customer_id);
CREATE INDEX idx_transactions_account ON transactions(account_id);
CREATE INDEX idx_accounts_customer ON bank_accounts(customer_id);
CREATE INDEX idx_devices_customer ON devices(customer_id);


