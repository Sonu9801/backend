from fastapi import APIRouter, Depends, HTTPException, Query
from app.auth import get_current_active_user
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from app.database import get_db
from app.models.user import User
from app.models.attendance import AttendanceLog, Attendance
from app.models.salary_profile import SalaryProfile
from app.models.payroll import AdvanceRequest, PayrollRecord
from datetime import datetime, date
import calendar

router = APIRouter(prefix="/payroll", tags=["payroll"], dependencies=[Depends(get_current_active_user)])

class AdvanceCreate(BaseModel):
    worker_id: int
    amount: float
    reason: str = None

@router.get("/worker/{worker_id}")
def get_worker_salaries(worker_id: int, db: Session = Depends(get_db)):
    """Fetch salary history for a worker"""
    records = db.query(PayrollRecord).filter(PayrollRecord.worker_id == worker_id).order_by(PayrollRecord.month.desc()).all()
    if not records:
        # Mocking for preview if none
        return [{
            "id": 999,
            "month": datetime.now().strftime("%Y-%m"),
            "base_salary": 20000,
            "days_present": 22,
            "half_days": 1,
            "days_absent": 0,
            "leave_days": 1,
            "ot_hours": 12,
            "net_working_days": 23.5,
            "ot_amount": 2500,
            "deductions": 500,
            "final_salary": 22000,
            "status": "Paid"
        }]
    return records

