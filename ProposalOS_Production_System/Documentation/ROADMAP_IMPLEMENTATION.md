# ProposalOS RFP EoC Discovery - Implementation Roadmap

## Executive Summary
Transforming the RFP EoC Discovery workflow from prototype to production-ready enterprise system with enhanced validation, automation, and scalability.

---

## 📊 Phase 1: Strengthen Validation & Error Detection (Weeks 1-2)

### 1.1 Cross-Regulation Consistency Checker

```python
# cross_regulation_validator.py
from typing import Dict, List, Tuple
from collections import defaultdict
import json

class CrossRegulationValidator:
    """Ensures consistent EoC treatment across FAR, DFARS, CAS"""
    
    CONSISTENCY_RULES = {
        "Travel": {
            "expected_classification": "direct",
            "required_citations": ["FAR 31.205-46", "DFARS 231.205-46"],
            "conflicting_sections": ["FAR 31.201-2"]  # General allowability, not travel-specific
        },
        "G&A": {
            "expected_classification": "indirect",
            "required_citations": ["CAS 410", "FAR 31.203"],
            "conflicting_sections": ["FAR 31.202"]  # Direct costs
        }
    }
    
    def validate_consistency(self, facts: List[Dict]) -> Dict[str, List[str]]:
        """Check if same element has consistent treatment across regulations"""
        element_classifications = defaultdict(set)
        element_citations = defaultdict(set)
        inconsistencies = []
        
        for fact in facts:
            element = fact["element"]
            classification = fact["classification"]
            element_classifications[element].add(classification)
            
            for cite in fact.get("regulatory_support", []):
                element_citations[element].add(cite["reg_section"])
        
        # Check classification consistency
        for element, classifications in element_classifications.items():
            if len(classifications) > 1:
                inconsistencies.append(
                    f"❌ {element} has multiple classifications: {classifications}"
                )
            
            # Check against known rules
            if element in self.CONSISTENCY_RULES:
                rule = self.CONSISTENCY_RULES[element]
                if classifications != {rule["expected_classification"]}:
                    inconsistencies.append(
                        f"⚠️ {element} should be {rule['expected_classification']}, "
                        f"found: {classifications}"
                    )
                
                # Check for required citations
                citations = element_citations.get(element, set())
                missing = set(rule["required_citations"]) - citations
                if missing:
                    inconsistencies.append(
                        f"📋 {element} missing required citations: {missing}"
                    )
        
        return {
            "inconsistencies": inconsistencies,
            "element_stats": {
                elem: {
                    "classifications": list(classes),
                    "citation_count": len(element_citations.get(elem, []))
                }
                for elem, classes in element_classifications.items()
            }
        }
```

### 1.2 Confidence Score Auto-Flagging

```python
# confidence_thresholds.py
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional

class ConfidenceLevel(Enum):
    HIGH = (0.8, 1.0, "✅ High confidence - Ready for use")
    MEDIUM = (0.5, 0.79, "⚠️ Medium confidence - Review recommended")
    LOW = (0.3, 0.49, "🔍 Low confidence - Manual review required")
    CRITICAL = (0.0, 0.29, "❌ Critical - Do not use without verification")

@dataclass
class ConfidenceValidator:
    auto_reject_threshold: float = 0.3
    auto_approve_threshold: float = 0.8
    
    def assess_fact(self, fact: Dict) -> Tuple[ConfidenceLevel, List[str]]:
        """Assess fact confidence and generate action items"""
        max_confidence = 0.0
        issues = []
        
        for cite in fact.get("regulatory_support", []):
            conf = cite.get("confidence", 0.0)
            max_confidence = max(max_confidence, conf)
            
            if conf < self.auto_reject_threshold:
                issues.append(f"Citation confidence too low: {conf:.2f}")
        
        # Determine level
        for level in ConfidenceLevel:
            if level.value[0] <= max_confidence <= level.value[1]:
                return level, issues
        
        return ConfidenceLevel.CRITICAL, issues
    
    def batch_assessment(self, facts: List[Dict]) -> Dict:
        """Assess all facts and categorize by action needed"""
        auto_approved = []
        needs_review = []
        auto_rejected = []
        
        for fact in facts:
            level, issues = self.assess_fact(fact)
            
            if level == ConfidenceLevel.HIGH:
                auto_approved.append(fact["fact_id"])
            elif level in [ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW]:
                needs_review.append({
                    "fact_id": fact["fact_id"],
                    "element": fact["element"],
                    "confidence": max(c.get("confidence", 0) 
                                     for c in fact.get("regulatory_support", [])),
                    "issues": issues
                })
            else:
                auto_rejected.append({
                    "fact_id": fact["fact_id"],
                    "reason": "Below minimum confidence threshold",
                    "issues": issues
                })
        
        return {
            "auto_approved": len(auto_approved),
            "needs_review": needs_review,
            "auto_rejected": auto_rejected,
            "summary": {
                "total": len(facts),
                "approved": len(auto_approved),
                "pending": len(needs_review),
                "rejected": len(auto_rejected)
            }
        }
```

