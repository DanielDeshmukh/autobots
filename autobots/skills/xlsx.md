# XLSX Excel Skill

## Purpose
Expert in creating, parsing, and manipulating Microsoft Excel spreadsheets (.xlsx) programmatically using Python libraries.

## Core Libraries

### openpyxl (Primary)
```python
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, Reference
```

### Key Operations

#### Create Workbook
```python
wb = Workbook()
ws = wb.active
ws.title = "Sheet1"

# Add data
ws['A1'] = 'Name'
ws['B1'] = 'Age'
ws['C1'] = 'City'

ws['A2'] = 'Alice'
ws['B2'] = 30
ws['C2'] = 'New York'

# Save
wb.save('output.xlsx')
```

#### Read Workbook
```python
wb = load_workbook('input.xlsx')
ws = wb.active

# Read cells
for row in ws.iter_rows(min_row=1, max_row=ws.max_row, values_only=True):
    print(row)

# Read specific range
for row in ws['A1:C10']:
    for cell in row:
        print(cell.value)
```

#### Format Cells
```python
# Font formatting
ws['A1'].font = Font(bold=True, size=12, color='000000')

# Fill formatting
ws['A1'].fill = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')

# Alignment
ws['A1'].alignment = Alignment(horizontal='center', vertical='center')

# Border
thin_border = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin')
)
ws['A1'].border = thin_border
```

#### Column Width & Row Height
```python
ws.column_dimensions['A'].width = 20
ws.row_dimensions[1].height = 30
```

### Charts
```python
# Create chart
chart = BarChart()
chart.title = "Sales Data"
chart.y_axis.title = "Amount"
chart.x_axis.title = "Month"

# Add data
data = Reference(ws, min_col=2, min_row=1, max_row=12)
cats = Reference(ws, min_col=1, min_row=2, max_row=12)
chart.add_data(data, titles_from_data=True)
chart.set_categories(cats)

ws.add_chart(chart, "E1")
```

## Best Practices

### Data Organization
1. Use headers in first row
2. Consistent data types per column
3. Remove empty rows/columns
4. Use proper column widths
5. Freeze panes for headers

### Performance
- Use `write_only=True` for large files
- Read specific ranges instead of entire sheet
- Avoid unnecessary formatting
- Use `load_workbook(read_only=True)` for reading

### Error Handling
```python
try:
    wb = load_workbook('file.xlsx')
except FileNotFoundError:
    print("File not found")
except Exception as e:
    print(f"Error: {e}")
```

## Common Templates

### Data Report
```python
def create_data_report(data, output_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Report"
    
    # Add headers
    headers = list(data[0].keys())
    for col, header in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=header)
        ws.cell(row=1, column=col).font = Font(bold=True)
    
    # Add data
    for row_idx, row_data in enumerate(data, 2):
        for col_idx, value in enumerate(row_data.values(), 1):
            ws.cell(row=row_idx, column=col_idx, value=value)
    
    # Auto-fit columns
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 15
    
    wb.save(output_path)
```

### Financial Model
```python
def create_financial_model(projections, output_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Financial Model"
    
    # Add projection data
    for i, projection in enumerate(projections):
        ws.cell(row=i+1, column=1, value=projection['month'])
        ws.cell(row=i+1, column=2, value=projection['revenue'])
        ws.cell(row=i+1, column=3, value=projection['expenses'])
        ws.cell(row=i+1, column=4, value=projection['profit'])
    
    # Add formulas
    for row in range(2, len(projections) + 2):
        ws.cell(row=row, column=4).value = f'=B{row}-C{row}'
    
    wb.save(output_path)
```

## Quality Checklist
- [ ] Proper header row
- [ ] Consistent data types
- [ ] Formatted for readability
- [ ] Charts properly configured
- [ ] Formulas correct
- [ ] Print area set
- [ ] Page breaks appropriate
- [ ] No circular references