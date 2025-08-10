# Project Status & Technical Blueprint

_Generated: 2025-08-10 03:38:38Z_

**Scanned root:** `/Users/carolinehusebo/Desktop/Agents writing reports`  
**Python files:** 59  
**Total functions:** 444  
**Avg cyclomatic complexity:** 5.39

## Technical Blueprint
- **Core modules discovered:**
  - `# updated_complile_reports.py`
  - `# updated_sandbox_cost_volume_assembler.py`
  - `# updated_sandbox_validate_kb.py`
  - `Cost_Volume_Assembly/Costing,Pricing Reports/annual_fiscal_year_report_assembler.py`
  - `Cost_Volume_Assembly/Costing,Pricing Reports/dfars_checklist_assembler.py`
  - `Cost_Volume_Assembly/Costing,Pricing Reports/dfars_cover_page_assembler.py`
  - `Cost_Volume_Assembly/Costing,Pricing Reports/far_15_2_assembler.py`
  - `Cost_Volume_Assembly/Costing,Pricing Reports/fccom_form_assembler.py`
  - `Cost_Volume_Assembly/Costing,Pricing Reports/render_md_dfars_templates.py`
  - `Cost_Volume_Assembly/sandbox_cost_algorithms.py`
  - `Cost_Volume_Assembly/sandbox_cost_volume_assembler.py`
  - `Cost_Volume_Assembly/sandbox_cost_volume_assembler_v2.py`
  - `ProposalOS_Production_System/Code_Snippets/1) Concrete prompt (RFP EoC Extraction v2).py`
  - `ProposalOS_Production_System/Code_Snippets/2) Tiny post-processor (reject:repair).py`
  - `ProposalOS_Production_System/Code_Snippets/3) Orchestrator patches (auth default-deny + extraction schema expectation).py`
  - `ProposalOS_Production_System/Code_Snippets/4) Redis token-bucket rate limiter (middleware).py`
  - `ProposalOS_Production_System/Code_Snippets/5) PR plan- align model choice + remove duplicates.py`
  - `ProposalOS_Production_System/Code_Snippets/Add Procurement Endpoints with a Circuit Breaker.py`
  - `ProposalOS_Production_System/Code_Snippets/And in your handler-.py`
  - `ProposalOS_Production_System/Code_Snippets/CORS tighten (env-driven).py`
  - `ProposalOS_Production_System/Code_Snippets/Extraction schema expectation (align server to new JSON).py`
  - `ProposalOS_Production_System/Core_Orchestrator/auth.py`
  - `ProposalOS_Production_System/Core_Orchestrator/circuit_breakers.py`
  - `ProposalOS_Production_System/Core_Orchestrator/config.py`
  - `ProposalOS_Production_System/Core_Orchestrator/extraction_service.py`
  - `ProposalOS_Production_System/Core_Orchestrator/orchestrator_enhanced.py`
  - `ProposalOS_Production_System/Core_Orchestrator/orchestrator_procurement_enhanced.py`
  - `ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py`
  - `ProposalOS_Production_System/Core_Orchestrator/state_manager.py`
  - `ProposalOS_Production_System/Procurement_Modules/procurement_compliance_checker.py`
  - `ProposalOS_Production_System/Procurement_Modules/sam_rfp_scraper.py`
  - `ProposalOS_Production_System/Procurement_Modules/validate_subcontract.py`
  - `ProposalOS_Production_System/Tests/test_proposalOS_integration.py`
  - `RFP_Discovery_System/compile_reports_refactor (1).py`
  - `RFP_Discovery_System/compile_reports_refactor.py`
  - `RFP_Discovery_System/complile_reports.py`
  - `RFP_Discovery_System/dita_parser_AF_SF_Army_Navy.py`
  - `RFP_Discovery_System/sandbox_graph_builder.py`
  - `Validation_Testing/error_tracking_dashboard.py`
  - `Validation_Testing/sandbox_validate_kb.py`
  - `Validation_Testing/test_error_scenarios.py`
  - `Validation_Testing/test_refactored_validator.py`
  - `extend inputs schema.py`
  - `main.py`
  - `procurement_integrator.py`
  - `project_audit (1).py`
  - `proposalos_rge/__init__.py`
  - `proposalos_rge/api/endpoints.py`
  - `proposalos_rge/example_usage.py`
  - `proposalos_rge/inputs/kb_loader.py`
  - `proposalos_rge/inputs/ui_adapter.py`
  - `proposalos_rge/normalize/builder.py`
  - `proposalos_rge/registry.py`
  - `proposalos_rge/render/__init__.py`
  - `proposalos_rge/render/md/annual_fy.py`
  - `proposalos_rge/render/md/dfars_templates.py`
  - `proposalos_rge/schemas.py`
  - `proposalos_rge/validate/rules.py`
  - `test_proposalos_rge.py`

- **HTTP endpoints (FastAPI heuristics):**
| File                            | Method | Route                    | Line |
| ------------------------------- | ------ | ------------------------ | ---- |
| proposalos_rge/api/endpoints.py | GET    | /templates               | 45   |
| proposalos_rge/api/endpoints.py | GET    | /templates/{template_id} | 56   |
| proposalos_rge/api/endpoints.py | POST   | /validate                | 73   |
| proposalos_rge/api/endpoints.py | POST   | /preview                 | 118  |
| proposalos_rge/api/endpoints.py | POST   | /generate                | 193  |
| proposalos_rge/api/endpoints.py | POST   | /batch                   | 298  |
| proposalos_rge/api/endpoints.py | GET    | /health                  | 328  |

## Ontology Snapshot

**Ontology elements (top 15):**
- Fact:db29b9b8: 1
- Section:far_31_201_2::31.201-2: 1
- Fact:71c734df: 1
- Fact:49170334: 1
- Fact:37e4c5c1: 1
- Section:dfars_231_205_46::231.205-46: 1
- Fact:93683e2e: 1
- Fact:ef4125f1: 1
- Fact:16b98039: 1
- Fact:e5b36d96: 1
- Fact:266332e5: 1
- Fact:3c37f2e7: 1
- Section:cas_410::410.50: 1
- Fact:134556fc: 1
- Fact:0e607d84: 1

## Functionality Inventory (Renderers & Templates)

| File                                                                      | Renderer                | Line |
| ------------------------------------------------------------------------- | ----------------------- | ---- |
| Cost_Volume_Assembly/Costing,Pricing Reports/render_md_dfars_templates.py | render_dfars_checklist  | 137  |
| Cost_Volume_Assembly/Costing,Pricing Reports/render_md_dfars_templates.py | render_dfars_cover_page | 196  |
| proposalos_rge/render/md/dfars_templates.py                               | render_dfars_checklist  | 66   |
| proposalos_rge/render/md/dfars_templates.py                               | render_dfars_cover_page | 208  |

## Quality Review
### Correctness

