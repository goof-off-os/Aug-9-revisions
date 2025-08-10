"""
DITA Parser adapter for ProposalOS - loads pre-parsed FAR/DFARS/GSAM data
"""
from pathlib import Path
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to pre-parsed JSON files
FUSION_DIR = Path("/Users/carolinehusebo/Desktop/untitled folder 4/Fusion")

def iter_docs():
    """
    Iterator that yields regulation documents from pre-parsed JSON files.
    Each doc has: id, title, section, text, url
    """
    json_files = [
        ("far_data_from_dita.json", "FAR", "https://www.acquisition.gov/far/"),
        ("dfars_data_from_dita.json", "DFARS", "https://www.acquisition.gov/dfars/"),
        ("gsam_data_from_dita.json", "GSAM", "https://www.acquisition.gov/gsam/")
    ]
    
    total_docs = 0
    
    for filename, reg_name, base_url in json_files:
        filepath = FUSION_DIR / filename
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            continue
            
        logger.info(f"Loading {reg_name} from {filename}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Parse the nested structure - handle both list and dict with "regulations" key
            if isinstance(data, dict) and 'regulations' in data:
                data = data['regulations']
            
            if isinstance(data, list):
                for part in data:
                    part_num = part.get('part_number', '')
                    part_title = part.get('part_title', '')
                    
                    for subpart in part.get('subparts', []):
                        subpart_num = subpart.get('subpart_number', '')
                        
                        for section in subpart.get('sections', []):
                            section_num = section.get('section_number', '')
                            section_title = section.get('section_title', '')
                            section_text = section.get('section_text', '')
                            
                            if section_text and section_text.strip():
                                doc_id = f"{reg_name.lower()}_{section_num.replace('.', '_').replace('-', '_')}"
                                url = f"{base_url}{section_num.replace('.', '/')}"
                                
                                yield {
                                    'id': doc_id,
                                    'title': f"{reg_name} {part_title} - {section_title}",
                                    'section': section_num,
                                    'text': section_text[:10000],  # Limit text length
                                    'url': url
                                }
                                total_docs += 1
                                
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            
    logger.info(f"Loaded {total_docs} total documents from all regulations")

# Alias for compatibility
load_docs = iter_docs
get_docs = lambda: list(iter_docs())