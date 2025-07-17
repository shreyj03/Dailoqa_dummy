from fpdf import FPDF
import os
from datetime import datetime

def generate_pdf(name, amount, emi, tenure, filename):
    pdf = FPDF()
    pdf.add_page()
    
    # Set margins
    pdf.set_margins(20, 20, 20)
    
    # Bank Header
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(0, 51, 102)  # Dark blue color
    pdf.cell(0, 10, txt="XYZ BANK", ln=1, align="C")
    
    # Bank tagline/address
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 5, txt="Registered Office: Mumbai | CIN: U65100MH1994PLC080618", ln=1, align="C")
    pdf.cell(0, 5, txt="www.xyzbank.com | Customer Care: 1800-XXX-XXXX", ln=1, align="C")
    
    # Add line separator
    pdf.ln(5)
    pdf.set_draw_color(0, 51, 102)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(10)
    
    # Document title
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 10, txt="LOAN SANCTION LETTER", ln=1, align="C")
    pdf.ln(5)
    
    # Reference details
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(0, 0, 0)
    current_date = datetime.now().strftime("%d/%m/%Y")
    loan_ref = f"XYZ{datetime.now().strftime('%Y%m%d')}{str(amount)[-4:]}"
    
    pdf.cell(0, 6, txt=f"Ref No: {loan_ref}", ln=1)
    pdf.cell(0, 6, txt=f"Date: {current_date}", ln=1)
    pdf.ln(5)
    
    # Customer details section
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 8, txt="CUSTOMER DETAILS", ln=1)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(3)
    
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, txt=f"Customer Name: {name}", ln=1)
    pdf.cell(0, 6, txt=f"Application Date: {current_date}", ln=1)
    pdf.ln(5)
    
    # Loan details section
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 8, txt="LOAN DETAILS", ln=1)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(3)
    
    # Create a table-like structure for loan details
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(0, 0, 0)
    
    # Calculate interest rate and total payable (example calculations)
    interest_rate = 12  # fixed rate
    total_payable = emi * tenure
    
    loan_details = [
        ("Loan Type:", "Personal Loan"),
        ("Principal Amount:", f"Rs. {amount:,}"),
        ("Interest Rate:", f"{interest_rate}% per annum"),
        ("Tenure:", f"{tenure} months"),
        ("EMI Amount:", f"Rs. {emi:,}"),
        ("Total Amount Payable:", f"Rs. {total_payable:,}")
    ]
    
    for label, value in loan_details:
        pdf.cell(60, 6, txt=label, ln=0)
        pdf.cell(0, 6, txt=value, ln=1)
    
    pdf.ln(5)
    
    # Terms and conditions
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 8, txt="TERMS AND CONDITIONS", ln=1)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(3)
    
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(0, 0, 0)
    
    terms = [
        "1. This loan is subject to the terms and conditions mentioned in the loan agreement.",
        "2. EMI payments must be made on or before the due date each month.",
        "3. Prepayment charges may apply as per bank's policy.",
        "4. Default in payment may result in penalty charges and legal action.",
        "5. The bank reserves the right to recall the loan at any time.",
        "6. Insurance coverage is mandatory for the loan tenure.",
        "7. All disputes are subject to Mumbai jurisdiction only."
    ]
    
    for term in terms:
        pdf.multi_cell(0, 5, txt=term)
        pdf.ln(1)
    
    pdf.ln(5)
    
    # Important notice
    pdf.set_font("Arial", "B", 10)
    pdf.set_text_color(204, 0, 0)  # Red color
    pdf.multi_cell(0, 5, txt="IMPORTANT: Please read all terms and conditions carefully before accepting this loan offer. Contact our customer service for any clarifications.")
    
    pdf.ln(10)
    
    # Signature section
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, txt="For XYZ Bank", ln=1)
    pdf.cell(0, 6, txt="Authorized Signatory", ln=1)
    pdf.cell(0, 6, txt="Branch Manager", ln=1)
    
    # Footer
    pdf.ln(10)
    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 4, txt="This is a computer-generated document and does not require a physical signature.", ln=1, align="C")
    pdf.cell(0, 4, txt="For queries, contact: customercare@xyzbank.com | 1800-XXX-XXXX", ln=1, align="C")
    
    # Save the PDF
    output_path = os.path.join("static", filename)
    pdf.output(output_path)
