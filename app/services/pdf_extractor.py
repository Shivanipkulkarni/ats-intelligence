import pdfplumber
from io import BytesIO

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract text from PDF file bytes.
    
    Args:
        pdf_bytes: Raw PDF file bytes
        
    Returns:
        Extracted text content from all pages
    """
    try:
        pdf_file = BytesIO(pdf_bytes)
        text_content = []
        
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
        
        return "\n".join(text_content)
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")
