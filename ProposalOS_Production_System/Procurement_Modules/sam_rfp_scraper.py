#!/usr/bin/env python3
"""
SAM.gov RFP Scraper for ProposalOS
===================================
Scrapes RFP opportunities from SAM.gov and integrates with EoC discovery pipeline

Usage:
    python sam_rfp_scraper.py --keywords "CPFF SatCom" --limit 10
    python sam_rfp_scraper.py --feed-to-discovery --output rfp_eocs.json
"""

import os
import sys
import json
import requests
import argparse
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import time
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class RFPOpportunity:
    """Structured RFP opportunity from SAM.gov"""
    notice_id: str
    title: str
    solicitation_number: str
    agency: str
    department: str
    posted_date: str
    response_deadline: Optional[str]
    description: str
    naics_code: Optional[str]
    set_aside: Optional[str]
    award_type: Optional[str]
    place_of_performance: Optional[str]
    estimated_value: Optional[float]
    url: str
    
    def to_eoc_doc(self) -> Dict[str, Any]:
        """Convert to format compatible with EoC discovery pipeline"""
        return {
            "id": self.notice_id,
            "title": self.title,
            "solicitation_number": self.solicitation_number,
            "agency": f"{self.department} - {self.agency}",
            "text": self.description,
            "metadata": {
                "posted_date": self.posted_date,
                "response_deadline": self.response_deadline,
                "naics_code": self.naics_code,
                "set_aside": self.set_aside,
                "award_type": self.award_type,
                "place_of_performance": self.place_of_performance,
                "url": self.url
            }
        }

class SAMRFPScraper:
    """Scraper for SAM.gov RFP opportunities"""
    
    def __init__(self, api_key: str):
        """
        Initialize scraper with SAM.gov API key
        
        Args:
            api_key: SAM.gov API key (get from https://open.gsa.gov/api/get-started/)
        """
        self.api_key = api_key
        self.base_url = "https://api.sam.gov/opportunities/v2/search"
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "ProposalOS/1.0"
        })
        
    def scrape_rfps(
        self,
        keywords: str = "",
        posted_days_ago: int = 30,
        limit: int = 10,
        naics_codes: Optional[List[str]] = None,
        set_aside_types: Optional[List[str]] = None,
        departments: Optional[List[str]] = None
    ) -> List[RFPOpportunity]:
        """
        Scrape RFP opportunities from SAM.gov
        
        Args:
            keywords: Search keywords for title/description
            posted_days_ago: Number of days to look back
            limit: Maximum number of results
            naics_codes: Filter by NAICS codes
            set_aside_types: Filter by set-aside types (e.g., "SBA", "8(a)")
            departments: Filter by departments
            
        Returns:
            List of RFPOpportunity objects
        """
        
        # Calculate date range
        posted_from = (datetime.now() - timedelta(days=posted_days_ago)).strftime("%m/%d/%Y")
        posted_to = datetime.now().strftime("%m/%d/%Y")
        
        # Build parameters
        params = {
            "limit": min(limit, 1000),  # SAM.gov max is 1000
            "api_key": self.api_key,
            "postedFrom": posted_from,
            "postedTo": posted_to,
            "ptype": "o",  # "o" for opportunities (not awards)
        }
        
        # Add optional filters
        if keywords:
            params["title"] = keywords  # Searches title and description
            
        if naics_codes:
            params["naicsCode"] = ",".join(naics_codes)
            
        if set_aside_types:
            params["typeOfSetAside"] = ",".join(set_aside_types)
            
        if departments:
            params["department"] = ",".join(departments)
        
        logger.info(f"Scraping RFPs with params: {params}")
        
        try:
            response = self.session.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"SAM.gov API error: {e}")
            if response.status_code == 429:
                logger.warning("Rate limited. Waiting 60 seconds...")
                time.sleep(60)
                return self.scrape_rfps(keywords, posted_days_ago, limit, naics_codes, set_aside_types, departments)
            raise ValueError(f"SAM.gov API error: {response.text if 'response' in locals() else str(e)}")
        
        # Parse response
        data = response.json()
        opportunities_data = data.get("opportunitiesData", [])
        
        logger.info(f"Found {len(opportunities_data)} RFP opportunities")
        
        # Convert to RFPOpportunity objects
        rfps = []
        for opp in opportunities_data:
            try:
                rfp = RFPOpportunity(
                    notice_id=opp.get("noticeId", ""),
                    title=opp.get("title", ""),
                    solicitation_number=opp.get("solicitationNumber", ""),
                    agency=opp.get("fullParentPathName", ""),
                    department=opp.get("department", ""),
                    posted_date=opp.get("postedDate", ""),
                    response_deadline=opp.get("responseDeadLine"),
                    description=opp.get("description", ""),
                    naics_code=opp.get("naicsCode"),
                    set_aside=opp.get("typeOfSetAside"),
                    award_type=opp.get("typeOfContractPricing"),
                    place_of_performance=opp.get("placeOfPerformance", {}).get("city", {}).get("name"),
                    estimated_value=self._parse_value(opp.get("awardAmount")),
                    url=opp.get("uiLink", f"https://sam.gov/opp/{opp.get('noticeId', '')}")
                )
                rfps.append(rfp)
                
            except Exception as e:
                logger.warning(f"Error parsing opportunity {opp.get('noticeId', 'unknown')}: {e}")
                continue
        
        return rfps
    
    def _parse_value(self, value_str: Optional[str]) -> Optional[float]:
        """Parse monetary value from string"""
        if not value_str:
            return None
        try:
            # Remove common characters and convert
            clean_value = value_str.replace("$", "").replace(",", "").replace("M", "000000").replace("K", "000")
            return float(clean_value)
        except:
            return None
    
    def extract_eocs_from_rfps(self, rfps: List[RFPOpportunity]) -> Dict[str, Any]:
        """
        Extract Elements of Cost from RFP descriptions
        
        This would integrate with compile_reports_refactor.py
        """
        
        eoc_indicators = {
            "Direct Labor": ["labor", "personnel", "staffing", "FTE", "man-hours"],
            "Travel": ["travel", "TDY", "per diem", "airfare", "lodging"],
            "Materials": ["materials", "supplies", "equipment", "hardware"],
            "Subcontracts": ["subcontract", "vendor", "supplier", "COTS"],
            "ODCs": ["ODC", "other direct cost", "direct cost"],
            "Overhead": ["overhead", "burden", "indirect"],
            "G&A": ["G&A", "general and administrative"],
            "Fee": ["fee", "profit", "award fee", "incentive fee"]
        }
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "total_rfps": len(rfps),
            "rfps_with_eocs": [],
            "eoc_summary": {}
        }
        
        for rfp in rfps:
            rfp_eocs = {
                "rfp_id": rfp.notice_id,
                "title": rfp.title,
                "identified_eocs": [],
                "contract_type": rfp.award_type
            }
            
            # Search for EoC indicators in description
            description_lower = rfp.description.lower()
            
            for eoc_type, indicators in eoc_indicators.items():
                if any(indicator in description_lower for indicator in indicators):
                    rfp_eocs["identified_eocs"].append({
                        "element": eoc_type,
                        "confidence": 0.8,  # Would be enhanced with ML
                        "indicators_found": [ind for ind in indicators if ind in description_lower]
                    })
            
            if rfp_eocs["identified_eocs"]:
                results["rfps_with_eocs"].append(rfp_eocs)
                
                # Update summary
                for eoc in rfp_eocs["identified_eocs"]:
                    element = eoc["element"]
                    results["eoc_summary"][element] = results["eoc_summary"].get(element, 0) + 1
        
        return results

