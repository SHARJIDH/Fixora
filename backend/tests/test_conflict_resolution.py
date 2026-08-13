import pytest
from unittest.mock import MagicMock, patch
from services.code_execution import CodeExecutionService, SandboxSession
from services.ai_service import AIService
from services.pr_service import PRService

@pytest.fixture
def mock_code_execution():
    service = MagicMock(spec=CodeExecutionService)
    # Default to no conflicts
    service.start_merge_check.return_value = {'has_conflicts': False}
    return service

@pytest.fixture
def mock_ai_service():
    service = MagicMock(spec=AIService)
    return service

@pytest.fixture
def mock_github_service():
    service = MagicMock()
    service.token = "test-token"
    return service

def test_start_merge_check():
    """Test start_merge_check detects conflicts and returns session."""
    with patch('services.code_execution.DockerSandboxService'):
        service = CodeExecutionService()

    with patch('subprocess.run') as mock_run:
        with patch('pathlib.Path.read_text', return_value="<<<<<<< HEAD\nMine\n=======\nTheirs\n>>>>>>>"):
            with patch('tempfile.mkdtemp', return_value="/tmp/sandbox-merge-123"):
                with patch('shutil.rmtree'):
                     with patch.object(service, '_clone_repo', return_value=MagicMock(success=True)):
                         # calls: fetch, config, config, merge, diff
                         mock_run.side_effect = [
                             MagicMock(returncode=0), # fetch
                             MagicMock(returncode=0), # git config
                             MagicMock(returncode=0), # git config
                             MagicMock(returncode=1), # merge (fail)
                             MagicMock(returncode=0, stdout="file1.txt"), # diff
                         ]

                         result = service.start_merge_check("http://repo", "feature", "main", "token")

                         assert result['has_conflicts'] is True
                         assert len(result['conflicts']) == 1
                         assert result['session'] is not None
                         assert result['session'].work_dir == "/tmp/sandbox-merge-123"

def test_complete_merge_resolution():
    """Test complete_merge_resolution commits and pushes."""
    with patch('services.code_execution.DockerSandboxService'):
        service = CodeExecutionService()

    session = SandboxSession(id="1", type="local_git", work_dir="/tmp/work", resource_id="none")
    resolved = [{'file_path': 'file1.txt', 'new_content': 'clean'}]

    with patch('subprocess.run') as mock_run:
        with patch('pathlib.Path.write_text'):
            with patch('os.path.exists', return_value=True):
                with patch('shutil.rmtree'):
                    mock_run.side_effect = [
                        MagicMock(returncode=0), # add
                        MagicMock(returncode=0), # commit
                        MagicMock(returncode=0), # push
                    ]

                    service.complete_merge_resolution(session, resolved)

                    # Verify calls
                    # args are list, check containment
                    assert mock_run.call_count == 3
                    assert "commit" in mock_run.call_args_list[1][0][0]
                    assert "push" in mock_run.call_args_list[2][0][0]

def test_resolve_merge_conflicts():
    """Test AI resolution of conflicts."""
    with patch('services.ai_service.OpenAI'):
        ai_service = AIService(api_key="test")

    # Mock OpenAI client
    mock_client = MagicMock()
    ai_service.client = mock_client

    mock_tool_call = MagicMock()
    mock_tool_call.function.name = "edit_file"
    mock_tool_call.function.arguments = '{"file_path": "file1.txt", "new_content": "Resolved Content", "reason": "Fixed conflict"}'

    mock_message = MagicMock()
    mock_message.tool_calls = [mock_tool_call]
    mock_client.chat.completions.create.return_value.choices = [MagicMock(message=mock_message)]

    conflicts = [{'file_path': 'file1.txt', 'content': '<<<<<<<'}]
    changes = ai_service.resolve_merge_conflicts(conflicts)

    assert len(changes) == 1
    assert changes[0]['new_content'] == "Resolved Content"

def test_pr_service_flow_with_conflicts(mock_github_service, mock_ai_service, mock_code_execution):
    """Test that PRService calls conflict resolution flow."""
    pr_service = PRService(mock_github_service, mock_ai_service, mock_code_execution)

    # Setup conflicts
    mock_session = MagicMock()
    mock_code_execution.start_merge_check.return_value = {
        'has_conflicts': True,
        'conflicts': [{'file_path': 'file1.txt', 'content': 'conflict'}],
        'session': mock_session
    }

    # Setup AI resolution
    mock_ai_service.resolve_merge_conflicts.return_value = [
        {'file_path': 'file1.txt', 'new_content': 'resolved', 'reason': 'fix'}
    ]

    repo = MagicMock()
    repo.default_branch = "main"
    repo.clone_url = "http://repo"

    pr_service._check_and_fix_conflicts(repo, "feature-branch")

    # Verify check was called with token
    mock_code_execution.start_merge_check.assert_called_with(
        repo_url="http://repo",
        source_branch="feature-branch",
        target_branch="main",
        github_token="test-token"
    )

    # Verify AI resolution
    mock_ai_service.resolve_merge_conflicts.assert_called()

    # Verify complete resolution was called
    mock_code_execution.complete_merge_resolution.assert_called_with(
        session=mock_session,
        resolved_files=[{'file_path': 'file1.txt', 'new_content': 'resolved', 'reason': 'fix'}]
    )
