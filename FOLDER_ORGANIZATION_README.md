# Folder Organization - Agents Writing Reports

## Directory Structure

This folder has been organized into logical subsystems for the ProposalOS project:

### 📁 **ProposalOS_Production_System/**
The main production-ready orchestrator system
- **Core_Orchestrator/** - Main orchestrator implementations
  - `orchestrator_production.py` - Production-hardened orchestrator
  - `orchestrator_enhanced.py` - Enhanced version with additional features
  - `orchestrator_procurement_enhanced.py` - Procurement-focused orchestrator
  
- **Procurement_Modules/** - Procurement and compliance modules
  - `sam_rfp_scraper.py` - SAM.gov RFP opportunity scraper
  - `procurement_compliance_checker.py` - Subcontractor compliance validation
  - `validate_subcontract.py` - DFARS/FAR validation logic
  
- **Tests/** - Integration and unit tests
  - `test_proposalOS_integration.py` - Comprehensive test suite
  
- **Documentation/** - System documentation
  - `PROPOSALÖS_PRODUCTION_READY_SUMMARY.md` - Production deployment guide
  - `PROPOSALEOS_COMPREHENSIVE_ANALYSIS_REPORT.md` - System analysis
  - `ROADMAP_IMPLEMENTATION.md` - Implementation roadmap
  
- **Code_Snippets/** - Implementation examples and patches
  - Various numbered Python files with specific patches and enhancements
  
- **Configuration/** - Environment and configuration files
  - `LLM_MODEL_G.env` - Gemini model configuration

### 📁 **RFP_Discovery_System/**
RFP processing and discovery pipeline
- `compile_reports_refactor.py` - Main RFP discovery engine
- `dita_parser_AF_SF_Army_Navy.py` - DITA format parser for military RFPs
- `sandbox_graph_builder.py` - Knowledge graph builder
- `KB_cleaned.json` - Cleaned knowledge base
- `demo_inputs.json` - Demo input data
- **RFP_Discovery_Reports/** - Generated discovery reports
- **RFP_KnowledgeBase/** - RFP knowledge base facts

### 📁 **Cost_Volume_Assembly/**
Cost volume generation and assembly tools
- `sandbox_cost_volume_assembler.py` - Cost volume assembler v1
- `sandbox_cost_volume_assembler_v2.py` - Cost volume assembler v2
- `sandbox_cost_algorithms.py` - Cost calculation algorithms
- `Cost_Volume_FULL.md` - Complete cost volume template
- `Cost_Volume_Skeleton.md` - Cost volume skeleton
- `Cost_Volume_Tables.md` - Cost volume tables format

### 📁 **Validation_Testing/**
Testing and validation infrastructure
- `test_refactored_validator.py` - Validator test suite
- `test_error_scenarios.py` - Error scenario tests
- `error_tracking_dashboard.py` - Error tracking dashboard
- `error_analysis_report.md` - Error analysis documentation
- `refactored_validator_test_report.md` - Validator test results
- `REFACTORED_VALIDATOR_ANALYSIS.md` - Validator analysis
- `sandbox_validate_kb.py` - Knowledge base validator
- `test_kb_errors.json` - Test error data
- `test_kb_errors.md` - Test error documentation

### 📁 **graph_out/**
Graph visualization outputs
- `adjacency.json` - Graph adjacency matrix
- `edges.csv` - Graph edges data
- `graph.graphml` - GraphML format
- `nodes.csv` - Graph nodes data

## Files Not Yet Organized

The following files remain in the root directory and may need further categorization:
- `# summary.md` - General summary
- `# updated_complile_reports.py` - Updated compiler
- `# updated_sandbox_cost_volume_assembler.py` - Updated assembler
- `# updated_sandbox_validate_kb.py` - Updated validator
- `Reports that need to be gernated.md` - Todo list for reports
- `extend inputs schema.py` - Schema extension
- Graph files in root (adjacency.json, edges.csv, graph.graphml, nodes.csv)

## Usage

Each subfolder represents a distinct component of the ProposalOS system:

1. **ProposalOS_Production_System** - Deploy this for the main orchestrator
2. **RFP_Discovery_System** - Use for RFP processing and EoC discovery
3. **Cost_Volume_Assembly** - Generate cost volumes and estimates
4. **Validation_Testing** - Run tests and validate implementations

## Recent Updates (August 9, 2025)

- Organized all ProposalOS production files into structured folders
- Separated procurement modules from core orchestrator
- Isolated test suites and validation tools
- Consolidated documentation in appropriate folders
- Preserved original graph outputs and knowledge bases

---

*Organization completed: August 9, 2025*