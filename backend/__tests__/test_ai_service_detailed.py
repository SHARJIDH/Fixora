import pytest
from unittest.mock import Mock, patch
from services.ai_service import AIService

@pytest.fixture
def mock_openai():
    with patch('services.ai_service.OpenAI') as mock:
        yield mock

def create_mock_response(content, tool_calls=None):
    mock_message = Mock()
    mock_message.content = content
    mock_message.tool_calls = tool_calls
    
    mock_choice = Mock()
    mock_choice.message = mock_message
    
    mock_response = Mock()
    mock_response.choices = [mock_choice]
    return mock_response

def test_analyze_issue_with_multiple_tool_calls(mock_openai):
    mock_client = mock_openai.return_value
    
    tool_call1 = Mock()
    tool_call1.function.name = 'edit_file'
    tool_call1.function.arguments = '''
    {
        "file_path": "a.py",
        "new_content": "print('a')",
        "reason": "reason a"
    }
    '''
    
    tool_call2 = Mock()
    tool_call2.function.name = 'edit_file'
    tool_call2.function.arguments = '''
    {
        "file_path": "b.py",
        "new_content": "print('b')",
        "reason": "reason b"
    }
    '''
    
    mock_client.chat.completions.create.return_value = create_mock_response(
        "I will edit two files.",
        tool_calls=[tool_call1, tool_call2]
    )
    
    service = AIService(api_key='test-key')
    result = service.analyze_issue_and_plan_changes("Title", "Body", "Comment", [])
    
    assert len(result['file_changes']) == 2
    assert result['file_changes'][0]['file_path'] == 'a.py'
    assert result['file_changes'][1]['file_path'] == 'b.py'

def test_analyze_issue_with_invalid_json_tool_arguments(mock_openai):
    mock_client = mock_openai.return_value
    
    tool_call = Mock()
    tool_call.function.name = 'edit_file'
    tool_call.function.arguments = '{ invalid json }'
    
    mock_client.chat.completions.create.return_value = create_mock_response(
        "I tried to edit but failed json.",
        tool_calls=[tool_call]
    )
    
    service = AIService(api_key='test-key')
    result = service.analyze_issue_and_plan_changes("Title", "Body", "Comment", [])
    
    # Should skip invalid tool calls
    assert len(result['file_changes']) == 0
    assert "Reached maximum conversation turns" in result['analysis']

def test_analyze_issue_no_content_no_tools(mock_openai):
    mock_client = mock_openai.return_value
    mock_client.chat.completions.create.return_value = create_mock_response(None, tool_calls=None)
    
    service = AIService(api_key='test-key')
    result = service.analyze_issue_and_plan_changes("Title", "Body", "Comment", [])
    
    assert "AI provided analysis" in result['analysis']
    assert result['file_changes'] == []

def test_analyze_issue_unexpected_tool_name(mock_openai):
    mock_client = mock_openai.return_value
    
    tool_call = Mock()
    tool_call.function.name = 'unknown_tool'
    tool_call.function.arguments = '{"some": "data"}'
    
    mock_client.chat.completions.create.return_value = create_mock_response(
        "Called wrong tool.",
        tool_calls=[tool_call]
    )
    
    service = AIService(api_key='test-key')
    result = service.analyze_issue_and_plan_changes("Title", "Body", "Comment", [])
    
    assert len(result['file_changes']) == 0