### 1.3 Enhanced Citation Mismatch Detection

```python
# enhanced_citation_validator.py
import re
from typing import Dict, List, Tuple

class EnhancedCitationValidator:
    """Advanced regex rules for citation validation"""
    
    CITATION_PATTERNS = {
        # Travel-specific patterns
        "Travel": [
            (r"31\.205[\-\.]46", 1.0, "FAR Travel Costs"),
            (r"231\.205[\-\.]46", 1.0, "DFARS Travel Costs"),
            (r"travel\s+costs?", 0.7, "Travel keyword match"),
            (r"per\s+diem|lodging|airfare", 0.6, "Travel component match"),
            (r"JTR|Joint\s+Travel", 0.8, "JTR reference")
        ],
        
        # G&A patterns
        "G&A": [
            (r"CAS\s*410", 1.0, "CAS 410 exact"),
            (r"410\.50", 0.9, "CAS 410.50 section"),
            (r"general\s*(?:and|&)\s*administrative", 0.8, "G&A text match"),
            (r"allocation.*G\s*&?\s*A", 0.7, "G&A allocation context"),
            (r"31\.203", 0.6, "FAR indirect costs")
        ],
        
        # Direct Labor patterns
        "Direct Labor": [
            (r"31\.202", 0.9, "FAR direct costs"),
            (r"direct\s+labor\s+(?:hours?|costs?)", 1.0, "Direct labor exact"),
            (r"labor\s+categories?|skill\s+mix", 0.7, "Labor context"),
            (r"productive\s+hours?|billable", 0.6, "Labor metrics")
        ]
    }
    
    def validate_citation(self, element: str, citation_text: str) -> Tuple[float, str]:
        """
        Validate citation relevance for element
        Returns: (confidence_score, match_description)
        """
        patterns = self.CITATION_PATTERNS.get(element, [])
        if not patterns:
            return 0.5, "No validation pattern defined"
        
        best_match = 0.0
        best_description = "No pattern match"
        
        for pattern, weight, description in patterns:
            if re.search(pattern, citation_text, re.IGNORECASE):
                if weight > best_match:
                    best_match = weight
                    best_description = description
        
        return best_match, best_description
    
    def validate_all_citations(self, fact: Dict) -> Dict:
        """Validate all citations in a fact"""
        element = fact["element"]
        validations = []
        
        for cite in fact.get("regulatory_support", []):
            text = f"{cite.get('reg_title', '')} {cite.get('reg_section', '')} {cite.get('quote', '')}"
            score, description = self.validate_citation(element, text)
            
            validations.append({
                "citation": f"{cite.get('reg_title', '')} {cite.get('reg_section', '')}",
                "validation_score": score,
                "match_type": description,
                "original_confidence": cite.get("confidence", 0.0),
                "adjusted_confidence": min(cite.get("confidence", 0.0), score)
            })
        
        return {
            "element": element,
            "citation_validations": validations,
            "overall_validity": max(v["validation_score"] for v in validations) if validations else 0.0
        }
```

---

## 🔧 Phase 2: Automate Cost Volume Assembly (Weeks 3-4)

### 2.1 Direct KB Integration

