#!/usr/bin/env python3
"""
Subcontract Validation Module for ProposalOS
=============================================
Comprehensive DFARS and FAR compliance validation for subcontract procurement

This module provides the validate_subcontract function used by the 
/procure/subcontract endpoint in the orchestrator.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComplianceSeverity(Enum):
    """Compliance issue severity levels"""
    CRITICAL = "Critical"  # Blocks procurement
    ERROR = "Error"        # Must be resolved
    WARNING = "Warning"    # Should be addressed
    INFO = "Info"          # Informational only

class DFARSValidator:
    """DFARS compliance validation for subcontracts"""
    
    # Key DFARS thresholds and requirements
    TINA_THRESHOLD = 2_000_000  # FAR 15.403-4
    SIMPLIFIED_ACQUISITION_THRESHOLD = 250_000  # FAR 2.101
    MICRO_PURCHASE_THRESHOLD = 10_000  # FAR 2.101
    CPSR_THRESHOLD = 50_000_000  # DFARS 244.303
    
    # DFARS clauses by contract type
    COST_REIMBURSABLE_CLAUSES = [
        "DFARS 252.244-7001",  # Contractor Purchasing System Administration
        "DFARS 252.204-7012",  # Safeguarding Covered Defense Information
        "DFARS 252.232-7006",  # Wide Area WorkFlow Payment Instructions
        "FAR 52.244-2"         # Subcontracts
    ]
    
    FIXED_PRICE_CLAUSES = [
        "DFARS 252.244-7000",  # Subcontracts for Commercial Items
        "DFARS 252.225-7001",  # Buy American and Balance of Payments
        "FAR 52.244-6"         # Subcontracts for Commercial Items
    ]
    
    def __init__(self):
        self.issues = []
        self.recommendations = []
        
    def validate_tina_compliance(self, contract_value: float) -> None:
        """Validate Truth in Negotiations Act (TINA) compliance"""
        if contract_value > self.TINA_THRESHOLD:
            self.issues.append({
                "code": "FAR-15.403-4",
                "description": f"Contract value ${contract_value:,.2f} exceeds TINA threshold of ${self.TINA_THRESHOLD:,.2f}",
                "severity": ComplianceSeverity.ERROR.value,
                "regulation": "FAR 15.403-4 - Requiring Certified Cost or Pricing Data",
                "remediation": "Obtain certified cost or pricing data from vendor unless exception applies"
            })
            self.recommendations.append(
                "Request Standard Form 1411 (Contract Pricing Proposal Cover Sheet) from vendor"
            )
    
    def validate_cmmc_requirements(
        self, 
        vendor_data: Dict[str, Any],
        contract_value: float
    ) -> None:
        """Validate Cybersecurity Maturity Model Certification (CMMC) requirements"""
        
        is_cmmc_certified = vendor_data.get("cmmc_certified", False)
        cmmc_level = vendor_data.get("cmmc_level", 0)
        
        if contract_value > self.MICRO_PURCHASE_THRESHOLD:
            if not is_cmmc_certified:
                severity = ComplianceSeverity.ERROR if contract_value > self.SIMPLIFIED_ACQUISITION_THRESHOLD else ComplianceSeverity.WARNING
                
                self.issues.append({
                    "code": "DFARS-252.204-7021",
                    "description": "Vendor lacks required CMMC certification for DoD contract",
                    "severity": severity.value,
                    "regulation": "DFARS 252.204-7021 - Cybersecurity Maturity Model Certification Requirements",
                    "remediation": "Verify vendor has CMMC Level 2 certification or higher via SPRS"
                })
            
            elif cmmc_level < 2 and contract_value > self.SIMPLIFIED_ACQUISITION_THRESHOLD:
                self.issues.append({
                    "code": "DFARS-252.204-7021-L2",
                    "description": f"Vendor CMMC Level {cmmc_level} insufficient for contract value",
                    "severity": ComplianceSeverity.WARNING.value,
                    "regulation": "DFARS 252.204-7021",
                    "remediation": "Vendor must achieve CMMC Level 2 certification"
                })
    
    def validate_sam_registration(self, vendor_data: Dict[str, Any]) -> None:
        """Validate System for Award Management (SAM) registration"""
        
        sam_registered = vendor_data.get("sam_registered", False)
        sam_uei = vendor_data.get("sam_uei")
        sam_exclusion = vendor_data.get("sam_exclusion", False)
        
        if not sam_registered:
            self.issues.append({
                "code": "FAR-9.404",
                "description": "Vendor not registered in SAM.gov",
                "severity": ComplianceSeverity.CRITICAL.value,
                "regulation": "FAR 9.404 - System for Award Management Exclusions",
                "remediation": "Vendor must complete SAM.gov registration before contract award"
            })
        
        if sam_exclusion:
            self.issues.append({
                "code": "FAR-9.405",
                "description": "Vendor is on SAM.gov exclusion list",
                "severity": ComplianceSeverity.CRITICAL.value,
                "regulation": "FAR 9.405 - Effect of Listing",
                "remediation": "Cannot award to excluded vendor. Find alternative source."
            })
        
        if sam_registered and not sam_uei:
            self.issues.append({
                "code": "SAM-UEI-MISSING",
                "description": "SAM Unique Entity Identifier (UEI) not provided",
                "severity": ComplianceSeverity.WARNING.value,
                "regulation": "FAR 4.1102",
                "remediation": "Obtain 12-character SAM UEI from vendor"
            })
    
    def validate_itar_compliance(self, vendor_data: Dict[str, Any]) -> None:
        """Validate International Traffic in Arms Regulations (ITAR) compliance"""
        
        itar_controlled = vendor_data.get("itar_controlled", False)
        itar_registered = vendor_data.get("itar_registered", False)
        ddtc_code = vendor_data.get("ddtc_registration_code")
        
        if itar_controlled and not itar_registered:
            self.issues.append({
                "code": "ITAR-122.1",
                "description": "Vendor not ITAR registered for defense articles",
                "severity": ComplianceSeverity.ERROR.value,
                "regulation": "22 CFR 122.1 - Registration of Manufacturers and Exporters",
                "remediation": "Verify vendor DDTC registration or obtain TAA/MLA"
            })
            self.recommendations.append(
                "Request copy of vendor's DDTC registration certificate"
            )
        
        if itar_registered and not ddtc_code:
            self.issues.append({
                "code": "ITAR-REG-CODE",
                "description": "DDTC registration code not provided",
                "severity": ComplianceSeverity.INFO.value,
                "regulation": "22 CFR 122.2",
                "remediation": "Obtain DDTC registration code for compliance records"
            })
    
    def validate_flowdown_clauses(
        self,
        contract_type: str,
        flowdown_clauses: List[str]
    ) -> None:
        """Validate required flowdown clauses based on contract type"""
        
        required_clauses = []
        
        if contract_type in ["CPFF", "CPIF", "T&M", "CPAF"]:
            required_clauses = self.COST_REIMBURSABLE_CLAUSES
        else:
            required_clauses = self.FIXED_PRICE_CLAUSES
        
        missing_clauses = set(required_clauses) - set(flowdown_clauses)
        
        if missing_clauses:
            self.issues.append({
                "code": "DFARS-FLOWDOWN",
                "description": f"Missing required flowdown clauses for {contract_type} contract",
                "severity": ComplianceSeverity.WARNING.value,
                "regulation": "DFARS 252.244-7000",
                "remediation": f"Include clauses: {', '.join(missing_clauses)}"
            })
    
    def validate_small_business_requirements(
        self,
        vendor_data: Dict[str, Any],
        contract_value: float
    ) -> None:
        """Validate small business subcontracting requirements"""
        
        is_small_business = vendor_data.get("small_business", False)
        
        if contract_value > 750_000 and not is_small_business:
            self.recommendations.append(
                "Consider small business set-aside per FAR 19.502-2"
            )
            
            # Check if subcontracting plan is required
            if contract_value > 750_000:
                self.issues.append({
                    "code": "FAR-19.702",
                    "description": "Subcontracting plan required for large business over $750K",
                    "severity": ComplianceSeverity.INFO.value,
                    "regulation": "FAR 19.702 - Statutory Requirements",
                    "remediation": "Obtain small business subcontracting plan from vendor"
                })
    
    def validate_dcaa_requirements(
        self,
        vendor_data: Dict[str, Any],
        contract_type: str,
        contract_value: float
    ) -> None:
        """Validate Defense Contract Audit Agency (DCAA) requirements"""
        
        accounting_system_approved = vendor_data.get("dcaa_approved", False)
        
        if contract_type in ["CPFF", "CPIF", "T&M", "CPAF"] and contract_value > 1_000_000:
            if not accounting_system_approved:
                self.issues.append({
                    "code": "DFARS-242.7502",
                    "description": "Cost-reimbursable contract requires approved accounting system",
                    "severity": ComplianceSeverity.ERROR.value,
                    "regulation": "DFARS 242.7502 - Contractor Accounting System Administration",
                    "remediation": "Request DCAA pre-award accounting system audit"
                })
                self.recommendations.append(
                    "Submit SF 1408 for DCAA audit request"
                )
    
    def validate_cpsr_requirements(self, prime_contract_value: Optional[float]) -> None:
        """Validate Contractor Purchasing System Review (CPSR) requirements"""
        
        if prime_contract_value and prime_contract_value > self.CPSR_THRESHOLD:
            self.recommendations.append(
                f"CPSR required - prime contract exceeds ${self.CPSR_THRESHOLD:,.0f} threshold (DFARS 244.303)"
            )
    
    def calculate_risk_score(self) -> int:
        """Calculate overall risk score based on issues"""
        
        risk_score = 0
        
        for issue in self.issues:
            if issue["severity"] == ComplianceSeverity.CRITICAL.value:
                risk_score += 40
            elif issue["severity"] == ComplianceSeverity.ERROR.value:
                risk_score += 25
            elif issue["severity"] == ComplianceSeverity.WARNING.value:
                risk_score += 10
            elif issue["severity"] == ComplianceSeverity.INFO.value:
                risk_score += 5
        
        return min(risk_score, 100)  # Cap at 100

async def validate_subcontract(
    vendor_data: Dict[str, Any],
    contract_value: float = 0,
    contract_type: str = "FFP",
    flowdown_clauses: List[str] = None,
    prime_contract_value: Optional[float] = None,
    is_dod_contract: bool = True
) -> Dict[str, Any]:
    """
    Main function to validate subcontract against DFARS and FAR requirements
    
    Args:
        vendor_data: Dictionary containing vendor information
        contract_value: Subcontract value in USD
        contract_type: Contract type (FFP, CPFF, T&M, etc.)
        flowdown_clauses: List of flowdown clauses to include
        prime_contract_value: Total prime contract value
        is_dod_contract: Whether this is a DoD contract
    
    Returns:
        Dictionary containing validation results, issues, and recommendations
    """
    
    logger.info(f"Validating subcontract for vendor: {vendor_data.get('vendor_name', 'Unknown')}")
    
    validator = DFARSValidator()
    flowdown_clauses = flowdown_clauses or []
    
    # Run all validation checks
    validator.validate_tina_compliance(contract_value)
    
    if is_dod_contract:
        validator.validate_cmmc_requirements(vendor_data, contract_value)
    
    validator.validate_sam_registration(vendor_data)
    
    if vendor_data.get("itar_controlled", False):
        validator.validate_itar_compliance(vendor_data)
    
    validator.validate_flowdown_clauses(contract_type, flowdown_clauses)
    validator.validate_small_business_requirements(vendor_data, contract_value)
    validator.validate_dcaa_requirements(vendor_data, contract_type, contract_value)
    validator.validate_cpsr_requirements(prime_contract_value)
    
    # Calculate risk and compliance
    risk_score = validator.calculate_risk_score()
    is_compliant = not any(
        issue["severity"] in [ComplianceSeverity.CRITICAL.value, ComplianceSeverity.ERROR.value]
        for issue in validator.issues
    )
    
    # Determine risk level
    risk_level = "Low"
    if risk_score > 70:
        risk_level = "High"
    elif risk_score > 40:
        risk_level = "Medium"
    elif risk_score > 20:
        risk_level = "Low-Medium"
    
    # Determine approval requirements
    approval_required = False
    approver_level = None
    
    if not is_compliant or risk_score > 30:
        approval_required = True
        if risk_score > 70:
            approver_level = "VP/Director"
        elif risk_score > 40:
            approver_level = "Program Manager"
        else:
            approver_level = "Contracts Lead"
    
    result = {
        "vendor_name": vendor_data.get("vendor_name", "Unknown"),
        "contract_value": contract_value,
        "contract_type": contract_type,
        "is_compliant": is_compliant,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "issues": validator.issues,
        "recommendations": validator.recommendations,
        "approval_required": approval_required,
        "approver_level": approver_level,
        "validation_timestamp": datetime.now().isoformat(),
        "dfars_checklist": {
            "tina_compliant": contract_value <= validator.TINA_THRESHOLD,
            "cmmc_verified": vendor_data.get("cmmc_certified", False),
            "sam_registered": vendor_data.get("sam_registered", False),
            "itar_compliant": not vendor_data.get("itar_controlled") or vendor_data.get("itar_registered", False),
            "flowdown_complete": len(set(validator.COST_REIMBURSABLE_CLAUSES if contract_type in ["CPFF", "CPIF", "T&M"] else validator.FIXED_PRICE_CLAUSES) - set(flowdown_clauses)) == 0
        }
    }
    
    logger.info(f"Validation complete - Compliant: {is_compliant}, Risk: {risk_level}")
    
    return result

def generate_compliance_report(validation_result: Dict[str, Any]) -> str:
    """
    Generate a formatted compliance report from validation results
    
    Args:
        validation_result: Result from validate_subcontract function
    
    Returns:
        Formatted report string
    """
    
    report = []
    report.append("="*60)
    report.append("SUBCONTRACT COMPLIANCE VALIDATION REPORT")
    report.append("="*60)
    report.append(f"Vendor: {validation_result['vendor_name']}")
    report.append(f"Contract Value: ${validation_result['contract_value']:,.2f}")
    report.append(f"Contract Type: {validation_result['contract_type']}")
    report.append(f"Validation Date: {validation_result['validation_timestamp']}")
    report.append("")
    
    # Compliance Status
    report.append("COMPLIANCE STATUS")
    report.append("-"*40)
    report.append(f"Overall Compliance: {'✅ COMPLIANT' if validation_result['is_compliant'] else '❌ NON-COMPLIANT'}")
    report.append(f"Risk Level: {validation_result['risk_level']} (Score: {validation_result['risk_score']}/100)")
    
    if validation_result['approval_required']:
        report.append(f"Approval Required: {validation_result['approver_level']}")
    
    report.append("")
    
    # DFARS Checklist
    report.append("DFARS COMPLIANCE CHECKLIST")
    report.append("-"*40)
    checklist = validation_result['dfars_checklist']
    report.append(f"✓ TINA Compliance: {'Yes' if checklist['tina_compliant'] else 'No - Certified cost data required'}")
    report.append(f"✓ CMMC Certified: {'Yes' if checklist['cmmc_verified'] else 'No - Certification required'}")
    report.append(f"✓ SAM Registered: {'Yes' if checklist['sam_registered'] else 'No - Registration required'}")
    report.append(f"✓ ITAR Compliant: {'Yes' if checklist['itar_compliant'] else 'No - Registration required'}")
    report.append(f"✓ Flowdown Clauses: {'Complete' if checklist['flowdown_complete'] else 'Incomplete'}")
    report.append("")
    
    # Issues
    if validation_result['issues']:
        report.append("COMPLIANCE ISSUES")
        report.append("-"*40)
        
        # Group by severity
        critical = [i for i in validation_result['issues'] if i['severity'] == 'Critical']
        errors = [i for i in validation_result['issues'] if i['severity'] == 'Error']
        warnings = [i for i in validation_result['issues'] if i['severity'] == 'Warning']
        info = [i for i in validation_result['issues'] if i['severity'] == 'Info']
        
        if critical:
            report.append("\n🔴 CRITICAL ISSUES (Block procurement):")
            for issue in critical:
                report.append(f"  [{issue['code']}] {issue['description']}")
                report.append(f"    Regulation: {issue['regulation']}")
                report.append(f"    Action: {issue['remediation']}")
        
        if errors:
            report.append("\n🟠 ERRORS (Must resolve):")
            for issue in errors:
                report.append(f"  [{issue['code']}] {issue['description']}")
                report.append(f"    Regulation: {issue['regulation']}")
                report.append(f"    Action: {issue['remediation']}")
        
        if warnings:
            report.append("\n🟡 WARNINGS (Should address):")
            for issue in warnings:
                report.append(f"  [{issue['code']}] {issue['description']}")
                if issue.get('regulation'):
                    report.append(f"    Regulation: {issue['regulation']}")
                if issue.get('remediation'):
                    report.append(f"    Action: {issue['remediation']}")
        
        if info:
            report.append("\n🔵 INFORMATION:")
            for issue in info:
                report.append(f"  [{issue['code']}] {issue['description']}")
        
        report.append("")
    
    # Recommendations
    if validation_result['recommendations']:
        report.append("RECOMMENDATIONS")
        report.append("-"*40)
        for i, rec in enumerate(validation_result['recommendations'], 1):
            report.append(f"{i}. {rec}")
        report.append("")
    
    report.append("="*60)
    report.append("END OF REPORT")
    report.append("="*60)
    
    return "\n".join(report)

# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_validation():
        """Test the validation function with sample data"""
        
        # Test Case 1: High-value DoD subcontract
        vendor_data = {
            "vendor_name": "Advanced Defense Systems Inc",
            "sam_registered": True,
            "sam_uei": "ABC123DEF456",
            "cmmc_certified": False,  # Issue!
            "cmmc_level": 1,
            "itar_controlled": True,
            "itar_registered": True,
            "ddtc_registration_code": "M12345",
            "small_business": False,
            "dcaa_approved": False  # Issue for CPFF!
        }
        
        result = await validate_subcontract(
            vendor_data=vendor_data,
            contract_value=3_000_000,  # Above TINA threshold
            contract_type="CPFF",
            flowdown_clauses=["DFARS 252.244-7001"],  # Missing some
            prime_contract_value=60_000_000,  # Above CPSR threshold
            is_dod_contract=True
        )
        
        # Generate report
        report = generate_compliance_report(result)
        print(report)
        
        print("\n" + "="*60)
        print("TEST CASE 2: Small Business FFP Contract")
        print("="*60 + "\n")
        
        # Test Case 2: Small business with good compliance
        vendor_data_2 = {
            "vendor_name": "Small Tech Solutions LLC",
            "sam_registered": True,
            "sam_uei": "XYZ789GHI012",
            "cmmc_certified": True,
            "cmmc_level": 2,
            "small_business": True,
            "itar_controlled": False
        }
        
        result_2 = await validate_subcontract(
            vendor_data=vendor_data_2,
            contract_value=500_000,
            contract_type="FFP",
            flowdown_clauses=["DFARS 252.244-7000", "DFARS 252.225-7001", "FAR 52.244-6"],
            is_dod_contract=True
        )
        
        print(f"Vendor: {result_2['vendor_name']}")
        print(f"Compliant: {result_2['is_compliant']}")
        print(f"Risk Level: {result_2['risk_level']}")
        print(f"Approval Required: {result_2['approval_required']}")
    
    # Run the test
    asyncio.run(test_validation())