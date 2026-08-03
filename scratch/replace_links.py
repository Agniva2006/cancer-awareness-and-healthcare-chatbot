import pypdf
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
resume_path = BASE_DIR / "resume.pdf"
output_path = BASE_DIR / "resume.pdf"

reader = pypdf.PdfReader(str(resume_path))
writer = pypdf.PdfWriter()

for page in reader.pages:
    writer.add_page(page)

page = writer.pages[0]

if "/Annots" in page:
    annots = page["/Annots"]
    for annot in annots:
        annot_obj = annot.get_object()
        if "/A" in annot_obj and "/URI" in annot_obj["/A"]:
            uri = annot_obj["/A"]["/URI"]
            if "iota-woad" in uri or "frontend-iota" in uri:
                print("Found old URI to replace:", uri)
                # Simple native dict update
                annot_obj["/A"].update({
                    "/URI": "https://cancer-awareness-and-healthcare-cha.vercel.app"
                })
                print("Updated to:", annot_obj["/A"]["/URI"])

with open(str(output_path), "wb") as f:
    writer.write(f)

print("Updated links successfully saved in PDF!")
