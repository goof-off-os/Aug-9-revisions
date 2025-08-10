--- a/orchestrator_enhanced.py
+++ b/orchestrator_enhanced.py
@@
-class Config:
+class Config:
     API_KEY_HASH = os.environ.get("API_KEY_HASH")  # hex SHA256
+    ALLOW_INSECURE = (os.environ.get("ALLOW_INSECURE") or "").strip().lower() in ("1","true","yes","on")
@@
-def verify_api_key(api_key: str) -> bool:
-    if not config.API_KEY_HASH:
-        return True  # current behavior: allow if unset
-    digest = hashlib.sha256((api_key or "").encode()).hexdigest()
-    return digest == config.API_KEY_HASH
+def verify_api_key(api_key: str) -> bool:
+    # Default deny if not explicitly allowed
+    if not config.API_KEY_HASH:
+        return config.ALLOW_INSECURE is True
+    digest = hashlib.sha256((api_key or "").encode()).hexdigest()
+    # timing-safe equality
+    return hmac.compare_digest(digest, config.API_KEY_HASH)
@@
-@app.on_event("startup")
-async def startup_event():
+@app.on_event("startup")
+async def startup_event():
     logger.info("starting...")
+    if not config.API_KEY_HASH and not config.ALLOW_INSECURE:
+        raise RuntimeError("API_KEY_HASH not set. For local dev only, set ALLOW_INSECURE=true.")
