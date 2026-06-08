# NVIDIA Retrieval Pipeline

## Document Type Handlers

### PDF Processing
```python
import fitz  # PyMuPDF

def extract_pdf(pdf_path: str) -> list[dict]:
    doc = fitz.open(pdf_path)
    pages = []
    for page_num, page in enumerate(doc):
        text = page.get_text("text")
        tables = page.find_tables()
        images = page.get_images()
        pages.append({
            "page": page_num + 1,
            "text": text,
            "tables": [extract_table(t) for t in tables],
            "image_count": len(images),
        })
    return pages
```

### Image Processing (OCR)
```python
from PIL import Image
import pytesseract

def extract_image_text(image_path: str) -> str:
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img)
    return text
```

### Audio Transcription
```python
import whisper

def transcribe_audio(audio_path: str) -> dict:
    model = whisper.load_model("base")
    result = model.transcribe(audio_path)
    return {
        "text": result["text"],
        "segments": result["segments"],
        "language": result["language"],
    }
```

## Unified Retrieval Interface
```python
def retrieve(query: str, doc_types: list[str] = None, top_k: int = 5):
    # Embed query
    query_emb = embed(query)
    
    # Search across relevant collections
    results = []
    for collection in get_collections(doc_types):
        hits = collection.search(query_emb, top_k)
        results.extend(hits)
    
    # Rerank and return top_k
    return rerank(query, results)[:top_k]
```
