# Banking Data Quality and Risk Detection Platform

## 1. Overview

This project simulates a secure banking data pipeline for a financial institution. It Includes:
- **Generates synthetic banking data** (customers, accounts, devices, transactions, authentication logs)
- **Performs data quality validation** 
- **Detects and logs risk/compliance violations** based on 2345/QĐ-NHNN (2023) for individual customers
- **Orchestrates daily checks** using Apache Airflow
---

## 2. Setup

### Prerequisites
- **Python**: 3.10+
- **Docker & Docker Compose**
- **PostgreSQL**

### Python Libraries
All dependencies are listed in `requirements.txt`.
Install with:
```sh
pip install -r requirements.txt
```


### Database Setup
- The schema is defined in `sql/schema.sql`.
- When using Docker Compose, the database is initialized automatically.
- If not, create database with the schema.
---

## 3. How to Run

### **A. With Docker Compose (Recommended)**
1. Build and start all services:
   ```sh
   docker-compose up --build
   ```
2. This will:
   - Start a Postgres database
   - Run the data generation and quality/audit scripts

### **B. Standalone Python Scripts**
1. Ensure your database is running and accessible.
2. Run scripts in order:
   ```sh
   python src/generate_data.py
   python src/data_quality_standards.py
   python src/monitoring_audit.py
   ```

### **C. With Airflow (for daily scheduling)**
1. Place `dags_or_jobs/banking_dq_dag.py` in your Airflow `dags/` folder.
2. Start Airflow (webserver & scheduler).
3. The DAG will run daily by default (`@daily`), executing:
   - Data generation
   - Data quality checks
   - Monitoring/audit checks

---

## 4. How to Run the DAG or Job Scheduler

- **Airflow UI**: Trigger or monitor the DAG named `banking_data_quality_dag`.
- **Command line**: 
  ```sh
  airflow dags trigger banking_data_quality_dag
  ```
- **Logs and violations** are output to the database (`risk_events` table).

---

## 5. Assumptions
- All compliance logic is for individual customers only.
- Device trust: All transactions must originate from a verified device.
- Synthetic data may not fully reflect real-world data.
- Database is assumed empty on first run.
- Airflow and database run in UTC timezone by default.

---

## 6. Repository Structure

```
banking-data-assignment/
├── dags_or_jobs/
│   └── banking_dq_dag.py
├── sql/
│   ├── schema.sql
│   └── ERD.png
├── src/
│   ├── generate_data.py
│   ├── data_quality_standards.py
│   └── monitoring_audit.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

