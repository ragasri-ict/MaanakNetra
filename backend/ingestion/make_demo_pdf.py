import fitz
import os

txt_path = os.path.join("demo", "sample_tender.txt")
pdf_path = os.path.join("demo", "sample_tender.pdf")

with open(txt_path, "r", encoding="utf-8") as f:
    text = f.read()

sections = text.split("\nSECTION ")
doc = fitz.open()

# Page 1: Header + Scope + Operating Conditions
p1_text = sections[0].strip()
if len(sections) > 1:
    p1_text += "\n\nSECTION " + sections[1].strip()
if len(sections) > 2:
    p1_text += "\n\nSECTION " + sections[2].strip()

page1 = doc.new_page(width=595, height=842) # A4
rect = fitz.Rect(50, 50, 545, 792)
page1.insert_textbox(rect, p1_text, fontsize=9.5, fontname="helv", color=(0.1, 0.1, 0.1))

# Page 2: Electrical + Governing Standards + Performance
p2_text = ""
if len(sections) > 3:
    p2_text += "SECTION " + sections[3].strip()
if len(sections) > 4:
    p2_text += "\n\nSECTION " + sections[4].strip()
if len(sections) > 5:
    p2_text += "\n\nSECTION " + sections[5].strip()

page2 = doc.new_page(width=595, height=842)
page2.insert_textbox(rect, p2_text, fontsize=9.5, fontname="helv", color=(0.1, 0.1, 0.1))

# Page 3: Installation + Quality Assurance
p3_text = ""
if len(sections) > 6:
    p3_text += "SECTION " + sections[6].strip()
if len(sections) > 7:
    p3_text += "\n\nSECTION " + sections[7].strip()

page3 = doc.new_page(width=595, height=842)
page3.insert_textbox(rect, p3_text, fontsize=9.5, fontname="helv", color=(0.1, 0.1, 0.1))

doc.save(pdf_path)
doc.close()
print(f"Generated {pdf_path} successfully. Page count: 3")
