"""
Excel extraction service.
Extracts tabular data from Excel files (.xlsx, .xls).
"""

import pandas as pd
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


def extract_from_excel(file_data):
    """
    Extract data from an Excel file.
    
    Args:
        file_data: Excel file as bytes
    
    Returns:
        dict: Extracted data from all sheets
            {
                'extracted_tables': {
                    'tables': list,
                    'table_count': int,
                    'sheet_count': int
                },
                'document_metadata': {
                    'sheet_names': list,
                    'sheet_count': int
                }
            }
    
    Raises:
        Exception: If Excel cannot be processed
    """
    results = {}
    
    try:
        # Read Excel file
        excel_file = pd.ExcelFile(BytesIO(file_data))
        
        all_tables = []
        
        # Extract data from each sheet
        for sheet_num, sheet_name in enumerate(excel_file.sheet_names, 1):
            try:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                
                # Skip empty sheets
                if df.empty:
                    logger.warning(f"Sheet '{sheet_name}' is empty, skipping")
                    continue
                
                table_data = {
                    'page': sheet_num,
                    'sheet_name': sheet_name,
                    'table_number': 1,
                    'columns': df.columns.tolist(),
                    'data': df.values.tolist(),
                    'row_count': len(df),
                    'column_count': len(df.columns)
                }
                
                all_tables.append(table_data)
                logger.info(f"Extracted sheet '{sheet_name}': {len(df)} rows, {len(df.columns)} columns")
                
            except Exception as sheet_error:
                logger.error(f"Failed to extract sheet '{sheet_name}': {sheet_error}")
                # Continue with other sheets
                continue
        
        if not all_tables:
            raise Exception("No data extracted from any sheet")
        
        results['extracted_tables'] = {
            'tables': all_tables,
            'table_count': len(all_tables),
            'sheet_count': len(excel_file.sheet_names)
        }
        
        results['document_metadata'] = {
            'sheet_names': excel_file.sheet_names,
            'sheet_count': len(excel_file.sheet_names),
            'extracted_sheet_count': len(all_tables)
        }
        
        logger.info(f"Successfully extracted Excel: {len(all_tables)} sheets processed")
        return results
        
    except Exception as e:
        logger.error(f"Failed to extract data from Excel: {e}")
        raise Exception(f"Excel extraction failed: {str(e)}")