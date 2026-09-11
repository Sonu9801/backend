import math
from datetime import datetime, timedelta, date, time, timezone
from app.models.attendance_settings import AttendanceSettings
from app.models.attendance import Attendance
from app.models.salary_profile import SalaryProfile
from sqlalchemy.orm import Session

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Haversine formula
    R = 6371e3 # metres
    phi1 = lat1 * math.pi/180
    phi2 = lat2 * math.pi/180
    delta_phi = (lat2-lat1) * math.pi/180
    delta_lambda = (lon2-lon1) * math.pi/180

    a = math.sin(delta_phi/2) * math.sin(delta_phi/2) + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda/2) * math.sin(delta_lambda/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c

class GeofenceEngine:
    @staticmethod
    def validate_punch(settings: AttendanceSettings, lat: float, lng: float, accuracy: float = None) -> tuple[bool, str]:
        if accuracy and accuracy > 50:
            return False, "GPS accuracy too low."
            
        settings_lat = settings.latitude if (settings and settings.latitude is not None) else 28.475117
        settings_lng = settings.longitude if (settings and settings.longitude is not None) else 77.297224
        radius = settings.geofence_radius if (settings and settings.geofence_radius is not None) else 10000

        distance = calculate_distance(lat, lng, settings_lat, settings_lng)
        
        if distance <= radius:
            return True, "Inside geofence"
        else:
            return False, f"Outside geofence ({int(distance)}m > {radius}m)"

class TimeEngine:
    @staticmethod
    def calculate_status(settings: AttendanceSettings, punch_in: datetime, punch_out: datetime = None, worker = None) -> dict:
        ist_offset = timezone(timedelta(hours=5, minutes=30))
        
        # Helper to convert naive database IST datetime or aware datetime to IST
        def to_ist_local(dt: datetime) -> datetime:
            if dt.tzinfo is None:
                return dt.replace(tzinfo=ist_offset)
            return dt.astimezone(ist_offset)

        punch_in_local = to_ist_local(punch_in)
        punch_out_local = to_ist_local(punch_out) if punch_out else None

        # Parse settings times for Shift:
        effective_date_0530 = date(2026, 9, 5)
        punch_date = punch_in_local.date()

        start_h, start_m, start_s = 9, 0, 0
        end_h, end_m, end_s = 17, 30, 0
        late_h, late_m, late_s = 9, 30, 0

        if worker and getattr(worker, 'shift_start', None) and getattr(worker, 'shift_end', None):
            try:
                s_parts = [int(p) for p in worker.shift_start.split(':')]
                e_parts = [int(p) for p in worker.shift_end.split(':')]
                start_h, start_m = s_parts[0], s_parts[1]
                start_s = s_parts[2] if len(s_parts) > 2 else 0
                end_h, end_m = e_parts[0], e_parts[1]
                end_s = e_parts[2] if len(e_parts) > 2 else 0
                # Late threshold = shift start + 30 mins
                late_time = (datetime(2000, 1, 1, start_h, start_m, start_s) + timedelta(minutes=30)).time()
                late_h, late_m, late_s = late_time.hour, late_time.minute, late_time.second
            except Exception:
                pass
        elif punch_date < effective_date_0530:
            start_h, start_m, start_s = 9, 30, 0
            end_h, end_m, end_s = 18, 0, 0
            late_h, late_m, late_s = 10, 0, 0
        else:
            try:
                start_h, start_m, start_s = map(int, (settings.default_shift_start or '09:00:00').split(':'))
                end_h, end_m, end_s = map(int, (settings.default_shift_end or '17:30:00').split(':'))
            except Exception:
                start_h, start_m, start_s = 9, 0, 0
                end_h, end_m, end_s = 17, 30, 0

            try:
                late_h, late_m, late_s = map(int, (getattr(settings, 'present_window_end', None) or '09:30:00').split(':'))
            except Exception:
                late_h, late_m, late_s = 9, 30, 0

        try:
            half_day_h, half_day_m, half_day_s = map(int, (settings.half_day_start or '13:00:00').split(':'))
        except Exception:
            half_day_h, half_day_m, half_day_s = 13, 0, 0
            
        shift_start = punch_in_local.replace(hour=start_h, minute=start_m, second=start_s)
        shift_end = punch_in_local.replace(hour=end_h, minute=end_m, second=end_s)
        late_threshold = punch_in_local.replace(hour=late_h, minute=late_m, second=late_s)
        half_day_threshold = punch_in_local.replace(hour=half_day_h, minute=half_day_m, second=half_day_s)
        
        late_minutes = 0
        if punch_in_local > late_threshold:
            late_minutes = int((punch_in_local - shift_start).total_seconds() / 60)
            
        # Business Rule:
        # Punch-in > 1:00 PM (13:00) -> Half Day
        # Punch-in > 09:30 AM -> Late (30 mins relaxation after 09:00 AM shift start)
        # Punch-in <= 09:30 AM -> Present
        if punch_in_local > half_day_threshold:
            status = "Half Day"
        elif punch_in_local > late_threshold:
            status = "Late"
        else:
            status = "Present"
            
        result = {
            "late_minutes": late_minutes,
            "status": status,
            "net_working_hours": 0.0,
            "ot_hours": 0.0,
            "early_exit_minutes": 0
        }
        
        if punch_out_local:
            # Effective punch-in for working hours calculation starts at shift_start if worker punched in early
            effective_punch_in = max(punch_in_local, shift_start)
            total_seconds = (punch_out_local - effective_punch_in).total_seconds()
            
            # Deduct 30 mins (0.5 hours) lunch break if worker was present between 01:00 PM and 01:30 PM
            lunch_start = punch_in_local.replace(hour=13, minute=0, second=0)
            lunch_end = punch_in_local.replace(hour=13, minute=30, second=0)
            if effective_punch_in <= lunch_start and punch_out_local >= lunch_end:
                total_seconds -= 1800 # 30 mins in seconds
                
            result["net_working_hours"] = max(0.0, round(total_seconds / 3600.0, 2))
            
            # Re-evaluate status based on total worked hours
            shift_length_hours = (shift_end - shift_start).total_seconds() / 3600.0
            if shift_length_hours <= 0:
                shift_length_hours = 9.0
                
            if result["net_working_hours"] < (shift_length_hours / 2):
                result["status"] = "Absent"
            elif result["net_working_hours"] < (shift_length_hours - 1.0) and result["status"] != "Absent":
                result["status"] = "Half Day"
            
            if punch_out_local < shift_end:
                result["early_exit_minutes"] = int((shift_end - punch_out_local).total_seconds() / 60)
            
            if settings.enable_ot and punch_out_local > shift_end:
                ot_start = max(shift_end, punch_in_local)
                if punch_out_local > ot_start:
                    ot_seconds = (punch_out_local - ot_start).total_seconds()
                    # Minimum 30 mins (6:30 PM threshold)
                    min_seconds = (settings.min_ot_minutes or 30) * 60
                    if ot_seconds >= min_seconds:
                        ot_hrs = round(ot_seconds / 3600.0, 1)
                        result["ot_hours"] = min(ot_hrs, float(settings.max_ot_hours or 12))
                    
        return result

class PayrollSyncEngine:
    @staticmethod
    def sync_daily_attendance(db: Session, attendance: Attendance, salary_profile: SalaryProfile):
        from app.models.payroll import PayrollRecord
        import calendar

        month_str = attendance.date.strftime("%Y-%m") if hasattr(attendance.date, 'strftime') else str(attendance.date)[:7]
        try:
            year_num, month_num = map(int, month_str.split("-"))
            _, days_in_month = calendar.monthrange(year_num, month_num)
        except:
            days_in_month = 30

        base_monthly = (salary_profile.monthly_salary if (salary_profile and salary_profile.monthly_salary) else 20000.0)
        daily_rate = base_monthly / 30.0
        hourly_rate = daily_rate / 8.0
        sunday_hourly_rate = hourly_rate

        payroll_record = db.query(PayrollRecord).filter(
            PayrollRecord.worker_id == attendance.worker_id,
            PayrollRecord.month == month_str
        ).first()
        
        if not payroll_record:
            payroll_record = PayrollRecord(
                worker_id=attendance.worker_id,
                month=month_str,
                base_salary=base_monthly,
                status="draft"
            )
            db.add(payroll_record)
            
        try:
            year_num, month_num = map(int, month_str.split("-"))
            start_date = date(year_num, month_num, 1)
            end_date = date(year_num, month_num, days_in_month)
            all_month_attendances = db.query(Attendance).filter(
                Attendance.worker_id == attendance.worker_id,
                Attendance.date >= start_date,
                Attendance.date <= end_date
            ).all()
        except Exception as e:
            # Fallback to loading all records and filtering in Python if parsing fails
            all_month_attendances = db.query(Attendance).filter(
                Attendance.worker_id == attendance.worker_id
            ).all()
            all_month_attendances = [
                att for att in all_month_attendances 
                if (att.date.strftime("%Y-%m") if hasattr(att.date, 'strftime') else str(att.date)[:7]) == month_str
            ]
        
        from app.models.holiday import Holiday
        holidays_db = db.query(Holiday).filter(
            Holiday.date >= start_date,
            Holiday.date <= end_date
        ).all()
        holiday_dates = {h.date for h in holidays_db}

        attendance_map = {att.date: att for att in all_month_attendances}

        present = 0.0; absent = 0.0; half = 0.0; late = 0
        leave_count = 0.0; sunday_count = 0.0; holiday_count = 0.0
        sunday_work_count = 0; holiday_work_count = 0
        total_ot = 0.0; total_hours = 0.0; sunday_hours = 0.0
        total_ot_earned = 0.0; total_sunday_earned = 0.0

        curr = start_date
        while curr <= end_date:
            att = attendance_map.get(curr)
            is_sun = (curr.weekday() == 6)
            is_hol = (curr in holiday_dates)

            if att:
                s = (att.status or "").lower()
                worked_hrs = att.net_working_hours or 0.0
                ot_hrs = att.ot_hours or 0.0

                total_hours += worked_hrs
                total_ot += ot_hrs

                if att.late_minutes and att.late_minutes > 0:
                    late += 1

                if (is_sun or is_hol or s in ["sunday work", "festival work", "holiday work"]) and (s in ["present", "half day", "sunday work", "holiday work", "festival work"] or worked_hrs > 0):
                    if is_hol or s in ["festival work", "holiday work"]: holiday_work_count += 1
                    if is_sun or s == "sunday work": sunday_work_count += 1
                    sunday_hours += worked_hrs
                    total_sunday_earned += worked_hrs * sunday_hourly_rate
                    if s == "half day": half += 0.5
                    else: present += 1.0
                else:
                    if s == "present": present += 1.0
                    elif s == "absent": absent += 1.0
                    elif s == "half day": half += 1.0
                    elif "leave" in s: leave_count += 1.0
                    elif "holiday" in s: holiday_count += 1.0
                    elif is_sun or s == "sunday": sunday_count += 1.0
                    elif curr <= date.today(): absent += 1.0

                total_ot_earned += ot_hrs * hourly_rate
            else:
                if is_hol:
                    holiday_count += 1.0
                elif is_sun:
                    sunday_count += 1.0
                elif curr <= date.today():
                    absent += 1.0

            curr += timedelta(days=1)

        paid_days = present + (half * 0.5) + leave_count + holiday_count + sunday_count
        absent_days = max(0.0, days_in_month - paid_days)
        effective_paid_days = 30.0 if absent_days == 0 else min(30.0, paid_days)
        earned_base_salary = round(daily_rate * effective_paid_days, 2)

        payroll_record.days_present = int(present)
        payroll_record.days_absent = int(absent)
        payroll_record.half_days = int(half)
        payroll_record.late_count = late
        payroll_record.leave_days = int(leave_count + holiday_count)
        payroll_record.sunday_work = sunday_work_count
        payroll_record.holiday_work = holiday_work_count
        payroll_record.working_hours = total_hours
        payroll_record.ot_hours = total_ot
        payroll_record.net_working_days = paid_days

        payroll_record.base_salary = base_monthly
        payroll_record.ot_amount = total_ot_earned
        payroll_record.sunday_amount = total_sunday_earned
        payroll_record.final_salary = earned_base_salary + total_ot_earned + total_sunday_earned + (payroll_record.bonus_amount or 0.0) - (payroll_record.deductions or 0.0)

        db.commit()
