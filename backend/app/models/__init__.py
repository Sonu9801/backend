from app.database import Base
from app.models.associations import vehicle_user_association, job_user_association
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.quality import QCRecord
from app.models.dispatch import DispatchRecord
from app.models.activity import ActivityEvent
from app.models.attendance import Attendance, AttendanceLog
from app.models.salary_profile import SalaryProfile
from app.models.oem_schedule import OEMSchedule

from app.models.attendance_settings import AttendanceSettings
from app.models.payroll import AdvanceRequest, PayrollRecord
from app.models.notification import Notification
from app.models.device import Device
from app.models.production_job import ProductionJob
from app.models.shift import Shift
from app.models.holiday import Holiday
from app.models.invoice import Invoice
from app.models.invoice_audit import InvoiceAudit
from app.models.job_photo import JobPhoto
from app.models.sales_invoice import SalesInvoice
from app.models.sales_invoice_audit import SalesInvoiceAudit

__all__ = [
    "Base",
    "vehicle_user_association",
    "job_user_association",
    "User",
    "Vehicle",
    "QCRecord",
    "DispatchRecord",
    "ActivityEvent",
    "Attendance",
    "AttendanceLog",
    "SalaryProfile",
    "OEMSchedule",
    "AttendanceSettings",
    "AdvanceRequest",
    "PayrollRecord",
    "Notification",
    "Device",
    "ProductionJob",
    "Shift",
    "Holiday",
    "Invoice",
    "InvoiceAudit",
    "JobPhoto",
    "SalesInvoice",
    "SalesInvoiceAudit",
]
