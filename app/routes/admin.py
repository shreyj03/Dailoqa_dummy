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
            "phone_number": s.phone_number,
            "user_name": s.user_name,
            "user_type": s.user_type,
            "loan_amount": s.loan_amount,
            "emi": s.emi,
            "step": s.step,
            "salary_amount": s.salary_amount,
            "consent_given": s.consent_given,
            "aadhar_uploaded": s.aadhar_uploaded,
            "tenure": s.tenure,
            "salary_uploaded": s.salary_uploaded,
            "cibil_auth": s.cibil_auth
            
        }
        for s in sessions
    ]
