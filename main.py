from datetime import datetime, date
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.database import Base, engine, get_db, SessionLocal
from app.models import Employee, Attendance, LeaveRequest
from app.schemas import EmployeeCreate, EmployeeUpdate, EmployeeOut, LeaveCreate, LeaveReview, LeaveOut
from app.security import hash_password, verify_password, create_access_token, get_current_user, require_admin
from app.config import settings

app = FastAPI(title="Employee Attendance & Leave Management API", version="1.0.0")

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = db.scalar(select(Employee).where(Employee.email == settings.admin_email.lower()))
        if not admin:
            db.add(Employee(full_name="System Administrator", email=settings.admin_email.lower(),
                            password_hash=hash_password(settings.admin_password), role="admin"))
            db.commit()
    finally:
        db.close()

@app.get("/")
def root():
    return {"message": "Employee Attendance & Leave Management API", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(Employee).where(Employee.email == form.username.lower()))
    if not user or not user.is_active or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return {"access_token": create_access_token(user), "token_type": "bearer",
            "user": {"id": user.id, "name": user.full_name, "email": user.email, "role": user.role}}

@app.get("/auth/me", response_model=EmployeeOut)
def me(user: Employee = Depends(get_current_user)):
    return user

@app.post("/employees", response_model=EmployeeOut, status_code=201)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db), admin: Employee = Depends(require_admin)):
    email = payload.email.strip().lower()
    if db.scalar(select(Employee).where(Employee.email == email)):
        raise HTTPException(status_code=409, detail="Email already exists")
    employee = Employee(full_name=payload.full_name, email=email, password_hash=hash_password(payload.password), department=payload.department)
    db.add(employee); db.commit(); db.refresh(employee)
    return employee

@app.get("/employees", response_model=list[EmployeeOut])
def list_employees(q: str | None = None, active: bool | None = None,
                   page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                   db: Session = Depends(get_db), admin: Employee = Depends(require_admin)):
    stmt = select(Employee).where(Employee.role == "employee")
    if q: stmt = stmt.where(Employee.full_name.ilike(f"%{q}%") | Employee.email.ilike(f"%{q}%"))
    if active is not None: stmt = stmt.where(Employee.is_active == active)
    return list(db.scalars(stmt.order_by(Employee.full_name).offset((page-1)*page_size).limit(page_size)).all())

@app.patch("/employees/{employee_id}", response_model=EmployeeOut)
def update_employee(employee_id: int, payload: EmployeeUpdate, db: Session = Depends(get_db), admin: Employee = Depends(require_admin)):
    employee = db.get(Employee, employee_id)
    if not employee or employee.role != "employee": raise HTTPException(status_code=404, detail="Employee not found")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(employee, key, value)
    db.commit(); db.refresh(employee)
    return employee

@app.post("/attendance/check-in")
def check_in(db: Session = Depends(get_db), user: Employee = Depends(get_current_user)):
    today = date.today()
    record = db.scalar(select(Attendance).where(Attendance.employee_id == user.id, Attendance.attendance_date == today))
    if record: raise HTTPException(status_code=409, detail="Already checked in today")
    record = Attendance(employee_id=user.id, attendance_date=today, check_in=datetime.now())
    db.add(record); db.commit(); db.refresh(record)
    return {"message": "Checked in", "attendance_id": record.id, "check_in": record.check_in}

@app.post("/attendance/check-out")
def check_out(db: Session = Depends(get_db), user: Employee = Depends(get_current_user)):
    record = db.scalar(select(Attendance).where(Attendance.employee_id == user.id, Attendance.attendance_date == date.today()))
    if not record or not record.check_in: raise HTTPException(status_code=400, detail="Check in first")
    if record.check_out: raise HTTPException(status_code=409, detail="Already checked out")
    record.check_out = datetime.now(); db.commit()
    return {"message": "Checked out", "check_out": record.check_out,
            "working_hours": round((record.check_out-record.check_in).total_seconds()/3600, 2)}

@app.get("/attendance/me")
def my_attendance(start_date: date | None = None, end_date: date | None = None,
                  page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                  db: Session = Depends(get_db), user: Employee = Depends(get_current_user)):
    stmt = select(Attendance).where(Attendance.employee_id == user.id)
    if start_date: stmt = stmt.where(Attendance.attendance_date >= start_date)
    if end_date: stmt = stmt.where(Attendance.attendance_date <= end_date)
    rows = db.scalars(stmt.order_by(Attendance.attendance_date.desc()).offset((page-1)*page_size).limit(page_size)).all()
    return [{"id": r.id, "date": r.attendance_date, "check_in": r.check_in, "check_out": r.check_out,
             "working_hours": round((r.check_out-r.check_in).total_seconds()/3600, 2) if r.check_in and r.check_out else None} for r in rows]

