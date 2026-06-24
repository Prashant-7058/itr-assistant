import os
import json
import fitz  # PyMuPDF
from dotenv import load_dotenv
from openai import OpenAI
from tools import get_fields, add_data, load_json
import pytesseract
from PIL import Image
import io
load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "ITR Assistant"
    }
)

MODEL_NAME = "openai/gpt-4o-mini"

BASE_DIR = os.path.dirname(__file__)

pytesseract.pytesseract.tesseract_cmd = os.path.join(
    BASE_DIR, "bin", "tesseract.exe"
)

os.environ["TESSDATA_PREFIX"] = os.path.join(
    BASE_DIR, "bin", "tessdata"
)

# ===============================
# DETECT ITR TYPE FROM SCHEMA
# ===============================
def detect_itr_type(schema_keys):
    itr4_keys = {"bus44ADTurnover", "bus44ADAReceipts", "bus44AETotalInc", "totalBusinessInc", "bus44ADInc6Pct"}
    itr1_keys = {"grossSal", "perquisites", "profitsInLieu", "employerCategory", "filingSection"}
    itr3_keys = {"businessIncome", "presumptiveIncome", "grossReceipts"}
    itr2_keys = {"stcg111a", "stcgOther", "ltcg112a", "ltcgOther"}

    key_set = set(schema_keys)
    if itr4_keys & key_set:
        return "ITR-4"
    if itr3_keys & key_set:
        return "ITR-3"
    if itr1_keys & key_set and not itr2_keys & key_set:
        return "ITR-1"
    return "ITR-2"


# ===============================
# PDF TEXT EXTRACTION
# ===============================
def extract_pdf_text(file_bytes, boxes=None, scale=1.4):
    full_text = ""
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for i, page in enumerate(doc):

            # Redact boxes BEFORE extracting text
            if boxes:
                page_boxes = boxes.get(str(i + 1), [])
                for b in page_boxes:
                    px = b["x"] / scale
                    py = b["y"] / scale
                    pw = b["w"] / scale
                    ph = b["h"] / scale
                    rect = fitz.Rect(px, py, px + pw, py + ph)
                    page.add_redact_annot(rect)
                page.apply_redactions()

            page_text = page.get_text()
            if page_text.strip():
                full_text += f"\n\n=== PAGE {i+1} ===\n{page_text}"
                continue

            # OCR fallback for scanned pages only
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            ocr_text = pytesseract.image_to_string(img)
            full_text += f"\n\n=== PAGE {i+1} (OCR) ===\n{ocr_text}"

    print("TOTAL TEXT LENGTH:", len(full_text))
    print("EXTRACTED TEXT:", full_text)
    return full_text


