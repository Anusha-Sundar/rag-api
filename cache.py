import redis
import hashlib
import json
from config import get_logger

logger = get_logger(__name__)

pool = redis.ConnectionPool(host="localhost",port=6379,db=0,decode_responses=True)
def get_redis_client() -> redis.Redis:
    return redis.Redis(connection_pool=pool)

def make_cache_key(question: str) -> str:
    qn = question.lower().strip()
    hashed = hashlib.md5(qn.encode()).hexdigest()
    return f"rag:answer:{hashed}"

def get_cached(client, question) -> dict | None:
    key = make_cache_key(question)
    cached = client.get(key)
    if cached:
        logger.info(f"Cache hit for key {key[:20]}")
        return json.loads(cached)
    logger.info("Cache miss")
    return None

def set_cached(client, question, answer, ttl=3600) -> None:
    key = make_cache_key(question)
    client.setex(key,ttl,json.dumps(answer))
    logger.info(f"key {key} has been set with answer for ttl {ttl}s")
    
def get_cache_stats(client) -> dict:
    keys = client.keys("rag:*")
    logger.info(f"{len(keys)} no of keys are found with keys: {keys}")
    return {"total_cached": len(keys), "keys":keys}