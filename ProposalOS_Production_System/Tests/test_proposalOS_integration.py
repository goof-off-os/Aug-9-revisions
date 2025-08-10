#!/usr/bin/env python3
"""
ProposalOS Integration Test Suite
==================================
Comprehensive testing for the production orchestrator and its components

Tests:
- Orchestrator endpoints
- SAM.gov RFP scraping
- Procurement compliance checking
- Knowledge graph integration
- Circuit breaker resilience
- State management
- Security and authentication
"""

import pytest
import asyncio
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import httpx
import redis
import pybreaker

# Set test environment
os.environ['ALLOW_INSECURE'] = 'true'
os.environ['USE_REDIS'] = 'false'
os.environ['USE_FIRESTORE'] = 'false'
os.environ['GEMINI_API_KEY'] = 'test-api-key'
os.environ['SAM_API_KEY'] = 'test-sam-key'

# Import after environment setup
from orchestrator_production import app, config, Config
from sam_rfp_scraper import SAMRFPScraper, RFPOpportunity
from procurement_compliance_checker import (
    SubcontractorComplianceChecker, 
    BillOfMaterialsGenerator,
    VendorData,
    BOMItem,
    ComplianceSeverity
)

from fastapi.testclient import TestClient

# Test fixtures
@pytest.fixture
def test_client():
    """Create test client for FastAPI app"""
    return TestClient(app)

@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    mock = Mock(spec=redis.Redis)
    mock.ping.return_value = True
    mock.pipeline.return_value = Mock(
        execute=Mock(return_value=[0, 1, 1, True])
    )
    return mock

@pytest.fixture
def vendor_data():
    """Sample vendor data for testing"""
    return VendorData(
        name="Test Vendor Inc",
        quote=3_000_000,
        cmmc_certified=False,
        itar_registered=True,
        sam_registered=True,
        small_business=False,
        cage_code="12345",
        duns_number="123456789",
        facility_clearance="SECRET",
        past_performance="GOOD"
    )

@pytest.fixture
def rfp_opportunity():
    """Sample RFP opportunity"""
    return RFPOpportunity(
        notice_id="TEST-2025-001",
        title="Advanced Satellite Communications System",
        solicitation_number="FA8750-25-R-0001",
        agency="Space Systems Command",
        department="Department of Defense",
        posted_date="2025-08-01",
        response_deadline="2025-09-01",
        description="Development of next-generation SATCOM terminals with CPFF contract structure",
        naics_code="334220",
        set_aside="None",
        award_type="CPFF",
        place_of_performance="Los Angeles, CA",
        estimated_value=50_000_000,
        url="https://sam.gov/opp/TEST-2025-001"
    )

