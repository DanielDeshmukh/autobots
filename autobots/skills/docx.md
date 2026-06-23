# DOCX Document Skill

## Purpose
Expert in creating, parsing, and manipulating Microsoft Word documents (.docx) programmatically using Python libraries.

## Core Libraries

### python-docx (Primary)
```python
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
```

### Key Operations

#### Create Document
```python
doc = Document()

# Add title
title = doc.add_heading('Document Title', 0)

# Add paragraphs
doc.add_paragraph('First paragraph')
doc.add_paragraph('Second paragraph')

# Add headings
doc.add_heading('Section 1', level=1)
doc.add_heading('Subsection', level=2)

# Add lists
doc.add_paragraph('Item 1', style='List Bullet')
doc.add_paragraph('Item 2', style='List Bullet')

# Add tables
table = doc.add_table(rows=3, cols=3)
table.style = 'Table Grid'
for i, row in enumerate(table.rows):
    for j, cell in enumerate(row.cells):
        cell.text = f'Row {i}, Col {j}'

# Save
doc.save('output.docx')
```

#### Read Document
```python
doc = Document('input.docx')

# Read paragraphs
for para in doc.paragraphs:
    print(para.text)

# Read tables
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            print(cell.text)
```

#### Format Text
```python
paragraph = doc.add_paragraph()
run = paragraph.add_run('Bold text')
run.bold = True
run.font.size = Pt(12)
run.font.color.rgb = RGBColor(0x00, 0x00, 0xFF)  # Blue

# Add image
doc.add_picture('image.png', width=Inches(4))
```

## Best Practices

### Document Structure
1. Use consistent heading levels (H1 → H2 → H3)
2. Apply styles consistently
3. Use tables for structured data
4. Add page breaks between sections
5. Include headers and footers

### Performance
- Use `Document()` for new files
- Use `Document.read_only()` for large files
- Process paragraphs in batches
- Avoid loading entire document into memory

### Error Handling
```python
try:
    doc = Document('file.docx')
except FileNotFoundError:
    print("File not found")
except PermissionError:
    print("Permission denied")
```

## Common Templates

### Report Template
```python
def create_report(title, sections, output_path):
    doc = Document()
    doc.add_heading(title, 0)
    
    for section in sections:
        doc.add_heading(section['title'], level=1)
        doc.add_paragraph(section['content'])
        
        if 'table' in section:
            # Add table logic
            pass
    
    doc.save(output_path)
```

### Invoice Template
```python
def create_invoice(items, total, output_path):
    doc = Document()
    doc.add_heading('Invoice', 0)
    
    # Add items table
    table = doc.add_table(rows=len(items)+1, cols=4)
    table.style = 'Table Grid'
    
    # Headers
    headers = ['Item', 'Quantity', 'Price', 'Total']
    for i, header in enumerate(headers):
        table.rows[0].cells[i].text = header
    
    # Add items
    for i, item in enumerate(items):
        table.rows[i+1].cells[0].text = item['name']
        table.rows[i+1].cells[1].text = str(item['qty'])
        table.rows[i+1].cells[2].text = f"${item['price']:.2f}"
        table.rows[i+1].cells[3].text = f"${item['total']:.2f}"
    
    # Add total
    doc.add_paragraph(f"\nTotal: ${total:.2f}")
    
    doc.save(output_path)
```

## Quality Checklist
- [ ] Proper document structure
- [ ] Consistent formatting
- [ ] No broken images or links
- [ ] Tables properly formatted
- [ ] Page breaks where needed
- [ ] Headers/footers correct
- [ ] Font sizes readable
- [ ] Colors accessible