import pdfplumber
import json
import os
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


# -----------------------------
# GROQ CLIENT
# -----------------------------
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

MODEL = "llama-3.3-70b-versatile"


# -----------------------------
# PDF TEXT EXTRACTION
# -----------------------------
def extract_pdf_text(pdf_path):

    text = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"

    return text


# -----------------------------
# CLEAN LLM JSON
# -----------------------------
def clean_json(text):

    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:
        text = text[start:end+1]

    return text.strip()


# -----------------------------
# VALIDATE PA / UTR RULES
# -----------------------------
def validate_pa_utr(data):

    pa = data.get("PA_Number", "").strip()
    utr = data.get("PA_UTR", "").strip()

    # Case 1: both exist
    if pa and utr:
        data["PA_Number"] = pa
        data["PA_UTR"] = utr
        return data

    # Case 2: only PA exists
    if pa and not utr:
        data["PA_Number"] = pa
        data["PA_UTR"] = ""
        return data

    # Case 3: only UTR exists
    if utr and not pa:
        data["PA_Number"] = utr
        data["PA_UTR"] = utr
        return data

    # Case 4: neither exists
    data["PA_Number"] = ""
    data["PA_UTR"] = ""

    return data


# -----------------------------
# LLM EXTRACTION
# -----------------------------
def extract_with_llm(pdf_text):

    prompt = f"""
You are an expert financial document parser.

Extract payment advice data from the document text.

Return STRICT JSON.

Schema:

{{
 "PA_Company":"",
 "PA_Total":"",
 "PA_Date":"",
 "PA_Number":"",
 "PA_MMD_Bank_Account_NAME":"",
 "PA_MMD_Bank_Account_NO":"",
 "PA_UTR":"",
 "pa_trans_line_details":[
  {{
   "pa_invoice_number":"",
   "pa_client_ref_number":"",
   "pa_client_ref_date":"",
   "pa_amount":"",
   "pa_trans_type":"",
   "pa_trans_des":"",
   "pa_account_site":""
  }}
 ]
}}

Rules:

1. PA_Company = payment sender (FROM company)
2. Never choose the company after "To" or "M/s"
3. PA_Number = payment reference such as:
   - NEFT No
   - Payment Advice No
   - Transaction Reference
4. PA_UTR = UTR reference if present
5. Invoice rows → pa_trans_type = "INV"
6. Less / TDS / negative rows → pa_trans_type = "TDS"
7. Dates → YYYY-MM-DD
8. Remove commas from amounts
9. Return ONLY JSON

Document Text:

{pdf_text}
"""

    response = client.responses.create(
        model=MODEL,
        input=prompt,
        temperature=0
    )

    return response.output_text


# -----------------------------
# MAIN PROCESS
# -----------------------------
def process_pdf(pdf_path):

    print("Extracting text from PDF...")

    pdf_text = extract_pdf_text(pdf_path)

    print("Sending to LLM...")

    raw = extract_with_llm(pdf_text)

    cleaned = clean_json(raw)

    try:

        data = json.loads(cleaned)

        # enforce PA/UTR rules
        data = validate_pa_utr(data)

        return data

    except:

        print("⚠ JSON parsing failed")
        print(raw)

        return None


# -----------------------------
# RUN SCRIPT
# -----------------------------
if __name__ == "__main__":

    pdf_path = r"C:/Users/harin\Downloads/IN Payee Advice_01a4468e1ece42f1a4468e1ece42f11c.pdf"

    result = process_pdf(pdf_path)

    if result:
        print(json.dumps(result, indent=4))