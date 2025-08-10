facts = validate_and_repair_facts(json.loads(response.text))
validated = [ExtractedFact(**f).dict() for f in facts]