# ===============================
# PDF PROCESSOR (FORCED TOOL FLOW)
# ===============================
def process_pdf(file_bytes, boxes=None, scale=1.4):

    schema = get_fields()
    schema_keys = list(schema.keys())
    itr_type = detect_itr_type(schema_keys)

    SYSTEM_PROMPT = f"""
You are a Chartered Accountant AI.

STRICT PATCH RULES:
- You MUST call add_data tool.
- ONLY include fields you extracted from the document.
- NEVER send full schema.
- NEVER include empty strings.
- NEVER include default values (0, "", [], null).
- NEVER include identity fields like pan, aadhaar, mobile, email.
- If nothing found → do NOT call add_data.

FIELD VALUE RULES:
- bankAccType must be: "SB" for Savings, "CA" for Current, "CC" for Cash Credit, "OD" for OD
- hp type must be: "S" for Self Occupied, "L" for Let Out
- regime must be: "new" or "old"
- gender must be: "M", "F", or "O"
- residentialStatus must be: "RES", "NRI", or "RNOR"

You are working with an {itr_type} schema.
"""

    tools_def = [
        {
            "type": "function",
            "function": {
                "name": "get_fields",
                "description": f"Return full {itr_type} schema",
                "parameters": {"type": "object", "properties": {}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "add_data",
                "description": f"Patch ONLY extracted fields into {itr_type}. Never send full schema.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "updates": {
                            "type": "object",
                            "additionalProperties": True
                        }
                    },
                    "required": ["updates"]
                }
            }
        }
    ]

    pdf_text = extract_pdf_text(file_bytes, boxes, scale)

    # Build array guide based on ITR type
    if itr_type == "ITR-1":
        ARRAY_GUIDE = """
ARRAY FIELDS — return as list of objects ONLY if found in document:

hp (House Property) → [{"type":"S" or "L", "rent":0, "munTax":0, "interest":0, "arrears":0}]
type S = Self Occupied, type L = Let Out

tds (TDS from Salary) → [{"tan":"", "employer":"", "income":0, "amount":0}]
tds2 (TDS other than salary) → [{"tan":"", "name":"", "income":0, "amount":0}]
tcs → [{"tan":"", "name":"", "payment":0, "collected":0}]
advTax → [{"bsr":"", "date":"YYYY-MM-DD", "serial":"", "amount":0}]
selfTax → [{"bsr":"", "date":"YYYY-MM-DD", "serial":"", "amount":0}]
"""
    elif itr_type == "ITR-4":
        ARRAY_GUIDE = """
ARRAY FIELDS — return as list of objects ONLY if found in document:

bus44ADEntries (44AD Business) → [{"name":"Business Name", "code":"01001", "desc":"description"}]
bus44ADAEntries (44ADA Profession) → [{"name":"Profession Name", "code":"", "desc":""}]
bus44AEEntries (44AE Goods Carriage) → [{"regNo":"vehicle reg", "vehicleType":"O" or "H", "months":12, "tonnage":0}]
gstinEntries → [{"gstin":"GSTIN number", "turnover":0}]
tds1Entries (TDS on Salary) → [{"tan":"", "employer":"", "grossSalary":0, "amount":0}]
tds2Entries (TDS other than salary) → [{"tan":"", "name":"", "credited":0, "amount":0}]
tcsEntries → [{"tan":"", "name":"", "amount":0, "collected":0}]
advTaxEntries → [{"bsr":"", "date":"YYYY-MM-DD", "serial":"", "amount":0}]
selfTaxEntries → [{"bsr":"", "date":"YYYY-MM-DD", "serial":"", "amount":0}]
"""
    else:
        ARRAY_GUIDE = """
ARRAY FIELDS — return as list of objects ONLY if found in document:

hp (House Property) → [{"type":"S" or "L", "rent":0, "tax":0, "interest":0}]
stcg111a → [{"asset":"description", "salePrice":0, "cost":0}]
stcgOther → [{"asset":"description", "salePrice":0, "cost":0}]
ltcg112a → [{"asset":"description", "salePrice":0, "cost":0}]
ltcgOther → [{"asset":"description", "salePrice":0, "cost":0}]
tds → [{"tan":"", "employer":"", "grossSalary":0, "amount":0}]
advTax → [{"bsr":"", "date":"YYYY-MM-DD", "serial":"", "amount":0}]
"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"""
Valid {itr_type} field keys — use ONLY these exact key names:
{json.dumps(schema_keys)}

{ARRAY_GUIDE}

Extract values ONLY from the document text below.
Do NOT use values from memory or prior context.
Only include fields explicitly present in the document.
Skip zeros and empty strings.

