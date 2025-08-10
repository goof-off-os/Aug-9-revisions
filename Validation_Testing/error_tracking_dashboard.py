#!/usr/bin/env python3
"""
ProposalOS Error Tracking Dashboard
====================================
Analyzes and visualizes error tracking, validation failures, and attribution chains
from the RFP EoC Discovery workflow.
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import argparse

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

@dataclass
class ValidationResult:
    """Tracks validation outcomes for a single fact"""
    fact_id: str
    element: str
    classification: str
    
    # Validation checks
    quote_length_valid: bool = True
    quote_word_count: int = 0
    regulatory_match: bool = True
    confidence_score: float = 0.0
    
    # Attribution
    source_doc_id: str = ""
    source_section: str = ""
    source_url: str = ""
    timestamp: str = ""
    
    # Errors/warnings
    warnings: List[str] = field(default_factory=list)
    was_dropped: bool = False
    drop_reason: str = ""

class ErrorTracker:
    """Analyzes error patterns and validation failures"""
    
    # Expected regulatory patterns per element
    ELEMENT_PATTERNS = {
        "Travel": [r"31\.205-46", r"231\.205-46", r"Travel Costs"],
        "G&A": [r"CAS\s*410", r"410\.50", r"Cost Accounting Standards"],
        "Direct Labor": [r"31\.202", r"31\.203", r"Direct\s+costs"],
        "Direct Materials": [r"31\.202", r"Direct\s+materials"],
        "Overhead": [r"31\.203", r"CAS\s*418", r"indirect\s+costs"],
        "Fringe": [r"31\.205-6", r"compensation", r"fringe"],
        "Fee": [r"15\.404-4", r"profit", r"Weighted\s+Guidelines"],
        "Subcontracts": [r"15\.404-3", r"52\.244", r"subcontract"],
    }
    
    def __init__(self):
        self.results: List[ValidationResult] = []
        self.error_summary = defaultdict(int)
        self.element_stats = defaultdict(lambda: {"total": 0, "valid": 0, "dropped": 0})
        
    def analyze_kb_file(self, kb_path: Path) -> Dict:
        """Analyze a knowledge base JSON file for errors"""
        with open(kb_path, 'r') as f:
            data = json.load(f)
        
        # Handle both envelope and raw formats
        facts = data.get("facts", data) if isinstance(data, dict) else data
        
        for fact in facts:
            result = self._validate_fact(fact)
            self.results.append(result)
            self._update_stats(result)
        
        return self._generate_report()
    
    def _validate_fact(self, fact: dict) -> ValidationResult:
        """Validate a single fact against all rules"""
        result = ValidationResult(
            fact_id=fact.get("fact_id", "unknown"),
            element=fact.get("element", ""),
            classification=fact.get("classification", ""),
            source_doc_id=fact.get("source", {}).get("doc_id", ""),
            source_section=fact.get("source", {}).get("section", ""),
            source_url=fact.get("source", {}).get("url", ""),
            timestamp=fact.get("timestamp", "")
        )
        
        # Check regulatory support
        support = fact.get("regulatory_support", [])
        if support:
            for cite in support:
                # 1. Quote length validation
                quote = cite.get("quote", "")
                words = quote.split()
                result.quote_word_count = len(words)
                if len(words) > 25:
                    result.quote_length_valid = False
                    result.warnings.append(f"Quote exceeds 25 words ({len(words)} words)")
                
                # 2. Regulatory match validation
                reg_title = cite.get("reg_title", "")
                reg_section = cite.get("reg_section", "")
                if not self._check_regulatory_match(result.element, reg_title, reg_section):
                    result.regulatory_match = False
                    result.warnings.append(
                        f"Regulatory mismatch: {result.element} cited from {reg_section}"
                    )
                
                # 3. Confidence score check
                confidence = cite.get("confidence", 0.0)
                result.confidence_score = max(result.confidence_score, confidence)
                if confidence < 0.3:
                    result.warnings.append(f"Low confidence: {confidence:.2f}")
                
                # 4. Missing attribution check
                if not cite.get("url"):
                    result.warnings.append("Missing URL in citation")
                if not cite.get("reg_section"):
                    result.warnings.append("Missing regulation section")
        else:
            result.warnings.append("No regulatory support provided")
            result.regulatory_match = False
        
        return result
    
    def _check_regulatory_match(self, element: str, title: str, section: str) -> bool:
        """Check if regulation matches expected pattern for element"""
        patterns = self.ELEMENT_PATTERNS.get(element, [])
        if not patterns:
            return True  # No pattern defined, assume valid
        
        combined = f"{title} {section}"
        return any(re.search(p, combined, re.IGNORECASE) for p in patterns)
    
    def _update_stats(self, result: ValidationResult):
        """Update aggregate statistics"""
        self.element_stats[result.element]["total"] += 1
        
        if result.regulatory_match and result.quote_length_valid:
            self.element_stats[result.element]["valid"] += 1
        
        if result.was_dropped:
            self.element_stats[result.element]["dropped"] += 1
            self.error_summary["dropped_facts"] += 1
        
        if not result.quote_length_valid:
            self.error_summary["quote_length_violations"] += 1
        
        if not result.regulatory_match:
            self.error_summary["regulatory_mismatches"] += 1
        
        if result.confidence_score < 0.3:
            self.error_summary["low_confidence"] += 1
        
        if result.warnings:
            self.error_summary["facts_with_warnings"] += 1
    
    def _generate_report(self) -> Dict:
        """Generate comprehensive error report"""
        total_facts = len(self.results)
        valid_facts = sum(1 for r in self.results 
                         if r.regulatory_match and r.quote_length_valid)
        
        return {
            "summary": {
                "total_facts": total_facts,
                "valid_facts": valid_facts,
                "validation_rate": f"{(valid_facts/total_facts*100):.1f}%" if total_facts else "0%",
                "error_counts": dict(self.error_summary)
            },
            "by_element": dict(self.element_stats),
            "top_warnings": self._get_top_warnings(),
            "attribution_coverage": self._check_attribution_coverage(),
            "deduplication_stats": self._check_deduplication()
        }
    
    def _get_top_warnings(self, limit: int = 5) -> List[Tuple[str, int]]:
        """Get most common warning types"""
        warning_counts = defaultdict(int)
        for result in self.results:
            for warning in result.warnings:
                # Normalize warning type
                if "Quote exceeds" in warning:
                    warning_type = "Quote length violation"
                elif "Regulatory mismatch" in warning:
                    warning_type = "Regulatory mismatch"
                elif "Low confidence" in warning:
                    warning_type = "Low confidence score"
                elif "Missing URL" in warning:
                    warning_type = "Missing URL"
                elif "Missing regulation section" in warning:
                    warning_type = "Missing section"
                else:
                    warning_type = warning
                warning_counts[warning_type] += 1
        
        return sorted(warning_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    def _check_attribution_coverage(self) -> Dict:
        """Check completeness of attribution data"""
        with_url = sum(1 for r in self.results if r.source_url)
        with_section = sum(1 for r in self.results if r.source_section)
        with_timestamp = sum(1 for r in self.results if r.timestamp)
        total = len(self.results)
        
        return {
            "url_coverage": f"{(with_url/total*100):.1f}%" if total else "0%",
            "section_coverage": f"{(with_section/total*100):.1f}%" if total else "0%",
            "timestamp_coverage": f"{(with_timestamp/total*100):.1f}%" if total else "0%"
        }
    
    def _check_deduplication(self) -> Dict:
        """Check for potential duplicates"""
        seen_keys = set()
        duplicates = 0
        
        for result in self.results:
            key = (result.element, result.classification, 
                   result.source_doc_id, result.source_section)
            if key in seen_keys:
                duplicates += 1
            seen_keys.add(key)
        
        return {
            "unique_facts": len(seen_keys),
            "duplicate_facts": duplicates,
            "deduplication_rate": f"{(duplicates/len(self.results)*100):.1f}%" if self.results else "0%"
        }
    
    def print_dashboard(self, report: Dict):
        """Print formatted dashboard to console"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}╔════════════════════════════════════════════════════════╗{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}║       ProposalOS Error Tracking Dashboard             ║{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}╚════════════════════════════════════════════════════════╝{Colors.END}\n")
        
        # Summary section
        summary = report["summary"]
        print(f"{Colors.BOLD}📊 VALIDATION SUMMARY{Colors.END}")
        print(f"  Total Facts: {summary['total_facts']}")
        print(f"  Valid Facts: {Colors.GREEN}{summary['valid_facts']}{Colors.END}")
        print(f"  Validation Rate: {self._color_rate(summary['validation_rate'])}")
        print()
        
        # Error counts
        if summary["error_counts"]:
            print(f"{Colors.BOLD}⚠️  ERROR COUNTS{Colors.END}")
            for error_type, count in summary["error_counts"].items():
                color = Colors.RED if count > 5 else Colors.YELLOW
                print(f"  {error_type.replace('_', ' ').title()}: {color}{count}{Colors.END}")
            print()
        
        # Element breakdown
        print(f"{Colors.BOLD}📦 ELEMENT BREAKDOWN{Colors.END}")
        for element, stats in report["by_element"].items():
            if stats["total"] > 0:
                valid_pct = (stats["valid"]/stats["total"]*100)
                color = Colors.GREEN if valid_pct >= 80 else Colors.YELLOW if valid_pct >= 50 else Colors.RED
                print(f"  {element:20s}: {stats['total']:3d} total, "
                      f"{color}{stats['valid']:3d} valid ({valid_pct:.0f}%){Colors.END}")
        print()
        
        # Top warnings
        if report["top_warnings"]:
            print(f"{Colors.BOLD}🔝 TOP WARNING TYPES{Colors.END}")
            for warning_type, count in report["top_warnings"]:
                print(f"  • {warning_type}: {Colors.YELLOW}{count}{Colors.END}")
            print()
        
        # Attribution coverage
        print(f"{Colors.BOLD}🔗 ATTRIBUTION COVERAGE{Colors.END}")
        attr = report["attribution_coverage"]
        for field, coverage in attr.items():
            print(f"  {field.replace('_', ' ').title()}: {self._color_rate(coverage)}")
        print()
        
        # Deduplication
        print(f"{Colors.BOLD}🔄 DEDUPLICATION STATS{Colors.END}")
        dedup = report["deduplication_stats"]
        print(f"  Unique Facts: {Colors.GREEN}{dedup['unique_facts']}{Colors.END}")
        print(f"  Duplicates Removed: {Colors.YELLOW}{dedup['duplicate_facts']}{Colors.END}")
        print()
    
    def _color_rate(self, rate_str: str) -> str:
        """Color code a percentage rate"""
        try:
            rate = float(rate_str.rstrip('%'))
            if rate >= 80:
                return f"{Colors.GREEN}{rate_str}{Colors.END}"
            elif rate >= 50:
                return f"{Colors.YELLOW}{rate_str}{Colors.END}"
            else:
                return f"{Colors.RED}{rate_str}{Colors.END}"
        except:
            return rate_str
    
    def export_detailed_report(self, output_path: Path):
        """Export detailed fact-by-fact validation report"""
        lines = ["# Detailed Validation Report\n\n"]
        
        # Group by validation status
        valid = [r for r in self.results if r.regulatory_match and r.quote_length_valid]
        invalid = [r for r in self.results if not (r.regulatory_match and r.quote_length_valid)]
        
        lines.append(f"## ✅ Valid Facts ({len(valid)})\n\n")
        for result in valid[:10]:  # Show first 10
            lines.append(f"- **{result.element}** ({result.classification})\n")
            lines.append(f"  - ID: `{result.fact_id}`\n")
            lines.append(f"  - Source: {result.source_section}\n")
            lines.append(f"  - Confidence: {result.confidence_score:.2f}\n\n")
        
        lines.append(f"\n## ❌ Invalid Facts ({len(invalid)})\n\n")
        for result in invalid[:10]:  # Show first 10
            lines.append(f"- **{result.element}** ({result.classification})\n")
            lines.append(f"  - ID: `{result.fact_id}`\n")
            lines.append(f"  - Issues:\n")
            for warning in result.warnings:
                lines.append(f"    - ⚠️ {warning}\n")
            lines.append(f"  - Source: {result.source_section}\n\n")
        
        output_path.write_text("".join(lines))
        print(f"Detailed report saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Analyze ProposalOS KB for errors")
    parser.add_argument("--kb", required=True, help="Path to KB JSON file")
    parser.add_argument("--output", help="Output path for detailed report")
    args = parser.parse_args()
    
    kb_path = Path(args.kb)
    if not kb_path.exists():
        print(f"Error: KB file not found: {kb_path}")
        return
    
    tracker = ErrorTracker()
    report = tracker.analyze_kb_file(kb_path)
    tracker.print_dashboard(report)
    
    if args.output:
        output_path = Path(args.output)
        tracker.export_detailed_report(output_path)

if __name__ == "__main__":
    main()