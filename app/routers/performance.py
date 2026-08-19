from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import extract, and_, or_, func, desc
from datetime import datetime, date, timedelta
from typing import List, Optional

from app.database import get_db
from app.models.user import User
from app.models.attendance import Attendance, AttendanceLog
from app.models.production_job import ProductionJob
from app.models.component_task import ComponentTask
from app.models.performance import WorkerDailyPerformance, TeamDailySummary
from app.auth import get_current_active_user

router = APIRouter(prefix="/performance", tags=["Performance"])

def get_efficiency(expected: float, actual: float) -> float:
    if expected > 0:
        return min(round((expected / max(actual, 1)) * 100, 1), 150.0)
    return 100.0 if expected == 0 and actual == 0 else 0.0

@router.get("/dashboard")
def get_performance_dashboard(
    date_str: Optional[str] = Query(None, alias="date"),
    month_str: Optional[str] = Query(None, alias="month"),
    department: Optional[str] = None,
    supervisor_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    # Parse target date
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = date.today()
    else:
        target_date = date.today()

    # Parse target month
    if month_str:
        try:
            target_year, target_month = map(int, month_str.split("-"))
        except ValueError:
            target_year, target_month = target_date.year, target_date.month
    else:
        target_year, target_month = target_date.year, target_date.month

    yesterday = target_date - timedelta(days=1)

    # 1. Fetch KPI Helper Function
    def calculate_kpis(for_date: date):
        # Present/Absent workers
        present_q = db.query(Attendance).filter(
            Attendance.date == for_date,
            Attendance.status.in_(["Present", "Half Day"])
        )
        if department:
            present_q = present_q.join(User).filter(User.department == department)
        if supervisor_id:
            present_q = present_q.join(User).filter(User.attendance_records.any(supervisor_id=supervisor_id))
        
        present_count = present_q.count()
        
        # Total active workers (live registered workers)
        total_workers_q = db.query(User).filter(User.employee_id.isnot(None))
        if department:
            total_workers_q = total_workers_q.filter(User.department == department)
        total_active = total_workers_q.count()
        absent_count = max(total_active - present_count, 0)

        # Production jobs metrics
        jobs_q = db.query(ProductionJob)
        if supervisor_id:
            jobs_q = jobs_q.filter(ProductionJob.supervisor_id == supervisor_id)
        if department:
            jobs_q = jobs_q.filter(ProductionJob.stage == department) # assuming stage is associated with dept
        
        all_jobs = jobs_q.all()
        
        # Filter jobs by date for completed ones, and current ones for active ones
        completed_today = 0
        running_today = 0
        pending_today = 0
        total_expected = 0.0
        total_actual = 0.0
        completion_durations = []

        for job in all_jobs:
            # Check completed today
            if job.status == "completed" and job.end_time and job.end_time.date() == for_date:
                completed_today += 1
                duration = 0
                if job.start_time:
                    duration = (job.end_time - job.start_time).total_seconds() / 60
                total_expected += job.expected_duration_minutes or 0
                total_actual += duration
                completion_durations.append(duration)
            # Check currently running/pending
            elif job.status == "in_progress":
                running_today += 1
            elif job.status in ["assigned", "not_started"]:
                pending_today += 1

        # Attendance hours
        total_working_hours = 0.0
        total_ot_hours = 0.0
        att_records = present_q.all()
        for att in att_records:
            total_working_hours += att.net_working_hours or 0
            total_ot_hours += att.ot_hours or 0

        avg_eff = get_efficiency(total_expected, total_actual)
        avg_comp = round(sum(completion_durations) / max(len(completion_durations), 1) / 60, 1) if completion_durations else 0.0

        return {
            "present": present_count,
            "absent": absent_count,
            "completed": completed_today,
            "running": running_today,
            "pending": pending_today,
            "efficiency": avg_eff,
            "working_hours": round(total_working_hours, 1),
            "ot_hours": round(total_ot_hours, 1),
            "avg_completion_time": avg_comp
        }

    kpis_today = calculate_kpis(target_date)
    kpis_yesterday = calculate_kpis(yesterday)

    # 2. Monthly Calendar generation
    calendar_days = []
    # Generate days in target month
    first_day_of_month = date(target_year, target_month, 1)
    if target_month == 12:
        last_day_of_month = date(target_year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day_of_month = date(target_year, target_month + 1, 1) - timedelta(days=1)

    # Query all completed jobs in the month
    jobs_month = db.query(ProductionJob).filter(
        ProductionJob.status == "completed",
        extract("year", ProductionJob.end_time) == target_year,
        extract("month", ProductionJob.end_time) == target_month
    ).all()

    # Pre-group completed jobs by date for speed
    jobs_by_date = {}
    for j in jobs_month:
        if j.end_time:
            j_date = j.end_time.date()
            if j_date not in jobs_by_date:
                jobs_by_date[j_date] = []
            jobs_by_date[j_date].append(j)

    curr = first_day_of_month
    while curr <= last_day_of_month:
        day_jobs = jobs_by_date.get(curr, [])
        total_expected_m = sum(j.expected_duration_minutes or 0 for j in day_jobs)
        total_actual_m = 0.0
        for j in day_jobs:
            if j.start_time and j.end_time:
                total_actual_m += (j.end_time - j.start_time).total_seconds() / 60

        eff = get_efficiency(total_expected_m, total_actual_m)
        
        # Color Rules
        if not day_jobs:
            color = "gray" # No production
            status = "No Production"
        elif eff >= 90:
            color = "green" # Excellent
            status = "Excellent"
        elif eff >= 70:
            color = "yellow" # Average
            status = "Average"
        else:
            color = "red" # Low
            status = "Low"

        calendar_days.append({
            "date": curr.strftime("%Y-%m-%d"),
            "total_jobs": len(day_jobs),
            "efficiency": eff,
            "status": status,
            "color": color
        })
        curr += timedelta(days=1)

    # 3. Department Analytics Chart Data (Dynamic Live Departments)
    live_depts = db.query(User.department).filter(User.employee_id.isnot(None), User.department.isnot(None)).distinct().all()
    depts = [d[0] for d in live_depts if d[0]]
    if not depts:
        depts = ["Fabrication", "Paint", "Assembly", "Quality", "Dispatch"]
    dept_performance = []
    for d in depts:
        d_jobs = db.query(ProductionJob).filter(
            ProductionJob.stage == d,
            ProductionJob.status == "completed",
            extract("year", ProductionJob.end_time) == target_year,
            extract("month", ProductionJob.end_time) == target_month
        ).all()
        
        d_expected = sum(j.expected_duration_minutes or 0 for j in d_jobs)
        d_actual = 0.0
        for j in d_jobs:
            if j.start_time and j.end_time:
                d_actual += (j.end_time - j.start_time).total_seconds() / 60
        
        dept_performance.append({
            "name": d,
            "efficiency": get_efficiency(d_expected, d_actual),
            "completed": len(d_jobs)
        })

    # Weekly Trends Chart Data (last 4 weeks)
    weekly_trends = []
    for w_idx in range(4):
        w_start = target_date - timedelta(days=(3 - w_idx) * 7 + 6)
        w_end = target_date - timedelta(days=(3 - w_idx) * 7)
        w_jobs = db.query(ProductionJob).filter(
            ProductionJob.status == "completed",
            ProductionJob.end_time >= datetime.combine(w_start, datetime.min.time()),
            ProductionJob.end_time <= datetime.combine(w_end, datetime.max.time())
        ).all()
        
        w_expected = sum(j.expected_duration_minutes or 0 for j in w_jobs)
        w_actual = 0.0
        for j in w_jobs:
            if j.start_time and j.end_time:
                w_actual += (j.end_time - j.start_time).total_seconds() / 60

        weekly_trends.append({
            "name": f"Week {w_idx+1}",
            "efficiency": get_efficiency(w_expected, w_actual),
            "jobs": len(w_jobs)
        })

    return {
        "kpis": {
            "today": kpis_today,
            "yesterday": kpis_yesterday
        },
        "calendar": calendar_days,
        "analytics": {
            "departmentPerformance": dept_performance,
            "weeklyTrends": weekly_trends
        }
    }

@router.get("/workers")
def get_performance_workers(
    date_str: Optional[str] = Query(None, alias="date"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1),
    search: Optional[str] = None,
    sort_by: Optional[str] = "name",
    sort_order: Optional[str] = "asc",
    department: Optional[str] = None,
    supervisor_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    # Parse date
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = date.today()
    else:
        target_date = date.today()

    # Query active registered workers
    workers_q = db.query(User).filter(User.employee_id.isnot(None))

    if department and department != "All":
        workers_q = workers_q.filter(User.department == department)
    if search:
        workers_q = workers_q.filter(User.name.ilike(f"%{search}%"))

    # Execute and construct results
    all_workers = workers_q.all()
    workers_performance = []

    for w in all_workers:
        # 1. Attendance status
        att = db.query(Attendance).filter(Attendance.worker_id == w.id, Attendance.date == target_date).first()
        att_status = att.status if att else "Absent"
        working_hours = att.net_working_hours if att else 0.0
        break_time = att.break_time if att else 0.0
        overtime = att.ot_hours if att else 0.0

        # 2. Production jobs counts and today's assignments
        jobs = db.query(ProductionJob).filter(
            ProductionJob.workers.any(id=w.id)
        ).all()

        completed_count = 0
        running_count = 0
        pending_count = 0
        total_expected = 0.0
        total_actual = 0.0
        today_assignment = "-"

        for job in jobs:
            # Check completed today
            if job.status == "completed" and job.end_time and job.end_time.date() == target_date:
                completed_count += 1
                total_expected += job.expected_duration_minutes or 0
                if job.start_time:
                    total_actual += (job.end_time - job.start_time).total_seconds() / 60
                today_assignment = job.stage
            elif job.status == "in_progress":
                running_count += 1
                today_assignment = job.stage
            elif job.status in ["assigned", "not_started"]:
                pending_count += 1
                today_assignment = job.stage

        # If no production jobs, check component tasks
        if today_assignment == "-":
            tasks = db.query(ComponentTask).filter(
                ComponentTask.workers.any(id=w.id)
            ).all()
            for t in tasks:
                if t.start_time and t.start_time.date() == target_date:
                    today_assignment = t.component_type
                    if t.status == "completed":
                        completed_count += 1
                    else:
                        running_count += 1

        # Supervisor name
        supervisor_name = "-"
        # Check supervisor assignments
        if jobs:
            latest_job = jobs[-1]
            if latest_job.supervisor:
                supervisor_name = latest_job.supervisor.name

        eff = get_efficiency(total_expected, total_actual)

        workers_performance.append({
            "id": w.id,
            "employeeId": w.employee_id or f"EMP-{w.id:03d}",
            "name": w.name,
            "photo": w.profile_photo_url,
            "department": w.department or "Unassigned",
            "todayAssignment": today_assignment,
            "supervisor": supervisor_name,
            "completedJobs": completed_count,
            "runningJobs": running_count,
            "pendingJobs": pending_count,
            "workingHours": round(working_hours, 1),
            "breakTime": round(break_time, 1),
            "overtime": round(overtime, 1),
            "efficiency": eff,
            "attendanceStatus": att_status
        })

    # Sort results
    reverse = (sort_order == "desc")
    if sort_by == "efficiency":
        workers_performance.sort(key=lambda x: x["efficiency"], reverse=reverse)
    elif sort_by == "completedJobs":
        workers_performance.sort(key=lambda x: x["completedJobs"], reverse=reverse)
    elif sort_by == "workingHours":
        workers_performance.sort(key=lambda x: x["workingHours"], reverse=reverse)
    else:
        workers_performance.sort(key=lambda x: x["name"].lower(), reverse=reverse)

    # Paginate
    total_count = len(workers_performance)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_items = workers_performance[start:end]

    return {
        "items": paginated_items,
        "total_count": total_count
    }

@router.get("/worker/{worker_id}")
def get_worker_detail(
    worker_id: int,
    date_str: Optional[str] = Query(None, alias="date"),
    history_days: int = 30,
    db: Session = Depends(get_db)
):
    worker = db.query(User).filter(User.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = date.today()
    else:
        target_date = date.today()

    # Present status & hours
    att = db.query(Attendance).filter(Attendance.worker_id == worker_id, Attendance.date == target_date).first()
    attendance_status = att.status if att else "Absent"
    working_hours = att.net_working_hours if att else 0.0
    break_time = att.break_time if att else 0.0
    overtime = att.ot_hours if att else 0.0

    # Today's Jobs
    jobs = db.query(ProductionJob).filter(
        ProductionJob.workers.any(id=worker_id)
    ).all()

    today_jobs_list = []
    timeline_events = []
    completed_count = 0
    running_count = 0
    pending_count = 0
    total_expected = 0.0
    total_actual = 0.0

    # Sort jobs by assigned time or start time
    for job in jobs:
        is_today = False
        if job.end_time and job.end_time.date() == target_date:
            is_today = True
        elif job.start_time and job.start_time.date() == target_date:
            is_today = True
        elif job.assigned_date and job.assigned_date.date() == target_date:
            is_today = True

        if is_today or job.status in ["in_progress", "assigned", "not_started"]:
            # Add to today's job list
            duration = 0
            if job.start_time and job.end_time:
                duration = int((job.end_time - job.start_time).total_seconds() / 60)
            
            today_jobs_list.append({
                "id": job.id,
                "name": job.stage,
                "assignedTime": job.assigned_date.strftime("%H:%M") if job.assigned_date else "-",
                "startedTime": job.start_time.strftime("%H:%M") if job.start_time else "-",
                "completedTime": job.end_time.strftime("%H:%M") if job.end_time else "-",
                "duration": duration,
                "status": job.status,
                "progress": job.progress_percent,
                "supervisor": job.supervisor.name if job.supervisor else "-",
                "remarks": job.comments or "",
                "images": [p.photo_url for p in job.photos] if job.photos else []
            })

            # Setup timeline events
            if job.assigned_date and job.assigned_date.date() == target_date:
                timeline_events.append({
                    "time": job.assigned_date.strftime("%H:%M"),
                    "title": f"Job Assigned ({job.stage})",
                    "description": f"Assigned by {job.supervisor.name if job.supervisor else 'System'}"
                })
            if job.start_time and job.start_time.date() == target_date:
                timeline_events.append({
                    "time": job.start_time.strftime("%H:%M"),
                    "title": "Job Started",
                    "description": f"Worker commenced work on {job.stage}"
                })
            if job.end_time and job.end_time.date() == target_date:
                timeline_events.append({
                    "time": job.end_time.strftime("%H:%M"),
                    "title": "Job Completed",
                    "description": f"Worker finished stage {job.stage}"
                })

            if job.status == "completed":
                completed_count += 1
                total_expected += job.expected_duration_minutes or 0
                total_actual += duration
            elif job.status == "in_progress":
                running_count += 1
            else:
                pending_count += 1

    # Sorting timeline chronologically
    timeline_events.sort(key=lambda x: x["time"])

    # If worker checked in today, add check in to timeline
    if att and att.punch_in:
        timeline_events.insert(0, {
            "time": att.punch_in.strftime("%H:%M"),
            "title": "Checked In",
            "description": "Marked attendance via PWA app"
        })
    if att and att.punch_out:
        timeline_events.append({
            "time": att.punch_out.strftime("%H:%M"),
            "title": "Checked Out",
            "description": "Punch out registered successfully"
        })

    # History trends
    history_start = target_date - timedelta(days=history_days)
    history_records = db.query(Attendance).filter(
        Attendance.worker_id == worker_id,
        Attendance.date >= history_start,
        Attendance.date <= target_date
    ).order_by(Attendance.date.asc()).all()

    history_list = []
    for h in history_records:
        # Calculate daily job count & efficiency
        h_jobs = [j for j in jobs if j.end_time and j.end_time.date() == h.date and j.status == "completed"]
        h_expected = sum(j.expected_duration_minutes or 0 for j in h_jobs)
        h_actual = 0.0
        for j in h_jobs:
            if j.start_time:
                h_actual += (j.end_time - j.start_time).total_seconds() / 60
        
        history_list.append({
            "date": h.date.strftime("%Y-%m-%d"),
            "workingHours": h.net_working_hours,
            "jobsCompleted": len(h_jobs),
            "efficiency": get_efficiency(h_expected, h_actual),
            "status": h.status
        })

    efficiency = get_efficiency(total_expected, total_actual)

    # Supervisor Review details
    daily_review = db.query(WorkerDailyPerformance).filter(
        WorkerDailyPerformance.worker_id == worker_id,
        WorkerDailyPerformance.date == target_date
    ).first()

    return {
        "overview": {
            "status": attendance_status,
            "workingHours": round(working_hours, 1),
            "breakTime": round(break_time, 1),
            "overtime": round(overtime, 1),
            "completedJobs": completed_count,
            "runningJobs": running_count,
            "pendingJobs": pending_count,
            "efficiency": efficiency,
            "productivityScore": min(int(efficiency * 0.9 + working_hours * 1.5), 100) if attendance_status != "Absent" else 0
        },
        "todayJobs": today_jobs_list,
        "timeline": timeline_events,
        "history": history_list,
        "remarks": daily_review.remarks if daily_review else "",
        "approvalStatus": daily_review.approval_status if daily_review else "Pending"
    }

@router.post("/worker/{worker_id}/approve")
def approve_worker_performance(
    worker_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    date_str = payload.get("date")
    remarks = payload.get("remarks", "")
    status = payload.get("status", "Approved")

    if not date_str:
        target_date = date.today()
    else:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    # Find or create daily performance record
    record = db.query(WorkerDailyPerformance).filter(
        WorkerDailyPerformance.worker_id == worker_id,
        WorkerDailyPerformance.date == target_date
    ).first()

    if not record:
        record = WorkerDailyPerformance(
            worker_id=worker_id,
            date=target_date,
            supervisor_id=current_user.id,
            remarks=remarks,
            approval_status=status
        )
        db.add(record)
    else:
        record.supervisor_id = current_user.id
        record.remarks = remarks
        record.approval_status = status

    db.commit()
    return {"message": "Performance record saved successfully"}
