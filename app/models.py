from sqlalchemy import Column, Integer, String, Boolean, Float, Text
from app.database import Base

class LoanSession(Base):
    __tablename__ = "loan_sessions"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, index=True)
    user_name = Column(String)
    user_type = Column(String)
    aadhar_number = Column(String)
    salary_amount = Column(Integer, nullable=True)
    tenure = Column(Integer, default=60)  # Default tenure in months
    cibil_score = Column(Integer)
    loan_amount = Column(Integer)
    emi = Column(Float)
    consent_given = Column(Boolean, default=False)
    message_history = Column(Text, nullable=True)
    step = Column(String)

