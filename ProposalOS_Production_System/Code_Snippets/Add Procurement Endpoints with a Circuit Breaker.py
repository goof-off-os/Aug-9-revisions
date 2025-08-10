# In orchestrator_production.py
import pybreaker

# ... (other imports)

# --- Add a circuit breaker for the compliance service ---
compliance_breaker = pybreaker.CircuitBreaker(fail_max=3, reset_timeout=60)

# ...

# --- Modified BOEValidationRequest for subcontracting ---
class SubcontractRequest(BaseModel):
    vendor_data: Dict[str, Any]
    contract_value: float
    # ... other relevant fields

# ...

@app.post("/procure/subcontract")
@backoff.on_exception(backoff.expo, (httpx.RequestError, pybreaker.CircuitBreakerError), max_tries=3)
async def procure_subcontract(request: SubcontractRequest, user_id: str = Depends(verify_api_key)):
    """
    Validates subcontractor against SAM.gov, DFARS, and other regulations.
    Uses a circuit breaker to protect against repeated failures of the compliance service.
    """
    try:
        # The external call is decorated with the circuit breaker
        @compliance_breaker
        async def validate_subcontract_with_service(data: dict):
            # This logic would call the external compliance service
            # and include checks for FAR 9.404 (exclusions) and DFARS 252.204-7012
            async with httpx.AsyncClient() as client:
                # response = await client.post(config.COMPLIANCE_SERVICE_URL, json=data)
                # response.raise_for_status()
                # return response.json()

                # Mock response for demonstration:
                print("Calling compliance service...")
                if request.contract_value > 500000:
                    return {"is_compliant": False, "issues": ["Exceeds simplified acquisition threshold, requires additional review."]}
                return {"is_compliant": True, "issues": []}

        compliance_result = await validate_subcontract_with_service(request.vendor_data)
        return {"status": "validated", "compliance": compliance_result}

    except pybreaker.CircuitBreakerError:
        logger.error("Compliance service circuit breaker is open. Returning degraded response.")
        error_counter.labels(error_type='circuit_breaker_open').inc()
        # Return a degraded, cached, or default response
        return {"status": "degraded", "compliance": {"is_compliant": None, "issues": ["Compliance service is temporarily unavailable."] }}
    except Exception as e:
        logger.error(f"Subcontract procurement error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during subcontract validation.")