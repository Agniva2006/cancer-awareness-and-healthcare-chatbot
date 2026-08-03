import pypdf
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
resume_path = BASE_DIR / "resume.pdf"

reader = pypdf.PdfReader(str(resume_path))
page = reader.pages[0]
text = page.extract_text()

with open("scratch/extracted_text.txt", "w", encoding="utf-8") as f:
    f.write(text)

print("Saved text of length:", len(text))
print("Keywords present in file:")
for kw in ["OncoGraph", "Cancer AI", "Osimertinib", "NetworkX", "FedAvg", "Gini"]:
    print(f"'{kw}':", kw.lower() in text.lower())
