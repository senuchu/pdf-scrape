from fastapi import FastAPI, File, UploadFile
import PyPDF2
import re
import json
import io

app = FastAPI()

def extract_second_page_text(pdf_bytes):
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        if len(reader.pages) < 2:
            return None
        return reader.pages[1].extract_text()
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return None

def classify_pdf(pdf_bytes):
    text = extract_second_page_text(pdf_bytes)
    if not text:
        return {"error": "PDF does not have a second page or could not be read."}

    similarity_match = re.search(r"(\d+)%\s*Overall Similarity", text)
    ai_match = re.search(r"(?:(\d+)\*?%|(\*%))(?:\s*detected as AI)", text)

    result = {
        "type": "Unknown",
        "Overall Similarity": None,
        "AI Detection": None,
        "AI Detection Asterisk": False,
        "Below_Threshold": False
    }
    
    if similarity_match and ai_match:
        result["type"] = "Plagiarism and AI Detection Report"
        result["Overall Similarity"] = int(similarity_match.group(1))
        if ai_match.group(1):
            result["AI Detection"] = int(ai_match.group(1))
            result["AI Detection Asterisk"] = '*' in ai_match.group(0)
        else:
            result["AI Detection"] = -1
            result["Below_Threshold"] = True
            result["AI Detection Asterisk"] = True
    elif similarity_match:
        result["type"] = "Plagiarism Report"
        result["Overall Similarity"] = int(similarity_match.group(1))
    elif ai_match:
        result["type"] = "AI Detection Report"
        if ai_match.group(1):
            result["AI Detection"] = int(ai_match.group(1))
            result["AI Detection Asterisk"] = '*' in ai_match.group(0)
        else:
            result["AI Detection"] = -1
            result["Below_Threshold"] = True
            result["AI Detection Asterisk"] = True

    return result

@app.post("/upload/")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        pdf_bytes = await file.read()
        if not pdf_bytes:
            return {"error": "Uploaded file is empty."}

        result = classify_pdf(pdf_bytes)
        return json.dumps(result, indent=4)
    
    except Exception as e:
        return {"error": f"Internal server error: {str(e)}"}