| File                                                                                           | Issue                                                                |
| ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| # updated_complile_reports.py                                                                  | Correctness: broad exception 'Exception' at L56. Narrow the scope.   |
| # updated_complile_reports.py                                                                  | Correctness: broad exception 'Exception' at L98. Narrow the scope.   |
| # updated_complile_reports.py                                                                  | Correctness: broad exception 'Exception' at L131. Narrow the scope.  |
| # updated_complile_reports.py                                                                  | Correctness: broad exception 'Exception' at L138. Narrow the scope.  |
| # updated_complile_reports.py                                                                  | Correctness: broad exception 'Exception' at L201. Narrow the scope.  |
| # updated_complile_reports.py                                                                  | Correctness: broad exception 'Exception' at L282. Narrow the scope.  |
| # updated_sandbox_validate_kb.py                                                               | Correctness: broad exception 'Exception' at L53. Narrow the scope.   |
| Cost_Volume_Assembly/Costing,Pricing Reports/render_md_dfars_templates.py                      | Correctness: broad exception 'Exception' at L289. Narrow the scope.  |
| Cost_Volume_Assembly/Costing,Pricing Reports/render_md_dfars_templates.py                      | Correctness: broad exception 'Exception' at L39. Narrow the scope.   |
| ProposalOS_Production_System/Code_Snippets/Add Procurement Endpoints with a Circuit Breaker.py | Correctness: broad exception 'Exception' at L51. Narrow the scope.   |
| ProposalOS_Production_System/Core_Orchestrator/auth.py                                         | Correctness: broad exception 'Exception' at L93. Narrow the scope.   |
| ProposalOS_Production_System/Core_Orchestrator/auth.py                                         | Correctness: bare 'except' at L141. Catch specific exceptions.       |
| ProposalOS_Production_System/Core_Orchestrator/circuit_breakers.py                             | Correctness: broad exception 'Exception' at L94. Narrow the scope.   |
| ProposalOS_Production_System/Core_Orchestrator/circuit_breakers.py                             | Correctness: broad exception 'Exception' at L285. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/circuit_breakers.py                             | Correctness: broad exception 'Exception' at L422. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/config.py                                       | Correctness: broad exception 'Exception' at L229. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/config.py                                       | Correctness: broad exception 'Exception' at L244. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/extraction_service.py                           | Correctness: broad exception 'Exception' at L445. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/extraction_service.py                           | Correctness: broad exception 'Exception' at L482. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_enhanced.py                        | Correctness: broad exception 'Exception' at L77. Narrow the scope.   |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_enhanced.py                        | Correctness: broad exception 'Exception' at L86. Narrow the scope.   |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_enhanced.py                        | Correctness: broad exception 'Exception' at L384. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_enhanced.py                        | Correctness: broad exception 'Exception' at L434. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_enhanced.py                        | Correctness: broad exception 'Exception' at L553. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_enhanced.py                        | Correctness: broad exception 'Exception' at L635. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_enhanced.py                        | Correctness: broad exception 'Exception' at L695. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_enhanced.py                        | Correctness: bare 'except' at L792. Catch specific exceptions.       |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_enhanced.py                        | Correctness: bare 'except' at L802. Catch specific exceptions.       |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_enhanced.py                        | Correctness: broad exception 'Exception' at L288. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_enhanced.py                        | Correctness: broad exception 'Exception' at L299. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_enhanced.py                        | Correctness: broad exception 'Exception' at L318. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_enhanced.py                        | Correctness: broad exception 'Exception' at L325. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_enhanced.py                        | Correctness: broad exception 'Exception' at L337. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_enhanced.py                        | Correctness: broad exception 'Exception' at L344. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_procurement_enhanced.py            | Correctness: bare 'except' at L86. Catch specific exceptions.        |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_procurement_enhanced.py            | Correctness: broad exception 'Exception' at L717. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_procurement_enhanced.py            | Correctness: broad exception 'Exception' at L758. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_procurement_enhanced.py            | Correctness: broad exception 'Exception' at L813. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_procurement_enhanced.py            | Correctness: broad exception 'Exception' at L882. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_procurement_enhanced.py            | Correctness: broad exception 'Exception' at L904. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_procurement_enhanced.py            | Correctness: broad exception 'Exception' at L309. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_procurement_enhanced.py            | Correctness: broad exception 'Exception' at L328. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_procurement_enhanced.py            | Correctness: broad exception 'Exception' at L398. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_procurement_enhanced.py            | Correctness: broad exception 'Exception' at L559. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_procurement_enhanced.py            | Correctness: broad exception 'Exception' at L568. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                      | Correctness: broad exception 'Exception' at L736. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                      | Correctness: broad exception 'Exception' at L792. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                      | Correctness: broad exception 'Exception' at L927. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                      | Correctness: broad exception 'Exception' at L972. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                      | Correctness: broad exception 'Exception' at L1111. Narrow the scope. |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                      | Correctness: broad exception 'Exception' at L1367. Narrow the scope. |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                      | Correctness: broad exception 'Exception' at L1561. Narrow the scope. |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                      | Correctness: broad exception 'Exception' at L1589. Narrow the scope. |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                      | Correctness: broad exception 'Exception' at L1621. Narrow the scope. |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                      | Correctness: broad exception 'Exception' at L275. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                      | Correctness: broad exception 'Exception' at L289. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                      | Correctness: broad exception 'Exception' at L1472. Narrow the scope. |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                      | Correctness: broad exception 'Exception' at L200. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                      | Correctness: broad exception 'Exception' at L342. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                      | Correctness: broad exception 'Exception' at L634. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                      | Correctness: broad exception 'Exception' at L647. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                      | Correctness: broad exception 'Exception' at L689. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                      | Correctness: broad exception 'Exception' at L711. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                      | Correctness: broad exception 'Exception' at L720. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/state_manager.py                                | Correctness: broad exception 'Exception' at L503. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/state_manager.py                                | Correctness: broad exception 'Exception' at L511. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/state_manager.py                                | Correctness: broad exception 'Exception' at L202. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/state_manager.py                                | Correctness: broad exception 'Exception' at L217. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/state_manager.py                                | Correctness: broad exception 'Exception' at L332. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/state_manager.py                                | Correctness: broad exception 'Exception' at L341. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/state_manager.py                                | Correctness: broad exception 'Exception' at L380. Narrow the scope.  |
| ProposalOS_Production_System/Core_Orchestrator/state_manager.py                                | Correctness: broad exception 'Exception' at L392. Narrow the scope.  |
| ProposalOS_Production_System/Procurement_Modules/sam_rfp_scraper.py                            | Correctness: broad exception 'Exception' at L433. Narrow the scope.  |
| ProposalOS_Production_System/Procurement_Modules/sam_rfp_scraper.py                            | Correctness: bare 'except' at L192. Catch specific exceptions.       |
| ProposalOS_Production_System/Procurement_Modules/sam_rfp_scraper.py                            | Correctness: broad exception 'Exception' at L178. Narrow the scope.  |
| ProposalOS_Production_System/Tests/test_proposalOS_integration.py                              | Correctness: bare 'except' at L454. Catch specific exceptions.       |
| ProposalOS_Production_System/Tests/test_proposalOS_integration.py                              | Correctness: bare 'except' at L474. Catch specific exceptions.       |
| RFP_Discovery_System/compile_reports_refactor.py                                               | Correctness: broad exception 'Exception' at L41. Narrow the scope.   |
| RFP_Discovery_System/compile_reports_refactor.py                                               | Correctness: broad exception 'Exception' at L202. Narrow the scope.  |
| RFP_Discovery_System/compile_reports_refactor.py                                               | Correctness: broad exception 'Exception' at L477. Narrow the scope.  |
| RFP_Discovery_System/compile_reports_refactor.py                                               | Correctness: broad exception 'Exception' at L123. Narrow the scope.  |
| RFP_Discovery_System/compile_reports_refactor.py                                               | Correctness: broad exception 'Exception' at L264. Narrow the scope.  |
| RFP_Discovery_System/compile_reports_refactor.py                                               | Correctness: broad exception 'Exception' at L414. Narrow the scope.  |
| RFP_Discovery_System/compile_reports_refactor.py                                               | Correctness: broad exception 'Exception' at L325. Narrow the scope.  |
| RFP_Discovery_System/complile_reports.py                                                       | Correctness: broad exception 'Exception' at L109. Narrow the scope.  |
| RFP_Discovery_System/complile_reports.py                                                       | Correctness: broad exception 'Exception' at L117. Narrow the scope.  |
| RFP_Discovery_System/complile_reports.py                                                       | Correctness: broad exception 'Exception' at L258. Narrow the scope.  |
| RFP_Discovery_System/complile_reports.py                                                       | Correctness: broad exception 'Exception' at L294. Narrow the scope.  |
| RFP_Discovery_System/complile_reports.py                                                       | Correctness: broad exception 'Exception' at L318. Narrow the scope.  |
| RFP_Discovery_System/dita_parser_AF_SF_Army_Navy.py                                            | Correctness: broad exception 'Exception' at L69. Narrow the scope.   |
| Validation_Testing/error_tracking_dashboard.py                                                 | Correctness: bare 'except' at L305. Catch specific exceptions.       |
| Validation_Testing/sandbox_validate_kb.py                                                      | Correctness: broad exception 'Exception' at L50. Narrow the scope.   |
| extend inputs schema.py                                                                        | Correctness: broad exception 'Exception' at L41. Narrow the scope.   |
| extend inputs schema.py                                                                        | Correctness: broad exception 'Exception' at L202. Narrow the scope.  |
| extend inputs schema.py                                                                        | Correctness: broad exception 'Exception' at L477. Narrow the scope.  |
| extend inputs schema.py                                                                        | Correctness: broad exception 'Exception' at L123. Narrow the scope.  |
| extend inputs schema.py                                                                        | Correctness: broad exception 'Exception' at L264. Narrow the scope.  |
| extend inputs schema.py                                                                        | Correctness: broad exception 'Exception' at L414. Narrow the scope.  |
| extend inputs schema.py                                                                        | Correctness: broad exception 'Exception' at L325. Narrow the scope.  |
| main.py                                                                                        | Correctness: broad exception 'Exception' at L577. Narrow the scope.  |
| main.py                                                                                        | Correctness: bare 'except' at L130. Catch specific exceptions.       |
| procurement_integrator.py                                                                      | Correctness: broad exception 'Exception' at L113. Narrow the scope.  |
| procurement_integrator.py                                                                      | Correctness: broad exception 'Exception' at L211. Narrow the scope.  |
| project_audit (1).py                                                                           | Correctness: broad exception 'Exception' at L51. Narrow the scope.   |
| project_audit (1).py                                                                           | Correctness: broad exception 'Exception' at L60. Narrow the scope.   |
| project_audit (1).py                                                                           | Correctness: broad exception 'Exception' at L190. Narrow the scope.  |
| project_audit (1).py                                                                           | Correctness: broad exception 'Exception' at L222. Narrow the scope.  |
| project_audit (1).py                                                                           | Correctness: broad exception 'Exception' at L54. Narrow the scope.   |
| proposalos_rge/api/endpoints.py                                                                | Correctness: broad exception 'Exception' at L173. Narrow the scope.  |
| proposalos_rge/api/endpoints.py                                                                | Correctness: broad exception 'Exception' at L320. Narrow the scope.  |
| proposalos_rge/example_usage.py                                                                | Correctness: broad exception 'Exception' at L381. Narrow the scope.  |
| proposalos_rge/example_usage.py                                                                | Correctness: broad exception 'Exception' at L388. Narrow the scope.  |
| proposalos_rge/example_usage.py                                                                | Correctness: broad exception 'Exception' at L393. Narrow the scope.  |
| test_proposalos_rge.py                                                                         | Correctness: broad exception 'Exception' at L96. Narrow the scope.   |
| test_proposalos_rge.py                                                                         | Correctness: broad exception 'Exception' at L122. Narrow the scope.  |
| test_proposalos_rge.py                                                                         | Correctness: broad exception 'Exception' at L211. Narrow the scope.  |
| test_proposalos_rge.py                                                                         | Correctness: broad exception 'Exception' at L280. Narrow the scope.  |
| test_proposalos_rge.py                                                                         | Correctness: broad exception 'Exception' at L368. Narrow the scope.  |
| test_proposalos_rge.py                                                                         | Correctness: broad exception 'Exception' at L414. Narrow the scope.  |
| test_proposalos_rge.py                                                                         | Correctness: broad exception 'Exception' at L477. Narrow the scope.  |
| test_proposalos_rge.py                                                                         | Correctness: broad exception 'Exception' at L543. Narrow the scope.  |
| test_proposalos_rge.py                                                                         | Correctness: broad exception 'Exception' at L571. Narrow the scope.  |

### Security

| File                                            | Issue                                                                              |
| ----------------------------------------------- | ---------------------------------------------------------------------------------- |
| Validation_Testing/test_refactored_validator.py | Security: Use of exec() can execute arbitrary code.                                |
| project_audit (1).py                            | Security: Use of eval() can execute arbitrary code.                                |
| project_audit (1).py                            | Security: Use of exec() can execute arbitrary code.                                |
| project_audit (1).py                            | Security: pickle.load is unsafe with untrusted data. Prefer json or a safe format. |
| project_audit (1).py                            | Security: pickle.loads is unsafe with untrusted data.                              |
| project_audit (1).py                            | Security: yaml.load without SafeLoader is unsafe; use safe_load.                   |

### Performance

| File                                                                                 | Function                       | Concern                                      |
| ------------------------------------------------------------------------------------ | ------------------------------ | -------------------------------------------- |
| # updated_complile_reports.py                                                        | run_rfp_discovery              | High complexity (29) may affect performance. |
| # updated_sandbox_validate_kb.py                                                     | sanity_score                   | High complexity (13) may affect performance. |
| Cost_Volume_Assembly/sandbox_cost_volume_assembler_v2.py                             | main                           | High complexity (17) may affect performance. |
| ProposalOS_Production_System/Code_Snippets/2) Tiny post-processor (reject:repair).py | validate_and_repair_facts      | High complexity (25) may affect performance. |
| ProposalOS_Production_System/Core_Orchestrator/config.py                             | __init__                       | High complexity (12) may affect performance. |
| ProposalOS_Production_System/Core_Orchestrator/config.py                             | _load_gemini_env               | High complexity (12) may affect performance. |
| ProposalOS_Production_System/Core_Orchestrator/config.py                             | validate                       | High complexity (16) may affect performance. |
| ProposalOS_Production_System/Core_Orchestrator/extraction_service.py                 | validate_and_repair            | High complexity (15) may affect performance. |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_procurement_enhanced.py  | procure_subcontract            | High complexity (15) may affect performance. |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py            | lifespan                       | High complexity (16) may affect performance. |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py            | extract_data_from_conversation | High complexity (15) may affect performance. |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py            | orchestrate_conversation       | High complexity (12) may affect performance. |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py            | export_session                 | High complexity (24) may affect performance. |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py            | check_vendor_compliance        | High complexity (19) may affect performance. |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py            | procure_subcontract            | High complexity (14) may affect performance. |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py            | health_check                   | High complexity (12) may affect performance. |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py            | query                          | High complexity (29) may affect performance. |
| ProposalOS_Production_System/Core_Orchestrator/state_manager.py                      | get_session                    | High complexity (15) may affect performance. |
| ProposalOS_Production_System/Core_Orchestrator/state_manager.py                      | delete_session                 | High complexity (13) may affect performance. |
| ProposalOS_Production_System/Core_Orchestrator/state_manager.py                      | get_user_sessions              | High complexity (22) may affect performance. |
| ProposalOS_Production_System/Procurement_Modules/procurement_compliance_checker.py   | check_subcontractor_compliance | High complexity (27) may affect performance. |
| ProposalOS_Production_System/Procurement_Modules/procurement_compliance_checker.py   | validate_bom                   | High complexity (12) may affect performance. |
| ProposalOS_Production_System/Procurement_Modules/sam_rfp_scraper.py                  | main                           | High complexity (19) may affect performance. |
| ProposalOS_Production_System/Procurement_Modules/sam_rfp_scraper.py                  | scrape_rfps                    | High complexity (12) may affect performance. |
| ProposalOS_Production_System/Procurement_Modules/validate_subcontract.py             | validate_subcontract           | High complexity (16) may affect performance. |
| ProposalOS_Production_System/Procurement_Modules/validate_subcontract.py             | generate_compliance_report     | High complexity (21) may affect performance. |
| RFP_Discovery_System/compile_reports_refactor.py                                     | load_parsed_regulations        | High complexity (20) may affect performance. |
| RFP_Discovery_System/compile_reports_refactor.py                                     | clean_items                    | High complexity (29) may affect performance. |
| RFP_Discovery_System/compile_reports_refactor.py                                     | run_rfp_discovery              | High complexity (25) may affect performance. |
| RFP_Discovery_System/complile_reports.py                                             | load_parsed_regulations        | High complexity (21) may affect performance. |
| RFP_Discovery_System/complile_reports.py                                             | run_rfp_discovery              | High complexity (34) may affect performance. |
| RFP_Discovery_System/dita_parser_AF_SF_Army_Navy.py                                  | iter_docs                      | High complexity (16) may affect performance. |
| Validation_Testing/test_error_scenarios.py                                           | create_test_kb_with_errors     | Very long function (234 LOC) may be slow.    |
| extend inputs schema.py                                                              | load_parsed_regulations        | High complexity (20) may affect performance. |
| extend inputs schema.py                                                              | clean_items                    | High complexity (29) may affect performance. |
| extend inputs schema.py                                                              | run_rfp_discovery              | High complexity (25) may affect performance. |
| main.py                                                                              | _generate_pdf_report           | Very long function (153 LOC) may be slow.    |
| project_audit (1).py                                                                 | find_endpoints                 | High complexity (18) may affect performance. |
| project_audit (1).py                                                                 | detect_issues                  | High complexity (24) may affect performance. |
| project_audit (1).py                                                                 | summarize_kb                   | High complexity (22) may affect performance. |
| project_audit (1).py                                                                 | main                           | High complexity (34) may affect performance. |
| project_audit (1).py                                                                 | main                           | Very long function (163 LOC) may be slow.    |
| proposalos_rge/api/endpoints.py                                                      | generate                       | High complexity (27) may affect performance. |
| proposalos_rge/example_usage.py                                                      | example_2_synthetic_data       | Very long function (200 LOC) may be slow.    |
| proposalos_rge/normalize/builder.py                                                  | _detect_conflicts              | High complexity (13) may affect performance. |
| proposalos_rge/render/md/annual_fy.py                                                | render                         | High complexity (48) may affect performance. |
| proposalos_rge/render/md/annual_fy.py                                                | render                         | Very long function (153 LOC) may be slow.    |
| proposalos_rge/render/md/dfars_templates.py                                          | render_dfars_checklist         | High complexity (27) may affect performance. |
| proposalos_rge/render/md/dfars_templates.py                                          | render_dfars_cover_page        | High complexity (26) may affect performance. |
| proposalos_rge/render/md/dfars_templates.py                                          | render_dfars_cover_page        | Very long function (163 LOC) may be slow.    |
| proposalos_rge/validate/rules.py                                                     | validate_facts                 | High complexity (17) may affect performance. |
| proposalos_rge/validate/rules.py                                                     | _validate_allocations          | High complexity (16) may affect performance. |