```python
# automated_cost_volume_builder.py
from typing import Dict, List, Optional
import pandas as pd
from pathlib import Path
import json

class AutomatedCostVolumeBuilder:
    """Automatically generate cost volumes from KB facts"""
    
    def __init__(self, kb_path: Path, inputs_path: Optional[Path] = None):
        self.kb_facts = self._load_kb(kb_path)
        self.cost_inputs = self._load_inputs(inputs_path) if inputs_path else {}
        self.eoc_sections = {}
        
    def _load_kb(self, path: Path) -> List[Dict]:
        """Load and validate KB facts"""
        with open(path) as f:
            data = json.load(f)
        return data.get("facts", data) if isinstance(data, dict) else data
    
    def build_cost_volume(self) -> str:
        """Generate complete cost volume markdown"""
        sections = []
        
        # 1. Executive Summary
        sections.append(self._build_executive_summary())
        
        # 2. Direct Costs
        sections.append(self._build_direct_costs())
        
        # 3. Indirect Costs
        sections.append(self._build_indirect_costs())
        
        # 4. Fee/Profit
        sections.append(self._build_fee_section())
        
        # 5. Compliance Matrix
        sections.append(self._build_compliance_matrix())
        
        # 6. Regulatory Citations
        sections.append(self._build_citations())
        
        return "\n\n".join(sections)
    
    def _build_direct_costs(self) -> str:
        """Build direct cost sections with auto-generated tables"""
        direct_facts = [f for f in self.kb_facts if f["classification"] == "direct"]
        
        sections = ["## Direct Costs\n"]
        
        # Group by element
        by_element = {}
        for fact in direct_facts:
            element = fact["element"]
            if element not in by_element:
                by_element[element] = []
            by_element[element].append(fact)
        
        for element, facts in by_element.items():
            sections.append(f"### {element}")
            
            # Add description from highest confidence fact
            best_fact = max(facts, key=lambda f: 
                          max(c.get("confidence", 0) for c in f.get("regulatory_support", [])))
            sections.append(f"**Basis**: {best_fact.get('rfp_relevance', '')}\n")
            
            # Add cost table if we have inputs
            if element in self.cost_inputs:
                df = self._generate_cost_table(element, self.cost_inputs[element])
                sections.append(df.to_markdown(index=False))
            
            # Add regulatory support
            sections.append("**Regulatory Support:**")
            for fact in facts:
                for cite in fact.get("regulatory_support", []):
                    sections.append(
                        f"- {cite['reg_title']} {cite['reg_section']}: "
                        f"\"{cite['quote']}\" "
                        f"([source]({cite.get('url', '#')}))"
                    )
            sections.append("")
        
        return "\n".join(sections)
    
    def _build_compliance_matrix(self) -> str:
        """Generate compliance traceability matrix"""
        rows = []
        
        for fact in self.kb_facts:
            for cite in fact.get("regulatory_support", []):
                rows.append({
                    "Element": fact["element"],
                    "Classification": fact["classification"],
                    "Regulation": f"{cite['reg_title']} {cite['reg_section']}",
                    "Compliance": "✅" if cite.get("validated") else "⚠️",
                    "Confidence": f"{cite.get('confidence', 0):.0%}"
                })
        
        df = pd.DataFrame(rows)
        return f"## Compliance Traceability Matrix\n\n{df.to_markdown(index=False)}"
```

### 2.2 Auto-Generate EoC Sections

```python
# eoc_section_generator.py
from typing import Dict, List
import re

class EoCTextGenerator:
    """Generate compliant BOE text for each Element of Cost"""
    
    TEMPLATES = {
        "Direct Labor": """
The Direct Labor estimate of {hours:,} hours and ${amount:,.2f} is based on:
- **Skill Mix**: {labor_categories} aligned with PWS requirements
- **Historical Performance**: Similar effort on {analogy_program}
- **Productivity Factors**: {productivity}% efficiency based on {basis}
- **Compliance**: Per FAR 31.202, direct labor is specifically identified with this contract
        """,
        
        "Travel": """
Travel costs totaling ${amount:,.2f} are estimated based on:
- **Trip Requirements**: {trip_count} trips supporting {purpose}
- **GSA Rates**: Per diem and lodging per FTR/JTR regulations
- **Compliance**: Allowable under FAR 31.205-46 and DFARS 231.205-46
- **Documentation**: Trip justifications maintained per FAR requirements
        """,
        
        "G&A": """
G&A rate of {rate:.2%} applied on a Total Cost Input base per:
- **CAS 410 Compliance**: Allocation methodology consistent with disclosure statement
- **DCAA Approved**: Forward pricing rate agreement dated {fpra_date}
- **Base**: ${base:,.2f} total cost input
- **Pool**: ${pool:,.2f} G&A expense pool
        """
    }
    
    def generate_boe_text(self, element: str, facts: List[Dict], 
                          inputs: Dict = None) -> str:
        """Generate BOE text for element based on facts and inputs"""
        template = self.TEMPLATES.get(element, "")
        if not template or not inputs:
            return self._generate_generic_text(element, facts)
        
        # Fill template with inputs
        try:
            return template.format(**inputs)
        except KeyError as e:
            return self._generate_generic_text(element, facts) + \
                   f"\n*Note: Missing input data for {e}*"
    
    def _generate_generic_text(self, element: str, facts: List[Dict]) -> str:
        """Fallback generic text generation"""
        citations = []
        for fact in facts:
            for cite in fact.get("regulatory_support", []):
                citations.append(f"{cite['reg_title']} {cite['reg_section']}")
        
        return f"""
{element} costs are estimated in accordance with:
- Regulatory Guidance: {', '.join(set(citations))}
- Classification: {facts[0]['classification'].title() if facts else 'TBD'}
- Basis: {facts[0].get('rfp_relevance', 'See detailed justification')}
        """
```

---

## 🔍 Phase 3: Improve Fact Attribution (Week 5)

### 3.1 Enhanced Metadata Tracking

