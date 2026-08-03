import pypdf
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
resume_path = BASE_DIR / "resume.pdf"
output_path = BASE_DIR / "resume.pdf"

reader = pypdf.PdfReader(str(resume_path))
writer = pypdf.PdfWriter()

# Copy pages to writer
for page in reader.pages:
    writer.add_page(page)

# Get the first page of the writer
writer_page = writer.pages[0]

# Modify the contents stream directly
contents = writer_page["/Contents"].get_object()
data = contents.get_data()

old_block = (
    b"[(Cancer)-394(AI)-395(Assistan)33(t)-394(2.0)-395(|)-394(RA)33(G-P)33(o)33(w)32(ered)-394(Medical)-394(Pla)-1(t)1(form)]TJ"
    b"/F41 8.9664 Tf [-11994(F)85(astAPI,)-342(Gro)-29(q)-342(Llama-3-70B,)-343(Scikit-learn)]TJ"
    b"/F47 8.9664 Tf 0 -10.411 Td [(\\210)]TJ"
    b"/F41 8.9664 Tf [-555(Built)-373(an)-373(end-to-end)-373(Retriev)57(al-Augmen)29(ted)-373(Generation)-373(\\050RA)28(G\\051)-373(applica)1(tion)-373(using)-373(F)85(astAPI,)-373(TF-IDF)-373(cosine)-373(similarit)29(y)-373(retriev)57(al,)-381(and)-373(Gro)-28(q)]TJ "
    b"9.587 -10.411 Td [(Llama-3-70B)-343(for)-342(highly)-343(resp)-28(onsiv)28(e)-342(cancer)-343(information)-342(querying.)]TJ"
    b"/F47 8.9664 Tf -9.587 -10.411 Td [(\\210)]TJ"
    b"/F41 8.9664 Tf [-555(Designed)-278(a)-278(secure)-277(con)28(t)1(ext-grounding)-278(prompt)-277(engineering)-278(w)29(ork\\015o)28(w)-277(equipp)-29(ed)-277(with)-278(safet)29(y)-278(heuristic)-278(la)29(y)29(ers)-278(to)-278(strictly)-277(prev)28(en)29(t)-278(direct)-277(medical)]TJ "
    b"9.587 -10.411 Td [(diagnosis)-343(out)1(put.)]TJ"
    b"/F47 8.9664 Tf -9.587 -10.411 Td [(\\210)]TJ"
    b"/F41 8.9664 Tf [-555(Engineered)-377(a)-376(top-tier)-376(UI)-377(featu)1(ring)-377(V)86(oice-to-T)86(ext)-377(in)29(teraction,)-385(dynamic)-376(topic)-376(infographics,)-385(session)-376(metrics)-377(trac)29(king,)-385(and)-376(p)-29(ersisten)29(t)-376(c)28(hat)]TJ "
    b"9.587 -10.411 Td [(history)-343(via)]TJ"
    b"/F48 8.9664 Tf [-342(localStorage)]TJ"
    b"/F41 8.9664 Tf [(.)]TJ"
)

new_block = (
    b"[(OncoGraph)-394(AI)-395(|)-394(Clinical)-394(Oncology)-394(Decision)-394(Support)-394(Workspace)]TJ"
    b"/F41 8.9664 Tf [-11994(F)85(astAPI,)-342(Scikit-learn,)-342(Ne)28(t)1(workX,)-342(NumP)29(y)]TJ"
    b"/F47 8.9664 Tf 0 -10.411 Td [(\\210)]TJ"
    b"/F41 8.9664 Tf [-555(Engineered)-373(a)-373(relational)-373(Knowledge)-373(Graph)-373(using)-373(Ne)28(t)1(workX)-373(mapping)-373(50+)-373(biomarker/toxicity)]TJ "
    b"9.587 -10.411 Td [(nodes,)-343(guaran)29(teeing)-342(100%)-343(NCCN/WHO)-342(clinical)-343(guideline)-342(compliance.)]TJ"
    b"/F47 8.9664 Tf -9.587 -10.411 Td [(\\210)]TJ"
    b"/F41 8.9664 Tf [-555(Designed)-278(a)-278(collabora)1(tiv)28(e)-278(Multi-Agent)-278(Swarm)-278(orchestrator)-277(to)-278(simulate)-278(multidisciplinar)29(y)]TJ "
    b"9.587 -10.411 Td [(tumor)-343(board)-342(consensus)-343(and)-342(active)-343(clinical)-342(trial)-343(matching.)]TJ"
    b"/F47 8.9664 Tf -9.587 -10.411 Td [(\\210)]TJ"
    b"/F41 8.9664 Tf [-555(Implemented)-377(prognosis)-377(staging)-376(prediction)-376(via)-377(Random)-377(F)85(orest)-377(models)-376(with)-377(local)-377(Gini)]TJ "
    b"9.587 -10.411 Td [(importances,)-343(DICOM/pathology)-342(image)-343(routing,)-342(and)-343(FedA)29(vg)-342(federated)-343(learning.)]TJ"
)

if old_block in data:
    print("Found exact block!")
    new_data = data.replace(old_block, new_block)
    
    # Set data directly on the ContentStream object
    contents.set_data(new_data)
    
    # Tell pypdf to update the stream dictionary
    # In some pypdf versions, the writer's objects must be saved
    with open(str(output_path), "wb") as f:
        writer.write(f)
    print("Updated PDF written successfully!")
else:
    print("Old block not found.")
