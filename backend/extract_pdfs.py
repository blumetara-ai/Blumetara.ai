import sys
from pypdf import PdfReader

def extract_pdf_to_text(pdf_path, text_path):
    print(f"Extracting {pdf_path} to {text_path}...")
    try:
        reader = PdfReader(pdf_path)
        with open(text_path, "w", encoding="utf-8") as f:
            for i, page in enumerate(reader.pages):
                f.write(f"\n--- PAGE {i+1} ---\n")
                text = page.extract_text()
                if text:
                    f.write(text)
        print("Success!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    extract_pdf_to_text(
        "/Users/pranav_ns/Desktop/Blumetara.ai/Untitled document (4).pdf",
        "/Users/pranav_ns/Desktop/Blumetara.ai/untitled_doc_4.txt"
    )
    extract_pdf_to_text(
        "/Users/pranav_ns/Desktop/Blumetara.ai/ilovepdf_merged.pdf",
        "/Users/pranav_ns/Desktop/Blumetara.ai/ilovepdf_merged.txt"
    )
