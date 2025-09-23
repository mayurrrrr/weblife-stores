"""PDF parser to extract laptop specifications from PDF documents."""

import fitz  # PyMuPDF
import json
import re
from pathlib import Path
from typing import Dict, Any, List
from app.config import PDF_MAPPINGS

class PDFParser:
    def __init__(self):
        self.spec_patterns = {
            "cpu": [
                r"processor[:\s]*([^\n]+)",
                r"cpu[:\s]*([^\n]+)",
                r"intel[®\s]*([^\n]+)",
                r"amd[®\s]*([^\n]+)"
            ],
            "ram": [
                r"memory[:\s]*([^\n]+)",
                r"ram[:\s]*([^\n]+)",
                r"(\d+\s*gb.*?memory)",
                r"(\d+\s*gb.*?ram)"
            ],
            "storage": [
                r"storage[:\s]*([^\n]+)",
                r"hard drive[:\s]*([^\n]+)",
                r"ssd[:\s]*([^\n]+)",
                r"(\d+\s*gb.*?ssd)",
                r"(\d+\s*tb.*?ssd)"
            ],
            "display": [
                r"display[:\s]*([^\n]+)",
                r"screen[:\s]*([^\n]+)",
                r"(\d+\.?\d*[\"\s]*.*?display)",
                r"(\d+x\d+.*?resolution)"
            ],
            "graphics": [
                r"graphics[:\s]*([^\n]+)",
                r"gpu[:\s]*([^\n]+)",
                r"video[:\s]*([^\n]+)"
            ],
            "battery": [
                r"battery[:\s]*([^\n]+)",
                r"(\d+\s*wh.*?battery)",
                r"(\d+\s*cell.*?battery)"
            ],
            "ports": [
                r"ports[:\s]*([^\n]+)",
                r"connectivity[:\s]*([^\n]+)",
                r"i/o[:\s]*([^\n]+)"
            ],
            "dimensions": [
                r"dimensions[:\s]*([^\n]+)",
                r"size[:\s]*([^\n]+)",
                r"(\d+\.?\d*\s*x\s*\d+\.?\d*\s*x\s*\d+\.?\d*)"
            ],
            "weight": [
                r"weight[:\s]*([^\n]+)",
                r"(\d+\.?\d*\s*kg)",
                r"(\d+\.?\d*\s*lbs?)"
            ],
            "operating_system": [
                r"operating system[:\s]*([^\n]+)",
                r"os[:\s]*([^\n]+)",
                r"windows[:\s]*([^\n]+)"
            ]
        }
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract all text from a PDF file."""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except Exception as e:
            print(f"Error reading PDF {pdf_path}: {e}")
            return ""
    
    def extract_specifications(self, text: str) -> Dict[str, Any]:
        """Extract specifications from PDF text using regex patterns."""
        specs = {}
        text_lower = text.lower()
        
        for spec_category, patterns in self.spec_patterns.items():
            matches = []
            for pattern in patterns:
                found = re.findall(pattern, text_lower, re.IGNORECASE | re.MULTILINE)
                matches.extend(found)
            
            if matches:
                # Clean and deduplicate matches
                cleaned_matches = []
                for match in matches:
                    if isinstance(match, tuple):
                        match = ' '.join(match)
                    cleaned = match.strip()
                    if cleaned and len(cleaned) > 3:  # Filter out very short matches
                        cleaned_matches.append(cleaned)
                
                # Remove duplicates while preserving order
                unique_matches = []
                for match in cleaned_matches:
                    if match not in unique_matches:
                        unique_matches.append(match)
                
                specs[spec_category] = unique_matches[:3] if len(unique_matches) > 3 else unique_matches
        
        return specs
    
    def parse_pdf(self, pdf_path: str, model_key: str) -> Dict[str, Any]:
        """Parse a single PDF and extract specifications."""
        if not Path(pdf_path).exists():
            print(f"PDF file not found: {pdf_path}")
            return {}
        
        print(f"Parsing PDF: {pdf_path}")
        text = self.extract_text_from_pdf(pdf_path)
        
        if not text:
            print(f"No text extracted from {pdf_path}")
            return {}
        
        specs = self.extract_specifications(text)
        
        # Add metadata
        result = {
            "model_key": model_key,
            "source_pdf": pdf_path,
            "specifications": specs,
            "text_length": len(text)
        }
        
        return result
    
    def parse_all_pdfs(self) -> Dict[str, Any]:
        """Parse all PDFs defined in PDF_MAPPINGS."""
        results = {}
        
        for model_key, pdf_filename in PDF_MAPPINGS.items():
            pdf_path = Path(pdf_filename)
            if pdf_path.exists():
                result = self.parse_pdf(str(pdf_path), model_key)
                if result:
                    results[model_key] = result
                    # Save individual JSON file
                    output_file = f"{model_key}_specs.json"
                    with open(output_file, 'w') as f:
                        json.dump(result, f, indent=2)
                    print(f"Saved specifications to {output_file}")
            else:
                print(f"PDF not found: {pdf_filename}")
        
        return results

def main():
    """Main function to parse all PDFs."""
    parser = PDFParser()
    results = parser.parse_all_pdfs()
    
    # Save combined results
    with open("all_laptop_specs.json", 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Parsed {len(results)} PDF files successfully!")
    print("Individual spec files and combined 'all_laptop_specs.json' have been created.")

if __name__ == "__main__":
    main()
