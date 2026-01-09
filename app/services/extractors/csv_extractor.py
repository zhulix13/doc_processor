"""
CSV extraction service.
Extracts tabular data from CSV files.
"""

import pandas as pd
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


def extract_from_csv(file_data):
    """
    Extract data from a CSV file.
    
    Args:
        file_data: CSV file as bytes
    
    Returns:
        dict: Extracted data
            {
                'extracted_tables': {
                    'tables': list,
                    'table_count': int,
                    'row_count': int,
                    'column_count': int
                }
            }
    
    Raises:
        Exception: If CSV cannot be processed
    """
    results = {}
    
    try:
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(BytesIO(file_data), encoding=encoding)
                logger.info(f"Successfully read CSV with encoding: {encoding}")
                break
            except UnicodeDecodeError:
                continue
        
        if df is None:
            raise Exception("Failed to decode CSV with any encoding")
        
        # Convert to table format
        table_data = {
            'page': 1,
            'table_number': 1,
            'columns': df.columns.tolist(),
            'data': df.values.tolist(),
            'row_count': len(df),
            'column_count': len(df.columns)
        }
        
        results['extracted_tables'] = {
            'tables': [table_data],
            'table_count': 1,
            'total_rows': len(df),
            'total_columns': len(df.columns)
        }
        
        # Basic statistics for numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            results['document_metadata'] = {
                'numeric_columns': numeric_cols,
                'total_rows': len(df),
                'total_columns': len(df.columns),
                'has_header': True  # Assuming first row is header
            }
        
        logger.info(f"Successfully extracted CSV: {len(df)} rows, {len(df.columns)} columns")
        return results
        
    except Exception as e:
        logger.error(f"Failed to extract data from CSV: {e}")
        raise Exception(f"CSV extraction failed: {str(e)}")