### Maintainability & Code Smells

| File                                                                                             | Function/Context                 | Smell / Suggestion                                                          |
| ------------------------------------------------------------------------------------------------ | -------------------------------- | --------------------------------------------------------------------------- |
| # updated_complile_reports.py                                                                    | run_rfp_discovery                | High cyclomatic complexity (29). Consider refactor into helpers.            |
| # updated_complile_reports.py                                                                    | run_rfp_discovery                | Long function (119 LOC). Extract smaller functions.                         |
| # updated_sandbox_cost_volume_assembler.py                                                       | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| # updated_sandbox_validate_kb.py                                                                 | sanity_score                     | High cyclomatic complexity (13). Consider refactor into helpers.            |
| # updated_sandbox_validate_kb.py                                                                 | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| Cost_Volume_Assembly/Costing,Pricing Reports/annual_fiscal_year_report_assembler.py              | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| Cost_Volume_Assembly/Costing,Pricing Reports/dfars_checklist_assembler.py                        | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| Cost_Volume_Assembly/Costing,Pricing Reports/dfars_cover_page_assembler.py                       | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| Cost_Volume_Assembly/Costing,Pricing Reports/far_15_2_assembler.py                               | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| Cost_Volume_Assembly/Costing,Pricing Reports/fccom_form_assembler.py                             | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| Cost_Volume_Assembly/Costing,Pricing Reports/render_md_dfars_templates.py                        | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| Cost_Volume_Assembly/sandbox_cost_algorithms.py                                                  | compute_bases_and_fee            | Many parameters (7). Consider grouping with dataclass/pydantic model.       |
| Cost_Volume_Assembly/sandbox_cost_volume_assembler.py                                            | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| Cost_Volume_Assembly/sandbox_cost_volume_assembler_v2.py                                         | main                             | High cyclomatic complexity (17). Consider refactor into helpers.            |
| Cost_Volume_Assembly/sandbox_cost_volume_assembler_v2.py                                         | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| ProposalOS_Production_System/Code_Snippets/2) Tiny post-processor (reject:repair).py             | _repair_if_generic               | High cyclomatic complexity (10). Consider refactor into helpers.            |
| ProposalOS_Production_System/Code_Snippets/2) Tiny post-processor (reject:repair).py             | validate_and_repair_facts        | High cyclomatic complexity (25). Consider refactor into helpers.            |
| ProposalOS_Production_System/Code_Snippets/5) PR plan- align model choice + remove duplicates.py | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| ProposalOS_Production_System/Code_Snippets/Add Procurement Endpoints with a Circuit Breaker.py   | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| ProposalOS_Production_System/Core_Orchestrator/auth.py                                           | authenticate                     | High cyclomatic complexity (11). Consider refactor into helpers.            |
| ProposalOS_Production_System/Core_Orchestrator/auth.py                                           | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| ProposalOS_Production_System/Core_Orchestrator/circuit_breakers.py                               | -                                | Code smell: empty except block (pass) at L422. Consider logging & handling. |
| ProposalOS_Production_System/Core_Orchestrator/circuit_breakers.py                               | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| ProposalOS_Production_System/Core_Orchestrator/config.py                                         | __init__                         | High cyclomatic complexity (12). Consider refactor into helpers.            |
| ProposalOS_Production_System/Core_Orchestrator/config.py                                         | __init__                         | Long function (133 LOC). Extract smaller functions.                         |
| ProposalOS_Production_System/Core_Orchestrator/config.py                                         | _load_gemini_env                 | High cyclomatic complexity (12). Consider refactor into helpers.            |
| ProposalOS_Production_System/Core_Orchestrator/config.py                                         | validate                         | High cyclomatic complexity (16). Consider refactor into helpers.            |
| ProposalOS_Production_System/Core_Orchestrator/config.py                                         | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| ProposalOS_Production_System/Core_Orchestrator/extraction_service.py                             | repair_generic_allowability      | High cyclomatic complexity (10). Consider refactor into helpers.            |
| ProposalOS_Production_System/Core_Orchestrator/extraction_service.py                             | validate_and_repair              | High cyclomatic complexity (15). Consider refactor into helpers.            |
| ProposalOS_Production_System/Core_Orchestrator/extraction_service.py                             | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_enhanced.py                          | extract_data_from_conversation   | High cyclomatic complexity (10). Consider refactor into helpers.            |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_enhanced.py                          | get_state                        | High cyclomatic complexity (10). Consider refactor into helpers.            |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_procurement_enhanced.py              | procure_subcontract              | High cyclomatic complexity (15). Consider refactor into helpers.            |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_procurement_enhanced.py              | procure_subcontract              | Long function (97 LOC). Extract smaller functions.                          |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_procurement_enhanced.py              | generate_cost_volume             | High cyclomatic complexity (11). Consider refactor into helpers.            |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                        | lifespan                         | High cyclomatic complexity (16). Consider refactor into helpers.            |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                        | extract_data_from_conversation   | High cyclomatic complexity (15). Consider refactor into helpers.            |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                        | orchestrate_conversation         | High cyclomatic complexity (12). Consider refactor into helpers.            |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                        | orchestrate_conversation         | Long function (98 LOC). Extract smaller functions.                          |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                        | export_session                   | High cyclomatic complexity (24). Consider refactor into helpers.            |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                        | check_vendor_compliance          | High cyclomatic complexity (19). Consider refactor into helpers.            |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                        | check_vendor_compliance          | Long function (132 LOC). Extract smaller functions.                         |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                        | procure_subcontract              | High cyclomatic complexity (14). Consider refactor into helpers.            |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                        | procure_subcontract              | Long function (120 LOC). Extract smaller functions.                         |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                        | health_check                     | High cyclomatic complexity (12). Consider refactor into helpers.            |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                        | validate                         | High cyclomatic complexity (10). Consider refactor into helpers.            |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                        | get_state                        | High cyclomatic complexity (10). Consider refactor into helpers.            |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                        | query                            | High cyclomatic complexity (29). Consider refactor into helpers.            |
| ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py                        | -                                | Maintainability: 1 TODO/FIXME notes present.                                |
| ProposalOS_Production_System/Core_Orchestrator/state_manager.py                                  | get_session                      | High cyclomatic complexity (15). Consider refactor into helpers.            |
| ProposalOS_Production_System/Core_Orchestrator/state_manager.py                                  | delete_session                   | High cyclomatic complexity (13). Consider refactor into helpers.            |
| ProposalOS_Production_System/Core_Orchestrator/state_manager.py                                  | get_user_sessions                | High cyclomatic complexity (22). Consider refactor into helpers.            |
| ProposalOS_Production_System/Core_Orchestrator/state_manager.py                                  | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| ProposalOS_Production_System/Procurement_Modules/procurement_compliance_checker.py               | main                             | High cyclomatic complexity (10). Consider refactor into helpers.            |
| ProposalOS_Production_System/Procurement_Modules/procurement_compliance_checker.py               | main                             | Long function (87 LOC). Extract smaller functions.                          |
| ProposalOS_Production_System/Procurement_Modules/procurement_compliance_checker.py               | check_subcontractor_compliance   | High cyclomatic complexity (27). Consider refactor into helpers.            |
| ProposalOS_Production_System/Procurement_Modules/procurement_compliance_checker.py               | check_subcontractor_compliance   | Long function (141 LOC). Extract smaller functions.                         |
| ProposalOS_Production_System/Procurement_Modules/procurement_compliance_checker.py               | generate_bom                     | Long function (104 LOC). Extract smaller functions.                         |
| ProposalOS_Production_System/Procurement_Modules/procurement_compliance_checker.py               | validate_bom                     | High cyclomatic complexity (12). Consider refactor into helpers.            |
| ProposalOS_Production_System/Procurement_Modules/procurement_compliance_checker.py               | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| ProposalOS_Production_System/Procurement_Modules/sam_rfp_scraper.py                              | main                             | High cyclomatic complexity (19). Consider refactor into helpers.            |
| ProposalOS_Production_System/Procurement_Modules/sam_rfp_scraper.py                              | main                             | Long function (92 LOC). Extract smaller functions.                          |
| ProposalOS_Production_System/Procurement_Modules/sam_rfp_scraper.py                              | scrape_rfps                      | High cyclomatic complexity (12). Consider refactor into helpers.            |
| ProposalOS_Production_System/Procurement_Modules/sam_rfp_scraper.py                              | scrape_rfps                      | Long function (96 LOC). Extract smaller functions.                          |
| ProposalOS_Production_System/Procurement_Modules/sam_rfp_scraper.py                              | scrape_rfps                      | Many parameters (7). Consider grouping with dataclass/pydantic model.       |
| ProposalOS_Production_System/Procurement_Modules/sam_rfp_scraper.py                              | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| ProposalOS_Production_System/Procurement_Modules/validate_subcontract.py                         | validate_subcontract             | High cyclomatic complexity (16). Consider refactor into helpers.            |
| ProposalOS_Production_System/Procurement_Modules/validate_subcontract.py                         | validate_subcontract             | Long function (96 LOC). Extract smaller functions.                          |
| ProposalOS_Production_System/Procurement_Modules/validate_subcontract.py                         | generate_compliance_report       | High cyclomatic complexity (21). Consider refactor into helpers.            |
| ProposalOS_Production_System/Procurement_Modules/validate_subcontract.py                         | generate_compliance_report       | Long function (96 LOC). Extract smaller functions.                          |
| ProposalOS_Production_System/Procurement_Modules/validate_subcontract.py                         | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| ProposalOS_Production_System/Tests/test_proposalOS_integration.py                                | -                                | Code smell: empty except block (pass) at L454. Consider logging & handling. |
| ProposalOS_Production_System/Tests/test_proposalOS_integration.py                                | -                                | Code smell: empty except block (pass) at L474. Consider logging & handling. |
| ProposalOS_Production_System/Tests/test_proposalOS_integration.py                                | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| RFP_Discovery_System/compile_reports_refactor.py                                                 | load_parsed_regulations          | High cyclomatic complexity (20). Consider refactor into helpers.            |
| RFP_Discovery_System/compile_reports_refactor.py                                                 | clean_items                      | High cyclomatic complexity (29). Consider refactor into helpers.            |
| RFP_Discovery_System/compile_reports_refactor.py                                                 | run_rfp_discovery                | High cyclomatic complexity (25). Consider refactor into helpers.            |
| RFP_Discovery_System/compile_reports_refactor.py                                                 | run_rfp_discovery                | Long function (82 LOC). Extract smaller functions.                          |
| RFP_Discovery_System/complile_reports.py                                                         | load_parsed_regulations          | High cyclomatic complexity (21). Consider refactor into helpers.            |
| RFP_Discovery_System/complile_reports.py                                                         | call_gemini                      | Many parameters (7). Consider grouping with dataclass/pydantic model.       |
| RFP_Discovery_System/complile_reports.py                                                         | run_rfp_discovery                | High cyclomatic complexity (34). Consider refactor into helpers.            |
| RFP_Discovery_System/complile_reports.py                                                         | run_rfp_discovery                | Long function (97 LOC). Extract smaller functions.                          |
| RFP_Discovery_System/dita_parser_AF_SF_Army_Navy.py                                              | iter_docs                        | High cyclomatic complexity (16). Consider refactor into helpers.            |
| RFP_Discovery_System/sandbox_graph_builder.py                                                    | main                             | High cyclomatic complexity (11). Consider refactor into helpers.            |
| RFP_Discovery_System/sandbox_graph_builder.py                                                    | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| Validation_Testing/error_tracking_dashboard.py                                                   | print_dashboard                  | High cyclomatic complexity (11). Consider refactor into helpers.            |
| Validation_Testing/error_tracking_dashboard.py                                                   | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| Validation_Testing/sandbox_validate_kb.py                                                        | sanity_score                     | High cyclomatic complexity (10). Consider refactor into helpers.            |
| Validation_Testing/sandbox_validate_kb.py                                                        | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| Validation_Testing/test_error_scenarios.py                                                       | create_test_kb_with_errors       | Long function (234 LOC). Extract smaller functions.                         |
| Validation_Testing/test_error_scenarios.py                                                       | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| Validation_Testing/test_refactored_validator.py                                                  | test_validation_module           | Long function (102 LOC). Extract smaller functions.                         |
| Validation_Testing/test_refactored_validator.py                                                  | create_comprehensive_test_report | Long function (101 LOC). Extract smaller functions.                         |
| Validation_Testing/test_refactored_validator.py                                                  | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| extend inputs schema.py                                                                          | load_parsed_regulations          | High cyclomatic complexity (20). Consider refactor into helpers.            |
| extend inputs schema.py                                                                          | clean_items                      | High cyclomatic complexity (29). Consider refactor into helpers.            |
| extend inputs schema.py                                                                          | run_rfp_discovery                | High cyclomatic complexity (25). Consider refactor into helpers.            |
| extend inputs schema.py                                                                          | run_rfp_discovery                | Long function (82 LOC). Extract smaller functions.                          |
| main.py                                                                                          | _calculate_compliance_metrics    | High cyclomatic complexity (10). Consider refactor into helpers.            |
| main.py                                                                                          | _generate_pdf_report             | High cyclomatic complexity (10). Consider refactor into helpers.            |
| main.py                                                                                          | _generate_pdf_report             | Long function (153 LOC). Extract smaller functions.                         |
| main.py                                                                                          | -                                | Code smell: empty except block (pass) at L130. Consider logging & handling. |
| main.py                                                                                          | -                                | Maintainability: 2 TODO/FIXME notes present.                                |
| project_audit (1).py                                                                             | find_endpoints                   | High cyclomatic complexity (18). Consider refactor into helpers.            |
| project_audit (1).py                                                                             | detect_issues                    | High cyclomatic complexity (24). Consider refactor into helpers.            |
| project_audit (1).py                                                                             | summarize_kb                     | High cyclomatic complexity (22). Consider refactor into helpers.            |
| project_audit (1).py                                                                             | main                             | High cyclomatic complexity (34). Consider refactor into helpers.            |
| project_audit (1).py                                                                             | main                             | Long function (163 LOC). Extract smaller functions.                         |
| project_audit (1).py                                                                             | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| project_audit (1).py                                                                             | -                                | Maintainability: 1 TODO/FIXME notes present.                                |
| proposalos_rge/api/endpoints.py                                                                  | generate                         | High cyclomatic complexity (27). Consider refactor into helpers.            |
| proposalos_rge/api/endpoints.py                                                                  | generate                         | Long function (101 LOC). Extract smaller functions.                         |
| proposalos_rge/example_usage.py                                                                  | example_2_synthetic_data         | Long function (200 LOC). Extract smaller functions.                         |
| proposalos_rge/example_usage.py                                                                  | -                                | Maintainability: direct print() detected. Prefer structured logging.        |
| proposalos_rge/normalize/builder.py                                                              | build_unified_payload            | High cyclomatic complexity (10). Consider refactor into helpers.            |
| proposalos_rge/normalize/builder.py                                                              | _detect_conflicts                | High cyclomatic complexity (13). Consider refactor into helpers.            |
| proposalos_rge/render/md/annual_fy.py                                                            | render                           | High cyclomatic complexity (48). Consider refactor into helpers.            |
| proposalos_rge/render/md/annual_fy.py                                                            | render                           | Long function (153 LOC). Extract smaller functions.                         |
| proposalos_rge/render/md/dfars_templates.py                                                      | render_dfars_checklist           | High cyclomatic complexity (27). Consider refactor into helpers.            |
| proposalos_rge/render/md/dfars_templates.py                                                      | render_dfars_checklist           | Long function (139 LOC). Extract smaller functions.                         |
| proposalos_rge/render/md/dfars_templates.py                                                      | render_dfars_cover_page          | High cyclomatic complexity (26). Consider refactor into helpers.            |
| proposalos_rge/render/md/dfars_templates.py                                                      | render_dfars_cover_page          | Long function (163 LOC). Extract smaller functions.                         |
| proposalos_rge/validate/rules.py                                                                 | validate_facts                   | High cyclomatic complexity (17). Consider refactor into helpers.            |
| proposalos_rge/validate/rules.py                                                                 | _validate_allocations            | High cyclomatic complexity (16). Consider refactor into helpers.            |
| proposalos_rge/validate/rules.py                                                                 | _validate_regulatory_compliance  | High cyclomatic complexity (10). Consider refactor into helpers.            |
| test_proposalos_rge.py                                                                           | test_dfars_checklist             | Long function (86 LOC). Extract smaller functions.                          |
| test_proposalos_rge.py                                                                           | test_annual_fy_report            | Long function (85 LOC). Extract smaller functions.                          |
| test_proposalos_rge.py                                                                           | -                                | Maintainability: direct print() detected. Prefer structured logging.        |