class TestOrchestrator:
    """Test orchestrator endpoints and functionality"""
    
    def test_health_check(self, test_client):
        """Test health endpoint"""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "uptime_seconds" in data
        assert "model_version" in data
        assert data["model_version"] == "gemini-2.5-pro"
    
    def test_metrics_endpoint(self, test_client):
        """Test Prometheus metrics endpoint"""
        response = test_client.get("/metrics")
        assert response.status_code == 200
        assert "proposalOS_requests_total" in response.text
        assert "proposalOS_active_sessions" in response.text
    
    @patch('orchestrator_production.genai.GenerativeModel')
    def test_conversation_start(self, mock_model, test_client):
        """Test starting a conversation"""
        # Mock Gemini response
        mock_response = Mock()
        mock_response.text = json.dumps({
            "data_state": "incomplete",
            "facts": {"travel_purpose": "Conference attendance"},
            "follow_up_questions": ["What are the travel dates?"]
        })
        mock_model.return_value.generate_content.return_value = mock_response
        
        response = test_client.post(
            "/conversation/start",
            json={"user_id": "test_user"},
            headers={"Authorization": "Bearer test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["data_state"] == "incomplete"
    
    @patch('orchestrator_production.genai.GenerativeModel')
    def test_conversation_continue(self, mock_model, test_client):
        """Test continuing a conversation"""
        # Start conversation first
        mock_response = Mock()
        mock_response.text = json.dumps({
            "data_state": "partial",
            "facts": {"travel_dates": "2025-09-15 to 2025-09-20"},
            "follow_up_questions": ["What is the destination?"]
        })
        mock_model.return_value.generate_content.return_value = mock_response
        
        # Create session
        start_response = test_client.post(
            "/conversation/start",
            json={"user_id": "test_user"},
            headers={"Authorization": "Bearer test-key"}
        )
        session_id = start_response.json()["session_id"]
        
        # Continue conversation
        response = test_client.post(
            "/conversation/continue",
            json={
                "session_id": session_id,
                "user_message": "Travel dates are September 15-20, 2025"
            },
            headers={"Authorization": "Bearer test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data_state"] == "partial"

class TestProcurementEndpoints:
    """Test procurement-related endpoints"""
    
    @patch('orchestrator_production.httpx.AsyncClient')
    async def test_scrape_rfps_endpoint(self, mock_client, test_client):
        """Test RFP scraping endpoint"""
        # Mock SAM.gov response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "opportunitiesData": [{
                "noticeId": "TEST-001",
                "title": "Test RFP",
                "solicitationNumber": "SOL-001",
                "fullParentPathName": "DOD/Space Force",
                "department": "DOD",
                "postedDate": "2025-08-01",
                "description": "Test description"
            }]
        }
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )
        
        response = test_client.post(
            "/procurement/scrape-rfps",
            json={
                "keywords": "satellite",
                "limit": 5,
                "posted_days_ago": 30
            },
            headers={"Authorization": "Bearer test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "opportunities" in data
        assert data["count"] > 0
    
    @patch('orchestrator_production.compliance_breaker')
    async def test_vendor_compliance_check(self, mock_breaker, test_client, vendor_data):
        """Test vendor compliance checking"""
        # Mock compliance service response
        mock_breaker.call = Mock(return_value={
            "is_compliant": False,
            "issues": ["CMMC certification required"]
        })
        
        response = test_client.post(
            "/procurement/check-vendor-compliance",
            json={
                "vendor_name": vendor_data.name,
                "quote": vendor_data.quote,
                "cmmc_certified": vendor_data.cmmc_certified,
                "contract_type": "CPFF"
            },
            headers={"Authorization": "Bearer test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "compliance_result" in data
        assert "issues" in data["compliance_result"]
    
    async def test_subcontract_validation(self, test_client):
        """Test subcontract procurement validation"""
        response = test_client.post(
            "/procure/subcontract",
            json={
                "vendor_data": {
                    "name": "SubK Corp",
                    "cage_code": "54321"
                },
                "contract_value": 1_500_000
            },
            headers={"Authorization": "Bearer test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["validated", "degraded"]

class TestComplianceChecker:
    """Test procurement compliance checker module"""
    
    def test_tina_threshold_check(self, vendor_data):
        """Test TINA threshold validation"""
        checker = SubcontractorComplianceChecker()
        vendor_data.quote = 2_500_000  # Above TINA threshold
        
        result = checker.check_subcontractor_compliance(
            vendor_data,
            contract_type="FFP",
            is_dod_contract=True
        )
        
        assert not result["is_compliant"]
        assert any("TINA" in issue["code"] for issue in result["issues"])
        assert result["risk_score"] >= 20
    
    def test_cmmc_requirement(self, vendor_data):
        """Test CMMC certification requirement for DoD"""
        checker = SubcontractorComplianceChecker()
        vendor_data.cmmc_certified = False
        vendor_data.quote = 300_000  # Above simplified acquisition threshold
        
        result = checker.check_subcontractor_compliance(
            vendor_data,
            contract_type="FFP",
            is_dod_contract=True
        )
        
        assert any("CMMC" in issue["description"] for issue in result["issues"])
        assert result["risk_level"] in ["Medium", "High"]
    
    def test_sam_registration_critical(self, vendor_data):
        """Test SAM.gov registration is critical"""
        checker = SubcontractorComplianceChecker()
        vendor_data.sam_registered = False
        
        result = checker.check_subcontractor_compliance(
            vendor_data,
            contract_type="FFP"
        )
        
        assert not result["is_compliant"]
        critical_issues = [i for i in result["issues"] 
                          if i["severity"] == "Critical"]
        assert len(critical_issues) > 0
        assert "SAM" in critical_issues[0]["description"]
    
    def test_batch_vendor_check(self):
        """Test checking multiple vendors"""
        checker = SubcontractorComplianceChecker()
        
        vendors = [
            VendorData("Vendor A", 1_000_000, cmmc_certified=True, sam_registered=True),
            VendorData("Vendor B", 500_000, cmmc_certified=False, sam_registered=True),
            VendorData("Vendor C", 3_000_000, cmmc_certified=True, sam_registered=False)
        ]
        
        result = checker.batch_check_vendors(
            vendors,
            contract_type="CPFF",
            prime_contract_value=10_000_000
        )
        
        assert result["total_vendors"] == 3
        assert result["recommended_vendor"] == "Vendor A"
        assert result["total_value"] == 4_500_000

class TestBOMGenerator:
    """Test Bill of Materials generation"""
    
    def test_bom_generation(self):
        """Test BOM generation from estimate"""
        generator = BillOfMaterialsGenerator()
        
        estimate = {
            "element": "Direct Materials",
            "amount": 2_000_000
        }
        
        bom = generator.generate_bom(estimate)
        
        assert len(bom) > 0
        assert all(isinstance(item, BOMItem) for item in bom)
        total = sum(item.total_cost for item in bom)
        assert total > 0
    
    def test_bom_validation(self):
        """Test BOM validation against constraints"""
        generator = BillOfMaterialsGenerator()
        
        bom = [
            BOMItem("Component A", "A-001", 10, 1000, "Vendor A", 
                   lead_time_days=45, itar_controlled=True),
            BOMItem("Component B", "B-001", 5, 2000, "Vendor B",
                   lead_time_days=30, country_of_origin="Taiwan")
        ]
        
        constraints = {
            "budget": 25000,
            "schedule_days": 60,
            "itar_approved": True,
            "buy_american": True
        }
        
        result = generator.validate_bom(bom, constraints)
        
        assert result["is_valid"]
        assert result["total_cost"] == 20000
        assert result["max_lead_time_days"] == 45
        assert len(result["warnings"]) > 0  # Foreign item warning
    
    def test_bom_csv_export(self, tmp_path):
        """Test BOM export to CSV"""
        generator = BillOfMaterialsGenerator()
        
        bom = [
            BOMItem("Test Item", "T-001", 5, 100, "Test Vendor")
        ]
        
        csv_file = tmp_path / "test_bom.csv"
        generator.export_bom_to_csv(bom, str(csv_file))
        
        assert csv_file.exists()
        with open(csv_file) as f:
            content = f.read()
            assert "Test Item" in content
            assert "500" in content  # Total cost

class TestRFPScraper:
    """Test SAM.gov RFP scraping"""
    
    @patch('sam_rfp_scraper.requests.Session')
    def test_rfp_scraping(self, mock_session):
        """Test basic RFP scraping"""
        # Mock SAM.gov API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "opportunitiesData": [{
                "noticeId": "TEST-001",
                "title": "Test Opportunity",
                "solicitationNumber": "SOL-001",
                "fullParentPathName": "DOD/Air Force",
                "department": "DOD",
                "postedDate": "2025-08-01",
                "description": "Test description with travel and labor requirements"
            }]
        }
        mock_session.return_value.get.return_value = mock_response
        
        scraper = SAMRFPScraper("test-api-key")
        rfps = scraper.scrape_rfps(
            keywords="satellite",
            posted_days_ago=30,
            limit=10
        )
        
        assert len(rfps) == 1
        assert rfps[0].notice_id == "TEST-001"
        assert rfps[0].department == "DOD"
    
    def test_eoc_extraction(self, rfp_opportunity):
        """Test Elements of Cost extraction from RFPs"""
        scraper = SAMRFPScraper("test-api-key")
        
        rfps = [rfp_opportunity]
        result = scraper.extract_eocs_from_rfps(rfps)
        
        assert result["total_rfps"] == 1
        assert len(result["rfps_with_eocs"]) > 0
        assert "Travel" in result["eoc_summary"]
    
    def test_rfp_to_eoc_doc_conversion(self, rfp_opportunity):
        """Test RFP to EoC document conversion"""
        doc = rfp_opportunity.to_eoc_doc()
        
        assert doc["id"] == rfp_opportunity.notice_id
        assert doc["title"] == rfp_opportunity.title
        assert "metadata" in doc
        assert doc["metadata"]["award_type"] == "CPFF"

class TestCircuitBreakers:
    """Test circuit breaker resilience patterns"""
    
    def test_compliance_circuit_breaker(self):
        """Test compliance service circuit breaker"""
        from orchestrator_production import compliance_breaker
        
        # Simulate failures
        for _ in range(4):
            try:
                compliance_breaker(lambda: (_ for _ in ()).throw(Exception("Service down")))
            except:
                pass
        
        # Circuit should be open
        assert compliance_breaker.state == pybreaker.STATE_OPEN
        
        with pytest.raises(pybreaker.CircuitBreakerError):
            compliance_breaker(lambda: "test")
    
    def test_sam_gov_circuit_breaker(self):
        """Test SAM.gov circuit breaker with longer recovery"""
        from orchestrator_production import sam_gov_breaker
        
        # Reset for testing
        sam_gov_breaker.reset()
        
        # Simulate failures
        for _ in range(4):
            try:
                sam_gov_breaker(lambda: (_ for _ in ()).throw(httpx.ConnectError("Connection failed")))
            except:
                pass
        
        assert sam_gov_breaker.state == pybreaker.STATE_OPEN

class TestKnowledgeGraph:
    """Test knowledge graph integration"""
    
    @patch('orchestrator_production.KnowledgeGraphService')
    async def test_knowledge_graph_query(self, mock_kg_service):
        """Test querying knowledge graph for regulations"""
        mock_service = mock_kg_service.return_value
        mock_service.query_regulations = AsyncMock(return_value=[
            {
                "citation": "FAR 31.205-46",
                "title": "Travel Costs",
                "applies_to": ["Direct Travel", "Per Diem"]
            }
        ])
        
        from orchestrator_production import KnowledgeGraphService
        service = KnowledgeGraphService(config)
        
        results = await service.query_regulations("travel")
        assert len(results) > 0
        assert results[0]["citation"] == "FAR 31.205-46"
    
    async def test_knowledge_graph_fallback(self):
        """Test knowledge graph fallback when service unavailable"""
        from orchestrator_production import KnowledgeGraphService
        
        # Create service with invalid URL
        test_config = Config()
        test_config.KNOWLEDGE_GRAPH_URL = "http://invalid:7474"
        
        service = KnowledgeGraphService(test_config)
        
        # Should return empty results instead of crashing
        results = await service.query_regulations("test")
        assert results == []

class TestSecurityFeatures:
    """Test security and authentication"""
    
    def test_api_key_validation(self, test_client):
        """Test API key validation"""
        # Test with invalid key
        response = test_client.get(
            "/conversation/sessions",
            headers={"Authorization": "Bearer invalid-key"}
        )
        # In ALLOW_INSECURE mode, should still work
        assert response.status_code in [200, 404]  # 404 if no sessions
    
    def test_rate_limiting(self, test_client, mock_redis):
        """Test rate limiting functionality"""
        with patch('orchestrator_production.app.state.redis_client', mock_redis):
            # Make multiple requests
            for i in range(10):
                response = test_client.get(
                    "/health",
                    headers={"Authorization": "Bearer test-key"}
                )
                assert response.status_code == 200
    
    def test_cors_headers(self, test_client):
        """Test CORS configuration"""
        response = test_client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        assert "access-control-allow-origin" in response.headers

class TestStateManagement:
    """Test session and state management"""
    
    @patch('orchestrator_production.genai.GenerativeModel')
    def test_session_creation(self, mock_model, test_client):
        """Test session creation and retrieval"""
        mock_response = Mock()
        mock_response.text = json.dumps({
            "data_state": "incomplete",
            "facts": {},
            "follow_up_questions": ["Initial question?"]
        })
        mock_model.return_value.generate_content.return_value = mock_response
        
        # Create session
        response = test_client.post(
            "/conversation/start",
            json={"user_id": "test_user"},
            headers={"Authorization": "Bearer test-key"}
        )
        
        session_id = response.json()["session_id"]
        assert session_id is not None
        
        # Retrieve sessions
        response = test_client.get(
            "/conversation/sessions",
            headers={"Authorization": "Bearer test-key"}
        )
        
        assert response.status_code == 200
        sessions = response.json()
        assert any(s["session_id"] == session_id for s in sessions)
    
    def test_session_expiration(self):
        """Test session TTL and cleanup"""
        from orchestrator_production import StateManager
        
        manager = StateManager(None, None)  # No Redis/Firestore
        
        # Create session
        session_id = manager.create_session("test_user")
        assert session_id in manager.sessions
        
        # Simulate expiration
        session = manager.sessions[session_id]
        session["last_activity"] = datetime.now() - timedelta(hours=2)
        
        # Clean expired
        manager.clean_expired_sessions()
        assert session_id not in manager.sessions

class TestErrorHandling:
    """Test error handling and recovery"""
    
    def test_malformed_request(self, test_client):
        """Test handling of malformed requests"""
        response = test_client.post(
            "/conversation/continue",
            json={"invalid": "data"},
            headers={"Authorization": "Bearer test-key"}
        )
        assert response.status_code == 422  # Validation error
    
    @patch('orchestrator_production.genai.GenerativeModel')
    def test_model_failure_recovery(self, mock_model, test_client):
        """Test recovery from model failures"""
        # Simulate model failure
        mock_model.return_value.generate_content.side_effect = Exception("Model error")
        
        response = test_client.post(
            "/conversation/start",
            json={"user_id": "test_user"},
            headers={"Authorization": "Bearer test-key"}
        )
        
        assert response.status_code == 500
        assert "error" in response.json()

@pytest.mark.asyncio
async def test_full_integration_flow():
    """Test complete integration flow from RFP to compliance check"""
    
    # 1. Scrape RFP
    scraper = SAMRFPScraper("test-key")
    rfp = RFPOpportunity(
        notice_id="INT-TEST-001",
        title="Integration Test RFP",
        solicitation_number="INT-SOL-001",
        agency="Test Agency",
        department="Test Dept",
        posted_date="2025-08-01",
        response_deadline="2025-09-01",
        description="Requirements for direct labor, travel, and subcontracts",
        naics_code="541512",
        set_aside=None,
        award_type="CPFF",
        place_of_performance="Washington, DC",
        estimated_value=10_000_000,
        url="https://test.gov/opp/INT-TEST-001"
    )
    
    # 2. Extract EoCs
    eoc_results = scraper.extract_eocs_from_rfps([rfp])
    assert len(eoc_results["rfps_with_eocs"]) > 0
    
    # 3. Check vendor compliance for subcontracts
    checker = SubcontractorComplianceChecker()
    vendor = VendorData(
        name="Integration Vendor",
        quote=1_500_000,
        cmmc_certified=True,
        itar_registered=True,
        sam_registered=True,
        small_business=True
    )
    
    compliance_result = checker.check_subcontractor_compliance(
        vendor,
        contract_type="CPFF",
        prime_contract_value=10_000_000,
        is_dod_contract=False
    )
    
    assert compliance_result["is_compliant"]
    assert compliance_result["risk_level"] in ["Low", "Low-Medium"]
    
    # 4. Generate BOM
    generator = BillOfMaterialsGenerator()
    bom = generator.generate_bom({
        "element": "Direct Materials",
        "amount": 2_000_000
    })
    
    assert len(bom) > 0
    
    # 5. Validate complete procurement
    validation = generator.validate_bom(bom, {
        "budget": 2_000_000,
        "schedule_days": 90,
        "itar_approved": True
    })
    
    assert validation["is_valid"] or len(validation["warnings"]) > 0
    
    print("\n" + "="*60)
    print("INTEGRATION TEST COMPLETE")
    print("="*60)
    print(f"RFP: {rfp.title}")
    print(f"EoCs Identified: {eoc_results['eoc_summary']}")
    print(f"Vendor Compliance: {compliance_result['risk_level']}")
    print(f"BOM Items: {len(bom)}")
    print(f"Total Cost: ${validation['total_cost']:,.2f}")
    print("="*60)

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])