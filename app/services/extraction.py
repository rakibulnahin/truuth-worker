import os, json, re, time, random, base64, tempfile, importlib.util
from pathlib import Path
from io import BytesIO
import numpy as np
import cv2
import pytesseract
from pypdfium2 import PdfiumError
from docx2pdf import convert
import fitz
import boto3
from botocore.exceptions import ClientError

from docx import Document
from docx.text.hyperlink import Hyperlink
import pycountry
import json

class Extractor():

    # ======================================================================
    # CONFIGURATION — edit these
    # ======================================================================
    PDF_INPUT_PATH  = ""   # local PDF to process
    OUTPUT_JSON     = "output/test5/haiku_same_as_pdf"    # where to save results

    AWS_PROFILE = "truuth-rnd"
    AWS_REGION  = "ap-southeast-2"
    BEDROCK_PY_PATH = "app/services/bedrock 2.py"     # your existing bedrock.py

    MODEL_ID = "claude-haiku-4.5"
    # ======================================================================
    
    # Load bedrock module
    # ----------------------------
    spec = importlib.util.spec_from_file_location("bedrock", BEDROCK_PY_PATH)
    bedrock_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bedrock_mod)
    Bedrock = bedrock_mod.Bedrock

    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    creds   = session.get_credentials().get_frozen_credentials()

    bedrock_file = Bedrock(
        # AWS_REGION,
        "us-east-1",
        creds.access_key,
        creds.secret_key,
        creds.token,
        )
    bedrock_file.enable_model(MODEL_ID)



    def is_session_valid(self):
        try:
            sts = self.session.client("sts")
            sts.get_caller_identity()
            print("Session is valid.")
            return True
        except ClientError as e:
            print("Session invalid:", e)
            return False
        

    # AUTO ROTATION (Tesseract OSD + best-of-4 fallback)
    # ======================================================================
    OSD_CONF_THRESHOLD = 5.0
    SCORE_MAX_SIDE     = 1400
    DEBUG_ROTATION     = False


    def _decode_to_bgr(self, path_or_bytes):
        if isinstance(path_or_bytes, BytesIO):
            data = np.frombuffer(path_or_bytes.getvalue(), dtype=np.uint8)
            return cv2.imdecode(data, cv2.IMREAD_COLOR)
        return cv2.imread(str(path_or_bytes), cv2.IMREAD_COLOR)


    def _rotate_90n(self, img, k):
        k = k % 4
        if k == 0: return img
        if k == 1: return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        if k == 2: return cv2.rotate(img, cv2.ROTATE_180)
        if k == 3: return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)


    def _apply_rotation_deg(self, img_bgr, deg):
        if deg == 90:  return cv2.rotate(img_bgr, cv2.ROTATE_90_CLOCKWISE)
        if deg == 180: return cv2.rotate(img_bgr, cv2.ROTATE_180)
        if deg == 270: return cv2.rotate(img_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return img_bgr


    def _resize_max_side(self, img_bgr, max_side):
        h, w = img_bgr.shape[:2]
        m = max(h, w)
        if m <= max_side:
            return img_bgr
        scale = max_side / float(m)
        return cv2.resize(img_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)


    def _tesseract_osd_rotation(self, img_bgr):
        try:
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            osd  = pytesseract.image_to_osd(gray, output_type=pytesseract.Output.STRING)
            rot, conf = 0, 0.0
            for line in osd.splitlines():
                if "Rotate:" in line:
                    rot = int(line.split(":")[1].strip())
                elif "Orientation confidence:" in line:
                    conf = float(line.split(":")[1].strip())
            return (rot if rot in (0, 90, 180, 270) else 0), conf
        except Exception:
            return 0, 0.0


    def _osd_upright_score(self, img_bgr):
        r, c = self._tesseract_osd_rotation(img_bgr)
        return (c if r == 0 else 0.0), r, c


    def _textline_score(self, img_bgr):
        img  = self._resize_max_side(img_bgr, self.SCORE_MAX_SIDE)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        bw   = 255 - cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (35, 3))
        morph  = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kernel, iterations=1)
        cnts, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return sum(cv2.boundingRect(c)[2] for c in cnts
                if cv2.boundingRect(c)[2] > 80 and cv2.boundingRect(c)[3] < 60)


    def _best_of_4_rotation(self, img_bgr):
        best_k, best_score = 0, -1.0
        for k in (0, 1, 2, 3):
            sc = self._textline_score(self._rotate_90n(img_bgr, k))
            if sc > best_score:
                best_score, best_k = sc, k
        return best_k, best_score


    def _autorotate(self, img_bgr):
        rot, conf = self._tesseract_osd_rotation(img_bgr)
        if self.DEBUG_ROTATION:
            print(f"[OSD] rot={rot} conf={conf:.2f}")

        if conf >= self.OSD_CONF_THRESHOLD:
            if rot == 0:
                return img_bgr
            candidates = {180: [180], 90: [90, 270], 270: [270, 90]}.get(rot, [0, 90, 180, 270])
            best_upright, best_img = 0.0, img_bgr
            for deg in candidates:
                test_img = self._apply_rotation_deg(img_bgr, deg)
                upright, _, _ = self._osd_upright_score(test_img)
                if upright > best_upright:
                    best_upright, best_img = upright, test_img
            if best_upright > 0:
                return best_img

        best_k, _ = self._best_of_4_rotation(img_bgr)
        return self._rotate_90n(img_bgr, best_k)


    def autorotate_image(self, path_or_bytes):
        """Auto-rotate image and save to a temp file. Returns temp file path."""
        img0 = self._decode_to_bgr(path_or_bytes)
        if img0 is None:
            raise ValueError("Could not decode image")
        img_rot = self._autorotate(img0)
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        cv2.imwrite(tmp.name, img_rot, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        tmp.close()
        return tmp.name
    
    # PROMPTS
    # ======================================================================
    SYSTEM_PROMPT = (
        "<role> You are a perfect resume information extraction specialist. You will be given resume files pdfs "
        "Your task is to extract ONLY the candidates identity fields (PID) and social media handles and return STRICT JSON "
        "that matches the schema. Do not include prose, comments, or extra keys—return a single JSON object only. </role>\n\n"

        "<schema>\n"
        "{\n"
        '  "candidate_name": {"value": "string|null", "confidence": 0.0, "justification": "string"},\n'
        '  "candidate_phone":{"value": [ {"text": "string"} ], "confidence": 0.0, "justification": "string"},\n'
        '  "candidate_email":{"value": [ {"text": "string"} ], "confidence": 0.0, "justification": "string"},\n'
        '  "candidate_address":{"value": [ {"text": "string"} ], "confidence": 0.0, "justification": "string"},\n'
        '  "candidate_DOB":{"value": [ {"text": "string"} ], "confidence": 0.0, "justification": "string"},\n'
        '  "candidate_social_handles":   {"value": [ {"text": "string"} ], "confidence": 0.0, "justification": "string"},\n'
        "}\n"
        "</schema>\n\n"
        "<rules>\n"
        "Return raw text exactly as seen; do NOT normalize or invent values.\n"
        "Output ONLY one valid JSON object—no markdown, no backticks, no extra text.\n"
        "Double check the pdf again with the JSON you created.\n"
        "If no change return json else repeat process \n"
        "JSON format must be returned accroding to SCHEMA\n"
        "MUST sure return emply values a JSON according to schema  if no PID or Social media found \n"
        "You MUST return the JSON format with the SCHEMA\n" \
        "DO NOT return Null or empty response"
        "</rules>"
    )

    USER_PROMPT = (
        "Extract all identities PID and social media from provided resume according to schema. " \
        "Do not guess or infer any information that not explicitly present in resume." \
        "PID and social media handles can be anywhere in the image. "
        "Social Media handles should returned as they are in resume without any modification or addition. " \
        "There can be multiple type of social media include personal portfolio website like linkedin profile, github and personal websites such as nahin.xxx.yy or www.nahin.com.ap.au "\
        "I social media not found re-check"\
        "After finishing with full extraction process and you have created json match your created json with resume ensure all informations are collected correctly with confidence 1" \
        "Before providing a response check if the json and the format is valid and has no errors in formatting for json parsing"\
        "</task>"
    )

    # LLM CALL WITH RETRIES
    # ======================================================================
    def call_llm(self, image_b64_list, resume_texts, max_retries=3, feedback_prompt=""):
        prompt = self.USER_PROMPT + feedback_prompt + "\n" + "\n".join(["<|image|>"] * len(image_b64_list))
        for attempt in range(max_retries):
            try:
                response = self.bedrock_file.run_prompt(
                    system_prompt=self.SYSTEM_PROMPT,
                    user_prompt=resume_texts+".\n "+prompt,
                    image_paths=image_b64_list,
                )
                return response 
            except Exception as e:
                msg = str(e)
                if "ModelTimeoutException" in msg or "ThrottlingException" in msg:
                    backoff = (2 ** attempt) + random.random()
                    print(f"⚠️  Throttled/timeout, retrying in {backoff:.1f}s...")
                    time.sleep(backoff)
                else:
                    raise
        return None
    
    # PDF → IMAGES
    # ======================================================================
    def pdf_to_rotated_images(self, pdf_path, max_pages=2):
        """Convert first N pages of a PDF to auto-rotated temp image files."""
        image_paths = []
        for page_num in range(max_pages):
            try:
                if pdf_path.lower().endswith(".jpg") or pdf_path.lower().endswith(".jpeg") or pdf_path.lower().endswith(".png"):
                    page_img = pdf_path  # already an image file
                else:
                    page_img = self.bedrock_mod.convert_pdf_to_png(pdf_path, page_number=page_num)
            except Exception:
                if page_num == 0:
                    raise
                break   # page doesn't exist, stop
            rotated = self.autorotate_image(page_img)
            image_paths.append(rotated)
        return image_paths
    
    # PDF -> Text
    def pdf_to_text(self, pdf_path):
        doc = fitz.open(pdf_path)
        extracted_text = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # 1. Grab all text blocks on the page
            page_text = page.get_text("text")
            
            # 2. Extract link annotations
            links = page.get_links()
            
            # If there are links, safely substitute or append them
            link_additions = []
            for link in links:
                if link.get("kind") == fitz.LINK_URI:  # Check if it's a web URL
                    uri = link.get("uri")
                    rect = link.get("from")  # Bounding box of the link
                    
                    # Extract the anchor text sitting inside that clickable box
                    anchor_text = page.get_textbox(rect).strip()
                    
                    if anchor_text:
                        link_additions.append(f"[{anchor_text} -> {uri}]")
            
            # Combine the plain text and the exposed URLs
            extracted_text.append(page_text)
            if link_additions:
                extracted_text.append("\n--- Extracted Links ---\n" + "\n".join(link_additions))
                
        return "\n".join(extracted_text)

    # doc/docx -> text


    def docx_to_text(self, docx_path):
        doc = Document(docx_path)
        full_text = []

        for paragraph in doc.paragraphs:
            paragraph_text = ""
            
            # Iterate through standard text and hyperlinks sequentially
            for item in paragraph.iter_inner_content():
                if isinstance(item, Hyperlink):
                    # item.text is the anchor (e.g., "LinkedIn")
                    # item.url is the hidden destination (e.g., "www.linkedin.com/ln/...")
                    paragraph_text += f"{item.text} ({item.url})"
                else:
                    # Regular text run
                    paragraph_text += item.text
                    
            if paragraph_text.strip():
                full_text.append(paragraph_text)
                
        # Also grab links inside tables, which are common in resumes
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        # (Apply the same inner content looping logic for tables if necessary)
                        pass

        return "\n".join(full_text)

    # JSON PARSING HELPERS
    # ======================================================================
    def safe_parse_json(self, text):
        if not text:
            return None
        # strip markdown code fences if present
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
        try:
            return json.loads(text)
        except Exception:
            pass
        # try extracting first {...} block
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end+1])
            except Exception:
                pass
        return None


    def get_scalar(self, js, key):
        raw = js.get(key, {})
        if raw is None:
            return "", "", ""
        if isinstance(raw, dict):
            return raw.get("value", ""), raw.get("confidence", ""), raw.get("justification", "")
        return str(raw or ""), "", ""


    def get_list(self, js, key):
        raw = js.get(key, {})
        value = raw.get("value", []) if isinstance(raw, dict) else raw
        conf  = raw.get("confidence", "") if isinstance(raw, dict) else ""
        just  = raw.get("justification", "") if isinstance(raw, dict) else ""

        texts = []
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and "text" in item:
                    texts.append(str(item["text"]).strip())
                elif isinstance(item, str) and item.strip():
                    texts.append(item.strip())
        elif isinstance(value, str) and value.strip():
            texts.append(value.strip())

        # deduplicate preserving order
        seen, unique = set(), []
        for t in texts:
            if t.lower() not in seen:
                seen.add(t.lower())
                unique.append(t)
        return unique, conf, just


    def store_temporary_locally():
        pass

    

    def refine_js(self, js):

        COUNTRY_ALIASES = {
            "usa": "United States",
            "us": "United States",
            "uk": "United Kingdom",
            "uae": "United Arab Emirates",
            "philippines": "Philippines",
            "bangladesh": "Bangladesh",
            "india": "India",
            "australia": "Australia",
            "canada": "Canada",
        }


        CITY_TO_COUNTRY = {
            "sydney": "Australia",
            "melbourne": "Australia",
            "dhaka": "Bangladesh",
            "manila": "Philippines",
            "bulacan": "Philippines",
            "cebu": "Philippines",
            "delhi": "India",
            "mumbai": "India",
            "london": "United Kingdom",
            "new york": "United States",
        }


        def get_text_values(field):

            if not field:
                return []

            values = field.get("value", [])

            if isinstance(values, list):
                return [
                    item.get("text", "").strip()
                    for item in values
                    if isinstance(item, dict) and item.get("text")
                ]

            return []


        def split_name(full_name):

            if not full_name:
                return "", ""

            parts = full_name.strip().split()

            first_name = parts[0] if parts else ""
            last_name = parts[-1] if len(parts) > 1 else ""

            return first_name, last_name


        def extract_nationality_from_address(address):

            if not address:
                return ""

            address_lower = address.lower()

            # Check aliases first
            for key, value in COUNTRY_ALIASES.items():
                if key in address_lower:
                    return value

            # Check official country names
            for country in pycountry.countries:
                if country.name.lower() in address_lower:
                    return country.name

            # Check cities
            for city, country in CITY_TO_COUNTRY.items():
                if city in address_lower:
                    return country

            return ""



        raw = js

        # Full name
        full_name = raw.get("candidate_name", {}).get(
            "value",
            ""
        ).title()

        first_name, last_name = split_name(full_name)

        # Phone
        phones = get_text_values(
            raw.get("candidate_phone")
        )

        phone = phones[0] if phones else ""

        # Email
        emails = get_text_values(
            raw.get("candidate_email")
        )

        email = emails[0] if emails else ""

        # Address
        addresses = get_text_values(
            raw.get("candidate_address")
        )

        address = addresses[0] if addresses else ""

        # DOB
        dobs = get_text_values(
            raw.get("candidate_DOB")
        )

        dob = dobs[0] if dobs else ""

        # Social Handles
        social_media = get_text_values(
            raw.get("candidate_social_handles")
        )

        # Nationality from address
        nationality = extract_nationality_from_address(
            address
        )

        refined = {
            "full_name": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": dob,
            "address": address,
            "nationality": nationality,
            "identifiers": {
                "email": email,
                "phone": phone,
                "social_media": social_media,
            },
        }

        return refined


    def start_extractor(self, test_paths):
        print(test_paths)
        for file_path in test_paths:
            feedback_prompt = ""
            for feedback_attempt in range(3):
                print("file_path", file_path)
                # pdf_path = os.path.join(PDF_INPUT_PATH, file_path)
                pdf_path = file_path

                if not os.path.exists(pdf_path):
                    raise FileNotFoundError(f"PDF not found: {pdf_path}")

                print(f"📄 Processing: {pdf_path}")

                # Step 1 — convert PDF pages to images
                print("🔄 Converting PDF pages to images...")
                tmp_images = []
                try:
                    if pdf_path.lower().endswith(".docx"):
                        # convert docx to pdf first
                        temp_pdf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
                        temp_pdf.close()
                        convert(pdf_path, temp_pdf.name)
                        pdf_path = temp_pdf.name

                    tmp_images = self.pdf_to_rotated_images(pdf_path, max_pages=2)
                    # print(f"   {len(tmp_images)} page(s) prepared")

                    # Step 2 — encode to base64
                    image_b64_list = []
                    for img_path in tmp_images:
                        with open(img_path, "rb") as f:
                            image_b64_list.append(base64.b64encode(f.read()).decode("utf-8"))

                    # Step3 - resume extract
                    
                    resume_text = (
                        "<task> You have been given images of resume" \
                        "Use IMAGE to "
                    )
                    
                    if pdf_path.lower().endswith(".pdf"):
                        resume_text = (
                            "<task> You have been given images of resume and extracted texts of resume" \
                            "Use BOTH TEXT and IMAGE to "
                        )
                        resume_text = self.pdf_to_text(pdf_path) + resume_text
                        
                    if pdf_path.lower().endswith(".docx"):
                        resume_text = (
                            "<task> You have been given images of resume and extracted texts of resume" \
                            "Use BOTH TEXT and IMAGE to "
                        )
                        resume_text = self.docx_to_text(pdf_path) + resume_text

                    # Step 4 — call LLM
                    print("🤖 Calling LLM on Bedrock...")
                    if feedback_prompt != "":
                        print("Problem in json parsing retrying with feedback prompt")

                    
                    resp = self.call_llm(tmp_images, resume_texts=resume_text, feedback_prompt=feedback_prompt) # for claude using image paths directly


                finally:
                    # always clean up temp image files
                    for p in tmp_images:
                        try:
                            os.remove(p)
                        except Exception:
                            pass

                # Step 4 — parse response
                if resp is None or not resp.get(self.MODEL_ID):
                    print("❌ No response from model (timeout or retries exhausted)")
                    

                r = resp[self.MODEL_ID]
                raw_text    = str(getattr(r, "response", "")).strip()
                js = self.safe_parse_json(raw_text)
                if js is None:
                    print("\n⚠️  Could not parse JSON from response. Raw output:")
                    print(raw_text, f"\n will retry. Feedback attempt {feedback_attempt}")
                    feedback_prompt = raw_text+" has error in json. Identify error and make sure json is returned correctly"
                else:
                    print("Json parsed feedback loop break")
                    break

            in_tokens   = getattr(r, "input_tokens_used", None)
            out_tokens  = getattr(r, "output_tokens_used", None)
            cost        = round(float(getattr(r, "cost", 0) or 0), 6)
            latency     = round(float(getattr(r, "duration", 0) or 0), 2)

            print(f"\n✅ Response received")
            print(f"   Input tokens:  {in_tokens}")
            print(f"   Output tokens: {out_tokens}")
            print(f"   Cost:          ${cost}")
            print(f"   Latency:       {latency}s")

            js = self.safe_parse_json(raw_text)
            if js is None:
                print("\n⚠️  Could not parse JSON from response. Raw output:")
                print(raw_text, "LLM cannot provide the right json")
            else:
                refined = self.refine_js(js)

            # Step 6 — build output
            output = {
                "source_file":    pdf_path,
                "model":          getattr(r, "model_name", self.MODEL_ID),
                "input_tokens":   in_tokens,
                "output_tokens":  out_tokens,
                "cost_usd":       cost,
                "latency_s":      latency,
                "raw_llm_response": js,   # full JSON from model including confidences
                "refined": refined
            }

        return output

    def __init__(self):
        
        print(self.is_session_valid())
        # MAIN
        # ======================================================================
        
        

    