def make_prompt_rfp_discovery(rfp: Dict[str, Any]) -> str:
    """
    Create prompt for RFP EoC discovery (compatible with compile_reports)
    
    Args:
        rfp: RFP document dictionary with 'text' field
        
    Returns:
        Prompt string for Gemini/GPT to extract EoCs
    """
    
    prompt = f"""Analyze this RFP solicitation and identify all Elements of Cost (EoCs) that would be required for proposal pricing.

RFP Title: {rfp.get('title', 'N/A')}
Agency: {rfp.get('agency', 'N/A')}
Solicitation: {rfp.get('solicitation_number', 'N/A')}

Description:
{rfp.get('text', '')}

For each Element of Cost identified, provide:
1. Element name (e.g., Direct Labor, Travel, Materials, Subcontracts, ODCs, Overhead, G&A, Fee)
2. Classification (direct, indirect, or fee)
3. Specific requirements from the RFP
4. Relevant FAR/DFARS citations if mentioned
5. Confidence level (0.0 to 1.0)

Format as JSON:
{{
    "elements": [
        {{
            "element": "Direct Labor",
            "classification": "direct",
            "requirements": "Technical staff for 24-month PoP",
            "citations": ["FAR 31.202"],
            "confidence": 0.9
        }}
    ]
}}

Focus on cost elements that would appear in a Cost Volume."""
    
    return prompt

