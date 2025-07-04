from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
from fpdf import FPDF
import os
import re
import math
#line 140 replace ngrok link everytime
app = Flask(__name__)
sessions = {}

# ETB mock user list
ETB_USERS = {
    "9650329636": "Rahul Sharma",
    "9899065257": "Priya Verma"
}

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    sender = request.values.get("From")
    incoming_msg = request.values.get("Body", "").strip().lower()
    media_filename = request.values.get("MediaFileName", "")
    media_url = request.values.get("MediaUrl0", "")
    resp = MessagingResponse()
    msg = resp.message()

    if sender not in sessions:
        sessions[sender] = {
            "step": "get_phone",
            "user_name": "",
            "user_type": "",
            "phone_number": "",
            "aadhar_uploaded": False,
            "salary_uploaded": False,
            "cibil_auth": False,
            "loan_amount": None,
            "emi": None,
            "consent_given": False
        }

    session = sessions[sender]

    # Reset logic
    if incoming_msg == "reset":
        sessions.pop(sender, None)
        new_resp = MessagingResponse()
        new_resp.message("🔄 Chat has been reset. Type 'loan' to begin again.")
        return Response(str(new_resp), mimetype="application/xml")

    # Phone input
    if session["step"] == "get_phone":
        msg.body("Please enter your 10-digit phone number to continue:")
        session["step"] = "check_phone"
        return Response(str(resp), mimetype="application/xml")

    if session["step"] == "check_phone":
        digits = re.sub(r"\D", "", incoming_msg)
        if len(digits) != 10:
            msg.body("❌ Invalid phone number. Please enter a 10-digit number.")
            return Response(str(resp), mimetype="application/xml")

        session["phone_number"] = digits
        if digits in ETB_USERS:
            session["user_type"] = "etb"
            session["user_name"] = ETB_USERS[digits]
            session["step"] = "get_loan_amount"
            msg.body(f"Welcome back, {session['user_name']}! How much would you like to borrow (in INR)?")
        else:
            session["user_type"] = "ntb"
            session["step"] = "get_name"
            msg.body("Thanks! What's your full name?")
        return Response(str(resp), mimetype="application/xml")

    if session["step"] == "get_name":
        session["user_name"] = incoming_msg.title()
        session["step"] = "upload_aadhar"
        msg.body("You're a new customer. Please upload your Aadhaar card (PDF or image).")
        return Response(str(resp), mimetype="application/xml")

    if session["step"] == "upload_aadhar":
        if media_url:
            session["aadhar_uploaded"] = True
            session["step"] = "ask_cibil"
            msg.body("✅ Aadhaar verified. Do you authorize us to collect your CIBIL score? Reply YES or NO.")
        else:
            msg.body("Please upload your Aadhaar file to continue.")
        return Response(str(resp), mimetype="application/xml")

    if session["step"] == "ask_cibil":
        if "yes" in incoming_msg:
            session["cibil_auth"] = True
            session["step"] = "upload_salary"
            msg.body("Thank you. Please upload your latest salary slip (PDF or image).")
        elif "no" in incoming_msg:
            msg.body("❌ Authorization declined. Cannot proceed without CIBIL score consent.")
            session["step"] = "end"
        else:
            msg.body("Please reply YES or NO.")
        return Response(str(resp), mimetype="application/xml")

    if session["step"] == "upload_salary":
        if media_url:
            session["salary_uploaded"] = True
            session["step"] = "get_loan_amount"
            msg.body("✅ Salary slip received. How much would you like to borrow (in INR)?")
        else:
            msg.body("Please upload your salary slip to continue.")
        return Response(str(resp), mimetype="application/xml")

    if session["step"] == "get_loan_amount":
        digits = re.sub(r"\D", "", incoming_msg)
        if not digits.isdigit():
            msg.body("❌ Please enter a valid numeric loan amount.")
            return Response(str(resp), mimetype="application/xml")

        amount = int(digits)
        session["loan_amount"] = amount
        session["emi"] = calculate_emi(amount, 0.105, 60)
        session["step"] = "get_consent"
        msg.body(f"💰 Loan Amount: ₹{amount:,}\n📅 Tenure: 60 months\n📈 Interest: 10.5%\n💳 EMI: ₹{session['emi']:,}/month\n\nDo you consent to proceed? (YES/NO)")
        return Response(str(resp), mimetype="application/xml")

    if session["step"] == "get_consent":
        if "yes" in incoming_msg:
            session["consent_given"] = True
            session["step"] = "confirm"
            msg.body("Reply CONFIRM to receive your loan summary PDF.")
        elif "no" in incoming_msg:
            session["step"] = "end"
            msg.body("❌ Understood. Let us know if you change your mind.")
        else:
            msg.body("Please reply YES or NO.")
        return Response(str(resp), mimetype="application/xml")

    if session["step"] == "confirm":
        if "confirm" in incoming_msg:
            filename = f"{sender.split(':')[-1]}_loan_summary.pdf"
            os.makedirs("static", exist_ok=True)
            generate_pdf(session["user_name"], session["loan_amount"], session["emi"], filename)

            # Replace this with actual ngrok URL eveyrtime
            media_link = f"https://0134-2406-b400-72-8847-14e3-a5a0-c3a0-11.ngrok-free.app/static/{filename}"

            msg.body("✅ Offer confirmed. Here's your PDF:")
            msg.media(media_link)
            session["step"] = "completed"
        else:
            msg.body("Please type CONFIRM to proceed.")
        return Response(str(resp), mimetype="application/xml")

    if session["step"] == "completed":
        msg.body("✅ You've already received your loan summary. Type 'reset' to start again.")
        return Response(str(resp), mimetype="application/xml")

    msg.body("❓ Unrecognized input. Please type 'reset' to restart.")
    return Response(str(resp), mimetype="application/xml")


def calculate_emi(principal, annual_rate, months):
    r = annual_rate / 12
    emi = (principal * r * (1 + r)**months) / ((1 + r)**months - 1)
    return math.ceil(emi)

def generate_pdf(name, amount, emi, filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Loan Offer Summary", ln=1, align="C")
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Name: {name}", ln=2)
    pdf.cell(200, 10, txt=f"Loan Amount: INR {amount:,}", ln=3)
    pdf.cell(200, 10, txt="Tenure: 60 months", ln=4)
    pdf.cell(200, 10, txt="Interest Rate: 10.5%", ln=5)
    pdf.cell(200, 10, txt=f"EMI: INR {emi:,}/month", ln=6)
    pdf.output(os.path.join("static", filename))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
