import pdfplumber
import pandas as pd
import re
import io
from pdfminer.high_level import extract_text
from rapidfuzz import process, fuzz
try:
    from PIL import Image
    import pytesseract
    from pdf2image import convert_from_path, convert_from_bytes
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

from src.data_processor import SCHEDULE_III_SCHEMA

class PDFExtractor:
    def __init__(self):
        self.extraction_method = "Unknown"
        self.confidence_scores = {} # Key: Field Name, Value: Score (High, Medium, Low)

    def extract(self, file_bytes):
        """
        Main entry point to extract data from a PDF file (bytes).
        Returns a DataFrame and extraction metadata.
        """
        self.extraction_method = "Table Parser (pdfplumber)"
        raw_text = ""
        tables = []
        
        # 1. Try pdfplumber for tables and text
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                full_text = []
                for page in pdf.pages:
                    full_text.append(page.extract_text() or "")
                    extracted_tables = page.extract_tables()
                    if extracted_tables:
                        tables.extend(extracted_tables)
                raw_text = "\n".join(full_text)
        except Exception as e:
            print(f"pdfplumber failed: {e}")

        # 2. Parsing Strategy
        # If we found good tables, using them is usually best for numbers.
        # But often tables are fragmented. 
        # Strategy: Text-based Regex parsing is often more robust for specific line items 
        # if tables are messy. We will try to structure data from text first if tables are few.
        
        # If text is too short, native extraction failed -> Try OCR
        if len(raw_text) < 100: 
            if OCR_AVAILABLE:
                self.extraction_method = "OCR (Tesseract)"
                try:
                    images = convert_from_bytes(file_bytes)
                    ocr_text = []
                    for img in images:
                        ocr_text.append(pytesseract.image_to_string(img))
                    raw_text = "\n".join(ocr_text)
                except Exception as e:
                    print(f"OCR failed: {e}")
                    self.extraction_method = "Failed"
            else:
                self.extraction_method = "Native Extraction Failed (OCR specific dependencies missing)"
        
        elif not tables:
             self.extraction_method = "Raw Text Parser (pdfminer)"

        # 3. Process the content
        df = self._parse_text_to_dataframe(raw_text)
        
        return df, self.extraction_method

    def extract_fiscal_year(self, text):
        """
        Attempts to detect the Fiscal Year from text.
        Returns the ending year (e.g. "2022-23" -> 2023).
        """
        # Patterns to look for
        # 1. "Annual Report 2022-23" or "2022-2023"
        matches = re.findall(r'20[12][0-9][\-\–]20?[12][0-9]', text)
        if matches:
            # Take the last part of "2022-23" -> 23 -> 2023
            # OR "2022-2023" -> 2023
            last_match = matches[0] # Usually Title is at top
            parts = re.split(r'[\-\–]', last_match)
            if len(parts) == 2:
                end_str = parts[1]
                if len(end_str) == 2: return int("20" + end_str)
                if len(end_str) == 4: return int(end_str)
        
        # 2. "FY23" or "FY 2023"
        matches = re.findall(r'FY\s?[-]?\s?(20[12][0-9]|[0-9]{2})', text, re.IGNORECASE)
        if matches:
            val = matches[0]
            if len(val) == 2: return int("20" + val)
            return int(val)
            
        # 3. "31st March 2023"
        matches = re.findall(r'(?:31st|31)\s+March,?\s+(20[12][0-9])', text, re.IGNORECASE)
        if matches:
            return int(matches[0])
            
        return None

    def _parse_text_to_dataframe(self, text):
        """
        Parses raw text to find Schedule III line items and their values.
        """
        data = {}
        
        # Flatten schema values for easier lookup [alias -> standard_name]
        schema_map = {}
        for std, aliases in SCHEDULE_III_SCHEMA.items():
            schema_map[std.lower()] = std
            for alias in aliases:
                schema_map[alias.lower()] = std
        
        lines = text.split('\n')
        
        # Identify Year columns (Naive approach: look for 4 digit years)
        years = sorted(list(set(re.findall(r'\b20[12][0-9]\b', text))))
        # Context: Usually current year is first or last. We'll try to detect lines with numbers.
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # Skip header lines usually
            if "schedule" in line.lower() or "page" in line.lower(): continue

            # 1. Fuzzy match line start to Schema
            # We take the text part of the line (remove numbers)
            line_text = re.sub(r'[0-9,\.\(\)]', '', line).strip()
            if len(line_text) < 3: continue
            
            match = process.extractOne(line_text, list(schema_map.keys()), scorer=fuzz.ratio)
            
            if match and match[1] > 85: # High confidence threshold
                matched_alias = match[0]
                std_name = schema_map[matched_alias]
                
                # 2. Extract Numbers from the line
                # Look for numbers at the end of the line
                # Pattern: 1,00,000 or (1,00,000) or 100.50
                # Regex for Indian currency
                numbers = re.findall(r'\(?[\d,]+\.?\d*\)?', line)
                
                # Filter strictly valid numbers
                valid_numbers = []
                for num in numbers:
                    clean_num = self._parse_indian_number(num)
                    if clean_num is not None:
                        valid_numbers.append(clean_num)
                
                if valid_numbers:
                    # Assumption: If 2 numbers, usually [Current Year, Previous Year] or vice versa.
                    # We'll take the first one found as 'Current Period' for now 
                    # (simplification, real parser needs column positional analysis)
                    if std_name not in data: # Don't overwrite if found earlier (usually top is clearer)
                        data[std_name] = valid_numbers[0]
                        self.confidence_scores[std_name] = "High" if match[1] > 95 else "Medium"

        # Create DataFrame
        # We need a standard format: [Year, Metric1, Metric2...]
        # Since we extracted a dict of metrics for a single period (mostly), we construct a single row DF.
        
        # Try to infer year from text if possible
        current_year = years[-1] if years else "Current Year"
        
        df_data = {"Year": [current_year]}
        df_data.update({k: [v] for k, v in data.items()})
        
        return pd.DataFrame(df_data)

    def _parse_indian_number(self, num_str):
        """
        Parses strings like '1,00,000', '(5000)', '10.5' to float.
        Returns None if not a valid number.
        """
        try:
            # Handle brackets for negative (common in accounting)
            is_negative = False
            if '(' in num_str and ')' in num_str:
                is_negative = True
                num_str = num_str.replace('(', '').replace(')', '')
            
            # Remove commas
            num_str = num_str.replace(',', '')
            
            # Check if it's just a bracket or empty
            if not num_str.strip(): return None
            
            val = float(num_str)
            return -val if is_negative else val
        except:
            return None