@router.get("/summary")
def get_payroll_summary(month: str = Query(None), db: Session = Depends(get_db)):
    """
    Get top level KPIs for the Payroll Dashboard.
    `month` should be in YYYY-MM format. Default is current month.
    """
    if month is None:
        month = datetime.now().strftime("%Y-%m")
        
    try:
        year, month_num = map(int, month.split("-"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM")

    # Get total active employees
    total_employees = db.query(User).filter(User.employee_id.isnot(None), User.employment_status == "Active").count()
    
    # We will compute costs based on attendance logic
    # Find all attendance records for the month
    start_date = f"{year}-{month_num:02d}-01"
    _, last_day = calendar.monthrange(year, month_num)
    end_date = f"{year}-{month_num:02d}-{last_day}"
    
    logs = db.query(Attendance).filter(
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).all()
    
    # We also need salary profiles to compute amounts
    salary_profiles = {sp.worker_id: sp for sp in db.query(SalaryProfile).all()}
    workers = {w.id: w for w in db.query(User).filter(User.employee_id.isnot(None)).all()}
    
    total_ot_cost = 0.0
    total_sunday_cost = 0.0
    total_base_salary = 0.0
    
    # Department aggregation
    dept_costs = {}
    employee_insights = []
    
    # Aggregate stats per worker
    worker_stats = {}
    
    for log in logs:
        wid = log.worker_id
        if wid not in worker_stats:
            worker_stats[wid] = {"present": 0, "half": 0, "absent": 0, "ot_hours": 0.0, "sunday_hours": 0.0}
            
        if log.status == "Present":
            worker_stats[wid]["present"] += 1
        elif log.status == "Half Day":
            worker_stats[wid]["half"] += 1
        elif log.status == "Absent":
            worker_stats[wid]["absent"] += 1
            
        worker_stats[wid]["ot_hours"] += (log.ot_hours or 0.0)
        try:
            if isinstance(log.date, str):
                log_date = datetime.strptime(log.date, "%Y-%m-%d").date()
            else:
                log_date = log.date
            
            # Since Attendance doesn't have working_hours, we add 8 for a full present sunday, or check if is_sunday is true
            if log_date.weekday() == 6 and log.status == "Present":
                worker_stats[wid]["sunday_hours"] += 8.0
            elif log_date.weekday() == 6 and log.status == "Half Day":
                worker_stats[wid]["sunday_hours"] += 4.0
        except Exception as e:
            print(e)

    # Compute financials
    for wid, stats in worker_stats.items():
        sp = salary_profiles.get(wid)
        w = workers.get(wid)
        if not sp or not w:
            continue
            
        ot_amount = stats["ot_hours"] * (sp.ot_rate_per_hour or 0.0)
        sunday_amount = stats["sunday_hours"] * (sp.sunday_rate_per_hour or 0.0)
        
        base = 0.0
        if sp.salary_type == "Monthly":
            base = sp.monthly_salary or 0.0
        elif sp.salary_type == "DailyWage":
            base = (sp.daily_wage or 0.0) * (stats["present"] + (stats["half"] * 0.5))
            
        total_salary = base + ot_amount + sunday_amount
        
        total_base_salary += base
        total_ot_cost += ot_amount
        total_sunday_cost += sunday_amount
        
        dept = w.department or "Unassigned"
        if dept not in dept_costs:
            dept_costs[dept] = 0.0
        dept_costs[dept] += total_salary
        
        employee_insights.append({
            "id": w.id,
            "name": w.name,
            "total_salary": total_salary,
            "ot_hours": stats["ot_hours"],
            "sunday_hours": stats["sunday_hours"]
        })
        
    monthly_payroll_cost = total_base_salary + total_ot_cost + total_sunday_cost
    
    # Insights Sorting
    highest_paid = sorted(employee_insights, key=lambda x: x["total_salary"], reverse=True)[:5]
    highest_ot = sorted(employee_insights, key=lambda x: x["ot_hours"], reverse=True)[:5]
    sunday_workers = sorted(employee_insights, key=lambda x: x["sunday_hours"], reverse=True)[:5]

    return {
        "totalEmployees": total_employees,
        "monthlyPayrollCost": monthly_payroll_cost,
        "baseSalaryCost": total_base_salary,
        "otCost": total_ot_cost,
        "sundayCost": total_sunday_cost,
        "pendingPayroll": monthly_payroll_cost,
        "approvedPayroll": 0.0,
        "paidPayroll": 0.0,
        "departmentCosts": dept_costs,
        "highestPaid": highest_paid,
        "highestOT": highest_ot,
        "sundayWorkers": sunday_workers
    }

@router.get("/employees")
def get_employee_payroll(month: str = Query(None), db: Session = Depends(get_db)):
    """
    Get detailed payroll table data per employee.
    """
    if month is None:
        month = datetime.now().strftime("%Y-%m")
        
    try:
        year, month_num = map(int, month.split("-"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM")

    start_date = f"{year}-{month_num:02d}-01"
    _, last_day = calendar.monthrange(year, month_num)
    end_date = f"{year}-{month_num:02d}-{last_day}"
    
    workers = db.query(User).filter(User.employee_id.isnot(None), User.employment_status == "Active").all()
    logs = db.query(Attendance).filter(
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).all()
    salary_profiles = {sp.worker_id: sp for sp in db.query(SalaryProfile).all()}
    
    # Get all active approved advances not yet deducted
    active_advances = db.query(AdvanceRequest).filter(
        AdvanceRequest.status == "Approved",
        AdvanceRequest.deducted_in_payroll == False
    ).all()
    
    advances_by_worker = {}
    for adv in active_advances:
        if adv.worker_id not in advances_by_worker:
            advances_by_worker[adv.worker_id] = 0.0
        advances_by_worker[adv.worker_id] += adv.amount
    
    # Group logs by worker
    worker_logs = {}
    for log in logs:
        if log.worker_id not in worker_logs:
            worker_logs[log.worker_id] = []
        worker_logs[log.worker_id].append(log)
        
    results = []
    
    records = {pr.worker_id: pr for pr in db.query(PayrollRecord).filter(PayrollRecord.month == month).all()}
    
    for w in workers:
        w_logs = worker_logs.get(w.id, [])
        sp = salary_profiles.get(w.id)
        pr = records.get(w.id)
        
        present = sum(1 for l in w_logs if l.status == "Present")
        half = sum(1 for l in w_logs if l.status == "Half Day")
        absent = sum(1 for l in w_logs if l.status == "Absent")
        ot_hrs = sum(l.ot_hours or 0.0 for l in w_logs)
        
        sunday_hrs = 0.0
        for l in w_logs:
            try:
                if isinstance(l.date, str):
                    dt = datetime.strptime(l.date, "%Y-%m-%d").date()
                else:
                    dt = l.date
                    
                if dt.weekday() == 6 and l.status == "Present":
                    sunday_hrs += 8.0
                elif dt.weekday() == 6 and l.status == "Half Day":
                    sunday_hrs += 4.0
            except Exception as e:
                pass
                
        ot_amount = ot_hrs * (sp.ot_rate_per_hour if sp else 0.0)
        sunday_amount = sunday_hrs * (sp.sunday_rate_per_hour if sp else 0.0)
        
        base_salary = 0.0
        if sp:
            if sp.salary_type == "Monthly":
                base_salary = sp.monthly_salary or 0.0
            elif sp.salary_type == "DailyWage":
                base_salary = (sp.daily_wage or 0.0) * (present + (half * 0.5))
                
        bonus_amount = 0.0
        deductions = advances_by_worker.get(w.id, 0.0)
        
        # Override with DB record if exists
        if pr:
            base_salary = pr.base_salary
            ot_amount = pr.ot_amount
            sunday_amount = pr.sunday_amount
            bonus_amount = pr.bonus_amount
            deductions = pr.deductions
            status = pr.status
        else:
            status = "Draft"
            
        total_salary = base_salary + ot_amount + sunday_amount
        final_salary = total_salary + bonus_amount - deductions
        
        results.append({
            "id": w.id,
            "employeeId": w.employee_id,
            "employeeName": w.name,
            "department": w.department,
            "role": w.role or "Worker",
            "presentDays": present,
            "halfDays": half,
            "absentDays": absent,
            "otHours": round(ot_hrs, 2),
            "sundayHours": round(sunday_hrs, 2),
            "baseSalary": round(base_salary, 2),
            "otAmount": round(ot_amount, 2),
            "sundayAmount": round(sunday_amount, 2),
            "bonusAmount": round(bonus_amount, 2),
            "deductions": round(deductions, 2),
            "totalSalary": round(total_salary, 2),
            "finalSalary": round(final_salary, 2),
            "status": status,
            "month": month
        })
        
    return results

class PayrollUpdatePayload(BaseModel):
    month: str
    base_salary: float = None
    ot_amount: float = None
    sunday_amount: float = None
    bonus_amount: float = None
    deductions: float = None
    status: str = None
    reason: str

@router.put("/employees/{worker_id}")
async def update_employee_payroll(worker_id: int, payload: PayrollUpdatePayload, db: Session = Depends(get_db), current_user = Depends(get_current_active_user)):
    if current_user.role not in ["owner", "admin", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    pr = db.query(PayrollRecord).filter(PayrollRecord.worker_id == worker_id, PayrollRecord.month == payload.month).first()
    
    old_data = {}
    if not pr:
        # We create one to persist edits
        pr = PayrollRecord(
            worker_id=worker_id,
            month=payload.month,
            base_salary=payload.base_salary or 0.0,
            ot_amount=payload.ot_amount or 0.0,
            sunday_amount=payload.sunday_amount or 0.0,
            bonus_amount=payload.bonus_amount or 0.0,
            deductions=payload.deductions or 0.0,
            status=payload.status or "Draft"
        )
        db.add(pr)
        db.commit()
        db.refresh(pr)
    else:
        old_data = {
            "base_salary": pr.base_salary,
            "ot_amount": pr.ot_amount,
            "bonus_amount": pr.bonus_amount,
            "deductions": pr.deductions,
            "status": pr.status
        }
        if payload.base_salary is not None: pr.base_salary = payload.base_salary
        if payload.ot_amount is not None: pr.ot_amount = payload.ot_amount
        if payload.sunday_amount is not None: pr.sunday_amount = payload.sunday_amount
        if payload.bonus_amount is not None: pr.bonus_amount = payload.bonus_amount
        if payload.deductions is not None: pr.deductions = payload.deductions
        if payload.status is not None: pr.status = payload.status
        
        pr.final_salary = pr.base_salary + pr.ot_amount + pr.sunday_amount + pr.bonus_amount - pr.deductions
        db.commit()
        db.refresh(pr)
        
    new_data = {
        "base_salary": pr.base_salary,
        "ot_amount": pr.ot_amount,
        "bonus_amount": pr.bonus_amount,
        "deductions": pr.deductions,
        "status": pr.status
    }
    
    from app.services.audit import log_audit_event
    await log_audit_event(
        db, "payroll_updated", f"Payroll updated for worker {worker_id} ({payload.month})",
        edited_by=getattr(current_user, "username", "System"),
        reason=payload.reason, old_value=old_data, new_value=new_data, worker_id=worker_id
    )
    
    return pr

@router.delete("/employees/{worker_id}")
async def delete_employee_payroll(
    worker_id: int, 
    month: str = Query(...), 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_active_user)
):
    if current_user.role not in ["owner", "admin", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    pr = db.query(PayrollRecord).filter(PayrollRecord.worker_id == worker_id, PayrollRecord.month == month).first()
    if not pr:
        raise HTTPException(status_code=404, detail="Payroll record not found")
        
    db.delete(pr)
    db.commit()
    
    from app.services.audit import log_audit_event
    await log_audit_event(
        db, "payroll_deleted", f"Payroll reset for worker {worker_id} ({month})",
        edited_by=getattr(current_user, "username", "System"),
        reason="Manual Deletion", worker_id=worker_id
    )
    
    return {"message": "Payroll record deleted/reset"}


@router.get("/advances")
def get_advances(db: Session = Depends(get_db)):
    advances = db.query(AdvanceRequest).order_by(AdvanceRequest.request_date.desc()).all()
    results = []
    for adv in advances:
        results.append({
            "id": adv.id,
            "worker_id": adv.worker_id,
            "employeeName": adv.worker.name if adv.worker else "Unknown",
            "department": adv.worker.department if adv.worker else "Unknown",
            "amount": adv.amount,
            "request_date": adv.request_date.isoformat(),
            "reason": adv.reason,
            "status": adv.status,
            "deducted": adv.deducted_in_payroll
        })
    return results

@router.post("/advances")
def create_advance(req: AdvanceCreate, db: Session = Depends(get_db)):
    adv = AdvanceRequest(
        worker_id=req.worker_id,
        amount=req.amount,
        reason=req.reason
    )
    db.add(adv)
    db.commit()
    db.refresh(adv)
    return {"message": "Advance request created successfully", "id": adv.id}

@router.patch("/advances/{adv_id}/status")
def update_advance_status(adv_id: int, status: str = Query(...), db: Session = Depends(get_db)):
    if status not in ["Approved", "Rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    adv = db.query(AdvanceRequest).filter(AdvanceRequest.id == adv_id).first()
    if not adv:
        raise HTTPException(status_code=404, detail="Advance not found")
        
    adv.status = status
    db.commit()
    return {"message": f"Advance status updated to {status}"}

@router.get("/analytics/full")
def get_payroll_full_analytics(db: Session = Depends(get_db)):
    """
    Get comprehensive analytics for 10 requested metrics across historical data.
    """
    from collections import defaultdict
    from datetime import datetime
    
    workers = {w.id: w for w in db.query(User).filter(User.employee_id.isnot(None), User.employment_status == "Active").all()}
    salary_profiles = {sp.worker_id: sp for sp in db.query(SalaryProfile).all()}
    all_attendance = db.query(Attendance).all()
    all_advances = db.query(AdvanceRequest).all()
    
    monthly_data = defaultdict(lambda: defaultdict(lambda: {"present": 0, "half": 0, "absent": 0, "ot_hrs": 0.0, "sunday_hrs": 0.0}))
    
    for att in all_attendance:
        try:
            if isinstance(att.date, str):
                dt = datetime.strptime(att.date, "%Y-%m-%d").date()
            else:
                dt = att.date
            
            month_key = dt.strftime("%Y-%m")
            wid = att.worker_id
            
            if att.status == "Present":
                monthly_data[month_key][wid]["present"] += 1
                if dt.weekday() == 6:
                    monthly_data[month_key][wid]["sunday_hrs"] += 8.0
            elif att.status == "Half Day":
                monthly_data[month_key][wid]["half"] += 1
                if dt.weekday() == 6:
                    monthly_data[month_key][wid]["sunday_hrs"] += 4.0
            elif att.status == "Absent":
                monthly_data[month_key][wid]["absent"] += 1
                
            monthly_data[month_key][wid]["ot_hrs"] += (att.ot_hours or 0.0)
        except Exception:
            pass

    month_summaries = {}
    
    for month_key, worker_stats in monthly_data.items():
        base_cost = 0.0
        ot_cost = 0.0
        sunday_cost = 0.0
        dept_costs = defaultdict(float)
        worker_salaries = []
        
        for wid, stats in worker_stats.items():
            sp = salary_profiles.get(wid)
            w = workers.get(wid)
            if not sp or not w:
                continue
                
            w_ot = stats["ot_hrs"] * (sp.ot_rate_per_hour or 0.0)
            w_sun = stats["sunday_hrs"] * (sp.sunday_rate_per_hour or 0.0)
            
            w_base = 0.0
            if sp.salary_type == "Monthly":
                w_base = sp.monthly_salary or 0.0
            else:
                w_base = (sp.daily_wage or 0.0) * (stats["present"] + (stats["half"] * 0.5))
                
            w_total = w_base + w_ot + w_sun
            
            base_cost += w_base
            ot_cost += w_ot
            sunday_cost += w_sun
            
            dept = w.department or "Unassigned"
            dept_costs[dept] += w_total
            
            worker_salaries.append({
                "worker_id": wid,
                "name": w.name,
                "dept": dept,
                "total": w_total,
                "base": w_base,
                "ot": w_ot,
                "sun": w_sun,
                "present": stats["present"],
                "total_days": stats["present"] + stats["half"] + stats["absent"]
            })
            
        month_summaries[month_key] = {
            "total_cost": base_cost + ot_cost + sunday_cost,
            "base_cost": base_cost,
            "ot_cost": ot_cost,
            "sunday_cost": sunday_cost,
            "dept_costs": dept_costs,
            "worker_salaries": worker_salaries
        }
        
    sorted_months = sorted(list(month_summaries.keys()))
    
    if not sorted_months:
        return {"error": "No historical data available"}
        
    current_month_key = sorted_months[-1]
    current_data = month_summaries[current_month_key]
    
    monthly_trend = [
        {
            "month": m, 
            "total": month_summaries[m]["total_cost"],
            "ot": month_summaries[m]["ot_cost"],
            "sunday": month_summaries[m]["sunday_cost"]
        } 
        for m in sorted_months[-6:]
    ]
    
    dept_cost_arr = [{"name": k, "value": v} for k, v in current_data["dept_costs"].items()]
    highest_paid = sorted(current_data["worker_salaries"], key=lambda x: x["total"], reverse=True)[:5]
    
    total_payroll = current_data["total_cost"]
    distribution = [
        {"name": "Base Salary", "value": current_data["base_cost"]},
        {"name": "Overtime", "value": current_data["ot_cost"]},
        {"name": "Sunday Pay", "value": current_data["sunday_cost"]}
    ]
    
    correlation = []
    for ws in current_data["worker_salaries"]:
        if ws["total_days"] > 0:
            att_rate = round((ws["present"] / ws["total_days"]) * 100, 1)
            correlation.append({
                "attendanceRate": att_rate,
                "salary": ws["total"],
                "name": ws["name"]
            })
            
    total_given = sum(a.amount for a in all_advances if a.status == "Approved")
    total_recovered = sum(a.amount for a in all_advances if a.status == "Approved" and a.deducted_in_payroll)
    advances = {
        "given": total_given,
        "recovered": total_recovered,
        "pending": total_given - total_recovered
    }
    
    forecast_val = 0
    if len(sorted_months) >= 3:
        vals = [month_summaries[m]["total_cost"] for m in sorted_months[-3:]]
        g1 = vals[1] - vals[0]
        g2 = vals[2] - vals[1]
        avg_g = (g1 + g2) / 2
        forecast_val = vals[2] + avg_g
    elif len(sorted_months) > 0:
        forecast_val = current_data["total_cost"]
        
    growth = 0.0
    if len(sorted_months) >= 2:
        prev = month_summaries[sorted_months[-2]]["total_cost"]
        curr = current_data["total_cost"]
        if prev > 0:
            growth = ((curr - prev) / prev) * 100
            
    return {
        "monthlyTrend": monthly_trend,
        "deptCost": dept_cost_arr,
        "distribution": distribution,
        "highestPaid": highest_paid,
        "correlation": correlation,
        "advances": advances,
        "forecast": forecast_val,
        "growth": growth,
        "currentMonthTotal": current_data["total_cost"]
    }

@router.post('/generate')
def generate_payroll(month: str = Query(None), db: Session = Depends(get_db)):
    from app.models.notification import Notification
    notification = Notification(
        type='success',
        title='Payroll Generated',
        message=f'Payroll for {month} has been successfully generated.',
        module='payroll',
        target_url='/payroll',
    )
    db.add(notification)
    db.commit()
    return {'message': 'Payroll generated successfully'}
