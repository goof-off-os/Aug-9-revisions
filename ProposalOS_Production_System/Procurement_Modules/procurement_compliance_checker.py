#!/usr/bin/env python3
"""
Procurement Compliance Checker for ProposalOS
=============================================
Validates subcontractor compliance and generates Bill of Materials (BOM)

Integrates with the orchestrator and cost volume assembly pipeline
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ComplianceSeverity(Enum):
    """Severity levels for compliance issues"""
    CRITICAL = "Critical"  # Blocks procurement
    ERROR = "Error"        # Must be resolved
    WARNING = "Warning"    # Should be addressed
    INFO = "Info"          # Informational only

@dataclass
class ComplianceIssue:
    """Single compliance issue"""
    code: str
    description: str
    severity: ComplianceSeverity
    regulation: str
    remediation: str
    
@dataclass
class VendorData:
    """Vendor/subcontractor information"""
    name: str
    quote: float
    cmmc_certified: bool = False
    itar_registered: bool = False
    sam_registered: bool = True
    small_business: bool = False
    cage_code: Optional[str] = None
    duns_number: Optional[str] = None
    facility_clearance: Optional[str] = None  # SECRET, TOP SECRET, etc.
    past_performance: Optional[str] = None  # EXCELLENT, GOOD, FAIR, POOR

@dataclass
class BOMItem:
    """Bill of Materials item"""
    item: str
    part_number: Optional[str]
    quantity: int
    unit_cost: float
    vendor: str
    lead_time_days: int = 30
    compliance: str = ""
    itar_controlled: bool = False
    country_of_origin: str = "USA"
    
    @property
    def total_cost(self) -> float:
        return self.quantity * self.unit_cost

class SubcontractorComplianceChecker:
    """Comprehensive subcontractor compliance validation"""
    
    # Thresholds from FAR/DFARS
    TINA_THRESHOLD = 2_000_000  # FAR 15.403-4
    SIMPLIFIED_ACQUISITION_THRESHOLD = 250_000  # FAR 2.101
    MICRO_PURCHASE_THRESHOLD = 10_000  # FAR 2.101
    CPSR_THRESHOLD = 50_000_000  # DFARS 244.303
    
    def check_subcontractor_compliance(
        self,
        vendor_data: VendorData,
        contract_type: str,
        prime_contract_value: Optional[float] = None,
        is_dod_contract: bool = True
    ) -> Dict[str, Any]:
        """
        Comprehensive subcontractor compliance check
        
        Args:
            vendor_data: Vendor information
            contract_type: Contract type (FFP, CPFF, T&M, etc.)
            prime_contract_value: Total prime contract value
            is_dod_contract: Whether this is a DoD contract
            
        Returns:
            Compliance check results with issues and recommendations
        """
        
        issues = []
        recommendations = []
        risk_score = 0
        
        # 1. TINA Compliance (FAR 15.403-4)
        if vendor_data.quote > self.TINA_THRESHOLD:
            issues.append(ComplianceIssue(
                code="FAR-15.403-4",
                description=f"Quote exceeds ${self.TINA_THRESHOLD:,} TINA threshold",
                severity=ComplianceSeverity.ERROR,
                regulation="FAR 15.403-4",
                remediation="Obtain certified cost or pricing data from vendor"
            ))
            risk_score += 20
        
        # 2. CMMC/Cybersecurity (DFARS 252.204-7012)
        if is_dod_contract and not vendor_data.cmmc_certified:
            if vendor_data.quote > self.MICRO_PURCHASE_THRESHOLD:
                issues.append(ComplianceIssue(
                    code="DFARS-252.204-7012",
                    description="Vendor not CMMC certified for DoD contract",
                    severity=ComplianceSeverity.ERROR if vendor_data.quote > self.SIMPLIFIED_ACQUISITION_THRESHOLD else ComplianceSeverity.WARNING,
                    regulation="DFARS 252.204-7012",
                    remediation="Verify vendor has CMMC Level 2 certification or SPRS score ≥ 110"
                ))
                risk_score += 15
        
        # 3. SAM Registration (FAR 9.404)
        if not vendor_data.sam_registered:
            issues.append(ComplianceIssue(
                code="FAR-9.404",
                description="Vendor not registered in SAM.gov",
                severity=ComplianceSeverity.CRITICAL,
                regulation="FAR 9.404",
                remediation="Vendor must complete SAM.gov registration before award"
            ))
            risk_score += 30
        
        # 4. Contract Type Specific Requirements
        if contract_type in ["CPFF", "CPIF", "T&M"]:
            # Cost-reimbursable contracts require additional oversight
            issues.append(ComplianceIssue(
                code="FAR-52.244-2",
                description=f"Cost-reimbursable subcontract ({contract_type}) requires flowdown clauses",
                severity=ComplianceSeverity.WARNING,
                regulation="FAR 52.244-2",
                remediation="Include all required flowdown clauses: FAR 52.244-2, DFARS 252.244-7001"
            ))
            
            # Recommend accounting system review
            if vendor_data.quote > 1_000_000:
                recommendations.append("Conduct pre-award accounting system review")
                risk_score += 10
        
        # 5. ITAR/Export Control
        if vendor_data.itar_registered == False:  # Explicitly False, not just None
            issues.append(ComplianceIssue(
                code="ITAR-120.1",
                description="Vendor not ITAR registered for defense articles",
                severity=ComplianceSeverity.ERROR,
                regulation="22 CFR 120.1",
                remediation="Verify vendor DDTC registration or obtain export license"
            ))
            risk_score += 25
        
        # 6. Small Business Considerations (FAR 19.502)
        if vendor_data.quote > 150_000 and vendor_data.quote < 750_000:
            if not vendor_data.small_business:
                recommendations.append("Consider small business set-aside per FAR 19.502")
        
        # 7. Facility Clearance Requirements
        if vendor_data.facility_clearance is None and is_dod_contract:
            if vendor_data.quote > 100_000:
                issues.append(ComplianceIssue(
                    code="NISPOM-2-102",
                    description="Facility clearance status unknown for classified work",
                    severity=ComplianceSeverity.WARNING,
                    regulation="NISPOM 2-102",
                    remediation="Verify facility clearance level via NCAISS CAGE lookup"
                ))
                risk_score += 10
        
        # 8. Past Performance
        if vendor_data.past_performance in ["FAIR", "POOR", None]:
            if vendor_data.quote > 500_000:
                issues.append(ComplianceIssue(
                    code="FAR-15.305",
                    description="Past performance concerns for high-value subcontract",
                    severity=ComplianceSeverity.WARNING,
                    regulation="FAR 15.305",
                    remediation="Conduct detailed past performance evaluation"
                ))
                risk_score += 15
        
        # 9. CPSR Requirements (DFARS 244.303)
        if prime_contract_value and prime_contract_value > self.CPSR_THRESHOLD:
            recommendations.append("Contractor Purchasing System Review (CPSR) required")
        
        # Calculate overall compliance
        is_compliant = not any(issue.severity in [ComplianceSeverity.CRITICAL, ComplianceSeverity.ERROR] 
                               for issue in issues)
        
        # Determine risk level
        risk_level = "Low"
        if risk_score > 70:
            risk_level = "High"
        elif risk_score > 40:
            risk_level = "Medium"
        elif risk_score > 20:
            risk_level = "Low-Medium"
        
        return {
            "vendor": vendor_data.name,
            "quote": vendor_data.quote,
            "contract_type": contract_type,
            "is_compliant": is_compliant,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "issues": [asdict(issue) for issue in issues],
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }
    
    def batch_check_vendors(
        self,
        vendors: List[VendorData],
        contract_type: str,
        prime_contract_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """Check multiple vendors and rank by compliance"""
        
        results = []
        for vendor in vendors:
            result = self.check_subcontractor_compliance(
                vendor, 
                contract_type,
                prime_contract_value
            )
            results.append(result)
        
        # Sort by risk score (lower is better)
        results.sort(key=lambda x: x["risk_score"])
        
        return {
            "total_vendors": len(vendors),
            "compliant_vendors": sum(1 for r in results if r["is_compliant"]),
            "total_value": sum(v.quote for v in vendors),
            "vendor_results": results,
            "recommended_vendor": results[0]["vendor"] if results and results[0]["is_compliant"] else None
        }

class BillOfMaterialsGenerator:
    """Generate and validate Bill of Materials"""
    
    def generate_bom(
        self,
        estimate_data: Dict[str, Any],
        procurement_type: str = "Direct Materials"
    ) -> List[BOMItem]:
        """
        Generate Bill of Materials from estimate data
        
        Args:
            estimate_data: Element estimate with amount
            procurement_type: Type of procurement
            
        Returns:
            List of BOM items
        """
        
        element = estimate_data.get("element", procurement_type)
        amount = estimate_data.get("amount", 0)
        
        # Example BOM generation - would be customized per project
        bom = []
        
        if element == "Direct Materials":
            # Generate sample materials BOM
            bom = [
                BOMItem(
                    item="RF Transceiver Module",
                    part_number="RT-5000-X",
                    quantity=100,
                    unit_cost=5000,
                    vendor="RF Systems Inc",
                    lead_time_days=45,
                    compliance="FAR 31.205-26",
                    itar_controlled=True,
                    country_of_origin="USA"
                ),
                BOMItem(
                    item="Power Amplifier",
                    part_number="PA-2000-S",
                    quantity=50,
                    unit_cost=10000,
                    vendor="Power Tech Corp",
                    lead_time_days=30,
                    compliance="ITAR-verified",
                    itar_controlled=True,
                    country_of_origin="USA"
                ),
                BOMItem(
                    item="Antenna Array",
                    part_number="AA-8X8-KU",
                    quantity=25,
                    unit_cost=20000,
                    vendor="Antenna Systems LLC",
                    lead_time_days=60,
                    compliance="FAR 31.205-26",
                    itar_controlled=False,
                    country_of_origin="USA"
                ),
                BOMItem(
                    item="Control Processor",
                    part_number="CP-3000",
                    quantity=100,
                    unit_cost=1500,
                    vendor="Embedded Solutions",
                    lead_time_days=20,
                    compliance="COTS",
                    itar_controlled=False,
                    country_of_origin="Taiwan"
                )
            ]
        
        elif element == "COTS":
            # Generate COTS items
            bom = [
                BOMItem(
                    item="Server Rack (42U)",
                    part_number="SR-42U-600",
                    quantity=10,
                    unit_cost=3000,
                    vendor="DataCenter Supply",
                    lead_time_days=14,
                    compliance="COTS",
                    itar_controlled=False,
                    country_of_origin="USA"
                ),
                BOMItem(
                    item="Network Switch (48-port)",
                    part_number="NSW-48P-10G",
                    quantity=20,
                    unit_cost=5000,
                    vendor="Network Gear Inc",
                    lead_time_days=7,
                    compliance="COTS",
                    itar_controlled=False,
                    country_of_origin="USA"
                )
            ]
        
        # Validate against estimate
        total = sum(item.total_cost for item in bom)
        
        if total > amount:
            logger.warning(f"BOM total ${total:,.2f} exceeds estimate ${amount:,.2f}")
        
        return bom
    
    def validate_bom(
        self,
        bom: List[BOMItem],
        constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate BOM against constraints
        
        Args:
            bom: List of BOM items
            constraints: Validation constraints (budget, schedule, compliance)
            
        Returns:
            Validation results
        """
        
        issues = []
        warnings = []
        
        # Budget validation
        total_cost = sum(item.total_cost for item in bom)
        budget = constraints.get("budget", float('inf'))
        
        if total_cost > budget:
            issues.append(f"BOM exceeds budget by ${total_cost - budget:,.2f}")
        
        # Schedule validation
        max_lead_time = max((item.lead_time_days for item in bom), default=0)
        schedule_days = constraints.get("schedule_days", float('inf'))
        
        if max_lead_time > schedule_days:
            issues.append(f"Longest lead time ({max_lead_time} days) exceeds schedule")
        
        # ITAR validation
        itar_items = [item for item in bom if item.itar_controlled]
        if itar_items and not constraints.get("itar_approved", True):
            issues.append(f"{len(itar_items)} ITAR-controlled items require export approval")
        
        # Country of origin validation
        foreign_items = [item for item in bom if item.country_of_origin != "USA"]
        if foreign_items and constraints.get("buy_american", False):
            warnings.append(f"{len(foreign_items)} items not US-origin (Buy American Act)")
        
        # Vendor diversity
        unique_vendors = set(item.vendor for item in bom)
        if len(unique_vendors) < 2 and len(bom) > 5:
            warnings.append("Limited vendor diversity increases supply chain risk")
        
        return {
            "is_valid": len(issues) == 0,
            "total_cost": total_cost,
            "max_lead_time_days": max_lead_time,
            "item_count": len(bom),
            "vendor_count": len(unique_vendors),
            "itar_controlled_items": len(itar_items),
            "foreign_items": len(foreign_items),
            "issues": issues,
            "warnings": warnings,
            "validation_timestamp": datetime.now().isoformat()
        }
    
    def export_bom_to_csv(self, bom: List[BOMItem], filename: str):
        """Export BOM to CSV for procurement"""
        import csv
        
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'item', 'part_number', 'quantity', 'unit_cost', 
                'total_cost', 'vendor', 'lead_time_days', 
                'compliance', 'itar_controlled', 'country_of_origin'
            ])
            writer.writeheader()
            
            for item in bom:
                row = asdict(item)
                row['total_cost'] = item.total_cost
                writer.writerow(row)
        
        logger.info(f"BOM exported to {filename}")

