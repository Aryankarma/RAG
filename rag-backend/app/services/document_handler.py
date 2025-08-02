import fitz  # PyMuPDF
from app.utils.splitter import chunk_text

async def parse_pdf(file):
    content = await file.read()
    doc = fitz.open(stream=content, filetype="pdf")
    text = "\n".join([page.get_text() for page in doc])
    return chunk_text(text)