```python
# enhanced_attribution.py
import hashlib
import uuid
from datetime import datetime
from typing import Dict, Optional
import platform
import getpass

class EnhancedAttribution:
    """Track complete provenance chain for facts"""
    
    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id or str(uuid.uuid4())
        self.run_metadata = self._capture_environment()
    
    def _capture_environment(self) -> Dict:
        """Capture execution environment for reproducibility"""
        return {
            "run_id": self.run_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "user": getpass.getuser(),
            "hostname": platform.node(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "proposalOS_version": self._get_version()
        }
    
    def _get_version(self) -> str:
        """Get ProposalOS version from git or package"""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "describe", "--tags", "--always"],
                capture_output=True, text=True
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            return "unknown"
    
    def enhance_fact(self, fact: Dict, source_metadata: Dict) -> Dict:
        """Add complete attribution to fact"""
        fact["attribution"] = {
            "run_id": self.run_id,
            "extraction_timestamp": datetime.utcnow().isoformat() + "Z",
            "parser_source": {
                "module": source_metadata.get("parser_module", "unknown"),
                "file": source_metadata.get("parser_file", "unknown"),
                "version": source_metadata.get("parser_version", "unknown")
            },
            "document_source": {
                "doc_id": fact.get("source", {}).get("doc_id"),
                "retrieval_timestamp": source_metadata.get("retrieval_time"),
                "source_url": fact.get("source", {}).get("url"),
                "hash": self._hash_content(fact.get("source", {}).get("text", ""))
            },
            "citation_timestamps": [
                {
                    "citation": f"{c.get('reg_title')} {c.get('reg_section')}",
                    "extracted_at": datetime.utcnow().isoformat() + "Z"
                }
                for c in fact.get("regulatory_support", [])
            ]
        }
        return fact
    
    def _hash_content(self, content: str) -> str:
        """Generate content hash for verification"""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def generate_attribution_report(self, facts: List[Dict]) -> Dict:
        """Generate attribution summary report"""
        return {
            "run_metadata": self.run_metadata,
            "fact_count": len(facts),
            "parser_sources": list(set(
                f["attribution"]["parser_source"]["module"] 
                for f in facts if "attribution" in f
            )),
            "unique_documents": len(set(
                f["source"]["doc_id"] 
                for f in facts if "source" in f
            )),
            "attribution_coverage": {
                "with_run_id": sum(1 for f in facts if "attribution" in f),
                "with_timestamps": sum(
                    1 for f in facts 
                    if f.get("attribution", {}).get("extraction_timestamp")
                ),
                "with_parser_info": sum(
                    1 for f in facts 
                    if f.get("attribution", {}).get("parser_source", {}).get("module")
                )
            }
        }
```

---

## 🎨 Phase 4: Develop Analyst Review Tools (Weeks 6-7)

### 4.1 Web-Based Review Interface

```python
# review_interface.py
from flask import Flask, render_template, request, jsonify
from pathlib import Path
import json
from typing import Dict, List

app = Flask(__name__)

class FactReviewInterface:
    """Web UI for fact review and approval"""
    
    def __init__(self, kb_path: Path):
        self.kb_path = kb_path
        self.facts = self._load_facts()
        self.review_status = {}
    
    def _load_facts(self) -> List[Dict]:
        with open(self.kb_path) as f:
            data = json.load(f)
        return data.get("facts", data)
    
    @app.route('/')
    def dashboard():
        """Main review dashboard"""
        return render_template('review_dashboard.html')
    
    @app.route('/api/facts')
    def get_facts():
        """API endpoint for fact retrieval with filtering"""
        filters = {
            'element': request.args.get('element'),
            'classification': request.args.get('classification'),
            'confidence_min': float(request.args.get('confidence_min', 0)),
            'status': request.args.get('status')
        }
        
        filtered_facts = []
        for fact in self.facts:
            # Apply filters
            if filters['element'] and fact['element'] != filters['element']:
                continue
            if filters['classification'] and fact['classification'] != filters['classification']:
                continue
            
            # Check confidence
            max_conf = max(
                c.get('confidence', 0) 
                for c in fact.get('regulatory_support', [])
            ) if fact.get('regulatory_support') else 0
            
            if max_conf < filters['confidence_min']:
                continue
            
            # Add review status
            fact['review_status'] = self.review_status.get(fact['fact_id'], 'pending')
            filtered_facts.append(fact)
        
        return jsonify({
            'facts': filtered_facts,
            'total': len(filtered_facts),
            'filters_applied': filters
        })
    
    @app.route('/api/facts/<fact_id>/review', methods=['POST'])
    def review_fact(fact_id):
        """Update fact review status"""
        data = request.json
        self.review_status[fact_id] = {
            'status': data.get('status'),  # approved/rejected/needs_edit
            'reviewer': data.get('reviewer'),
            'timestamp': datetime.utcnow().isoformat(),
            'comments': data.get('comments'),
            'edits': data.get('edits', {})
        }
        
        # Save review status
        self._save_reviews()
        
        return jsonify({'success': True, 'fact_id': fact_id})
    
    @app.route('/api/analytics')
    def get_analytics():
        """Confidence score distribution and statistics"""
        confidences = []
        for fact in self.facts:
            for cite in fact.get('regulatory_support', []):
                confidences.append(cite.get('confidence', 0))
        
        import numpy as np
        return jsonify({
            'confidence_distribution': {
                'mean': float(np.mean(confidences)),
                'median': float(np.median(confidences)),
                'std': float(np.std(confidences)),
                'histogram': np.histogram(confidences, bins=10)[0].tolist()
            },
            'review_progress': {
                'total': len(self.facts),
                'approved': sum(1 for s in self.review_status.values() 
                              if s.get('status') == 'approved'),
                'rejected': sum(1 for s in self.review_status.values() 
                              if s.get('status') == 'rejected'),
                'pending': len(self.facts) - len(self.review_status)
            }
        })
```

