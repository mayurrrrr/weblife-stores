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
                r"(?:intel|amd)[\s®]*(?:core\s*)?(?:i[3579]|ryzen|pentium|celeron)[\s-]*\d*[a-z]*\d*[a-z]*",
                r"processor:\s*([^\n\r]+)",
                r"cpu:\s*([^\n\r]+)",
                r"\b(?:i3|i5|i7|i9)[\s-]\d{4}[a-z]*\b",
                r"\bryzen\s*[357]\s*\d{4}[a-z]*\b"
            ],
            "ram": [
                r"\b\d+\s*gb\s*(?:ddr[45]|lpddr[45]|memory|ram)\b",
                r"\b(?:4|8|16|32|64)\s*gb\s*(?:memory|ram)\b",
                r"memory:\s*([^\n\r]+)",
                r"\b\d+\s*gb\s*ddr[45][\s-]\d+\b"
            ],
            "storage": [
                r"\b\d+\s*(?:gb|tb)\s*(?:ssd|nvme|m\.2|pcie)\b",
                r"\b(?:256|512|1024|1|2)\s*(?:gb|tb)\s*ssd\b",
                r"storage:\s*([^\n\r]+)",
                r"\b\d+\s*(?:gb|tb)\s*(?:hard\s*drive|hdd)\b"
            ],
            "display": [
                r"\b1[34]\.\d+[\"']\s*(?:fhd|hd|4k|oled|ips|lcd)\b",
                r"\b\d{4}\s*[x×]\s*\d{4}\s*(?:resolution|pixels?)\b",
                r"display:\s*([^\n\r]+)",
                r"\b(?:14|15\.6|13\.3)[\"']\s*(?:screen|display|monitor)\b"
            ],
            "graphics": [
                r"(?:intel|amd|nvidia)[\s®]*(?:iris|radeon|geforce|gtx|rtx|uhd|xe)\s*(?:graphics?|gpu)?\s*\d*[a-z]*",
                r"graphics:\s*([^\n\r]+)",
                r"\b(?:integrated|discrete)\s*graphics?\b",
                r"\bgtx\s*\d{4}[a-z]*\b|\brtx\s*\d{4}[a-z]*\b"
            ],
            "battery": [
                r"\b\d+\s*wh\s*(?:battery|lithium)\b",
                r"\b\d+[\s-]cell\s*battery\b",
                r"battery:\s*([^\n\r]+)",
                r"\b(?:up\s*to\s*)?\d+\s*hours?\s*battery\s*life\b"
            ],
            "ports": [
                r"\b\d+\s*[x×]\s*usb[\s-]?[abc]?\s*(?:\d\.\d)?\b",
                r"\b(?:hdmi|thunderbolt|displayport|ethernet|rj[\s-]?45)\b",
                r"ports?:\s*([^\n\r]+)",
                r"\b(?:audio|headphone)\s*(?:jack|port)\b"
            ],
            "dimensions": [
                r"\b\d+\.?\d*\s*[x×]\s*\d+\.?\d*\s*[x×]\s*\d+\.?\d*\s*(?:mm|cm|in|inches?)\b",
                r"dimensions:\s*([^\n\r]+)",
                r"\b(?:width|height|depth):\s*\d+\.?\d*\s*(?:mm|cm|in)\b"
            ],
            "weight": [
                r"\b\d+\.?\d*\s*(?:kg|lbs?|pounds?)\b",
                r"weight:\s*([^\n\r]+)",
                r"\bstarting\s*(?:at\s*)?\d+\.?\d*\s*(?:kg|lbs?)\b"
            ],
            "operating_system": [
                r"windows\s*\d+\s*(?:home|pro|enterprise)?",
                r"(?:ubuntu|linux|chrome\s*os|mac\s*os)",
                r"operating\s*system:\s*([^\n\r]+)",
                r"\b(?:dos|free\s*dos|no\s*os)\b"
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
        """Extract specifications from PDF text using improved regex patterns."""
        specs = {}
        
        for spec_category, patterns in self.spec_patterns.items():
            matches = []
            for pattern in patterns:
                found = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                matches.extend(found)
            
            if matches:
                # Clean and validate matches
                cleaned_matches = []
                for match in matches:
                    if isinstance(match, tuple):
                        match = ' '.join(match)
                    
                    cleaned = match.strip()
                    # More stringent filtering
                    if (cleaned and 
                        len(cleaned) > 2 and 
                        len(cleaned) < 100 and  # Not too long
                        not cleaned.startswith(('*', '•', '-', '(', '[')) and  # Not bullets/notes
                        not cleaned.endswith((':', '**', '*'))):  # Not headers
                        
                        # Additional category-specific validation
                        if self._is_valid_spec(spec_category, cleaned):
                            cleaned_matches.append(cleaned)
                
                # Remove duplicates and similar matches
                unique_matches = self._deduplicate_matches(cleaned_matches)
                
                if unique_matches:
                    specs[spec_category] = unique_matches[:5]  # Keep top 5 matches
        
        return specs
    
    def _is_valid_spec(self, category: str, text: str) -> bool:
        """Validate if extracted text is actually a valid specification."""
        text_lower = text.lower()
        
        # Category-specific validation
        if category == "cpu":
            return any(term in text_lower for term in ['intel', 'amd', 'processor', 'core', 'ryzen', 'i3', 'i5', 'i7', 'i9'])
        elif category == "ram":
            return any(term in text_lower for term in ['gb', 'memory', 'ram', 'ddr']) and any(num in text for num in ['4', '8', '16', '32', '64'])
        elif category == "storage":
            return any(term in text_lower for term in ['gb', 'tb', 'ssd', 'nvme', 'storage', 'drive'])
        elif category == "display":
            return any(term in text_lower for term in ['display', 'screen', 'resolution', 'fhd', 'hd', '1920', '1366', '"', 'inch'])
        elif category == "graphics":
            return any(term in text_lower for term in ['graphics', 'gpu', 'intel', 'amd', 'nvidia', 'integrated', 'iris', 'xe', 'radeon'])
        elif category == "battery":
            return any(term in text_lower for term in ['wh', 'battery', 'cell', 'hour', 'life'])
        elif category == "ports":
            return any(term in text_lower for term in ['usb', 'hdmi', 'port', 'thunderbolt', 'ethernet', 'audio', 'jack'])
        elif category == "weight":
            return any(term in text_lower for term in ['kg', 'lb', 'pound', 'weight']) and any(char.isdigit() for char in text)
        elif category == "dimensions":
            return ('x' in text_lower or '×' in text) and any(char.isdigit() for char in text)
        elif category == "operating_system":
            return any(term in text_lower for term in ['windows', 'linux', 'ubuntu', 'chrome', 'mac', 'dos'])
        
        return True  # Default to valid for other categories
    
    def _deduplicate_matches(self, matches: List[str]) -> List[str]:
        """Remove duplicate and very similar matches."""
        if not matches:
            return []
        
        unique_matches = []
        for match in matches:
            # Check if this match is significantly different from existing ones
            is_unique = True
            for existing in unique_matches:
                # Simple similarity check - if 80% of words are the same, consider duplicate
                match_words = set(match.lower().split())
                existing_words = set(existing.lower().split())
                if len(match_words & existing_words) / max(len(match_words), len(existing_words)) > 0.8:
                    is_unique = False
                    break
            
            if is_unique:
                unique_matches.append(match)
        
        return unique_matches
    
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
