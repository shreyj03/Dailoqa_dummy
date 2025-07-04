
from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse

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
    media_url = request.values.get("MediaUrl0", "")
    resp = MessagingResponse()
    msg = resp.message()

    # Reset logic
    if incoming_msg == "reset":
        sessions.pop(sender, None)
        msg.body("Your session has been reset. Type 'gold loan' to start again.")
        return str(resp)

    # Initialize session if not present
    if sender not in sessions:
        sessions[sender] = {"step": "start", "data": {}}

    session = sessions[sender]

    # Start gold loan flow
    if "gold loan" in incoming_msg and session["step"] == "start":
        session["step"] = "get_phone"
        msg.body("Welcome to the Gold Loan service! Please enter your phone number to check your details.")
        return str(resp)

    # Phone number check and user type 
    if session["step"] == "get_phone":
        session["data"]["phone"] = incoming_msg
        if incoming_msg in ETB_USERS:
            session["step"] = "ask_gold_weight"
            session["data"]["name"] = ETB_USERS[incoming_msg]
            msg.body(f"Welcome back, {ETB_USERS[incoming_msg]}! Please tell me the weight of your gold in grams.")
        else:
            session["step"] = "get_name"
            msg.body("Looks like you're a new customer. What's your full name?")
        return str(resp)

    # NTB user flow
    if session["step"] == "get_name":
        session["data"]["name"] = incoming_msg
        session["step"] = "get_pan"
        msg.body("Got it. Please share your PAN number.")
        return str(resp)

    if session["step"] == "get_pan":
        session["data"]["pan"] = incoming_msg
        session["step"] = "ask_gold_photo"
        msg.body("Optional: Please upload a photo of the gold item. If you want to skip, type 'skip'.")
        return str(resp)

    if session["step"] == "ask_gold_photo":
        if incoming_msg == "skip" or media_url:
            session["step"] = "ask_gold_weight"
            msg.body("Please tell me the weight of your gold in grams.")
        else:
            msg.body("Please upload a photo of your gold or type 'skip' to proceed without it.")
        return str(resp)

    # Gold weight and loan offer
    if session["step"] == "ask_gold_weight":
        try:
            gold_weight = float(incoming_msg)
            loan_amount = gold_weight * 9600 * 0.75  # Assuming ₹9600 per gram and 75% LTV
            session["data"]["loan_amount"] = loan_amount
            session["step"] = "confirm_offer"
            msg.body(f"You are eligible for a loan of approximately ₹{loan_amount:,.0f}. Interest rate is 9% p.a. for a 12-month tenure. Do you want to proceed? (yes/no)")
        except ValueError:
            msg.body("Please enter a valid number for the gold weight.")
        return str(resp)

    # Confirm loan offer
    if session["step"] == "confirm_offer":
        if "yes" in incoming_msg:
            if session["data"]["phone"] not in ETB_USERS:
                session["step"] = "get_address"
                msg.body("Thanks. Please provide your address.")
            else:
                session["step"] = "schedule_mode"
                msg.body("Perfect! Do you want to schedule a pickup or visit a branch for gold verification? (pickup/branch)")
        else:
            msg.body("No worries. Let us know if you change your mind.")
            sessions.pop(sender)
        return str(resp)

    # NTB additional details
    # if session["step"] == "get_aadhaar":
    #     session["data"]["aadhaar"] = incoming_msg
    #     session["step"] = "get_address"
    #     msg.body("Thanks. Please provide your address.")
    #     return str(resp)

    if session["step"] == "get_address":
        session["data"]["address"] = incoming_msg
        session["step"] = "schedule_mode"
        msg.body("Almost done! Do you want to schedule a pickup or visit a branch for gold verification? (pickup/branch)")
        return str(resp)

    # Ask for mode (pickup or branch)
    if session["step"] == "schedule_mode":
        if incoming_msg in ["pickup", "branch"]:
            session["data"]["mode"] = incoming_msg
            session["step"] = "get_datetime"
            msg.body(f"When would you like to schedule your {incoming_msg}? Please provide date and time in this format: DD/MM/YYYY HH:MM")
        else:
            msg.body("Please reply with 'pickup' or 'branch'.")
        return str(resp)

    # Collect date and time
    if session["step"] == "get_datetime":
        session["data"]["datetime"] = incoming_msg
        session["step"] = "loan_confirmed"
        msg.body(f"Thank you! Your gold verification ({session['data']['mode']}) is scheduled for {incoming_msg}. "
                 "Once verified, we will confirm your loan and send the pledge receipt here. Funds will be credited the same day.")
        return str(resp)

    msg.body("Please type 'gold loan' to get started.")
    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