### 4.2 Review Dashboard HTML Template

```html
<!-- templates/review_dashboard.html -->
<!DOCTYPE html>
<html>
<head>
    <title>ProposalOS Fact Review Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .filters { background: #f5f5f5; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .fact-card { 
            border: 1px solid #ddd; 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 8px;
            transition: all 0.3s;
        }
        .fact-card:hover { box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        .confidence-high { border-left: 4px solid #28a745; }
        .confidence-medium { border-left: 4px solid #ffc107; }
        .confidence-low { border-left: 4px solid #dc3545; }
        .actions { margin-top: 10px; }
        .btn { 
            padding: 8px 16px; 
            margin: 0 5px; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer; 
        }
        .btn-approve { background: #28a745; color: white; }
        .btn-reject { background: #dc3545; color: white; }
        .btn-edit { background: #007bff; color: white; }
        .analytics { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
        .chart-container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 ProposalOS Fact Review Dashboard</h1>
        
        <!-- Analytics Section -->
        <div class="analytics">
            <div class="chart-container">
                <h3>Confidence Distribution</h3>
                <canvas id="confidenceChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>Review Progress</h3>
                <canvas id="progressChart"></canvas>
            </div>
        </div>
        
        <!-- Filters -->
        <div class="filters">
            <h3>Filters</h3>
            <select id="elementFilter">
                <option value="">All Elements</option>
                <option value="Travel">Travel</option>
                <option value="Direct Labor">Direct Labor</option>
                <option value="G&A">G&A</option>
                <option value="Overhead">Overhead</option>
            </select>
            
            <select id="classificationFilter">
                <option value="">All Classifications</option>
                <option value="direct">Direct</option>
                <option value="indirect">Indirect</option>
                <option value="fee">Fee</option>
            </select>
            
            <label>Min Confidence:
                <input type="range" id="confidenceFilter" min="0" max="1" step="0.1" value="0">
                <span id="confidenceValue">0.0</span>
            </label>
            
            <button class="btn" onclick="applyFilters()">Apply Filters</button>
        </div>
        
        <!-- Facts List -->
        <div id="factsList"></div>
    </div>
    
    <script>
        let facts = [];
        
        async function loadFacts() {
            const response = await fetch('/api/facts');
            const data = await response.json();
            facts = data.facts;
            renderFacts();
        }
        
        function renderFacts() {
            const container = document.getElementById('factsList');
            container.innerHTML = facts.map(fact => {
                const maxConfidence = Math.max(...fact.regulatory_support.map(c => c.confidence || 0));
                const confidenceClass = maxConfidence >= 0.8 ? 'confidence-high' : 
                                       maxConfidence >= 0.5 ? 'confidence-medium' : 'confidence-low';
                
                return `
                    <div class="fact-card ${confidenceClass}">
                        <h4>${fact.element} (${fact.classification})</h4>
                        <p>${fact.rfp_relevance}</p>
                        <p><strong>Confidence:</strong> ${(maxConfidence * 100).toFixed(0)}%</p>
                        <p><strong>Source:</strong> ${fact.source.title} - ${fact.source.section}</p>
                        <div class="actions">
                            <button class="btn btn-approve" onclick="reviewFact('${fact.fact_id}', 'approved')">
                                ✅ Approve
                            </button>
                            <button class="btn btn-reject" onclick="reviewFact('${fact.fact_id}', 'rejected')">
                                ❌ Reject
                            </button>
                            <button class="btn btn-edit" onclick="editFact('${fact.fact_id}')">
                                ✏️ Edit
                            </button>
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        async function reviewFact(factId, status) {
            const response = await fetch(`/api/facts/${factId}/review`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    status: status,
                    reviewer: 'current_user',
                    timestamp: new Date().toISOString()
                })
            });
            
            if (response.ok) {
                alert(`Fact ${status}!`);
                loadFacts();
            }
        }
        
        async function loadAnalytics() {
            const response = await fetch('/api/analytics');
            const data = await response.json();
            
            // Confidence distribution chart
            new Chart(document.getElementById('confidenceChart'), {
                type: 'bar',
                data: {
                    labels: ['0-0.1', '0.1-0.2', '0.2-0.3', '0.3-0.4', '0.4-0.5', 
                            '0.5-0.6', '0.6-0.7', '0.7-0.8', '0.8-0.9', '0.9-1.0'],
                    datasets: [{
                        label: 'Number of Facts',
                        data: data.confidence_distribution.histogram,
                        backgroundColor: 'rgba(54, 162, 235, 0.5)'
                    }]
                }
            });
            
            // Progress chart
            new Chart(document.getElementById('progressChart'), {
                type: 'doughnut',
                data: {
                    labels: ['Approved', 'Rejected', 'Pending'],
                    datasets: [{
                        data: [
                            data.review_progress.approved,
                            data.review_progress.rejected,
                            data.review_progress.pending
                        ],
                        backgroundColor: ['#28a745', '#dc3545', '#ffc107']
                    }]
                }
            });
        }
        
        // Initialize
        loadFacts();
        loadAnalytics();
    </script>
