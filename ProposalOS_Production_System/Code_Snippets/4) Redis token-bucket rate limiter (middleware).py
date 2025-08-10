# at top-level
import time, json, hashlib, hmac
from redis.asyncio import Redis
from fastapi import Request, HTTPException

redis = Redis.from_url(os.environ.get("REDIS_URL","redis://localhost:6379"), decode_responses=True)

RATE_LIMIT = int(os.environ.get("RATE_LIMIT","120"))   # tokens per minute
BURST_SIZE = int(os.environ.get("RATE_BURST","240"))   # bucket capacity

def _client_key(request: Request, api_key: str) -> str:
    ip = request.client.host if request.client else "unknown"
    ak = hashlib.sha256((api_key or "").encode()).hexdigest()
    return f"rl:{ak}:{ip}"

@app.middleware("http")
async def rate_limiter(request: Request, call_next):
    # Skip health
    if request.url.path in ("/health", "/metrics"):
        return await call_next(request)

    api_key = request.headers.get("x-api-key") or request.query_params.get("api_key") or ""
    # If auth fails, let auth handler reject; but use api_key (or empty) for keying
    key = _client_key(request, api_key)

    now = int(time.time())
    window = now // 60

    # Lua would be ideal; keep it simple:
    pipe = redis.pipeline()
    # initialize bucket if not exists
    pipe.hgetall(key)
    data = await pipe.execute()
    state = data[0] or {}
    tokens = int(state.get("tokens", BURST_SIZE))
    last = int(state.get("window", window))

    # refill based on elapsed minutes
    if window > last:
        elapsed = window - last
        tokens = min(BURST_SIZE, tokens + elapsed * RATE_LIMIT)

    if tokens <= 0:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    tokens -= 1
    await redis.hset(key, mapping={"tokens": tokens, "window": window})
    await redis.expire(key, 180)  # keep small ttl

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT)
    response.headers["X-RateLimit-Remaining"] = str(tokens)
    return response
