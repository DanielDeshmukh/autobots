# File Reading Skill

## Purpose
Universal file router — tells agents the correct tool for every format (pdf, docx, xlsx, csv, json, images, archives). No format left behind.

## Format Detection & Routing

### Text Files
| Extension | Tool | Method |
|-----------|------|--------|
| `.txt`, `.md`, `.csv` | `read()` | Direct read |
| `.json`, `.jsonl` | `json.load()` | Parse with validation |
| `.xml`, `.html` | `xml.etree` / `BeautifulSoup` | DOM parsing |
| `.yaml`, `.yml`, `.toml` | `yaml.load()` / `tomllib` | Config parsing |
| `.py`, `.js`, `.ts`, `.java`, `.go` | `read()` | Direct read |
| `.log` | `read()` with offset/limit | Streaming read |

### Document Files
| Extension | Tool | Method |
|-----------|------|--------|
| `.pdf` | `pypdf` / `pdfplumber` | Extract text, tables, images |
| `.docx` | `python-docx` | Extract paragraphs, tables, images |
| `.xlsx`, `.xls` | `openpyxl` / `pandas` | Read sheets, cells, formulas |
| `.pptx` | `python-pptx` | Extract slides, shapes, text |

### Image Files
| Extension | Tool | Method |
|-----------|------|--------|
| `.png`, `.jpg`, `.jpeg` | `PIL/Pillow` | Open, resize, analyze |
| `.gif` | `PIL/Pillow` | Read frames |
| `.svg` | `xml.etree` | Parse XML structure |
| `.webp` | `PIL/Pillow` | Convert or analyze |

### Data Files
| Extension | Tool | Method |
|-----------|------|--------|
| `.csv` | `pandas` / `csv` | Tabular read |
| `.parquet` | `pandas` | Columnar read |
| `.sqlite`, `.db` | `sqlite3` | Query execution |
| `.h5`, `.hdf5` | `h5py` | Array read |

### Archive Files
| Extension | Tool | Method |
|-----------|------|--------|
| `.zip` | `zipfile` | Extract contents |
| `.tar`, `.gz` | `tarfile` | Extract contents |
| `.7z` | `py7zr` | Extract contents |

## Reading Patterns

### Safe Read with Fallback
```python
def safe_read(path, encodings=('utf-8', 'latin-1', 'cp1252')):
    for enc in encodings:
        try:
            return Path(path).read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Cannot decode {path}")
```

### Chunked Read for Large Files
```python
def read_chunks(path, chunk_size=8192):
    with open(path, 'r', encoding='utf-8') as f:
        while chunk := f.read(chunk_size):
            yield chunk
```

### Format-Aware Read
```python
def read_file(path):
    ext = Path(path).suffix.lower()
    if ext == '.pdf':
        return read_pdf(path)
    elif ext == '.docx':
        return read_docx(path)
    elif ext in ('.xlsx', '.xls'):
        return read_excel(path)
    elif ext == '.json':
        return json.loads(Path(path).read_text())
    else:
        return Path(path).read_text(encoding='utf-8')
```

## Quality Checklist
- [ ] Detect file format before reading
- [ ] Handle encoding errors gracefully
- [ ] Support chunked reading for large files
- [ ] Validate structure after reading
- [ ] Return consistent output format