# PDF Reading Skill

## Purpose
Extract text, tables, images, and form fields from any PDF. Handles scanned docs via OCR strategy routing.

## Libraries

### pypdf (Lightweight)
```python
from pypdf import PdfReader

reader = PdfReader('document.pdf')
text = '\n'.join(page.extract_text() for page in reader.pages)
```

### pdfplumber (Tables)
```python
import pdfplumber

with pdfplumber.open('document.pdf') as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        tables = page.extract_tables()
```

### PyMuPDF (Images + OCR)
```python
import fitz  # PyMuPDF

doc = fitz.open('document.pdf')
for page in doc:
    text = page.get_text()
    images = page.get_images()
```

## Extraction Patterns

### Text Extraction
```python
def extract_text(pdf_path):
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        return '\n'.join(
            page.extract_text() or '' 
            for page in pdf.pages
        )
```

### Table Extraction
```python
def extract_tables(pdf_path):
    import pdfplumber
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_tables = page.extract_tables()
            for table in page_tables:
                if table:
                    tables.append(table)
    return tables
```

### Image Extraction
```python
def extract_images(pdf_path):
    import fitz
    images = []
    doc = fitz.open(pdf_path)
    for page_num, page in enumerate(doc):
        for img in page.get_images():
            xref = img[0]
            base_image = doc.extract_image(xref)
            images.append({
                'page': page_num,
                'data': base_image['image'],
                'ext': base_image['ext']
            })
    return images
```

### Form Field Extraction
```python
def extract_form_fields(pdf_path):
    from pypdf import PdfReader
    reader = PdfReader(pdf_path)
    fields = reader.get_fields()
    return {name: field.get('/V') for name, field in fields.items()}
```

## OCR Strategy (Scanned PDFs)

```python
def ocr_pdf(pdf_path):
    import fitz
    doc = fitz.open(pdf_path)
    text = []
    for page in doc:
        # Check if page has text
        page_text = page.get_text()
        if page_text.strip():
            text.append(page_text)
        else:
            # Render to image and OCR
            pix = page.get_pixmap()
            # Use Tesseract or similar OCR
            text.append(ocr_image(pix.tobytes()))
    return '\n'.join(text)
```

## Quality Checklist
- [ ] Extract text preserving structure
- [ ] Detect and extract tables
- [ ] Handle scanned PDFs with OCR
- [ ] Extract embedded images
- [ ] Read form fields