</body>
</html>
```

---

## 🚀 Phase 5: Orchestrate Full Pipeline (Week 8)

### 5.1 Unified CLI Service

```python
# proposalOS_cli.py
import click
import asyncio
from pathlib import Path
from typing import Optional
import yaml

@click.group()
@click.version_option(version='1.0.0')
def cli():
    """ProposalOS - RFP Intelligence Pipeline"""
    pass

@cli.command()
@click.option('--config', type=click.Path(exists=True), help='Configuration file')
@click.option('--output-dir', type=click.Path(), default='./output')
@click.option('--dry-run', is_flag=True, help='Run without API calls')
@click.option('--parallel', is_flag=True, help='Enable parallel processing')
def run_pipeline(config: Optional[str], output_dir: str, dry_run: bool, parallel: bool):
    """Execute complete pipeline: Discovery → Validation → KB → Cost Volume"""
    
    click.echo("🚀 Starting ProposalOS Pipeline")
    
    # Load configuration
    if config:
        with open(config) as f:
            cfg = yaml.safe_load(f)
    else:
        cfg = _default_config()
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Discovery
    click.echo("📖 Step 1: Extracting Elements of Cost...")
    kb_path = _run_discovery(cfg, output_path, dry_run, parallel)
    
    # Step 2: Validation
    click.echo("✅ Step 2: Validating facts...")
    validated_kb = _run_validation(kb_path, output_path)
    
    # Step 3: Knowledge Base Build
    click.echo("🧠 Step 3: Building knowledge graph...")
    graph_path = _build_knowledge_graph(validated_kb, output_path)
    
    # Step 4: Cost Volume Assembly
    click.echo("📊 Step 4: Assembling Cost Volume...")
    cv_path = _assemble_cost_volume(validated_kb, cfg.get('inputs'), output_path)
    
    # Step 5: Generate Report
    click.echo("📈 Step 5: Generating executive report...")
    report_path = _generate_report(output_path)
    
    click.echo(f"""
✨ Pipeline Complete!
    
Outputs:
- Knowledge Base: {validated_kb}
- Graph: {graph_path}
- Cost Volume: {cv_path}
- Report: {report_path}
    
To review: python review_interface.py --kb {validated_kb}
    """)

