-allow_origins=["*"]
+allow_origins=os.environ.get("ALLOWED_ORIGINS","http://localhost:3000").split(",")
