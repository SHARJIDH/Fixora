import time
import json
import uuid
from services.redis_service import redis_client, set_cache, get_cache, delete_cache, set_job_cache, get_job_cache, enqueue_job
import tasks

def test_redis_basic():
    print("--- Testing Basic Redis Caching ---")
    key = "test_key_123"
    val = "Hello Redis"
    
    # Test set/get
    set_cache(key, val, expire=10)
    retrieved = get_cache(key)
    print(f"Retrieved basic value: {retrieved}")
    assert retrieved == val, "Basic Redis Get/Set failed"
    
    # Test delete
    delete_cache(key)
    retrieved_after_del = get_cache(key)
    print(f"Retrieved after delete: {retrieved_after_del}")
    assert retrieved_after_del is None, "Redis Delete failed"
    print("✓ Basic Redis tests passed\n")

def test_job_caching():
    print("--- Testing Job-Specific Caching (Write-Through) ---")
    job_id = f"test-job-{uuid.uuid4().hex[:8]}"
    job_data = {
        "id": job_id,
        "status": "processing",
        "stage": "analyzing",
        "logs": ["Test log 1"],
        "updated_at": time.time()
    }
    
    # Test set job cache
    set_job_cache(job_id, job_data)
    
    # Test get job cache
    retrieved_job = get_job_cache(job_id)
    print(f"Retrieved job status: {retrieved_job.get('status')}")
    assert retrieved_job == job_data, "Job caching failed"
    
    # Test update job cache
    job_data["status"] = "completed"
    set_job_cache(job_id, job_data)
    updated_retrieved = get_job_cache(job_id)
    print(f"Retrieved updated job status: {updated_retrieved.get('status')}")
    assert updated_retrieved["status"] == "completed", "Job cache update failed"
    print("✓ Job caching tests passed\n")

def test_queue_enqueue():
    print("--- Testing RQ Enqueue ---")
    # Using a function from a module so RQ can serialize it
    job = enqueue_job(tasks.dummy_task, 10, 20)
    if job:
        print(f"Job enqueued with ID: {job.id}")
        assert job.id is not None
    else:
        print("Failed to enqueue job")
        assert False, "Job enqueue failed"
    print("✓ Queue enqueue tests passed\n")

if __name__ == "__main__":
    try:
        # Check if Redis is reachable
        redis_client.ping()
        print("Redis is UP!\n")
        
        test_redis_basic()
        test_job_caching()
        test_queue_enqueue()
        
        print("======================================")
        print("ALL REDIS AND QUEUE TESTS PASSED!")
        print("======================================")
        print("\nNOTE: To test background execution, run 'python worker.py' in another terminal.")
        
    except Exception as e:
        print(f"TESTS FAILED: {str(e)}")
