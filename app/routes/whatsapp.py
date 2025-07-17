# app/routes/whatsapp.py
import os
import json
import requests
import pytesseract
from PIL import Image
from fastapi import APIRouter, Form
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import LoanSession
from app.utils import generate_pdf
from langgraph.graph import StateGraph, END
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
import re
import pdfplumber  # 🔄 Replaced fitz with pdfplumber for PDF OCR

router = APIRouter()

# ✅ Inject Anthropic API key directly (not using .env)
os.environ["ANTHROPIC_API_KEY"] = "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"

# ✅ LLM via Anthropic Claude (LangChain wrapper)
llm = ChatAnthropic(
    model="claude-3-5-sonnet-20240620",
    temperature=0,
    max_tokens=1024,
    max_retries=2
)

def call_llm(messages):
    prompt = f"""
You are a helpful but concise AI loan assistant for an indian bank. Keep your replies under 30 words and use appropriate emojis to sound friendly and simple. we have a standard non negotiable intetest rate of 12% for all loans.

Here is the full chat history:
{json.dumps(messages, indent=2)}

First, try to extract name and salary from uploaded documents (if any). Only ask the user for these if not already extracted.

Your job is to:
1. Reply appropriately.
2. Determine the next step (e.g., get_name, upload_aadhar, ask_cibil, upload_salary, get_loan_amount, ask for tenure (in months) get_consent, confirm, completed).
3. Set generate_pdf to true ONLY when the user has confirmed the loan and all information is collected.
4. If available, extract `loan_amount` and `emi` as numbers.

Respond ONLY in this JSON format:
{{
  "response": "<bot reply>",
  "next_step": "<step>",
  "generate_pdf": true/false,
  "loan_amount": optional number,
  "emi": optional number
  "user_name": "<extracted name>",
  "tenure": optional number,
  "salary_amount": optional number
}}
"""
    try:
        result = llm.invoke([HumanMessage(content=prompt)])
        return result.content
    except Exception as e:
        print("LLM error:", e)
        return '{"response": "Sorry, I could not understand that.", "next_step": "auto", "generate_pdf": false}'

def extract_text_from_url(url):
    try:
        from io import BytesIO
        response = requests.get(url)
        if url.lower().endswith(".pdf"):
            with pdfplumber.open(BytesIO(response.content)) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        else:
            image = Image.open(BytesIO(response.content))
            text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        print("OCR error:", e)
        return ""

def extract_name_from_text(text):
    try:
        match = re.search(r'Name\s*[:\-]?\s*([A-Z][a-z]+\s[A-Z][a-z]+)', text)
        if match:
            return match.group(1)
    except:
        pass
    return None

def extract_salary_from_text(text):
    try:
        match = re.search(r'Salary\s*[:\-]?\s*(\d{4,6})', text)
        if match:
            return int(match.group(1))
    except:
        pass
    return None

def decide_step_and_respond(state):
    messages = state.get("messages", [])
    raw = call_llm(messages)
    parsed = json.loads(raw)
    messages.append({"role": "assistant", "content": parsed['response']})
    print("\n--- Chat History ---")
    for m in messages:
        print(f"{m['role']}: {m['content']}")
    print("---------------------\n")
    return {
        "messages": messages,
        "next_step": parsed.get("next_step", "auto"),
        "generate_pdf": parsed.get("generate_pdf", False),
        "loan_amount": parsed.get("loan_amount"),
        "tenure": parsed.get("tenure", 60),  # Default to 60 months if not provided
        "user_name": parsed.get("user_name"),
        "salary_amount": parsed.get("salary_amount"),
        "emi": parsed.get("emi")
    }

graph_builder = StateGraph(dict)
graph_builder.add_node("decide_step", decide_step_and_respond)
graph_builder.set_entry_point("decide_step")
graph_builder.add_edge("decide_step", END)
graph = graph_builder.compile()

@router.post("/whatsapp")
async def whatsapp_reply(
    Body: str = Form(...),
    From: str = Form(...),
    MediaFileName: str = Form(default=""),
    MediaUrl0: str = Form(default="")
):
    db: Session = SessionLocal()
    phone_number = From.split(":")[-1]
    incoming_msg = Body.strip()
    resp = MessagingResponse()
    msg = resp.message()

    if incoming_msg.lower() == "reset":
        # Delete all existing sessions for this phone number when reset
        db.query(LoanSession).filter(LoanSession.phone_number == phone_number).delete()
        db.commit()
        print(f"Resetting chat for {phone_number}")
        msg.body("Chat has been reset. Type 'loan' to begin again.")
        return Response(content=str(resp), media_type="application/xml")

    try:
        session = db.query(LoanSession).filter(LoanSession.phone_number == phone_number).first()

        if not session:
            # Create new session only if none exists
            session = LoanSession(
                phone_number=phone_number,
                user_name=None,
                user_type=None,
                aadhar_uploaded=False,
                salary_uploaded=False,
                salary_amount=None,
                loan_amount=None,
                tenure=60,
                emi=None,
                step="auto",
                message_history="[]"
            )
            db.add(session)
            db.flush()

        message_history = json.loads(session.message_history) if session.message_history else []
        message_history.append({"role": "user", "content": incoming_msg})

        if MediaUrl0:
            print(MediaUrl0, MediaFileName)
            extracted_text = extract_text_from_url(MediaUrl0)
            message_history.append({"role": "user", "content": f"Uploaded document text: {extracted_text}"})

            if "Aadhar" in MediaFileName.lower():
                extracted_name = extract_name_from_text(extracted_text)
                if extracted_name:
                    session.user_name = extracted_name

            if "salary" in MediaFileName.lower():
                extracted_salary = extract_salary_from_text(extracted_text)
                if extracted_salary:
                    session.salary_amount = extracted_salary
                    if not session.loan_amount:
                        session.loan_amount = extracted_salary * 10

        result = graph.invoke({"messages": message_history})
        reply = result['messages'][-1]['content']
        msg.body(reply)

        session.step = result.get("next_step", "auto")
        session.loan_amount = result.get("loan_amount", session.loan_amount)
        session.emi = result.get("emi", session.emi)
        session.user_name = result.get("user_name", session.user_name)
        session.tenure = result.get("tenure", session.tenure)
        session.salary_amount = result.get("salary_amount", session.salary_amount)
        session.consent_given = (session.step == "get_consent")
        # session.salary_uploaded = bool(session.salary_amount)
        session.message_history = json.dumps(result.get("messages", message_history))

        if result.get("generate_pdf"):
            filename = f"{phone_number}_loan_summary.pdf"
            generate_pdf(session.user_name or "Customer", session.loan_amount or 0, session.emi or 0, session.tenure or 60, filename)
            media_link = f"https://53a03b0aae9b.ngrok-free.app/static/{filename}"
            msg.media(media_link)
            session.step = "completed"

        db.commit()

    except Exception as e:
        db.rollback()
        print("LangGraph bot error:", e)
        msg.body("⚠️ Something went wrong. Please try again or type 'reset'.")

    finally:
        db.close()

    return Response(content=str(resp), media_type="application/xml")