DOCUMENT:
{pdf_text}
"""
        }
    ]

    # FORCED LOOP
    for _ in range(6):

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=tools_def,
            tool_choice="auto",
            max_tokens=4096,
            temperature=0
        )

        msg = response.choices[0].message
        print("TOOL CALLS:", msg.tool_calls)
        messages.append(msg)

        if not msg.tool_calls:
            break

        for tool_call in msg.tool_calls:
            tool_name = tool_call.function.name
            try:
                args = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError as e:
                print(f"JSON PARSE ERROR for tool {tool_name}: {e}")
                print(f"RAW ARGUMENTS: {tool_call.function.arguments}")
                continue

            if tool_name == "get_fields":
                result = get_fields()

            elif tool_name == "add_data":
                updates = args["updates"] if "updates" in args else args
                print("UPDATES RECEIVED:", updates)
                result = add_data(updates)

            else:
                result = {}

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result)
            })

    final_data = load_json()

    return {
        "status": "completed",
        "updated_data": final_data
    }


# ===============================
# FIELD ASSIST (SMART CHAT FLOW)
# ===============================
def assist_field(field_key, user_message, options=None):

    def is_question(text):
        text = text.strip().lower()
        return (
            text.endswith("?")
            or text.startswith("what")
            or text.startswith("why")
            or text.startswith("how")
            or text.startswith("is ")
            or text.startswith("can ")
            or text.startswith("which")
        )

    options_block = ""
    if options:
        opts_text = "\n".join(f'  - "{o["value"]}": {o["label"]}' for o in options)
        options_block = f"\n\nThis is a DROPDOWN field. Available options (value → label):\n{opts_text}\n"

    prompt = f"""
You are a tax assistant helping fill an Indian Income Tax Return.

Field: {field_key}{options_block}
User says: {user_message}

STRICT RULES:
- Always return JSON with "reply" and optionally "fillValue".
- If this is a dropdown and user asks which options it has → list all options clearly in "reply".
- If user picks an option (by label or value) → set "fillValue" to the option's VALUE (not label).
- If user provides a numeric/text VALUE for a non-dropdown field → set "fillValue".
- If explanation or question → only set "reply", do NOT set fillValue.
- Do NOT include the field name in reply.
- Keep reply concise and helpful.
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        max_tokens=200,
        temperature=0
    )

    try:
        data = json.loads(response.choices[0].message.content)
    except:
        return {"reply": response.choices[0].message.content, "fillValue": ""}

    # NORMALIZE OUTPUT
    if "reply" not in data:
        for key in ("explanation", "description", "message"):
            if key in data:
                data["reply"] = data[key]
                break
        else:
            data["reply"] = ""

    if "fillValue" not in data:
        data["fillValue"] = ""

    if data["fillValue"] is None:
        data["fillValue"] = ""

    # MAP FIELD KEY IF USER SENT VALUE
    if data["fillValue"] != "" and not is_question(user_message):

        schema = get_fields()

        def normalize(text):
            return ''.join(c.lower() for c in text if c.isalnum())

        label_norm = normalize(field_key)
        matched_key = None

        for key in schema.keys():
            if normalize(key) == label_norm:
                matched_key = key
                break

        if not matched_key:
            for key in schema.keys():
                k = normalize(key)
                if label_norm in k or k in label_norm:
                    matched_key = key
                    break

        if matched_key:
            data["field"] = matched_key

        if not data.get("reply"):
            data["reply"] = "Updated"

    print("FIELD ASSIST RESULT:", data)

    return data




def itr_selector_llm(message, history=None):

    SYSTEM_PROMPT = """
You are a Chartered Accountant helping a common Indian taxpayer select the correct ITR form.

STRICT RULES:
- Act like a human CA.
- Do NOT give generic answers.
- Ask clarifying questions if needed.
- Only recommend ITR when confident.
- When confident, return fillValue as one of:
  "ITR-1", "ITR-2", "ITR-3", "ITR-4"

Always respond in JSON format:
{
  "reply": "...",
  "fillValue": "" (or ITR-X if confident)
}

ITR KNOWLEDGE:

ITR-1 → Only salary, max 1 house property, no capital gains, no business.
ITR-2 → Salary + capital gains OR multiple house properties.
ITR-3 → Business or professional income.
ITR-4 → Presumptive income (44AD/44ADA/44AE).

If user only says "salary", ask clarifying questions.
Do NOT redirect unless confident.
"""

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history:
        messages.extend(history)

    messages.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0
    )

    return json.loads(response.choices[0].message.content)