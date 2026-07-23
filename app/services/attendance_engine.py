import math
from datetime import datetime, timedelta, date, time
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
            
        distance = calculate_distance(lat, lng, settings.latitude, settings.longitude)
        
        if distance <= settings.geofence_radius:
            return True, "Inside geofence"
        else:
            return False, f"Outside geofence ({int(distance)}m > {settings.geofence_radius}m)"

class TimeEngine:
    @staticmethod
    def calculate_status(settings: AttendanceSettings, punch_in: datetime, punch_out: datetime = None) -> dict:
        # Parse settings times
        try:
            start_h, start_m, start_s = map(int, settings.default_shift_start.split(':'))
            end_h, end_m, end_s = map(int, settings.default_shift_end.split(':'))
            half_day_h, half_day_m, half_day_s = map(int, settings.half_day_start.split(':'))
        except:
            start_h, start_m, start_s = 9, 0, 0
            end_h, end_m, end_s = 18, 0, 0
            half_day_h, half_day_m, half_day_s = 10, 0, 0
            
        shift_start = punch_in.replace(hour=start_h, minute=start_m, second=start_s)
        shift_end = punch_in.replace(hour=end_h, minute=end_m, second=end_s)
        half_day_time = punch_in.replace(hour=half_day_h, minute=half_day_m, second=half_day_s)
        
        late_minutes = 0
        if punch_in > shift_start:
            late_minutes = int((punch_in - shift_start).total_seconds() / 60)
            
        status = "Present"
        if punch_in > half_day_time:
            status = "Half Day"
            
        result = {
            "late_minutes": late_minutes,
            "status": status,
            "net_working_hours": 0.0,
            "ot_hours": 0.0,
            "early_exit_minutes": 0
        }
        
        if punch_out:
            total_seconds = (punch_out - punch_in).total_seconds()
            
            # Deduct 30 mins (0.5 hours) lunch break if worker was present between 01:00 PM and 01:30 PM
            lunch_start = punch_in.replace(hour=13, minute=0, second=0)
            lunch_end = punch_in.replace(hour=13, minute=30, second=0)
            if punch_in <= lunch_start and punch_out >= lunch_end:
                total_seconds -= 1800 # 30 mins in seconds
                
            result["net_working_hours"] = round(total_seconds / 3600.0, 2)
            
            # Re-evaluate status based on total worked hours
            shift_length_hours = (shift_end - shift_start).total_seconds() / 3600.0
            if shift_length_hours <= 0:
                shift_length_hours = 9.0
                
            if result["net_working_hours"] < (shift_length_hours / 2):
                result["status"] = "Absent"
            elif result["net_working_hours"] < (shift_length_hours - 1.0) and result["status"] != "Absent":
                result["status"] = "Half Day"
            
            if punch_out < shift_end:
                result["early_exit_minutes"] = int((shift_end - punch_out).total_seconds() / 60)
            
            if settings.enable_ot and punch_out > shift_end:
                ot_seconds = (punch_out - shift_end).total_seconds()
                if ot_seconds >= (settings.min_ot_minutes * 60):
                    ot_hrs = round(ot_seconds / 3600.0, 2)
                    result["ot_hours"] = min(ot_hrs, settings.max_ot_hours)
                    
        return result

class PayrollSyncEngine:
    @staticmethod
    def sync_daily_attendance(db: Session, attendance: Attendance, salary_profile: SalaryProfile):
        if not salary_profile:
            return
            
        # Example sync: Update a PayrollRecord or similar
        # Since Payroll module is assumed to process monthly, we can just aggregate or create a daily record
        from app.models.payroll import PayrollRecord
        
        # Check if monthly record exists for this worker
        month_str = attendance.date.strftime("%Y-%m")
        payroll_record = db.query(PayrollRecord).filter(
            PayrollRecord.worker_id == attendance.worker_id,
            PayrollRecord.month == month_str
        ).first()
        
        if not payroll_record:
            payroll_record = PayrollRecord(
                worker_id=attendance.worker_id,
                month=month_str,
                base_salary=salary_profile.monthly_salary or 0,
                status="draft"
            )
            db.add(payroll_record)
            
        all_month_attendances = db.query(Attendance).filter(
            Attendance.worker_id == attendance.worker_id,
            Attendance.date.like(f"{month_str}-%")
        ).all()
        
        present = 0; absent = 0; half = 0; late = 0;
        leave = 0; sunday = 0; holiday = 0
        total_ot = 0.0; total_hours = 0.0
        
        for att in all_month_attendances:
            s = (att.status or "").lower()
            if s == "present": present += 1
            elif s == "absent": absent += 1
            elif s == "half day": half += 1
            elif s == "leave" or s == "paid leave": leave += 1
            
            if att.late_minutes and att.late_minutes > 0: late += 1
            if att.is_sunday: sunday += 1
            
            total_ot += (att.ot_hours or 0.0)
            total_hours += (att.net_working_hours or 0.0)
            
        payroll_record.days_present = present
        payroll_record.days_absent = absent
        payroll_record.half_days = half
        payroll_record.late_count = late
        payroll_record.leave_days = leave
        payroll_record.sunday_work = sunday
        payroll_record.holiday_work = holiday
        payroll_record.working_hours = total_hours
        payroll_record.ot_hours = total_ot
        payroll_record.net_working_days = present + (half * 0.5) + leave
        
        daily_rate = (payroll_record.base_salary / 30) if payroll_record.base_salary else (salary_profile.daily_wage or 0.0)
        earned = (payroll_record.net_working_days or 0.0) * daily_rate
        ot_earned = total_ot * (salary_profile.ot_rate_per_hour or 0.0)
        
        payroll_record.ot_amount = ot_earned
        payroll_record.final_salary = earned + ot_earned - (payroll_record.deductions or 0.0)
        
        db.commit()
