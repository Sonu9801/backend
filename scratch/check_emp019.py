import sys, os
sys.path.append(os.path.abspath("."))
import sqlalchemy
from app.config import settings

def run():
    engine = sqlalchemy.create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        users = conn.execute(sqlalchemy.text("SELECT id, name, employee_id FROM users WHERE employee_id='FOX-EMP-019'")).fetchall()
        print("User:", users)
        if users:
            wid = users[0][0]
            sp = conn.execute(sqlalchemy.text(f"SELECT id, worker_id, salary_type, monthly_salary, daily_wage FROM salary_profiles WHERE worker_id={wid}")).fetchall()
            print("SalaryProfile:", sp)
            pr = conn.execute(sqlalchemy.text(f"SELECT id, month, base_salary, final_salary, status FROM payroll_records WHERE worker_id={wid}")).fetchall()
            print("PayrollRecords:", pr)

if __name__ == '__main__':
    run()
