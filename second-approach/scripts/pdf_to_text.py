import os
import argparse
from pathlib import Path
from pdf2image import convert_from_path
import pytesseract
from tqdm import tqdm

def pdf_to_text(pdf_path: str, output_path: str = None) -> str:
    """Convert a PDF file to text using OCR.
    
    Args:
        pdf_path: Path to the PDF file
        output_path: Optional path to save the text file. If None, uses the PDF name with .txt extension
    
    Returns:
        Path to the saved text file
    """
    if output_path is None:
        output_path = str(Path(pdf_path).with_suffix('.txt'))
    
    print(f"Converting {pdf_path} to text...")
    
    try:
        # Convert PDF to images
        images = convert_from_path(pdf_path)
    except Exception as e:
        raise Exception(f"Failed to convert PDF to images: {str(e)}")
    
    # Extract text from each page
    text_content = []
    failed_pages = []
    
    for i, image in enumerate(tqdm(images, desc="Processing pages")):
        try:
            # Extract text from the image
            text = pytesseract.image_to_string(image)
            text_content.append(f"--- Page {i+1} ---\n{text}\n")
        except Exception as e:
            print(f"Warning: Failed to process page {i+1}: {str(e)}")
            failed_pages.append(i+1)
            text_content.append(f"--- Page {i+1} ---\n[OCR FAILED FOR THIS PAGE]\n")
            continue
    
    if failed_pages:
        print(f"Warning: Failed to process {len(failed_pages)} pages: {failed_pages}")
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(text_content))
    
    print(f"Text saved to: {output_path}")
    return output_path

def process_directory(dir_path: str, output_dir: str = None) -> list[str]:
    """Process all PDFs in a directory.
    
    Args:
        dir_path: Path to directory containing PDFs
        output_dir: Optional output directory for text files. If None, uses same directory as PDFs
    
    Returns:
        List of paths to generated text files
    """
    dir_path = Path(dir_path)
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    pdf_files = list(dir_path.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {dir_path}")
        return []
    
    print(f"Found {len(pdf_files)} PDF files")
    output_files = []
    failed_pdfs = []
    
    for pdf_file in tqdm(pdf_files, desc="Processing PDFs"):
        try:
            if output_dir:
                output_path = str(output_dir / pdf_file.with_suffix('.txt').name)
            else:
                output_path = None
            
            output_file = pdf_to_text(str(pdf_file), output_path)
            output_files.append(output_file)
        except Exception as e:
            print(f"Error processing {pdf_file}: {str(e)}")
            failed_pdfs.append(pdf_file.name)
            continue
    
    if failed_pdfs:
        print(f"\nFailed to process {len(failed_pdfs)} PDFs:")
        for pdf in failed_pdfs:
            print(f"- {pdf}")
    
    return output_files

def main():
    parser = argparse.ArgumentParser(description='Convert PDF(s) to text using OCR')
    parser.add_argument('path', type=str, help='Path to PDF file or directory containing PDFs')
    parser.add_argument('--output', type=str, help='Output text file path (for single PDF) or directory (for multiple PDFs)')
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        raise ValueError(f"Path not found: {path}")

    if path.is_file():
        if path.suffix.lower() != '.pdf':
            raise ValueError("File must be a PDF")
        pdf_to_text(str(path), args.output)
    else:
        process_directory(str(path), args.output)

if __name__ == "__main__":
    main() 