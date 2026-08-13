import pytest
from unittest.mock import MagicMock, patch
from services.pr_service import PRService

@pytest.fixture
def mock_github_service():
    service = MagicMock()
    service.get_repo.return_value = MagicMock()
    return service

@pytest.fixture
def mock_ai_service():
    return MagicMock()

@pytest.fixture
def mock_code_execution():
    return MagicMock()

@pytest.fixture
def pr_service(mock_github_service, mock_ai_service, mock_code_execution):
    return PRService(mock_github_service, mock_ai_service, mock_code_execution)

def test_process_issue_success(pr_service, mock_ai_service, mock_github_service):
    # Mock AI result
    mock_ai_service.analyze_issue_and_plan_changes.return_value = {
        'analysis': 'Test analysis',
        'file_changes': [{'file_path': 'test.py', 'new_content': 'print("hello")', 'reason': 'test'}]
    }
    
    # Mock GitHub objects
    repo = mock_github_service.get_repo.return_value
    repo.full_name = 'owner/repo'
    repo.default_branch = 'main'
    
    # Mock _execute_ai_task to avoid deep branching in this test
    with patch.object(pr_service, '_execute_ai_task', return_value={'pr_id': 1, 'pr_url': 'http://pr/1', 'success': True}) as mock_execute:
        result = pr_service.process_issue(
            repo_full_name='owner/repo',
            issue_number=1,
            issue_title='Test Issue',
            issue_body='Test Body',
            comment_body='@bot fix'
        )
        
        assert result['success'] is True
        assert result['pr_url'] == 'http://pr/1'
        mock_execute.assert_called_once()

def test_is_documentation_only(pr_service):
    doc_changes = [
        {'file_path': 'README.md', 'new_content': 'docs'},
        {'file_path': 'docs/index.md', 'new_content': 'docs'}
    ]
    code_changes = [
        {'file_path': 'src/main.py', 'new_content': 'code'},
        {'file_path': 'README.md', 'new_content': 'docs'}
    ]
    config_changes = [
        {'file_path': 'package.json', 'new_content': '{}'}
    ]
    
    assert pr_service._is_documentation_only(doc_changes) is True
    assert pr_service._is_documentation_only(code_changes) is False
    assert pr_service._is_documentation_only(config_changes) is False

def test_validate_with_retries_no_sandbox(pr_service):
    # If code_execution is None, it should skip validation
    pr_service.code_execution = None
    repo = MagicMock()
    
    file_changes = [{'file_path': 'test.py', 'new_content': 'code'}]
    result = pr_service._validate_with_retries(repo, 'branch', file_changes)
    
    assert result['success'] is True

@patch('services.db.insert_job_log')
def test_execute_ai_task_doc_only(mock_insert_log, pr_service, mock_github_service):
    repo = MagicMock()
    repo.create_git_ref.return_value = None
    repo.get_branch.return_value = MagicMock()
    
    ai_result = {
        'analysis': 'Docs update',
        'file_changes': [{'file_path': 'DOCS.md', 'new_content': 'new docs', 'reason': 'update'}]
    }
    
    with patch.object(pr_service, '_is_documentation_only', return_value=True):
        # Mock PR creation on github_service
        mock_github_service.create_pull_request.return_value = {'success': True, 'pr_number': 1, 'pr_url': 'http://pr/1'}
        
        result = pr_service._execute_ai_task({
            'repo': repo,
            'issue_number': 1,
            'issue_title': 'Title',
            'issue_body': 'Body',
            'ai_result': ai_result,
        })
        
        assert result['pr_url'] == 'http://pr/1'
        # Verify no validation was attempted because it's doc-only
        assert not pr_service.code_execution.run_code_task.called

def test_process_pr_comment_success(pr_service, mock_ai_service, mock_github_service):
    repo = mock_github_service.get_repo.return_value
    pr = MagicMock()
    pr.head.ref = 'feature-branch'
    pr.base.ref = 'main'
    
    # Mock PR files
    mock_file = MagicMock()
    mock_file.filename = 'test.py'
    mock_file.status = 'modified'
    pr.get_files.return_value = [mock_file]
    
    repo.get_pull.return_value = pr
    mock_github_service.get_file_content.return_value = "print('old')"
    
    mock_ai_service.analyze_pr_comment.return_value = {
        'analysis': 'Comment fix',
        'file_changes': [{'file_path': 'test.py', 'new_content': 'print("fixed")', 'reason': 'fix'}]
    }
    
    with patch.object(pr_service, '_execute_ai_task', return_value={'pr_id': 1, 'pr_url': 'http://pr/1', 'success': True}) as mock_execute:
        # We need to mock _validate_with_retries too or satisfy its requirements
        with patch.object(pr_service, '_validate_with_retries', return_value={'success': True, 'file_changes': [{'file_path': 'test.py', 'new_content': 'print("fixed")', 'reason': 'fix'}]}):
            result = pr_service.process_pr_comment('owner/repo', 1, 'please fix this')
            
            assert result['success'] is True