## Recommendations & Best Practices

- Enforce type checking (mypy/pyright) and docstrings for all public functions.
- Replace bare/broad exceptions with specific ones; log with structured context.
- Avoid `print`; use `logging.getLogger(__name__)` with consistent formatting.
- Add input validation via Pydantic models at all boundaries (API & internal services).
- Extract functions with CC >= 10 or >80 LOC; prefer pure functions for testability.
- Replace unsafe calls (eval/exec/pickle/yaml.load) with safer alternatives.
- Prefer dependency injection for I/O (files, network) to enable fast unit tests.
- Add rate limiting, authZ default‑deny, and request size/time limits on FastAPI endpoints.
- Cache expensive pure computations (functools.lru_cache) when appropriate.
- Ship a pre-commit config (ruff/black/isort, mypy) and a CI run (pytest -q).


## Targeted Test Coverage Plan

1. **Schema tests**: Validate Pydantic models with representative payloads (happy/edge).
2. **Renderer tests**: Golden-file markdown comparisons for each `render_*` function.
3. **Validator tests**: Given contrived bad inputs, assert specific flags/errors.
4. **API tests**: FastAPI TestClient for /reports/* with auth, size, and timeouts.
5. **Regression tests**: Lock fixtures for KB parsing and template registry wiring.
6. **Property tests**: Fuzz table builders (no crashes, idempotent, valid Markdown).


## Appendix: File Details

### # updated_complile_reports.py
| Function                  | Line | LOC | Async | Args | CC |
| ------------------------- | ---- | --- | ----- | ---- | -- |
| _ensure_genai             | 46   | 13  | no    | 0    | 5  |
| base_output_dir           | 63   | 4   | no    | 0    | 2  |
| now_ts                    | 76   | 1   | no    | 0    | 1  |
| sha8                      | 79   | 1   | no    | 1    | 1  |
| utc_now_iso               | 82   | 1   | no    | 0    | 1  |
| word_count                | 86   | 1   | no    | 1    | 1  |
| truncate_quote_25w        | 89   | 1   | no    | 1    | 1  |
| safe_float                | 92   | 7   | no    | 2    | 6  |
| _module_iter_docs         | 102  | 14  | no    | 1    | 7  |
| load_parsed_regulations   | 118  | 28  | no    | 0    | 7  |
| make_prompt_rfp_discovery | 158  | 10  | no    | 2    | 1  |
| make_mock_items_from_text | 170  | 18  | no    | 1    | 6  |
| call_gemini               | 191  | 5   | no    | 1    | 2  |
| parse_json_array          | 198  | 4   | no    | 1    | 3  |
| apply_sanity_and_truncate | 216  | 11  | no    | 3    | 6  |
| dedupe_merge              | 229  | 21  | no    | 1    | 6  |
| parse_args                | 253  | 6   | no    | 0    | 1  |
| run_rfp_discovery         | 262  | 119 | no    | 4    | 29 |
- **Classes:** KBItem
| Issue                                                               |
| ------------------------------------------------------------------- |
| Correctness: broad exception 'Exception' at L56. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L98. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L131. Narrow the scope. |
| Correctness: broad exception 'Exception' at L138. Narrow the scope. |
| Correctness: broad exception 'Exception' at L201. Narrow the scope. |
| Correctness: broad exception 'Exception' at L282. Narrow the scope. |

### # updated_sandbox_cost_volume_assembler.py
| Function | Line | LOC | Async | Args | CC |
| -------- | ---- | --- | ----- | ---- | -- |
| main     | 66   | 35  | no    | 0    | 8  |
| Issue                                                                |
| -------------------------------------------------------------------- |
| Maintainability: direct print() detected. Prefer structured logging. |

### # updated_sandbox_validate_kb.py
| Function     | Line | LOC | Async | Args | CC |
| ------------ | ---- | --- | ----- | ---- | -- |
| wcount       | 30   | 1   | no    | 1    | 3  |
| trunc25      | 33   | 1   | no    | 1    | 3  |
| sanity_score | 36   | 9   | no    | 5    | 13 |
| safe_float   | 47   | 7   | no    | 2    | 6  |
| dedupe_merge | 56   | 23  | no    | 1    | 6  |
| main         | 81   | 41  | no    | 0    | 7  |
| Issue                                                                |
| -------------------------------------------------------------------- |
| Correctness: broad exception 'Exception' at L53. Narrow the scope.   |
| Maintainability: direct print() detected. Prefer structured logging. |

### Cost_Volume_Assembly/Costing,Pricing Reports/annual_fiscal_year_report_assembler.py
| Function | Line | LOC | Async | Args | CC |
| -------- | ---- | --- | ----- | ---- | -- |
| main     | 15   | 32  | no    | 0    | 5  |
| Issue                                                                |
| -------------------------------------------------------------------- |
| Maintainability: direct print() detected. Prefer structured logging. |

### Cost_Volume_Assembly/Costing,Pricing Reports/dfars_checklist_assembler.py
| Function | Line | LOC | Async | Args | CC |
| -------- | ---- | --- | ----- | ---- | -- |
| main     | 38   | 29  | no    | 0    | 4  |
| Issue                                                                |
| -------------------------------------------------------------------- |
| Maintainability: direct print() detected. Prefer structured logging. |

### Cost_Volume_Assembly/Costing,Pricing Reports/dfars_cover_page_assembler.py
| Function | Line | LOC | Async | Args | CC |
| -------- | ---- | --- | ----- | ---- | -- |
| main     | 32   | 13  | no    | 0    | 1  |
| Issue                                                                |
| -------------------------------------------------------------------- |
| Maintainability: direct print() detected. Prefer structured logging. |

### Cost_Volume_Assembly/Costing,Pricing Reports/far_15_2_assembler.py
| Function | Line | LOC | Async | Args | CC |
| -------- | ---- | --- | ----- | ---- | -- |
| main     | 34   | 13  | no    | 0    | 1  |
| Issue                                                                |
| -------------------------------------------------------------------- |
| Maintainability: direct print() detected. Prefer structured logging. |

### Cost_Volume_Assembly/Costing,Pricing Reports/fccom_form_assembler.py
| Function | Line | LOC | Async | Args | CC |
| -------- | ---- | --- | ----- | ---- | -- |
| main     | 39   | 19  | no    | 0    | 1  |
| Issue                                                                |
| -------------------------------------------------------------------- |
| Maintainability: direct print() detected. Prefer structured logging. |

### Cost_Volume_Assembly/Costing,Pricing Reports/render_md_dfars_templates.py
| Function                       | Line | LOC | Async | Args | CC |
| ------------------------------ | ---- | --- | ----- | ---- | -- |
| _get                           | 28   | 13  | no    | 1    | 8  |
| _utcnow_iso                    | 44   | 1   | no    | 0    | 1  |
| _kb_has                        | 48   | 4   | no    | 2    | 2  |
| _derive_checklist_placeholders | 116  | 18  | no    | 2    | 2  |
| render_dfars_checklist         | 137  | 22  | no    | 2    | 4  |
| render_dfars_cover_page        | 196  | 55  | no    | 2    | 1  |
| register                       | 262  | 32  | no    | 1    | 5  |
| _put                           | 274  | 17  | no    | 3    | 5  |
| Issue                                                                |
| -------------------------------------------------------------------- |
| Correctness: broad exception 'Exception' at L289. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L39. Narrow the scope.   |
| Maintainability: direct print() detected. Prefer structured logging. |

### Cost_Volume_Assembly/sandbox_cost_algorithms.py
| Function                 | Line | LOC | Async | Args | CC |
| ------------------------ | ---- | --- | ----- | ---- | -- |
| escalate                 | 60   | 1   | no    | 3    | 1  |
| to_markdown              | 63   | 6   | no    | 1    | 3  |
| build_labor_table        | 72   | 26  | no    | 3    | 6  |
| build_materials_table    | 101  | 24  | no    | 1    | 6  |
| build_subcontracts_table | 128  | 20  | no    | 1    | 7  |
| build_travel_table       | 151  | 25  | no    | 1    | 7  |
| compute_bases_and_fee    | 179  | 18  | no    | 7    | 2  |
- **Classes:** LaborLine, RateSet, TravelLine, MaterialLine, SubcontractLine

### Cost_Volume_Assembly/sandbox_cost_volume_assembler.py
| Function | Line | LOC | Async | Args | CC |
| -------- | ---- | --- | ----- | ---- | -- |
| main     | 65   | 34  | no    | 0    | 8  |
| Issue                                                                |
| -------------------------------------------------------------------- |
| Maintainability: direct print() detected. Prefer structured logging. |

### Cost_Volume_Assembly/sandbox_cost_volume_assembler_v2.py
| Function    | Line | LOC | Async | Args | CC |
| ----------- | ---- | --- | ----- | ---- | -- |
| md_table    | 24   | 1   | no    | 1    | 1  |
| load_inputs | 27   | 9   | no    | 1    | 1  |
| main        | 38   | 71  | no    | 0    | 17 |
| Issue                                                                |
| -------------------------------------------------------------------- |
| Maintainability: direct print() detected. Prefer structured logging. |

### ProposalOS_Production_System/Code_Snippets/1) Concrete prompt (RFP EoC Extraction v2).py
| Issue                                                            |
| ---------------------------------------------------------------- |
| Parse error: invalid character '≤' (U+2264) (<unknown>, line 24) |

### ProposalOS_Production_System/Code_Snippets/2) Tiny post-processor (reject:repair).py
| Function                  | Line | LOC | Async | Args | CC |
| ------------------------- | ---- | --- | ----- | ---- | -- |
| _word_count               | 18   | 1   | no    | 1    | 3  |
| _is_allowed               | 21   | 10  | no    | 3    | 9  |
| _repair_if_generic        | 33   | 8   | no    | 1    | 10 |
| _dedupe_key               | 43   | 8   | no    | 1    | 5  |
| validate_and_repair_facts | 53   | 37  | no    | 1    | 25 |

### ProposalOS_Production_System/Code_Snippets/3) Orchestrator patches (auth default-deny + extraction schema expectation).py
| Issue                                           |
| ----------------------------------------------- |
| Parse error: invalid syntax (<unknown>, line 3) |

### ProposalOS_Production_System/Code_Snippets/4) Redis token-bucket rate limiter (middleware).py
| Function     | Line | LOC | Async | Args | CC |
| ------------ | ---- | --- | ----- | ---- | -- |
| _client_key  | 11   | 3   | no    | 2    | 4  |
| rate_limiter | 17   | 36  | yes   | 2    | 8  |

### ProposalOS_Production_System/Code_Snippets/5) PR plan- align model choice + remove duplicates.py
| Issue                                                                |
| -------------------------------------------------------------------- |
| Maintainability: direct print() detected. Prefer structured logging. |

### ProposalOS_Production_System/Code_Snippets/Add Procurement Endpoints with a Circuit Breaker.py
| Function                          | Line | LOC | Async | Args | CC |
| --------------------------------- | ---- | --- | ----- | ---- | -- |
| procure_subcontract               | 21   | 32  | yes   | 2    | 5  |
| validate_subcontract_with_service | 29   | 12  | yes   | 1    | 2  |
- **Classes:** SubcontractRequest
| Issue                                                                |
| -------------------------------------------------------------------- |
| Correctness: broad exception 'Exception' at L51. Narrow the scope.   |
| Maintainability: direct print() detected. Prefer structured logging. |

### ProposalOS_Production_System/Code_Snippets/And in your handler-.py

### ProposalOS_Production_System/Code_Snippets/CORS tighten (env-driven).py
| Issue                                                                                                   |
| ------------------------------------------------------------------------------------------------------- |
| Parse error: cannot assign to expression here. Maybe you meant '==' instead of '='? (<unknown>, line 1) |

### ProposalOS_Production_System/Code_Snippets/Extraction schema expectation (align server to new JSON).py
- **Classes:** Regulation, Locator, ExtractedFact, ExtractionResponse

### ProposalOS_Production_System/Core_Orchestrator/auth.py
| Function                    | Line | LOC | Async | Args | CC |
| --------------------------- | ---- | --- | ----- | ---- | -- |
| get_auth_service            | 302  | 7   | no    | 1    | 2  |
| verify_api_key              | 313  | 18  | yes   | 2    | 1  |
| require_permission          | 335  | 22  | no    | 2    | 2  |
| security_headers_middleware | 361  | 14  | yes   | 2    | 1  |
| __init__                    | 38   | 3   | no    | 2    | 1  |
| check_rate_limit            | 43   | 23  | yes   | 4    | 6  |
| _check_redis_limit          | 68   | 28  | yes   | 4    | 3  |
| _check_local_limit          | 98   | 29  | no    | 4    | 4  |
| get_remaining_tokens        | 129  | 16  | yes   | 2    | 4  |
| __init__                    | 153  | 8   | no    | 3    | 3  |
| _get_client_identifier      | 163  | 10  | no    | 2    | 4  |
| _hash_api_key               | 175  | 2   | no    | 2    | 1  |
| _verify_api_key_hash        | 179  | 6   | no    | 2    | 2  |
| authenticate                | 187  | 77  | yes   | 3    | 11 |
| authorize                   | 266  | 29  | yes   | 4    | 2  |
| permission_checker          | 346  | 9   | yes   | 1    | 2  |
| test_auth                   | 382  | 26  | yes   | 0    | 3  |
- **Classes:** RateLimiter, AuthService, MockRequest
| Issue                                                                |
| -------------------------------------------------------------------- |
| Correctness: broad exception 'Exception' at L93. Narrow the scope.   |
| Correctness: bare 'except' at L141. Catch specific exceptions.       |
| Maintainability: direct print() detected. Prefer structured logging. |

### ProposalOS_Production_System/Core_Orchestrator/circuit_breakers.py
| Function                     | Line | LOC | Async | Args | CC |
| ---------------------------- | ---- | --- | ----- | ---- | -- |
| circuit_breaker              | 303  | 18  | no    | 1    | 1  |
| with_circuit_breaker         | 325  | 39  | yes   | 2    | 5  |
| get_circuit_breaker_registry | 371  | 5   | no    | 0    | 2  |
| get_compliance_breaker       | 380  | 2   | no    | 0    | 1  |
| get_sam_gov_breaker          | 385  | 2   | no    | 0    | 1  |
| get_gemini_breaker           | 390  | 2   | no    | 0    | 1  |
| get_knowledge_graph_breaker  | 395  | 2   | no    | 0    | 1  |
| is_open                      | 49   | 1   | no    | 1    | 1  |
| is_closed                    | 53   | 1   | no    | 1    | 1  |
| is_half_open                 | 57   | 1   | no    | 1    | 1  |
| __init__                     | 66   | 18  | no    | 2    | 2  |
| call                         | 86   | 10  | no    | 2    | 3  |
| get_metrics                  | 98   | 9   | no    | 1    | 3  |
| _expected_reset_time         | 109  | 4   | no    | 1    | 4  |
| __init__                     | 121  | 11  | no    | 2    | 3  |
| _initialize_breakers         | 134  | 65  | no    | 1    | 1  |
| get                          | 201  | 20  | no    | 2    | 3  |
| get_all_metrics              | 223  | 10  | no    | 1    | 1  |
| get_health_status            | 235  | 33  | no    | 1    | 1  |
| reset                        | 270  | 17  | no    | 2    | 3  |
| reset_all                    | 289  | 10  | no    | 1    | 2  |
| decorator                    | 315  | 5   | no    | 1    | 1  |
| test_breakers                | 404  | 39  | yes   | 0    | 4  |
| on_open_wrapper              | 78   | 4   | no    | 1    | 2  |
| wrapper                      | 316  | 3   | no    | 0    | 1  |
| failing_function             | 415  | 1   | no    | 0    | 1  |
| async_api_call               | 434  | 2   | yes   | 0    | 1  |
| sync_wrapper                 | 352  | 1   | no    | 0    | 1  |
- **Classes:** ServiceName, CircuitBreakerMetrics, MonitoredCircuitBreaker, CircuitBreakerRegistry
| Issue                                                                       |
| --------------------------------------------------------------------------- |
| Correctness: broad exception 'Exception' at L94. Narrow the scope.          |
| Correctness: broad exception 'Exception' at L285. Narrow the scope.         |
| Correctness: broad exception 'Exception' at L422. Narrow the scope.         |
| Code smell: empty except block (pass) at L422. Consider logging & handling. |
| Maintainability: direct print() detected. Prefer structured logging.        |

### ProposalOS_Production_System/Core_Orchestrator/config.py
| Function              | Line | LOC | Async | Args | CC |
| --------------------- | ---- | --- | ----- | ---- | -- |
| get_config            | 305  | 11  | no    | 0    | 2  |
| __init__              | 32   | 133 | no    | 1    | 12 |
| _load_gemini_env      | 167  | 28  | no    | 1    | 12 |
| validate              | 197  | 63  | no    | 1    | 16 |
| get_connection_string | 262  | 8   | no    | 2    | 1  |
| to_dict               | 272  | 26  | no    | 1    | 4  |
- **Classes:** Config
| Issue                                                                |
| -------------------------------------------------------------------- |
| Correctness: broad exception 'Exception' at L229. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L244. Narrow the scope.  |
| Maintainability: direct print() detected. Prefer structured logging. |

### ProposalOS_Production_System/Core_Orchestrator/extraction_service.py
| Function                    | Line | LOC | Async | Args | CC |
| --------------------------- | ---- | --- | ----- | ---- | -- |
| get_extraction_service      | 497  | 8   | no    | 2    | 2  |
| validate_ambiguity          | 55   | 4   | no    | 3    | 4  |
| word_count                  | 87   | 2   | no    | 1    | 3  |
| is_regulation_allowed       | 91   | 13  | no    | 4    | 9  |
| repair_generic_allowability | 106  | 11  | no    | 2    | 10 |
| validate_and_repair         | 119  | 51  | no    | 2    | 15 |
| __init__                    | 178  | 20  | no    | 4    | 5  |
| _load_prompts               | 200  | 74  | no    | 1    | 1  |
| extract_from_rfp            | 276  | 62  | yes   | 3    | 9  |
| extract_from_conversation   | 340  | 43  | yes   | 2    | 4  |
| validate_procurement        | 385  | 40  | yes   | 2    | 4  |
| _call_model                 | 427  | 20  | yes   | 3    | 3  |
| batch_extract               | 449  | 41  | no    | 3    | 5  |
| test_extraction             | 512  | 30  | yes   | 0    | 2  |
| generate_content_async      | 515  | 10  | yes   | 2    | 1  |
- **Classes:** Regulation, Locator, ExtractedFact, ExtractionResponse, FactValidator, ExtractionService, MockModel, Response
| Issue                                                                |
| -------------------------------------------------------------------- |
| Correctness: broad exception 'Exception' at L445. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L482. Narrow the scope.  |
| Maintainability: direct print() detected. Prefer structured logging. |

### ProposalOS_Production_System/Core_Orchestrator/orchestrator_enhanced.py
| Function                       | Line | LOC | Async | Args | CC |
| ------------------------------ | ---- | --- | ----- | ---- | -- |
| verify_api_key                 | 108  | 8   | no    | 1    | 3  |
| get_auth_token                 | 378  | 8   | no    | 0    | 3  |
| extract_data_from_conversation | 388  | 48  | yes   | 3    | 10 |
| calculate_completion           | 438  | 9   | no    | 1    | 1  |
| identify_missing_fields        | 449  | 19  | no    | 1    | 3  |
| determine_data_state           | 470  | 9   | no    | 1    | 3  |
| orchestrate_conversation       | 483  | 72  | yes   | 2    | 3  |
| validate_boe                   | 558  | 79  | yes   | 2    | 7  |
| get_session_state              | 640  | 18  | yes   | 2    | 4  |
| clear_session                  | 661  | 10  | yes   | 2    | 1  |
| get_user_sessions              | 674  | 24  | yes   | 2    | 5  |
| export_session_data            | 701  | 36  | yes   | 2    | 2  |
| health_check                   | 740  | 18  | yes   | 0    | 4  |
| get_metrics                    | 761  | 14  | yes   | 1    | 1  |
| startup_event                  | 779  | 26  | yes   | 0    | 8  |
| shutdown_event                 | 808  | 9   | yes   | 0    | 5  |
| validate_session_id            | 133  | 3   | no    | 2    | 2  |
| __init__                       | 271  | 1   | no    | 1    | 1  |
| get_state                      | 274  | 29  | yes   | 2    | 10 |
| save_state                     | 305  | 21  | yes   | 3    | 7  |
| delete_state                   | 328  | 17  | yes   | 2    | 7  |
| _create_new_state              | 347  | 26  | no    | 1    | 1  |
- **Classes:** Config, DataState, OrchestrationRequest, OrchestrationResponse, BOEValidationRequest, BOEValidationResponse, StateManager
| Issue                                                               |
| ------------------------------------------------------------------- |
| Correctness: broad exception 'Exception' at L77. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L86. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L384. Narrow the scope. |
| Correctness: broad exception 'Exception' at L434. Narrow the scope. |
| Correctness: broad exception 'Exception' at L553. Narrow the scope. |
| Correctness: broad exception 'Exception' at L635. Narrow the scope. |
| Correctness: broad exception 'Exception' at L695. Narrow the scope. |
| Correctness: bare 'except' at L792. Catch specific exceptions.      |
| Correctness: bare 'except' at L802. Catch specific exceptions.      |
| Correctness: broad exception 'Exception' at L288. Narrow the scope. |
| Correctness: broad exception 'Exception' at L299. Narrow the scope. |
| Correctness: broad exception 'Exception' at L318. Narrow the scope. |
| Correctness: broad exception 'Exception' at L325. Narrow the scope. |
| Correctness: broad exception 'Exception' at L337. Narrow the scope. |
| Correctness: broad exception 'Exception' at L344. Narrow the scope. |

### ProposalOS_Production_System/Core_Orchestrator/orchestrator_procurement_enhanced.py
| Function                     | Line | LOC | Async | Args | CC |
| ---------------------------- | ---- | --- | ----- | ---- | -- |
| load_gemini_api_key          | 105  | 16  | no    | 0    | 9  |
| lifespan                     | 544  | 38  | yes   | 1    | 7  |
| verify_api_key               | 603  | 16  | yes   | 2    | 4  |
| procure_subcontract          | 623  | 97  | yes   | 3    | 15 |
| procurement_nli              | 723  | 37  | yes   | 3    | 6  |
| refine_boe_generational      | 764  | 52  | yes   | 3    | 8  |
| generate_cost_volume         | 820  | 64  | yes   | 2    | 11 |
| store_procurement_validation | 887  | 18  | yes   | 3    | 3  |
| health_check                 | 909  | 22  | yes   | 0    | 6  |
| metrics                      | 934  | 2   | yes   | 0    | 1  |
| format                       | 55   | 5   | no    | 2    | 3  |
| __init__                     | 131  | 51  | no    | 1    | 5  |
| __init__                     | 273  | 3   | no    | 3    | 1  |
| query_regulations            | 279  | 34  | yes   | 3    | 6  |
| query_graph                  | 315  | 17  | yes   | 2    | 4  |
| __init__                     | 338  | 8   | no    | 1    | 1  |
| validate_vendor_sam          | 350  | 52  | yes   | 2    | 9  |
| get_required_flowdowns       | 404  | 14  | no    | 2    | 4  |
| calculate_risk_score         | 420  | 28  | no    | 3    | 9  |
- **Classes:** SanitizingFormatter, Config, DataState, ProcurementType, VendorData, SubcontractRequest, ProcurementValidationResponse, BOEData, CostVolumeRequest, KnowledgeBaseService, ProcurementService, ConversationTurn, EnhancedSessionState, Config
| Issue                                                               |
| ------------------------------------------------------------------- |
| Correctness: bare 'except' at L86. Catch specific exceptions.       |
| Correctness: broad exception 'Exception' at L717. Narrow the scope. |
| Correctness: broad exception 'Exception' at L758. Narrow the scope. |
| Correctness: broad exception 'Exception' at L813. Narrow the scope. |
| Correctness: broad exception 'Exception' at L882. Narrow the scope. |
| Correctness: broad exception 'Exception' at L904. Narrow the scope. |
| Correctness: broad exception 'Exception' at L309. Narrow the scope. |
| Correctness: broad exception 'Exception' at L328. Narrow the scope. |
| Correctness: broad exception 'Exception' at L398. Narrow the scope. |
| Correctness: broad exception 'Exception' at L559. Narrow the scope. |
| Correctness: broad exception 'Exception' at L568. Narrow the scope. |

### ProposalOS_Production_System/Core_Orchestrator/orchestrator_production.py
| Function                          | Line | LOC | Async | Args | CC |
| --------------------------------- | ---- | --- | ----- | ---- | -- |
| load_gemini_api_key               | 78   | 17  | no    | 0    | 9  |
| lifespan                          | 235  | 68  | yes   | 1    | 16 |
| verify_api_key                    | 365  | 27  | yes   | 2    | 5  |
| get_auth_token                    | 730  | 8   | yes   | 0    | 3  |
| run_in_thread                     | 740  | 3   | yes   | 1    | 1  |
| extract_data_from_conversation    | 745  | 50  | yes   | 4    | 15 |
| calculate_completion              | 797  | 5   | no    | 1    | 1  |
| get_recent_questions              | 804  | 8   | no    | 1    | 4  |
| get_next_action                   | 814  | 15  | no    | 1    | 2  |
| orchestrate_conversation          | 833  | 98  | yes   | 2    | 12 |
| validate_boe                      | 935  | 52  | yes   | 2    | 4  |
| export_session                    | 990  | 55  | yes   | 3    | 24 |
| scrape_sam_gov_rfps               | 1050 | 64  | yes   | 2    | 5  |
| check_vendor_compliance           | 1117 | 132 | yes   | 2    | 19 |
| procure_subcontract               | 1253 | 120 | yes   | 2    | 14 |
| local_compliance_validation       | 1375 | 15  | yes   | 1    | 5  |
| query_knowledge_graph             | 1514 | 50  | yes   | 3    | 6  |
| validate_citation                 | 1567 | 24  | yes   | 3    | 3  |
| get_element_citations             | 1594 | 29  | yes   | 3    | 3  |
| health_check                      | 1626 | 27  | yes   | 0    | 12 |
| metrics                           | 1656 | 2   | yes   | 0    | 1  |
| root                              | 1662 | 16  | yes   | 0    | 1  |
| format                            | 51   | 5   | no    | 2    | 2  |
| __init__                          | 107  | 66  | no    | 1    | 9  |
| validate                          | 175  | 28  | no    | 1    | 10 |
| _get_model                        | 255  | 5   | no    | 1    | 4  |
| __init__                          | 326  | 2   | no    | 2    | 1  |
| check_rate_limit                  | 330  | 30  | yes   | 4    | 9  |
| validate_session_id               | 444  | 3   | no    | 2    | 2  |
| validate_keywords                 | 481  | 3   | no    | 2    | 2  |
| sanitize_vendor_name              | 512  | 2   | no    | 2    | 1  |
| __init__                          | 612  | 3   | no    | 3    | 1  |
| get_state                         | 617  | 34  | yes   | 3    | 10 |
| _create_new_state                 | 653  | 22  | yes   | 3    | 2  |
| _check_session_limit              | 677  | 15  | yes   | 2    | 5  |
| save_state                        | 694  | 27  | yes   | 3    | 8  |
| flush_all                         | 723  | 3   | yes   | 1    | 2  |
| __init__                          | 1396 | 26  | no    | 1    | 1  |
| query                             | 1425 | 50  | yes   | 3    | 29 |
| get_regulatory_citations          | 1477 | 14  | yes   | 3    | 1  |
| validate_citation                 | 1493 | 15  | yes   | 3    | 2  |
| validate_subcontract_with_service | 1264 | 26  | yes   | 1    | 2  |
- **Classes:** SanitizingFormatter, Config, RateLimiter, DataState, SessionData, SessionMetadata, SessionState, OrchestrationRequest, OrchestrationResponse, BOEValidationRequest, BOEValidationResponse, RFPScrapeRequest, RFP, VendorComplianceRequest, ComplianceIssue, VendorComplianceResponse, SubcontractRequest, RFPScrapeResponse, StateManager, KnowledgeGraphService, Config
| Issue                                                                |
| -------------------------------------------------------------------- |
| Correctness: broad exception 'Exception' at L736. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L792. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L927. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L972. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L1111. Narrow the scope. |
| Correctness: broad exception 'Exception' at L1367. Narrow the scope. |
| Correctness: broad exception 'Exception' at L1561. Narrow the scope. |
| Correctness: broad exception 'Exception' at L1589. Narrow the scope. |
| Correctness: broad exception 'Exception' at L1621. Narrow the scope. |
| Correctness: broad exception 'Exception' at L275. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L289. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L1472. Narrow the scope. |
| Correctness: broad exception 'Exception' at L200. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L342. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L634. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L647. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L689. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L711. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L720. Narrow the scope.  |
| Maintainability: 1 TODO/FIXME notes present.                         |

### ProposalOS_Production_System/Core_Orchestrator/state_manager.py
| Function                 | Line | LOC | Async | Args | CC |
| ------------------------ | ---- | --- | ----- | ---- | -- |
| get_state_manager        | 525  | 11  | no    | 2    | 2  |
| to_dict                  | 51   | 5   | no    | 1    | 1  |
| from_dict                | 59   | 3   | no    | 2    | 1  |
| __init__                 | 71   | 35  | no    | 4    | 3  |
| create_session           | 108  | 56  | yes   | 3    | 6  |
| get_session              | 166  | 58  | yes   | 3    | 15 |
| update_session           | 226  | 38  | yes   | 3    | 8  |
| add_to_conversation      | 266  | 39  | yes   | 5    | 5  |
| delete_session           | 307  | 45  | yes   | 2    | 13 |
| get_user_sessions        | 354  | 49  | yes   | 3    | 22 |
| cleanup_user_sessions    | 405  | 21  | yes   | 2    | 5  |
| cleanup_all_expired      | 428  | 22  | yes   | 1    | 6  |
| flush_all                | 452  | 9   | yes   | 1    | 5  |
| _store_session           | 465  | 18  | yes   | 3    | 4  |
| _store_redis_session     | 485  | 19  | yes   | 2    | 3  |
| _store_firestore_session | 506  | 6   | yes   | 2    | 3  |
| _is_session_active       | 514  | 4   | no    | 2    | 1  |
| test_state_manager       | 543  | 35  | yes   | 0    | 1  |
- **Classes:** DataState, SessionData, StateManager
| Issue                                                                |
| -------------------------------------------------------------------- |
| Correctness: broad exception 'Exception' at L503. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L511. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L202. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L217. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L332. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L341. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L380. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L392. Narrow the scope.  |
| Maintainability: direct print() detected. Prefer structured logging. |

### ProposalOS_Production_System/Procurement_Modules/procurement_compliance_checker.py
| Function                       | Line | LOC | Async | Args | CC |
| ------------------------------ | ---- | --- | ----- | ---- | -- |
| main                           | 440  | 87  | no    | 0    | 10 |
| total_cost                     | 68   | 1   | no    | 1    | 1  |
| check_subcontractor_compliance | 80   | 141 | no    | 5    | 27 |
| batch_check_vendors            | 223  | 26  | no    | 4    | 5  |
| generate_bom                   | 254  | 104 | no    | 3    | 4  |
| validate_bom                   | 360  | 59  | no    | 3    | 12 |
| export_bom_to_csv              | 421  | 17  | no    | 3    | 3  |
- **Classes:** ComplianceSeverity, ComplianceIssue, VendorData, BOMItem, SubcontractorComplianceChecker, BillOfMaterialsGenerator
| Issue                                                                |
| -------------------------------------------------------------------- |
| Maintainability: direct print() detected. Prefer structured logging. |

### ProposalOS_Production_System/Procurement_Modules/sam_rfp_scraper.py
| Function                          | Line | LOC | Async | Args | CC |
| --------------------------------- | ---- | --- | ----- | ---- | -- |
| make_prompt_rfp_discovery         | 249  | 42  | no    | 1    | 1  |
| integrate_with_discovery_pipeline | 293  | 48  | no    | 2    | 5  |
| main                              | 343  | 92  | no    | 0    | 19 |
| to_eoc_doc                        | 49   | 17  | no    | 1    | 1  |
| __init__                          | 71   | 13  | no    | 2    | 1  |
| scrape_rfps                       | 86   | 96  | no    | 7    | 12 |
| _parse_value                      | 184  | 9   | no    | 2    | 4  |
| extract_eocs_from_rfps            | 195  | 52  | no    | 2    | 6  |
- **Classes:** RFPOpportunity, SAMRFPScraper
| Issue                                                                |
| -------------------------------------------------------------------- |
| Correctness: broad exception 'Exception' at L433. Narrow the scope.  |
| Correctness: bare 'except' at L192. Catch specific exceptions.       |
| Correctness: broad exception 'Exception' at L178. Narrow the scope.  |
| Maintainability: direct print() detected. Prefer structured logging. |

### ProposalOS_Production_System/Procurement_Modules/validate_subcontract.py
| Function                             | Line | LOC | Async | Args | CC |
| ------------------------------------ | ---- | --- | ----- | ---- | -- |
| validate_subcontract                 | 258  | 96  | yes   | 6    | 16 |
| generate_compliance_report           | 356  | 96  | no    | 1    | 21 |
| __init__                             | 50   | 2   | no    | 1    | 1  |
| validate_tina_compliance             | 54   | 12  | no    | 2    | 2  |
| validate_cmmc_requirements           | 68   | 29  | no    | 3    | 7  |
| validate_sam_registration            | 99   | 32  | no    | 2    | 6  |
| validate_itar_compliance             | 133  | 26  | no    | 2    | 7  |
| validate_flowdown_clauses            | 161  | 23  | no    | 3    | 3  |
| validate_small_business_requirements | 186  | 22  | no    | 3    | 5  |
| validate_dcaa_requirements           | 210  | 21  | no    | 4    | 5  |
| validate_cpsr_requirements           | 233  | 6   | no    | 2    | 4  |
| calculate_risk_score                 | 241  | 15  | no    | 1    | 6  |
| test_validation                      | 458  | 56  | yes   | 0    | 1  |
- **Classes:** ComplianceSeverity, DFARSValidator
| Issue                                                                |
| -------------------------------------------------------------------- |
| Maintainability: direct print() detected. Prefer structured logging. |

### ProposalOS_Production_System/Tests/test_proposalOS_integration.py
| Function                        | Line | LOC | Async | Args | CC |
| ------------------------------- | ---- | --- | ----- | ---- | -- |
| test_client                     | 51   | 2   | no    | 0    | 1  |
| mock_redis                      | 56   | 7   | no    | 0    | 1  |
| vendor_data                     | 66   | 13  | no    | 0    | 1  |
| rfp_opportunity                 | 82   | 17  | no    | 0    | 1  |
| test_full_integration_flow      | 630  | 73  | yes   | 0    | 3  |
| test_health_check               | 104  | 8   | no    | 2    | 1  |
| test_metrics_endpoint           | 114  | 5   | no    | 2    | 1  |
| test_conversation_start         | 122  | 20  | no    | 3    | 1  |
| test_conversation_continue      | 145  | 31  | no    | 3    | 1  |
| test_scrape_rfps_endpoint       | 182  | 33  | yes   | 3    | 1  |
| test_vendor_compliance_check    | 218  | 22  | yes   | 4    | 1  |
| test_subcontract_validation     | 242  | 16  | yes   | 2    | 1  |
| test_tina_threshold_check       | 263  | 13  | no    | 2    | 1  |
| test_cmmc_requirement           | 278  | 13  | no    | 2    | 1  |
| test_sam_registration_critical  | 293  | 14  | no    | 2    | 1  |
| test_batch_vendor_check         | 309  | 18  | no    | 1    | 1  |
| test_bom_generation             | 332  | 14  | no    | 1    | 1  |
| test_bom_validation             | 348  | 23  | no    | 1    | 1  |
| test_bom_csv_export             | 373  | 15  | no    | 2    | 2  |
| test_rfp_scraping               | 394  | 27  | no    | 2    | 1  |
| test_eoc_extraction             | 423  | 9   | no    | 2    | 1  |
| test_rfp_to_eoc_doc_conversion  | 434  | 7   | no    | 2    | 1  |
| test_compliance_circuit_breaker | 446  | 15  | no    | 1    | 5  |
| test_sam_gov_circuit_breaker    | 463  | 14  | no    | 1    | 4  |
| test_knowledge_graph_query      | 483  | 16  | yes   | 2    | 1  |
| test_knowledge_graph_fallback   | 501  | 12  | yes   | 1    | 1  |
| test_api_key_validation         | 518  | 8   | no    | 2    | 1  |
| test_rate_limiting              | 528  | 9   | no    | 3    | 3  |
| test_cors_headers               | 539  | 9   | no    | 2    | 1  |
| test_session_creation           | 554  | 28  | no    | 3    | 1  |
| test_session_expiration         | 584  | 16  | no    | 1    | 1  |
| test_malformed_request          | 605  | 7   | no    | 2    | 1  |
| test_model_failure_recovery     | 615  | 12  | no    | 3    | 1  |
- **Classes:** TestOrchestrator, TestProcurementEndpoints, TestComplianceChecker, TestBOMGenerator, TestRFPScraper, TestCircuitBreakers, TestKnowledgeGraph, TestSecurityFeatures, TestStateManagement, TestErrorHandling
| Issue                                                                       |
| --------------------------------------------------------------------------- |
| Correctness: bare 'except' at L454. Catch specific exceptions.              |
| Code smell: empty except block (pass) at L454. Consider logging & handling. |
| Correctness: bare 'except' at L474. Catch specific exceptions.              |
| Code smell: empty except block (pass) at L474. Consider logging & handling. |
| Maintainability: direct print() detected. Prefer structured logging.        |

### RFP_Discovery_System/compile_reports_refactor (1).py
| Function       | Line | LOC | Async | Args | CC |
| -------------- | ---- | --- | ----- | ---- | -- |
| validate_facts | 24   | 32  | no    | 1    | 7  |

### RFP_Discovery_System/compile_reports_refactor.py
| Function                  | Line | LOC | Async | Args | CC |
| ------------------------- | ---- | --- | ----- | ---- | -- |
| default_base_dir          | 68   | 6   | no    | 0    | 2  |
| now_ts                    | 77   | 1   | no    | 0    | 1  |
| sha8                      | 80   | 1   | no    | 1    | 1  |
| _module_iter_docs         | 89   | 8   | no    | 1    | 4  |
| load_parsed_regulations   | 100  | 31  | no    | 0    | 20 |
| make_prompt_rfp_discovery | 159  | 15  | no    | 1    | 2  |
| _grab_sentence            | 189  | 14  | no    | 3    | 5  |
| make_mock_items_from_text | 206  | 35  | no    | 1    | 6  |
| call_gemini               | 245  | 22  | no    | 1    | 9  |
| parse_json_array          | 270  | 6   | no    | 1    | 4  |
| _quote_within_limit       | 280  | 1   | no    | 2    | 1  |
| _support_matches          | 284  | 3   | no    | 3    | 2  |
| clean_items               | 290  | 77  | no    | 3    | 29 |
| parse_args                | 371  | 7   | no    | 0    | 1  |
| run_rfp_discovery         | 382  | 82  | no    | 0    | 25 |
| Issue                                                               |
| ------------------------------------------------------------------- |
| Correctness: broad exception 'Exception' at L41. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L202. Narrow the scope. |
| Correctness: broad exception 'Exception' at L477. Narrow the scope. |
| Correctness: broad exception 'Exception' at L123. Narrow the scope. |
| Correctness: broad exception 'Exception' at L264. Narrow the scope. |
| Correctness: broad exception 'Exception' at L414. Narrow the scope. |
| Correctness: broad exception 'Exception' at L325. Narrow the scope. |

### RFP_Discovery_System/complile_reports.py
| Function                  | Line | LOC | Async | Args | CC |
| ------------------------- | ---- | --- | ----- | ---- | -- |
| now_ts                    | 63   | 1   | no    | 0    | 1  |
| slugify                   | 66   | 5   | no    | 1    | 1  |
| sha8                      | 73   | 1   | no    | 1    | 1  |
| _module_iter_docs         | 77   | 15  | no    | 1    | 7  |
| load_parsed_regulations   | 94   | 47  | no    | 0    | 21 |
| make_prompt_rfp_discovery | 167  | 16  | no    | 1    | 2  |
| _first_quote              | 197  | 2   | no    | 2    | 1  |
| make_mock_items_from_text | 201  | 38  | no    | 1    | 4  |
| call_gemini               | 242  | 19  | no    | 7    | 8  |
| parse_json_array          | 263  | 7   | no    | 1    | 4  |
| parse_args                | 273  | 4   | no    | 0    | 1  |
| run_rfp_discovery         | 280  | 97  | no    | 2    | 34 |
| Issue                                                               |
| ------------------------------------------------------------------- |
| Correctness: broad exception 'Exception' at L109. Narrow the scope. |
| Correctness: broad exception 'Exception' at L117. Narrow the scope. |
| Correctness: broad exception 'Exception' at L258. Narrow the scope. |
| Correctness: broad exception 'Exception' at L294. Narrow the scope. |
| Correctness: broad exception 'Exception' at L318. Narrow the scope. |

### RFP_Discovery_System/dita_parser_AF_SF_Army_Navy.py
| Function  | Line | LOC | Async | Args | CC |
| --------- | ---- | --- | ----- | ---- | -- |
| iter_docs | 14   | 58  | no    | 0    | 16 |
| Issue                                                              |
| ------------------------------------------------------------------ |
| Correctness: broad exception 'Exception' at L69. Narrow the scope. |

### RFP_Discovery_System/sandbox_graph_builder.py
| Function | Line | LOC | Async | Args | CC |
| -------- | ---- | --- | ----- | ---- | -- |
| node_id  | 16   | 1   | no    | 2    | 1  |
| main     | 19   | 66  | no    | 0    | 11 |
| Issue                                                                |
| -------------------------------------------------------------------- |
| Maintainability: direct print() detected. Prefer structured logging. |

### Validation_Testing/error_tracking_dashboard.py
| Function                    | Line | LOC | Async | Args | CC |
| --------------------------- | ---- | --- | ----- | ---- | -- |
| main                        | 335  | 17  | no    | 0    | 3  |
| __init__                    | 68   | 3   | no    | 1    | 1  |
| analyze_kb_file             | 73   | 13  | no    | 2    | 4  |
| _validate_fact              | 88   | 48  | no    | 2    | 8  |
| _check_regulatory_match     | 138  | 7   | no    | 4    | 2  |
| _update_stats               | 147  | 21  | no    | 2    | 9  |
| _generate_report            | 170  | 17  | no    | 1    | 4  |
| _get_top_warnings           | 189  | 20  | no    | 2    | 8  |
| _check_attribution_coverage | 211  | 11  | no    | 1    | 4  |
| _check_deduplication        | 224  | 16  | no    | 1    | 4  |
| print_dashboard             | 242  | 51  | no    | 2    | 11 |
| _color_rate                 | 295  | 11  | no    | 2    | 5  |
| export_detailed_report      | 308  | 25  | no    | 2    | 8  |
- **Classes:** Colors, ValidationResult, ErrorTracker
| Issue                                                                |
| -------------------------------------------------------------------- |
| Correctness: bare 'except' at L305. Catch specific exceptions.       |
| Maintainability: direct print() detected. Prefer structured logging. |

### Validation_Testing/sandbox_validate_kb.py
| Function     | Line | LOC | Async | Args | CC |
| ------------ | ---- | --- | ----- | ---- | -- |
| wcount       | 29   | 1   | no    | 1    | 3  |
| trunc25      | 32   | 1   | no    | 1    | 3  |
| sanity_score | 35   | 7   | no    | 4    | 10 |
| safe_float   | 44   | 7   | no    | 2    | 6  |
| dedupe_merge | 53   | 23  | no    | 1    | 6  |
| main         | 78   | 40  | no    | 0    | 7  |
| Issue                                                                |
| -------------------------------------------------------------------- |
| Correctness: broad exception 'Exception' at L50. Narrow the scope.   |
| Maintainability: direct print() detected. Prefer structured logging. |

### Validation_Testing/test_error_scenarios.py
| Function                    | Line | LOC | Async | Args | CC |
| --------------------------- | ---- | --- | ----- | ---- | -- |
| create_test_kb_with_errors  | 12   | 234 | no    | 0    | 1  |
| create_test_report_markdown | 248  | 57  | no    | 0    | 1  |
| main                        | 307  | 27  | no    | 0    | 3  |
| Issue                                                                |
| -------------------------------------------------------------------- |
| Maintainability: direct print() detected. Prefer structured logging. |

### Validation_Testing/test_refactored_validator.py
| Function                         | Line | LOC | Async | Args | CC |
| -------------------------------- | ---- | --- | ----- | ---- | -- |
| load_test_data                   | 23   | 59  | no    | 0    | 3  |
| test_validation_module           | 84   | 102 | no    | 0    | 9  |
| create_comprehensive_test_report | 188  | 101 | no    | 0    | 1  |
| Issue                                                                |
| -------------------------------------------------------------------- |
| Maintainability: direct print() detected. Prefer structured logging. |
| Security: Use of exec() can execute arbitrary code.                  |

### extend inputs schema.py
| Function                  | Line | LOC | Async | Args | CC |
| ------------------------- | ---- | --- | ----- | ---- | -- |
| default_base_dir          | 68   | 6   | no    | 0    | 2  |
| now_ts                    | 77   | 1   | no    | 0    | 1  |
| sha8                      | 80   | 1   | no    | 1    | 1  |
| _module_iter_docs         | 89   | 8   | no    | 1    | 4  |
| load_parsed_regulations   | 100  | 31  | no    | 0    | 20 |
| make_prompt_rfp_discovery | 159  | 15  | no    | 1    | 2  |
| _grab_sentence            | 189  | 14  | no    | 3    | 5  |
| make_mock_items_from_text | 206  | 35  | no    | 1    | 6  |
| call_gemini               | 245  | 22  | no    | 1    | 9  |
| parse_json_array          | 270  | 6   | no    | 1    | 4  |
| _quote_within_limit       | 280  | 1   | no    | 2    | 1  |
| _support_matches          | 284  | 3   | no    | 3    | 2  |
| clean_items               | 290  | 77  | no    | 3    | 29 |
| parse_args                | 371  | 7   | no    | 0    | 1  |
| run_rfp_discovery         | 382  | 82  | no    | 0    | 25 |
| Issue                                                               |
| ------------------------------------------------------------------- |
| Correctness: broad exception 'Exception' at L41. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L202. Narrow the scope. |
| Correctness: broad exception 'Exception' at L477. Narrow the scope. |
| Correctness: broad exception 'Exception' at L123. Narrow the scope. |
| Correctness: broad exception 'Exception' at L264. Narrow the scope. |
| Correctness: broad exception 'Exception' at L414. Narrow the scope. |
| Correctness: broad exception 'Exception' at L325. Narrow the scope. |

### main.py
| Function                      | Line | LOC | Async | Args | CC |
| ----------------------------- | ---- | --- | ----- | ---- | -- |
| get_db_connection             | 101  | 9   | no    | 0    | 2  |
| get_report_generator          | 528  | 11  | no    | 1    | 2  |
| generate_report               | 543  | 16  | yes   | 2    | 1  |
| process_report                | 561  | 21  | yes   | 2    | 3  |
| get_report_status             | 585  | 3   | yes   | 1    | 1  |
| get_report_types              | 591  | 12  | yes   | 0    | 1  |
| get_compliance_metrics        | 606  | 13  | yes   | 0    | 1  |
| health_check                  | 622  | 7   | yes   | 0    | 1  |
| __init__                      | 116  | 3   | no    | 2    | 1  |
| generate                      | 121  | 2   | yes   | 1    | 1  |
| cleanup                       | 125  | 6   | no    | 1    | 4  |
| generate                      | 136  | 16  | yes   | 1    | 4  |
| _fetch_audit_data             | 154  | 27  | yes   | 1    | 1  |
| _calculate_compliance_metrics | 183  | 40  | yes   | 1    | 10 |
| _fetch_violations             | 225  | 25  | yes   | 1    | 1  |
| _generate_pdf_report          | 252  | 153 | yes   | 4    | 10 |
| _generate_excel_report        | 407  | 43  | yes   | 4    | 5  |
| _generate_json_report         | 452  | 28  | yes   | 4    | 4  |
| _create_compliance_chart      | 482  | 32  | yes   | 2    | 3  |
| _get_status_indicator         | 516  | 9   | no    | 2    | 4  |
- **Classes:** ReportType, ReportFormat, ReportRequest, ReportStatus, ComplianceMetrics, ReportGenerator, ComplianceAuditReport
| Issue                                                                       |
| --------------------------------------------------------------------------- |
| Correctness: broad exception 'Exception' at L577. Narrow the scope.         |
| Correctness: bare 'except' at L130. Catch specific exceptions.              |
| Code smell: empty except block (pass) at L130. Consider logging & handling. |
| Maintainability: 2 TODO/FIXME notes present.                                |

### procurement_integrator.py
| Function                | Line | LOC | Async | Args | CC |
| ----------------------- | ---- | --- | ----- | ---- | -- |
| load_knowledge_graph    | 92   | 3   | no    | 1    | 2  |
| gemini_check_compliance | 98   | 17  | yes   | 1    | 3  |
| scrape_rfps             | 119  | 28  | yes   | 1    | 3  |
| validate_subcontract    | 151  | 17  | yes   | 1    | 6  |
| generate_bom            | 172  | 25  | yes   | 1    | 3  |
| security_check          | 201  | 21  | yes   | 1    | 7  |
| add_procurement_to_kb   | 225  | 10  | no    | 2    | 1  |
- **Classes:** ScrapeRFPRequest, SubcontractValidateRequest, BOMGenerateRequest, SecurityCheckRequest
| Issue                                                               |
| ------------------------------------------------------------------- |
| Correctness: broad exception 'Exception' at L113. Narrow the scope. |
| Correctness: broad exception 'Exception' at L211. Narrow the scope. |

### project_audit (1).py
| Function              | Line | LOC | Async | Args | CC |
| --------------------- | ---- | --- | ----- | ---- | -- |
| iter_py_files         | 39   | 7   | no    | 1    | 3  |
| read_text             | 48   | 7   | no    | 1    | 5  |
| short                 | 57   | 4   | no    | 2    | 3  |
| cyclomatic_complexity | 93   | 7   | no    | 1    | 3  |
| decorator_names       | 102  | 13  | no    | 1    | 8  |
| is_fastapi_decorator  | 117  | 1   | no    | 1    | 3  |
| find_endpoints        | 120  | 17  | no    | 1    | 18 |
| detect_issues         | 139  | 45  | no    | 2    | 24 |
| scan_module           | 186  | 27  | no    | 2    | 6  |
| summarize_kb          | 217  | 29  | no    | 1    | 22 |
| md_table              | 250  | 9   | no    | 1    | 2  |
| suggest_for_function  | 261  | 8   | no    | 1    | 4  |
| aggregate_findings    | 271  | 11  | no    | 1    | 1  |
| main                  | 286  | 163 | no    | 0    | 34 |
| fmt                   | 254  | 1   | no    | 1    | 1  |
- **Classes:** FunctionInfo, ModuleInfo
| Issue                                                                              |
| ---------------------------------------------------------------------------------- |
| Correctness: broad exception 'Exception' at L51. Narrow the scope.                 |
| Correctness: broad exception 'Exception' at L60. Narrow the scope.                 |
| Correctness: broad exception 'Exception' at L190. Narrow the scope.                |
| Correctness: broad exception 'Exception' at L222. Narrow the scope.                |
| Correctness: broad exception 'Exception' at L54. Narrow the scope.                 |
| Maintainability: direct print() detected. Prefer structured logging.               |
| Maintainability: 1 TODO/FIXME notes present.                                       |
| Security: Use of eval() can execute arbitrary code.                                |
| Security: Use of exec() can execute arbitrary code.                                |
| Security: pickle.load is unsafe with untrusted data. Prefer json or a safe format. |
| Security: pickle.loads is unsafe with untrusted data.                              |
| Security: yaml.load without SafeLoader is unsafe; use safe_load.                   |

### proposalos_rge/__init__.py

### proposalos_rge/api/endpoints.py
| Function          | Line | LOC | Async | Args | CC |
| ----------------- | ---- | --- | ----- | ---- | -- |
| list_templates    | 45   | 7   | no    | 0    | 1  |
| get_template_info | 56   | 13  | no    | 1    | 2  |
| validate_only     | 73   | 41  | no    | 1    | 4  |
| preview           | 118  | 71  | no    | 1    | 9  |
| generate          | 193  | 101 | no    | 1    | 27 |
| batch_generate    | 298  | 25  | no    | 2    | 5  |
| health_check      | 328  | 6   | no    | 0    | 1  |
- **Classes:** PreviewBody, GenerateBody, TemplateListResponse, ValidationResponse
| Method | Route                    | Line |
| ------ | ------------------------ | ---- |
| GET    | /templates               | 45   |
| GET    | /templates/{template_id} | 56   |
| POST   | /validate                | 73   |
| POST   | /preview                 | 118  |
| POST   | /generate                | 193  |
| POST   | /batch                   | 298  |
| GET    | /health                  | 328  |
| Issue                                                               |
| ------------------------------------------------------------------- |
| Correctness: broad exception 'Exception' at L173. Narrow the scope. |
| Correctness: broad exception 'Exception' at L320. Narrow the scope. |

### proposalos_rge/example_usage.py
| Function                        | Line | LOC | Async | Args | CC |
| ------------------------------- | ---- | --- | ----- | ---- | -- |
| example_1_basic_dfars_checklist | 28   | 33  | no    | 0    | 3  |
| example_2_synthetic_data        | 64   | 200 | no    | 0    | 6  |
| example_3_export_formats        | 267  | 43  | no    | 0    | 1  |
| example_4_from_extraction       | 313  | 53  | no    | 0    | 2  |
| main                            | 369  | 29  | no    | 0    | 7  |
| Issue                                                                |
| -------------------------------------------------------------------- |
| Correctness: broad exception 'Exception' at L381. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L388. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L393. Narrow the scope.  |
| Maintainability: direct print() detected. Prefer structured logging. |

### proposalos_rge/inputs/kb_loader.py
| Function                       | Line | LOC | Async | Args | CC |
| ------------------------------ | ---- | --- | ----- | ---- | -- |
| load_kb_to_payload             | 8    | 41  | no    | 2    | 8  |
| load_rfp_extraction_to_payload | 52   | 46  | no    | 2    | 4  |

### proposalos_rge/inputs/ui_adapter.py
| Function                       | Line | LOC | Async | Args | CC |
| ------------------------------ | ---- | --- | ----- | ---- | -- |
| adapt_ui_request               | 6    | 19  | no    | 1    | 1  |
| create_allocations_from_travel | 28   | 27  | no    | 2    | 2  |
| create_allocations_from_labor  | 58   | 38  | no    | 2    | 4  |
| create_assumptions_from_facts  | 99   | 36  | no    | 1    | 3  |
| create_hefs_from_config        | 138  | 23  | no    | 3    | 2  |
| create_gfx_from_rfp            | 164  | 28  | no    | 1    | 3  |

### proposalos_rge/normalize/builder.py
| Function              | Line | LOC | Async | Args | CC |
| --------------------- | ---- | --- | ----- | ---- | -- |
| build_unified_payload | 13   | 61  | no    | 3    | 10 |
| _detect_conflicts     | 77   | 47  | no    | 1    | 13 |
| merge_payloads        | 127  | 37  | no    | 1    | 8  |

### proposalos_rge/registry.py
| Function     | Line | LOC | Async | Args | CC |
| ------------ | ---- | --- | ----- | ---- | -- |
| get_template | 94   | 2   | no    | 1    | 1  |
- **Classes:** SectionSpec, TemplateSpec

### proposalos_rge/render/__init__.py
| Function | Line | LOC | Async | Args | CC |
| -------- | ---- | --- | ----- | ---- | -- |
| render   | 16   | 10  | no    | 2    | 1  |
- **Classes:** Renderer

### proposalos_rge/render/md/annual_fy.py
| Function                      | Line | LOC | Async | Args | CC |
| ----------------------------- | ---- | --- | ----- | ---- | -- |
| _infer_allocations_from_facts | 8    | 27  | no    | 1    | 5  |
| render                        | 38   | 153 | no    | 1    | 48 |

### proposalos_rge/render/md/dfars_templates.py
| Function                | Line | LOC | Async | Args | CC |
| ----------------------- | ---- | --- | ----- | ---- | -- |
| render_dfars_checklist  | 66   | 139 | no    | 2    | 27 |
| render_dfars_cover_page | 208  | 163 | no    | 2    | 26 |
| _safe_get               | 374  | 29  | no    | 3    | 7  |
| register                | 406  | 41  | no    | 1    | 3  |

### proposalos_rge/schemas.py
- **Classes:** RegulatorySupport, SourceRef, KBFact, Allocation, Assumption, HEF, GFX, ChartSpec, UIInputs, RFPMeta, AuditEntry, Audit, UnifiedPayload

### proposalos_rge/validate/rules.py
| Function                        | Line | LOC | Async | Args | CC |
| ------------------------------- | ---- | --- | ----- | ---- | -- |
| validate_facts                  | 7    | 59  | no    | 1    | 17 |
| run_validators                  | 69   | 36  | no    | 1    | 3  |
| _validate_allocations           | 108  | 42  | no    | 1    | 16 |
| _validate_regulatory_compliance | 153  | 41  | no    | 1    | 10 |
| _validate_math_consistency      | 197  | 25  | no    | 1    | 9  |

### test_proposalos_rge.py
| Function                | Line | LOC | Async | Args | CC |
| ----------------------- | ---- | --- | ----- | ---- | -- |
| test_schema_creation    | 35   | 63  | no    | 0    | 3  |
| test_registry           | 101  | 23  | no    | 0    | 5  |
| test_dfars_checklist    | 127  | 86  | no    | 0    | 5  |
| test_dfars_cover_page   | 216  | 66  | no    | 0    | 8  |
| test_annual_fy_report   | 285  | 85  | no    | 0    | 8  |
| test_validation_rules   | 373  | 43  | no    | 0    | 5  |
| test_dict_compatibility | 419  | 60  | no    | 0    | 8  |
| test_edge_cases         | 482  | 63  | no    | 0    | 9  |
| run_all_tests           | 548  | 52  | no    | 0    | 8  |
| Issue                                                                |
| -------------------------------------------------------------------- |
| Correctness: broad exception 'Exception' at L96. Narrow the scope.   |
| Correctness: broad exception 'Exception' at L122. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L211. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L280. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L368. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L414. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L477. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L543. Narrow the scope.  |
| Correctness: broad exception 'Exception' at L571. Narrow the scope.  |
| Maintainability: direct print() detected. Prefer structured logging. |
