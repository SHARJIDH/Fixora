import pytest
import os
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from services.models import Base, Job, Issue, Repository
from services import db

# Use in-memory SQLite for testing
TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def test_db():
    engine = create_engine(TEST_DB_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    
    from contextlib import contextmanager
    @contextmanager
    def mock_get_db_session():
        session = Session()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    # Patch modules that use get_db_session and socketio
    with patch('services.db.get_db_session', side_effect=mock_get_db_session), \
         patch('services.db.get_engine', return_value=engine), \
         patch('services.socket_service.socketio', MagicMock()), \
         patch('services.socket_service.emit_job_status', MagicMock()), \
         patch('services.socket_service.emit_job_update', MagicMock()):
        yield engine
    
    Base.metadata.drop_all(engine)

def test_insert_and_get_job(test_db):
    job_data = {
        'id': 'job-123',
        'repositoryId': 'owner/repo',
        'issueNumber': 1,
        'status': 'in_progress',
    }
    
    db.insert_job(job_data)
    job = db.get_job_by_id('job-123')
    
    assert job is not None
    assert job['id'] == 'job-123'
    assert job['repositoryId'] == 'owner/repo'

def test_update_job(test_db):
    job_data = {'id': 'job-456', 'status': 'pending'}
    db.insert_job(job_data)
    
    db.update_job('job-456', {'status': 'completed', 'prUrl': 'http://pr/456'})
    job = db.get_job_by_id('job-456')
    
    assert job['status'] == 'completed'
    assert job['prUrl'] == 'http://pr/456'

def test_atomic_create_job_if_not_exists(test_db):
    repo = 'owner/repo'
    issue = 1
    job_id = f"{repo}-{issue}-timestamp"
    job_data = {'id': job_id, 'repositoryId': repo, 'issueNumber': issue}
    
    # First creation should succeed
    created = db.atomic_create_job_if_not_exists(repo, issue, job_data)
    assert created is not None
    assert created['id'] == job_id
    
    # Second creation for same issue should return None (already in progress)
    job_id_2 = f"{repo}-{issue}-timestamp2"
    job_data_2 = {'id': job_id_2, 'repositoryId': repo, 'issueNumber': issue}
    created_2 = db.atomic_create_job_if_not_exists(repo, issue, job_data_2)
    assert created_2 is None

def test_insert_repository(test_db):
    repo_data = {
        'id': 'repo-1',
        'name': 'test-repo',
        'fullName': 'owner/test-repo',
        'htmlUrl': 'http://github/owner/test-repo',
        'userId': 'user-1'
    }
    db.insert_repository(repo_data)
    
    repos = db.get_repositories('user-1')
    assert len(repos) == 1
    assert repos[0]['fullName'] == 'owner/test-repo'

def test_get_stats(test_db):
    # Insert some data
    db.insert_job({'id': 'j1', 'status': 'completed', 'userId': 'u1'})
    db.insert_job({'id': 'j2', 'status': 'failed', 'userId': 'u1'})
    db.insert_issue({'id': 'i1', 'githubId': 'gh-123', 'repositoryId': 'r1', 'userId': 'u1', 'number': 1, 'title': 'Test Issue'})
    
    stats = db.get_stats('u1')
    assert stats['total_jobs'] == 2
    assert stats['completed_jobs'] == 1
    assert stats['failed_jobs'] == 1
    assert stats['total_issues'] == 1
