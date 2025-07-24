import os
import json
import requests
from io import BytesIO
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
from dotenv import load_dotenv
import re
import pdfplumber

router = APIRouter()

load_dotenv()
ANTHROPIC_API_KEY= os.getenv("ANTHROPIC_API_KEY")

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

First, try to extract name and salary from uploaded documents. Only ask the user for these if not already extracted or the document uploaded is empty or unsuccessful.
Your job is to:
1. Reply appropriately abd be smart and informative and helpful.
2. Determine the next step (this is the flow, get_name, upload_aadhar, upload_salary, get_loan_amount, ask for tenure (in months), ask_cibil_score, get_consent, confirm, completed) You cant skip any step.
3. Set generate_pdf to true ONLY when the user has confirmed the loan and all information is collected and when you send the pdf let the customer know that this is the application preview and our loan officer will contact you within 2 business days to confirm your offer.
4. If available, extract `loan_amount` and `emi` as numbers.
5. dont directly tell them about the interest rate unless the person reaches the step where emi is calculated. do mention interest rate when emi is calculated.

When a user sends hi Greet them and you must explain our 3 financial Credit Card, EMI/Buy Now Pay Later and Personal Loan Ask: "Which would you like to explore?" remmeber we only do perosnal loan but need to offer these 3 products so if user selects credit card or emi direct them to personal loan. skip the explaining if user has already said personal loan.

Once you scan their aadhar, you must send a msg for them to confirm their aadhar details in this format 📄 Aadhar Verified!

We've successfully scanned your Aadhar details:

    Name: Rahul Sharma

    Aadhar Number: full aadhar number

    Address: full address from aadhar

Ask: To proceed for the next step.
dont skip this step

CIBIL Score Rules:
- If the user sends a message like "my CIBIL is 650", recognize this as a score input.
- If CIBIL score is ≤700: explain the following options in details with all the relative information available and dont reveal our 700 limit
  -Option 1 (shorter tenure): Shorten your loan tenure to half of original value and maintain credit card usage below 60%. (Loan: ₹<original_loan_amount>, Tenure: half of original, Interest nrate, EMI: ₹<emi1>)

🔹 Option 2 (reduced amount): Reduce your loan amount by 25% to maintain safer debt levels. (Loan: ₹<reduced_loan_amount>, Tenure: what customer wanted, Interest rate, EMI: ₹<emi2>)
   - Ask user which option they wan to proceed.
- If CIBIL score >700, proceed normally to get loan amount and tenure.


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
  "aadhar_number": "<extracted aadhar number>"
  "cibil_score": optional number,
}}
"""
    try:
        result = llm.invoke([HumanMessage(content=prompt)])
        print("Claude LLM raw output:", repr(result.content))  # See what it’s returning
        return result.content
    except Exception as e:
        print("LLM error:", e)
        return '{"response": "Sorry, I could not understand that.", "next_step": "auto", "generate_pdf": false}'
    

def extract_text_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        file_bytes = BytesIO(response.content)

        if "pdf" in content_type:
            with pdfplumber.open(file_bytes) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages)
        elif "image" in content_type:
            image = Image.open(file_bytes)
            return pytesseract.image_to_string(image)
        else:
            return f"Unsupported file type: {content_type}"
    except Exception as e:
        return f"OCR extraction failed: {str(e)}"

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
        "aadhar_number": parsed.get("aadhar_number"),
        "cibil_score": parsed.get("cibil_score"),
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
        # Delete all existing sessions for this phone number when reset - hard reset
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
                aadhar_number=False,
                salary_amount=None,
                cibil_score=None,
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

        result = graph.invoke({"messages": message_history})
        reply = result['messages'][-1]['content']
        msg.body(reply)

        session.step = result.get("next_step", "auto")
        session.loan_amount = result.get("loan_amount", session.loan_amount)
        session.emi = result.get("emi", session.emi)
        session.user_name = result.get("user_name", session.user_name)
        session.tenure = result.get("tenure", session.tenure)
        session.salary_amount = result.get("salary_amount", session.salary_amount)
        session.cibil_score = result.get("cibil_score", session.cibil_score)
        session.aadhar_number = result.get("aadhar_number", session.aadhar_number)
        session.consent_given = (session.step == "get_consent")
        session.message_history = json.dumps(result.get("messages", message_history))

        if result.get("generate_pdf"):
            filename = f"{phone_number}_loan_application_preview.pdf"
            generate_pdf(session.user_name or "Customer", session.loan_amount or 0, session.emi or 0, session.tenure or 60, filename)
            media_link = f"https://da2ca1da3429.ngrok-free.app/static/{filename}"
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
