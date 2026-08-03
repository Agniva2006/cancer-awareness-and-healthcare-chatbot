import pypdf
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
resume_path = BASE_DIR / "resume.pdf"

reader = pypdf.PdfReader(str(resume_path))
page = reader.pages[0]

if "/Annots" in page:
    annots = page["/Annots"]
    for annot in annots:
        annot_obj = annot.get_object()
        if "/A" in annot_obj and "/URI" in annot_obj["/A"]:
            print("Link URI:", annot_obj["/A"]["/URI"])
else:
    print("No links found on page!")