@cli.command()
@click.option('--schedule', type=str, help='Cron expression for scheduling')
@click.option('--trigger', type=str, help='File/event to trigger on')
def schedule(schedule: Optional[str], trigger: Optional[str]):
    """Schedule pipeline runs"""
    if schedule:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
        
        scheduler = BlockingScheduler()
        scheduler.add_job(
            func=lambda: run_pipeline.callback(None, './scheduled_output', False, True),
            trigger=CronTrigger.from_crontab(schedule),
            id='proposalOS_pipeline',
            name='ProposalOS Pipeline Run',
            replace_existing=True
        )
        
        click.echo(f"📅 Scheduled pipeline with: {schedule}")
        try:
            scheduler.start()
        except KeyboardInterrupt:
            click.echo("Scheduler stopped.")
            scheduler.shutdown()
    
    elif trigger:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        
        class TriggerHandler(FileSystemEventHandler):
            def on_created(self, event):
                if event.src_path.endswith(trigger):
                    click.echo(f"🎯 Trigger detected: {event.src_path}")
                    run_pipeline.callback(None, './triggered_output', False, True)
        
        observer = Observer()
        observer.schedule(TriggerHandler(), path='.', recursive=False)
        observer.start()
        
        click.echo(f"👀 Watching for trigger: {trigger}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

def _default_config() -> dict:
    """Default pipeline configuration"""
    return {
        'discovery': {
            'limit': 100,
            'model': 'gemini-2.5-pro',
            'confidence_threshold': 0.3
        },
        'validation': {
            'strict': False,
            'auto_approve_threshold': 0.8,
            'auto_reject_threshold': 0.3
        },
        'cost_volume': {
            'template': 'default',
            'include_citations': True
        }
    }

if __name__ == '__main__':
    cli()
```

---

## 🧪 Phase 6: Expand Testing & QA (Week 9)

### 6.1 Comprehensive Test Suite

```python
# tests/test_proposalos_pipeline.py
import pytest
from unittest.mock import Mock, patch
import json
from pathlib import Path

class TestQuoteValidation:
    """Test quote length enforcement"""
    
    def test_quote_within_limit(self):
        quote = "This is a valid quote with exactly twenty five words"
        assert len(quote.split()) <= 25
        
    def test_quote_truncation(self):
        long_quote = " ".join(["word"] * 50)
        from proposalOS import truncate_quote_25w
        result = truncate_quote_25w(long_quote)
        assert len(result.split()) == 25
        
    def test_quote_preserves_sentence(self):
        quote = "This is a complete sentence. This is another sentence that will be cut."
        from proposalOS import smart_truncate
        result = smart_truncate(quote, 10)
        assert result.endswith(('.', '...'))

class TestCitationValidation:
    """Test element-to-regulation matching"""
    
    @pytest.mark.parametrize("element,section,expected", [
        ("Travel", "31.205-46", True),
        ("Travel", "231.205-46", True),
        ("Travel", "31.201-2", False),  # Wrong section
        ("G&A", "CAS 410", True),
        ("G&A", "410.50", True),
        ("G&A", "31.205-46", False),  # Travel reg for G&A
    ])
    def test_citation_matching(self, element, section, expected):
        from proposalOS import _support_matches
        result = _support_matches(element, "", section)
        assert result == expected

class TestDeduplication:
    """Test fact deduplication logic"""
    
    def test_removes_exact_duplicates(self):
        facts = [
            {"element": "Travel", "classification": "direct", 
             "source": {"doc_id": "1", "section": "A"}},
            {"element": "Travel", "classification": "direct", 
             "source": {"doc_id": "1", "section": "A"}}  # Duplicate
        ]
        from proposalOS import dedupe_merge
        result = dedupe_merge(facts)
        assert len(result) == 1
        
    def test_preserves_different_sources(self):
        facts = [
            {"element": "Travel", "classification": "direct", 
             "source": {"doc_id": "1", "section": "A"}},
            {"element": "Travel", "classification": "direct", 
             "source": {"doc_id": "2", "section": "A"}}  # Different doc
        ]
        from proposalOS import dedupe_merge
        result = dedupe_merge(facts)
        assert len(result) == 2

class TestRegressionDataset:
    """Maintain accuracy over time"""
    
    @pytest.fixture
    def regression_kb(self):
        """Load known-good KB for regression testing"""
        with open('tests/fixtures/regression_kb.json') as f:
            return json.load(f)
    
    def test_extraction_accuracy(self, regression_kb):
        """Ensure extraction quality doesn't degrade"""
        from proposalOS import run_rfp_discovery
        
        # Run on same test documents
        _, kb_path = run_rfp_discovery(
            dry_run=True,
            limit=10,
            outdir='./test_output',
            strict=False,
            model_name='gemini-2.5-pro'
        )
        
        with open(kb_path) as f:
            new_kb = json.load(f)
        
        # Compare key metrics
        assert len(new_kb) >= len(regression_kb) * 0.95  # Allow 5% variance
        
        # Check critical elements are found
        elements = {f['element'] for f in new_kb}
        assert 'Travel' in elements
        assert 'Direct Labor' in elements
        assert 'G&A' in elements

class TestIntegration:
    """End-to-end pipeline tests"""
    
    @pytest.mark.integration
    def test_full_pipeline(self, tmp_path):
        """Test complete pipeline execution"""
        from proposalOS_cli import run_pipeline
        
        result = run_pipeline.callback(
            config=None,
            output_dir=str(tmp_path),
            dry_run=True,
            parallel=False
        )
        
        # Check all outputs generated
        assert (tmp_path / 'RFP_KnowledgeBase').exists()
        assert (tmp_path / 'RFP_Discovery_Reports').exists()
        assert (tmp_path / 'Cost_Volume_Complete.md').exists()
        
    @pytest.mark.performance
    def test_parallel_processing(self, benchmark):
        """Benchmark parallel vs sequential"""
        from proposalOS import process_docs_parallel
        
        docs = [{"text": f"Document {i}"} for i in range(100)]
        
        result = benchmark(
            asyncio.run,
            process_docs_parallel(docs, max_concurrent=5)
        )
        
        assert len(result) == 100
```

---

## 🌐 Phase 7: SaaS/API Enablement (Week 10)

### 7.1 REST API Service

```python
# api/proposalOS_api.py
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile
from pydantic import BaseModel
from typing import List, Optional, Dict
import uuid
from datetime import datetime

app = FastAPI(title="ProposalOS API", version="1.0.0")

# Models
class DiscoveryRequest(BaseModel):
    documents: List[Dict[str, str]]  # [{title, section, text, url}]
    model: str = "gemini-2.5-pro"
    strict: bool = False
    confidence_threshold: float = 0.3

class DiscoveryResponse(BaseModel):
    job_id: str
    status: str
    facts_count: int
    kb_url: Optional[str]

class CostVolumeRequest(BaseModel):
    kb_url: str
    inputs: Dict  # Labor, materials, travel, etc.
    template: str = "default"

# Job tracking
jobs = {}

@app.post("/api/v1/discovery", response_model=DiscoveryResponse)
async def start_discovery(request: DiscoveryRequest, background_tasks: BackgroundTasks):
    """Start asynchronous EoC discovery job"""
    job_id = str(uuid.uuid4())
    
    # Start background processing
    background_tasks.add_task(
        process_discovery,
        job_id=job_id,
        request=request
    )
    
    jobs[job_id] = {
        "status": "processing",
        "started_at": datetime.utcnow().isoformat(),
        "request": request.dict()
    }
    
    return DiscoveryResponse(
        job_id=job_id,
        status="processing",
        facts_count=0,
        kb_url=None
    )

@app.get("/api/v1/discovery/{job_id}")
async def get_discovery_status(job_id: str):
    """Check discovery job status"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]

@app.post("/api/v1/cost-volume")
async def generate_cost_volume(request: CostVolumeRequest):
    """Generate cost volume from KB and inputs"""
    from automated_cost_volume_builder import AutomatedCostVolumeBuilder
    
    # Download KB from URL
    kb_path = await download_kb(request.kb_url)
    
    # Build cost volume
    builder = AutomatedCostVolumeBuilder(kb_path, request.inputs)
    cv_content = builder.build_cost_volume()
    
    # Store and return URL
    cv_url = await store_cost_volume(cv_content)
    
    return {
        "status": "success",
        "cost_volume_url": cv_url,
        "total_cost": builder.get_total_cost()
    }

@app.post("/api/v1/validate")
async def validate_facts(facts: List[Dict]):
    """Validate facts for compliance"""
    from enhanced_citation_validator import EnhancedCitationValidator
    from confidence_thresholds import ConfidenceValidator
    
    citation_validator = EnhancedCitationValidator()
    confidence_validator = ConfidenceValidator()
    
    results = []
    for fact in facts:
        citation_result = citation_validator.validate_all_citations(fact)
        confidence_result = confidence_validator.assess_fact(fact)
        
        results.append({
            "fact_id": fact.get("fact_id"),
            "element": fact.get("element"),
            "citation_validity": citation_result["overall_validity"],
            "confidence_level": confidence_result[0].name,
            "issues": confidence_result[1]
        })
    
    return {
        "total_facts": len(facts),
        "valid_facts": sum(1 for r in results if r["citation_validity"] > 0.5),
        "results": results
    }

@app.post("/api/v1/kb/merge")
async def merge_kb_with_inputs(file: UploadFile, user_inputs: Dict):
    """Merge uploaded KB with user inputs"""
    # Parse uploaded KB
    content = await file.read()
    kb_facts = json.loads(content)
    
    # Merge with user inputs
    merged_facts = []
    for fact in kb_facts:
        # Check if user has override for this element
        if fact["element"] in user_inputs:
            fact["user_override"] = user_inputs[fact["element"]]
            fact["confidence"] = 1.0  # User input has full confidence
        merged_facts.append(fact)
    
    # Add new user facts
    for element, data in user_inputs.items():
        if not any(f["element"] == element for f in kb_facts):
            merged_facts.append({
                "fact_id": str(uuid.uuid4()),
                "element": element,
                "classification": data.get("classification", "direct"),
                "source": "user_input",
                "confidence": 1.0,
                "user_data": data
            })
    
    return {
        "merged_facts": merged_facts,
        "original_count": len(kb_facts),
        "user_additions": len(user_inputs),
        "total_facts": len(merged_facts)
    }

# Webhook support
@app.post("/api/v1/webhooks/parser-update")
async def handle_parser_update(background_tasks: BackgroundTasks):
    """Trigger pipeline on parser update"""
    background_tasks.add_task(trigger_pipeline_run)
    return {"status": "Pipeline triggered"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## 📈 Implementation Timeline & Metrics

### Timeline
- **Weeks 1-2**: Validation enhancements
- **Weeks 3-4**: Cost Volume automation
- **Week 5**: Attribution improvements
- **Weeks 6-7**: Review interface
- **Week 8**: Pipeline orchestration
- **Week 9**: Testing framework
- **Week 10**: API deployment

### Success Metrics
- **Validation Rate**: >95% facts pass validation
- **Processing Speed**: <2 min for 1000 documents
- **API Response**: <500ms for validation endpoints
- **Test Coverage**: >80% code coverage
- **User Adoption**: 50+ facts reviewed/day

### Risk Mitigation
- **Backup LLM providers** (Gemini → GPT-4 fallback)
- **Incremental rollout** (pilot with 5 users first)
- **Rollback capability** (version all KB outputs)
- **Performance monitoring** (APM with DataDog/NewRelic)

This roadmap transforms ProposalOS from a prototype to a production-ready system with enterprise-grade validation, automation, and scalability.