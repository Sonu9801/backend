from app.database import SessionLocal
from app.models.attendance import Attendance, AttendanceLog
from app.models.user import User
from app.models.holiday import Holiday
from app.models.payroll import PayrollRecord
from app.services.attendance_engine import PayrollSyncEngine
from datetime import date, datetime, timedelta
import calendar

def main():
    db = SessionLocal()
    try:
        shubham = db.query(User).filter(User.id == 26).first()
        dilbagh = db.query(User).filter(User.id == 36).first()
        akhilesh = db.query(User).filter(User.id == 31).first()

        print(f"Target workers: {shubham.name} (id {shubham.id}), {dilbagh.name} (id {dilbagh.id}), {akhilesh.name} (id {akhilesh.id})")

        start_date = date(2026, 9, 1)
        end_date = date(2026, 9, 30)

        # Remove existing Sept attendance for these 3 workers
        del_count = db.query(Attendance).filter(
            Attendance.worker_id.in_([26, 36, 31]),
            Attendance.date >= start_date,
            Attendance.date <= end_date
        ).delete(synchronize_session=False)
        print(f"Cleared {del_count} existing September attendance records for targets.")

        # Also clear any punch logs in Sept for them
        db.query(AttendanceLog).filter(
            AttendanceLog.worker_id.in_([26, 36, 31]),
            AttendanceLog.timestamp >= datetime(2026, 9, 1, 0, 0, 0),
            AttendanceLog.timestamp <= datetime(2026, 9, 30, 23, 59, 59)
        ).delete(synchronize_session=False)

        # 1. Shubham Srivastava - All 26 working days Present (General shift 09:00 - 17:30)
        shubham_last_att = None
        for day in range(1, 31):
            cur_date = date(2026, 9, day)
            is_sun = (cur_date.weekday() == 6)

            if is_sun:
                att = Attendance(
                    worker_id=shubham.id,
                    date=cur_date,
                    status="Sunday",
                    is_sunday=True,
                    net_working_hours=0.0,
                    ot_hours=0.0
                )
            else:
                p_in = datetime(2026, 9, day, 9, 0, 0)
                p_out = datetime(2026, 9, day, 17, 30, 0)
                att = Attendance(
                    worker_id=shubham.id,
                    date=cur_date,
                    punch_in=p_in,
                    punch_out=p_out,
                    status="Present",
                    is_sunday=False,
                    net_working_hours=8.0,
                    break_time=0.5,
                    late_minutes=0,
                    early_exit_minutes=0,
                    ot_hours=0.0
                )
                # Punch logs
                db.add(AttendanceLog(worker_id=shubham.id, action="Punch In", timestamp=p_in, latitude=28.5, longitude=77.2, is_valid=True, device_info="Web App"))
                db.add(AttendanceLog(worker_id=shubham.id, action="Punch Out", timestamp=p_out, latitude=28.5, longitude=77.2, is_valid=True, device_info="Web App"))
            
            db.add(att)
            shubham_last_att = att

        # 2. Dilbagh Singh - All 26 working days Present (General shift 09:30 - 18:00)
        dilbagh_last_att = None
        for day in range(1, 31):
            cur_date = date(2026, 9, day)
            is_sun = (cur_date.weekday() == 6)

            if is_sun:
                att = Attendance(
                    worker_id=dilbagh.id,
                    date=cur_date,
                    status="Sunday",
                    is_sunday=True,
                    net_working_hours=0.0,
                    ot_hours=0.0
                )
            else:
                p_in = datetime(2026, 9, day, 9, 30, 0)
                p_out = datetime(2026, 9, day, 18, 0, 0)
                att = Attendance(
                    worker_id=dilbagh.id,
                    date=cur_date,
                    punch_in=p_in,
                    punch_out=p_out,
                    status="Present",
                    is_sunday=False,
                    net_working_hours=8.0,
                    break_time=0.5,
                    late_minutes=0,
                    early_exit_minutes=0,
                    ot_hours=0.0
                )
                # Punch logs
                db.add(AttendanceLog(worker_id=dilbagh.id, action="Punch In", timestamp=p_in, latitude=28.5, longitude=77.2, is_valid=True, device_info="Web App"))
                db.add(AttendanceLog(worker_id=dilbagh.id, action="Punch Out", timestamp=p_out, latitude=28.5, longitude=77.2, is_valid=True, device_info="Web App"))
            
            db.add(att)
            dilbagh_last_att = att

        # 3. Akhilesh Sharma - 22 working days Present in Evening Shift (17:30 - 23:00)
        # 4 working days Absent, 4 Sundays. Total 26 working days.
        akhilesh_last_att = None
        present_count = 0
        for day in range(1, 31):
            cur_date = date(2026, 9, day)
            is_sun = (cur_date.weekday() == 6)

            if is_sun:
                att = Attendance(
                    worker_id=akhilesh.id,
                    date=cur_date,
                    status="Sunday",
                    is_sunday=True,
                    net_working_hours=0.0,
                    ot_hours=0.0
                )
            else:
                if present_count < 22:
                    # Present in Evening Shift
                    p_in = datetime(2026, 9, day, 17, 30, 0)
                    p_out = datetime(2026, 9, day, 23, 0, 0)
                    att = Attendance(
                        worker_id=akhilesh.id,
                        date=cur_date,
                        punch_in=p_in,
                        punch_out=p_out,
                        status="Present",
                        is_sunday=False,
                        net_working_hours=5.5,
                        break_time=0.0,
                        late_minutes=0,
                        early_exit_minutes=0,
                        ot_hours=0.0
                    )
                    # Punch logs
                    db.add(AttendanceLog(worker_id=akhilesh.id, action="Punch In", timestamp=p_in, latitude=28.5, longitude=77.2, is_valid=True, device_info="Web App"))
                    db.add(AttendanceLog(worker_id=akhilesh.id, action="Punch Out", timestamp=p_out, latitude=28.5, longitude=77.2, is_valid=True, device_info="Web App"))
                    present_count += 1
                else:
                    # Absent
                    att = Attendance(
                        worker_id=akhilesh.id,
                        date=cur_date,
                        status="Absent",
                        is_sunday=False,
                        net_working_hours=0.0,
                        ot_hours=0.0
                    )

            db.add(att)
            akhilesh_last_att = att

        db.commit()
        print(f"Attendance records successfully saved: Shubham=30, Dilbagh=30, Akhilesh=30 (Present={present_count}, Absent=4, Sunday=4)")

        # Sync Payroll records for September
        print("Synchronizing September PayrollRecords...")
        from app.models.salary_profile import SalaryProfile
        sp_shubham = db.query(SalaryProfile).filter(SalaryProfile.worker_id == shubham.id).first()
        sp_dilbagh = db.query(SalaryProfile).filter(SalaryProfile.worker_id == dilbagh.id).first()
        sp_akhilesh = db.query(SalaryProfile).filter(SalaryProfile.worker_id == akhilesh.id).first()

        PayrollSyncEngine.sync_daily_attendance(db, shubham_last_att, sp_shubham)
        PayrollSyncEngine.sync_daily_attendance(db, dilbagh_last_att, sp_dilbagh)
        PayrollSyncEngine.sync_daily_attendance(db, akhilesh_last_att, sp_akhilesh)

        # Verification
        prs = db.query(PayrollRecord).filter(
            PayrollRecord.worker_id.in_([26, 36, 31]),
            PayrollRecord.month == "2026-09"
        ).all()
        for pr in prs:
            w_name = shubham.name if pr.worker_id == 26 else (dilbagh.name if pr.worker_id == 36 else akhilesh.name)
            print(f"Payroll [{w_name}]: Days Present={pr.days_present}, Absent={pr.days_absent}, Base={pr.base_salary}, Final={pr.final_salary}")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
