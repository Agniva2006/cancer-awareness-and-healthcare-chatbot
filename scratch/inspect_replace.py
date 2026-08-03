import pypdf
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
resume_path = BASE_DIR / "resume.pdf"

reader = pypdf.PdfReader(str(resume_path))
page = reader.pages[0]
contents = page.get_contents()
data = contents.get_data()

print("Is old_block in the updated PDF stream?", b"[(Cancer)" in data)
print("Is new_block in the updated PDF stream?", b"[(OncoGraph)" in data)

# Let's inspect what is in the stream around index 7150
idx = data.find(b"[(Cancer)")
if idx != -1:
    print("Found '[(Cancer)' at:", idx)
    print(data[idx:idx+200])
else:
    idx2 = data.find(b"[(OncoGraph)")
    print("Found '[(OncoGraph)' at:", idx2)
    print(data[idx2:idx2+200] if idx2 != -1 else "Neither found!")
