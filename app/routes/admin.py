# app/routes/admin.py
from fastapi import APIRouter
from app.database import SessionLocal
from app.models import LoanSession

router = APIRouter()

@router.get("/admin/sessions")
def get_all_sessions():
    db = SessionLocal()
    sessions = db.query(LoanSession).all()
    db.close()
    return [
        {
            "id": s.id,
            "Phone Number": s.phone_number,
            "User Name": s.user_name,
            "Loan Amount": s.loan_amount,
            "EMI": s.emi,
            "Step": s.step,
            "Salary Amount": s.salary_amount,
            "consent_given": s.consent_given,
            "Aadhar Number": s.aadhar_number,
            "Tenure": s.tenure,
            "CIBIL Score": s.cibil_score
            
        }
        for s in sessions
    ]