@app.get("/attendance")
def all_attendance(start_date: date | None = None, end_date: date | None = None, employee_id: int | None = None,
                   page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                   db: Session = Depends(get_db), admin: Employee = Depends(require_admin)):
    stmt = select(Attendance)
    if start_date: stmt = stmt.where(Attendance.attendance_date >= start_date)
    if end_date: stmt = stmt.where(Attendance.attendance_date <= end_date)
    if employee_id: stmt = stmt.where(Attendance.employee_id == employee_id)
    rows = db.scalars(stmt.order_by(Attendance.attendance_date.desc()).offset((page-1)*page_size).limit(page_size)).all()
    return [{"id": r.id, "employee_id": r.employee_id, "date": r.attendance_date, "check_in": r.check_in,
             "check_out": r.check_out, "working_hours": round((r.check_out-r.check_in).total_seconds()/3600, 2) if r.check_in and r.check_out else None} for r in rows]

@app.post("/leaves", response_model=LeaveOut, status_code=201)
def request_leave(payload: LeaveCreate, db: Session = Depends(get_db), user: Employee = Depends(get_current_user)):
    leave = LeaveRequest(employee_id=user.id, **payload.model_dump())
    db.add(leave); db.commit(); db.refresh(leave)
    return leave

@app.get("/leaves/me", response_model=list[LeaveOut])
def my_leaves(status: str | None = None, db: Session = Depends(get_db), user: Employee = Depends(get_current_user)):
    stmt = select(LeaveRequest).where(LeaveRequest.employee_id == user.id)
    if status: stmt = stmt.where(LeaveRequest.status == status.lower())
    return list(db.scalars(stmt.order_by(LeaveRequest.created_at.desc())).all())

@app.get("/leaves", response_model=list[LeaveOut])
def all_leaves(status: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
               db: Session = Depends(get_db), admin: Employee = Depends(require_admin)):
    stmt = select(LeaveRequest)
    if status: stmt = stmt.where(LeaveRequest.status == status.lower())
    return list(db.scalars(stmt.order_by(LeaveRequest.created_at.desc()).offset((page-1)*page_size).limit(page_size)).all())

@app.patch("/leaves/{leave_id}/review", response_model=LeaveOut)
def review_leave(leave_id: int, payload: LeaveReview, db: Session = Depends(get_db), admin: Employee = Depends(require_admin)):
    leave = db.get(LeaveRequest, leave_id)
    if not leave: raise HTTPException(status_code=404, detail="Leave request not found")
    if leave.status != "pending": raise HTTPException(status_code=409, detail="Only pending requests can be reviewed")
    leave.status = payload.status; leave.admin_comment = payload.admin_comment
    leave.reviewed_by = admin.id; leave.reviewed_at = datetime.utcnow()
    db.commit(); db.refresh(leave)
    return leave

@app.get("/dashboard/admin")
def admin_dashboard(db: Session = Depends(get_db), admin: Employee = Depends(require_admin)):
    today = date.today()
    total = db.scalar(select(func.count(Employee.id)).where(Employee.role == "employee", Employee.is_active == True)) or 0
    present = db.scalar(select(func.count(Attendance.id)).where(Attendance.attendance_date == today)) or 0
    pending = db.scalar(select(func.count(LeaveRequest.id)).where(LeaveRequest.status == "pending")) or 0
    return {"date": today, "total_employees": total, "present_employees": present,
            "absent_employees": max(total-present, 0), "pending_leave_requests": pending}

@app.get("/dashboard/employee")
def employee_dashboard(db: Session = Depends(get_db), user: Employee = Depends(get_current_user)):
    today = date.today()
    row = db.scalar(select(Attendance).where(Attendance.employee_id == user.id, Attendance.attendance_date == today))
    pending = db.scalar(select(func.count(LeaveRequest.id)).where(LeaveRequest.employee_id == user.id, LeaveRequest.status == "pending")) or 0
    hours = round((row.check_out-row.check_in).total_seconds()/3600, 2) if row and row.check_in and row.check_out else None
    return {"date": today, "attendance_status": "not_checked_in" if not row else ("checked_out" if row.check_out else "checked_in"),
            "check_in": row.check_in if row else None, "check_out": row.check_out if row else None,
            "working_hours": hours, "pending_leave_requests": pending}
