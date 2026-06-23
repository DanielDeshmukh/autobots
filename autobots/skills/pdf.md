# PDF Document Skill

## Purpose
Expert in creating, parsing, and manipulating PDF documents programmatically using Python libraries.

## Core Libraries

### reportlab (Primary for Creation)
```python
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
```

### PyPDF2 (Primary for Reading)
```python
from PyPDF2 import PdfReader, PdfWriter
```

### Key Operations

#### Create PDF
```python
def create_pdf(filename, content):
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Add title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        alignment=TA_CENTER,
        spaceAfter=30
    )
    story.append(Paragraph(content['title'], title_style))
    story.append(Spacer(1, 12))
    
    # Add content
    for paragraph in content['paragraphs']:
        story.append(Paragraph(paragraph, styles['Normal']))
        story.append(Spacer(1, 12))
    
    # Add table
    if 'table' in content:
        table_data = content['table']
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), HexColor('#ecf0f1')),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#bdc3c7'))
        ]))
        story.append(table)
    
    doc.build(story)
```

#### Read PDF
```python
def read_pdf(filename):
    reader = PdfReader(filename)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text
```

#### Merge PDFs
```python
def merge_pdfs(pdf_list, output_path):
    writer = PdfWriter()
    for pdf in pdf_list:
        reader = PdfReader(pdf)
        for page in reader.pages:
            writer.add_page(page)
    with open(output_path, 'wb') as f:
        writer.write(f)
```

## Best Practices

### Document Design
1. Use proper margins (1 inch default)
2. Choose readable fonts (Helvetica, Times Roman)
3. Limit font sizes (12pt body, 24pt title)
4. Use consistent spacing
5. Add page numbers

### Performance
- Use `SimpleDocTemplate` for simple documents
- Build story incrementally for large documents
- Use `Spacer` for consistent spacing
- Avoid complex graphics when possible

### Error Handling
```python
try:
    doc = SimpleDocTemplate('output.pdf', pagesize=letter)
except Exception as e:
    print(f"Error creating PDF: {e}")
```

## Common Templates

### Report Template
```python
def create_report(title, sections, output_path):
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    story.append(Paragraph(title, styles['Title']))
    story.append(Spacer(1, 30))
    
    # Sections
    for section in sections:
        story.append(Paragraph(section['heading'], styles['Heading1']))
        story.append(Spacer(1, 12))
        story.append(Paragraph(section['content'], styles['Normal']))
        story.append(Spacer(1, 24))
    
    doc.build(story)
```

### Invoice Template
```python
def create_invoice(invoice_data, output_path):
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Header
    story.append(Paragraph("INVOICE", styles['Title']))
    story.append(Spacer(1, 30))
    
    # Invoice details
    details = [
        f"Invoice #: {invoice_data['number']}",
        f"Date: {invoice_data['date']}",
        f"Due Date: {invoice_data['due_date']}"
    ]
    for detail in details:
        story.append(Paragraph(detail, styles['Normal']))
    
    story.append(Spacer(1, 30))
    
    # Items table
    table_data = [['Item', 'Quantity', 'Price', 'Total']]
    for item in invoice_data['items']:
        table_data.append([
            item['name'],
            str(item['qty']),
            f"${item['price']:.2f}",
            f"${item['total']:.2f}"
        ])
    
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, HexColor('#bdc3c7'))
    ]))
    story.append(table)
    
    # Total
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"Total: ${invoice_data['total']:.2f}", styles['Normal']))
    
    doc.build(story)
```

## Quality Checklist
- [ ] Proper page size (letter/A4)
- [ ] Readable fonts and sizes
- [ ] Consistent margins
- [ ] Page numbers included
- [ ] Headers/footers correct
- [ ] Images properly sized
- [ ] Tables formatted
- [ ] No broken layouts