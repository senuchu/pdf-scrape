from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import fitz  # PyMuPDF
import os
import shutil
import re
import docx

app = FastAPI()
UPLOAD_DIR = "/tmp"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Define max file size (4MB to stay under Vercel's limit)
MAX_FILE_SIZE = 4 * 1024 * 1024  # 4MB in bytes

def count_words_in_pdf(pdf_path):
    """Counts words in a PDF, ignoring empty lines and comments."""
    try:
        doc = fitz.open(pdf_path)
        text = " ".join([page.get_text("text") for page in doc])
        # Remove comments (lines starting with # or //)
        text = re.sub(r"^\s*(#|//).*$", "", text, flags=re.MULTILINE)
        # Remove extra whitespace and count words
        words = re.findall(r"\b\w+\b", text)
        return len(words)
    except Exception as e:
        print(f"Error counting words in PDF: {e}")
        return None

def count_words_in_docx(docx_path):
    """Counts words in a DOCX file."""
    try:
        doc = docx.Document(docx_path)
        text = " ".join([para.text for para in doc.paragraphs])
        words = re.findall(r"\b\w+\b", text)
        return len(words)
    except Exception as e:
        print(f"Error counting words in DOCX: {e}")
        return None

def count_words_in_text(text_path):
    """Counts words in a text file."""
    try:
        with open(text_path, "r") as file:
            text = file.read()
        words = re.findall(r"\b\w+\b", text)
        return len(words)
    except Exception as e:
        print(f"Error counting words in text file: {e}")
        return None

def validate_file_extension(file: UploadFile):
    """Validates the file extension to ensure it's one of the allowed types."""
    allowed_extensions = ['.pdf', '.docx', '.txt']
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF, DOCX, and TXT files are allowed.")
    return file_extension

@app.post("/count-words")
async def count_words_endpoint(file: UploadFile = File(...)):
    """Processes an uploaded file and counts the words in it."""
    # Check file size first before processing
    # Read a small portion to get content length from headers if available
    file_content = await file.read(1024)
    content_length = file.size if hasattr(file, 'size') else None
    
    # If we can't get size from headers, estimate based on first chunk
    if content_length is None:
        # Reset file position
        await file.seek(0)
        content = await file.read()
        content_length = len(content)
        # Reset file position again
        await file.seek(0)
    else:
        # Reset file position
        await file.seek(0)
        
    if content_length > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {MAX_FILE_SIZE/1024/1024}MB."
        )
        
    file_extension = validate_file_extension(file)
    input_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    word_count = None
    if file_extension == '.pdf':
        word_count = count_words_in_pdf(input_path)
    elif file_extension == '.docx':
        word_count = count_words_in_docx(input_path)
    elif file_extension == '.txt':
        word_count = count_words_in_text(input_path)

    if word_count is None:
        raise HTTPException(status_code=500, detail="Error processing the file.")

    response = {
        "total_words": word_count
    }

    return JSONResponse(content=response)