def main():
    """Example usage of compliance checker and BOM generator"""
    
    # Initialize services
    compliance_checker = SubcontractorComplianceChecker()
    bom_generator = BillOfMaterialsGenerator()
    
    # Example 1: Check single vendor compliance
    print("="*60)
    print("SUBCONTRACTOR COMPLIANCE CHECK")
    print("="*60)
    
    vendor = VendorData(
        name="SubK Inc",
        quote=3_000_000,
        cmmc_certified=False,
        itar_registered=True,
        sam_registered=True,
        small_business=False,
        past_performance="GOOD"
    )
    
    result = compliance_checker.check_subcontractor_compliance(
        vendor,
        contract_type="CPFF",
        prime_contract_value=50_000_000
    )
    
    print(f"Vendor: {result['vendor']}")
    print(f"Quote: ${result['quote']:,.2f}")
    print(f"Compliant: {result['is_compliant']}")
    print(f"Risk Level: {result['risk_level']} (Score: {result['risk_score']})")
    
    if result['issues']:
        print("\nCompliance Issues:")
        for issue in result['issues']:
            print(f"  [{issue['severity']}] {issue['description']}")
            print(f"    Regulation: {issue['regulation']}")
            print(f"    Fix: {issue['remediation']}")
    
    if result['recommendations']:
        print("\nRecommendations:")
        for rec in result['recommendations']:
            print(f"  - {rec}")
    
    # Example 2: Generate BOM
    print("\n" + "="*60)
    print("BILL OF MATERIALS GENERATION")
    print("="*60)
    
    estimate = {
        "element": "Direct Materials",
        "amount": 2_000_000
    }
    
    bom = bom_generator.generate_bom(estimate)
    
    print(f"Generated {len(bom)} BOM items:")
    for item in bom:
        print(f"  - {item.item} ({item.part_number})")
        print(f"    Qty: {item.quantity} @ ${item.unit_cost:,.2f} = ${item.total_cost:,.2f}")
        print(f"    Vendor: {item.vendor}, Lead: {item.lead_time_days} days")
    
    # Validate BOM
    validation = bom_generator.validate_bom(bom, {
        "budget": estimate["amount"],
        "schedule_days": 90,
        "itar_approved": True,
        "buy_american": True
    })
    
    print(f"\nBOM Validation:")
    print(f"  Valid: {validation['is_valid']}")
    print(f"  Total Cost: ${validation['total_cost']:,.2f}")
    print(f"  Max Lead Time: {validation['max_lead_time_days']} days")
    
    if validation['issues']:
        print("  Issues:")
        for issue in validation['issues']:
            print(f"    - {issue}")
    
    if validation['warnings']:
        print("  Warnings:")
        for warning in validation['warnings']:
            print(f"    - {warning}")
    
    # Export BOM
    bom_generator.export_bom_to_csv(bom, "bom_export.csv")

if __name__ == "__main__":
    main()