def integrate_with_discovery_pipeline(
    rfps: List[RFPOpportunity],
    gemini_api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Integrate RFP scraping with the EoC discovery pipeline
    
    This would connect to compile_reports_refactor.py
    """
    
    discovered_facts = []
    
    for rfp in rfps:
        # Convert to document format
        doc = rfp.to_eoc_doc()
        
        # Create discovery prompt
        prompt = make_prompt_rfp_discovery(doc)
        
        # Here you would call Gemini/GPT for extraction
        # For now, we'll use pattern matching as a placeholder
        
        fact = {
            "fact_id": f"rfp_{rfp.notice_id}",
            "source_rfp": rfp.solicitation_number,
            "elements_identified": [],
            "extraction_method": "pattern_matching",  # Would be "gemini" with API
            "timestamp": datetime.now().isoformat()
        }
        
        # Simple pattern matching (would be replaced with Gemini call)
        if "labor" in doc["text"].lower():
            fact["elements_identified"].append({
                "element": "Direct Labor",
                "classification": "direct",
                "confidence": 0.7
            })
            
        if "travel" in doc["text"].lower():
            fact["elements_identified"].append({
                "element": "Travel",
                "classification": "direct",
                "confidence": 0.8
            })
        
        if fact["elements_identified"]:
            discovered_facts.append(fact)
    
    return discovered_facts

def main():
    """Main entry point for RFP scraping"""
    
    parser = argparse.ArgumentParser(description="Scrape RFPs from SAM.gov for EoC discovery")
    parser.add_argument("--api-key", help="SAM.gov API key (or set SAM_API_KEY env var)")
    parser.add_argument("--keywords", default="", help="Search keywords")
    parser.add_argument("--days", type=int, default=30, help="Days to look back")
    parser.add_argument("--limit", type=int, default=10, help="Maximum results")
    parser.add_argument("--naics", nargs="+", help="NAICS codes to filter")
    parser.add_argument("--set-aside", nargs="+", help="Set-aside types to filter")
    parser.add_argument("--departments", nargs="+", help="Departments to filter")
    parser.add_argument("--output", default="rfps.json", help="Output file")
    parser.add_argument("--extract-eocs", action="store_true", help="Extract EoCs from RFPs")
    parser.add_argument("--feed-to-discovery", action="store_true", help="Feed to discovery pipeline")
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or os.environ.get("SAM_API_KEY")
    if not api_key:
        logger.error("SAM.gov API key required. Set SAM_API_KEY env var or use --api-key")
        sys.exit(1)
    
    # Initialize scraper
    scraper = SAMRFPScraper(api_key)
    
    try:
        # Scrape RFPs
        logger.info(f"Scraping RFPs with keywords: '{args.keywords}'")
        rfps = scraper.scrape_rfps(
            keywords=args.keywords,
            posted_days_ago=args.days,
            limit=args.limit,
            naics_codes=args.naics,
            set_aside_types=args.set_aside,
            departments=args.departments
        )
        
        logger.info(f"Scraped {len(rfps)} RFPs")
        
        # Save raw RFPs
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            json.dump([asdict(rfp) for rfp in rfps], f, indent=2, default=str)
        logger.info(f"Saved RFPs to {output_path}")
        
        # Extract EoCs if requested
        if args.extract_eocs:
            logger.info("Extracting Elements of Cost from RFPs...")
            eoc_results = scraper.extract_eocs_from_rfps(rfps)
            
            eoc_output = output_path.with_stem(f"{output_path.stem}_eocs")
            with open(eoc_output, 'w') as f:
                json.dump(eoc_results, f, indent=2)
            
            logger.info(f"EoC Summary: {eoc_results['eoc_summary']}")
            logger.info(f"Saved EoC analysis to {eoc_output}")
        
        # Feed to discovery pipeline if requested
        if args.feed_to_discovery:
            logger.info("Feeding RFPs to discovery pipeline...")
            discovered_facts = integrate_with_discovery_pipeline(rfps)
            
            facts_output = output_path.with_stem(f"{output_path.stem}_facts")
            with open(facts_output, 'w') as f:
                json.dump(discovered_facts, f, indent=2)
            
            logger.info(f"Discovered {len(discovered_facts)} facts from RFPs")
            logger.info(f"Saved discovered facts to {facts_output}")
        
        # Print summary
        print("\n" + "="*60)
        print("RFP SCRAPING SUMMARY")
        print("="*60)
        print(f"Total RFPs scraped: {len(rfps)}")
        
        if rfps:
            print("\nSample RFPs:")
            for rfp in rfps[:3]:
                print(f"  - {rfp.title[:80]}...")
                print(f"    Agency: {rfp.agency}")
                print(f"    Posted: {rfp.posted_date}")
                print(f"    Contract Type: {rfp.award_type or 'Not specified'}")
                print()
        
        if args.extract_eocs and 'eoc_results' in locals():
            print("Elements of Cost identified:")
            for element, count in eoc_results['eoc_summary'].items():
                print(f"  - {element}: {count} RFPs")
        
    except Exception as e:
        logger.error(f"Error scraping RFPs: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()