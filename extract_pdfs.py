import os
import fitz

files_dir = "Files"
output_file = "all_guidelines_pymupdf.md"

with open(output_file, "w", encoding="utf-8") as out:
    for filename in sorted(os.listdir(files_dir)):
        if filename.endswith(".pdf"):
            out.write(f"# {filename}\n\n")
            filepath = os.path.join(files_dir, filename)
            try:
                doc = fitz.open(filepath)
                for page in doc:
                    text = page.get_text("text")
                    if text:
                        out.write(text + "\n")
            except Exception as e:
                out.write(f"Error reading {filename}: {e}\n")
            out.write("\n---\n\n")
print(f"Extracted all text to {output_file}")
