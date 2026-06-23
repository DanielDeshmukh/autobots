# PPTX PowerPoint Skill

## Purpose
Expert in creating, parsing, and manipulating Microsoft PowerPoint presentations (.pptx) programmatically using Python libraries.

## Core Libraries

### python-pptx (Primary)
```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
```

### Key Operations

#### Create Presentation
```python
prs = Presentation()

# Add slide with title layout
slide_layout = prs.slide_layouts[0]  # Title slide
slide = prs.slides.add_slide(slide_layout)
title = slide.shapes.title
title.text = "Presentation Title"

# Add content slide
slide_layout = prs.slide_layouts[1]  # Title and content
slide = prs.slides.add_slide(slide_layout)
title = slide.shapes.title
title.text = "Slide Title"
body = slide.placeholders[1]
body.text = "Slide content goes here"

# Save
prs.save('output.pptx')
```

#### Read Presentation
```python
prs = Presentation('input.pptx')

for slide in prs.slides:
    for shape in slide.shapes:
        if hasattr(shape, "text"):
            print(shape.text)
```

#### Add Shapes & Text
```python
# Add text box
from pptx.util import Inches
left = top = width = height = Inches(1)
textbox = slide.shapes.add_textbox(left, top, width, height)
text_frame = textbox.text_frame
text_frame.text = "Hello World"

# Add shape
shape = slide.shapes.add_shape(
    MSO_SHAPE.RECTANGLE,
    Inches(1), Inches(1),
    Inches(2), Inches(2)
)
shape.fill.solid()
shape.fill.fore_color.rgb = RGBColor(0, 128, 255)
```

#### Format Text
```python
paragraph = text_frame.paragraphs[0]
run = paragraph.add_run()
run.text = "Formatted Text"
run.font.size = Pt(24)
run.font.bold = True
run.font.color.rgb = RGBColor(255, 0, 0)
paragraph.alignment = PP_ALIGN.CENTER
```

#### Add Images
```python
slide.shapes.add_picture(
    'image.png',
    Inches(1), Inches(1),
    width=Inches(4)
)
```

## Best Practices

### Slide Design
1. Use consistent layouts
2. Limit text per slide (6-8 lines max)
3. Use visuals over text
4. Maintain contrast for readability
5. Use animations sparingly

### Performance
- Reuse slide layouts
- Minimize image sizes
- Use `Presentation()` for new files
- Avoid complex animations

### Error Handling
```python
try:
    prs = Presentation('file.pptx')
except FileNotFoundError:
    print("File not found")
except Exception as e:
    print(f"Error: {e}")
```

## Common Templates

### Business Presentation
```python
def create_business_presentation(title, sections, output_path):
    prs = Presentation()
    
    # Title slide
    slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(slide_layout)
    slide.shapes.title.text = title
    
    # Content slides
    slide_layout = prs.slide_layouts[1]
    for section in sections:
        slide = prs.slides.add_slide(slide_layout)
        slide.shapes.title.text = section['title']
        
        body = slide.placeholders[1]
        body.text = section['content']
    
    prs.save(output_path)
```

### Photo Album
```python
def create_photo_album(images, output_path):
    prs = Presentation()
    
    # Title slide
    slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(slide_layout)
    slide.shapes.title.text = "Photo Album"
    
    # Photo slides
    for image in images:
        slide_layout = prs.slide_layouts[5]  # Blank layout
        slide = prs.slides.add_slide(slide_layout)
        
        # Add image
        slide.shapes.add_picture(
            image['path'],
            Inches(1), Inches(1),
            width=Inches(8)
        )
        
        # Add caption
        textbox = slide.shapes.add_textbox(
            Inches(1), Inches(6),
            Inches(8), Inches(1)
        )
        textbox.text_frame.text = image['caption']
    
    prs.save(output_path)
```

## Quality Checklist
- [ ] Consistent slide layouts
- [ ] Readable fonts (24pt+ for body)
- [ ] High contrast colors
- [ ] Images properly sized
- [ ] Animations purposeful
- [ ] Speaker notes included
- [ ] Slide numbers added
- [ ] Handout version available