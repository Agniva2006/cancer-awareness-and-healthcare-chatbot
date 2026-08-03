import pypdf
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
resume_path = BASE_DIR / "resume.pdf"

reader = pypdf.PdfReader(str(resume_path))
page = reader.pages[0]
text = page.extract_text()

# Check for keywords
print("Keywords check in updated PDF text extraction:")
for word in ["OncoGraph", "Cancer AI", "Subway", "MDT", "Random Forest", "Gini", "FedAvg", "Knowledge Graph"]:
    print(f"'{word}':", word in text)

print("\nFull Text excerpt around OncoGraph:")
idx = text.find("OncoGraph")
if idx != -1:
    print(text[max(0, idx-50):min(len(text), idx+500)])
else:
    print("OncoGraph not found in extracted text!")
