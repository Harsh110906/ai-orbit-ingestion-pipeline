from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
import os

def generate_pdf():
    pdf_path = os.path.join(os.getcwd(), 'docs', 'architecture.pdf')
    md_path = os.path.join(os.getcwd(), 'docs', 'architecture.md')
    
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter
    y = height - 50
    
    for line in content.split('\n'):
        # simple text drawing, stripping markdown
        text = line.replace('#', '').strip()
        if not text:
            y -= 15
            continue
            
        lines = simpleSplit(text, 'Helvetica', 12, width - 100)
        for l in lines:
            if y < 50:
                c.showPage()
                y = height - 50
            c.drawString(50, y, l)
            y -= 15
    c.save()
    print(f"Generated {pdf_path}")

if __name__ == '__main__':
    generate_pdf()
