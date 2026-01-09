"""
PDF extraction service.
Extracts text, tables, images, and metadata from PDF files.
"""

import pdfplumber
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


def extract_from_pdf(file_data):
    """
    Extract all data from a PDF file.
    
    Args:
        file_data: PDF file as bytes
    
    Returns:
        dict: Extracted data organized by type
            {
                'extracted_text': {'text': str, 'page_count': int},
                'extracted_tables': {'tables': list, 'table_count': int},
                'document_metadata': {'page_count': int, 'metadata': dict}
            }
    
    Raises:
        Exception: If PDF cannot be processed
    """
    results = {}
    
    try:
        with pdfplumber.open(BytesIO(file_data)) as pdf:
            # Extract text from all pages
            all_text = []
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    all_text.append(text)
                else:
                    logger.warning(f"No text found on page {page_num}")
            
            if all_text:
                results['extracted_text'] = {
                    'text': '\n\n'.join(all_text),
                    'page_count': len(pdf.pages),
                    'char_count': sum(len(t) for t in all_text)
                }
            else:
                logger.warning("No text extracted from PDF")
            
            # Extract tables from all pages
            all_tables = []
            for page_num, page in enumerate(pdf.pages, 1):
                tables = page.extract_tables()
                if tables:
                    for table_num, table in enumerate(tables, 1):
                        # Filter out empty rows
                        filtered_table = [row for row in table if any(cell for cell in row)]
                        
                        if filtered_table:
                            all_tables.append({
                                'page': page_num,
                                'table_number': table_num,
                                'data': filtered_table,
                                'row_count': len(filtered_table),
                                'column_count': len(filtered_table[0]) if filtered_table else 0
                            })
            
            if all_tables:
                results['extracted_tables'] = {
                    'tables': all_tables,
                    'table_count': len(all_tables)
                }
            else:
                logger.info("No tables found in PDF")
            
            # Extract metadata
            metadata = pdf.metadata or {}
            results['document_metadata'] = {
                'page_count': len(pdf.pages),
                'author': metadata.get('Author'),
                'title': metadata.get('Title'),
                'subject': metadata.get('Subject'),
                'creator': metadata.get('Creator'),
                'producer': metadata.get('Producer'),
                'creation_date': str(metadata.get('CreationDate')) if metadata.get('CreationDate') else None,
                'modification_date': str(metadata.get('ModDate')) if metadata.get('ModDate') else None
            }
        
        logger.info(f"Successfully extracted data from PDF: {len(results)} result types")
        return results
        
    except Exception as e:
        logger.error(f"Failed to extract data from PDF: {e}")
        raise Exception(f"PDF extraction failed: {str(e)}")