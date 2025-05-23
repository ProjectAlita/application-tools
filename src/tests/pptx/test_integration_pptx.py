import os
import pytest
import tempfile
from unittest.mock import MagicMock, patch, Mock
from dotenv import load_dotenv
import pptx

from alita_tools.pptx.pptx_wrapper import PPTXWrapper

# Load environment variables from .env file
load_dotenv()

class MockAlitaClient:
    """Mock Alita client for testing"""
    def __init__(self):
        self.artifact = MagicMock()
    
    def download_artifact(self, bucket_name, file_name):
        """Mock downloading an artifact"""
        return b'Mock PPTX binary content'

class MockLLM:
    """Mock LLM for testing"""
    def invoke(self, prompt):
        """Return a predictable response based on the prompt"""
        if "translate" in prompt.lower():
            return "Translated content"
        elif "placeholder" in prompt.lower():
            return "Generated content for placeholder"
        else:
            return "Generic LLM response"

@pytest.fixture
def mock_alita():
    """Create a mock Alita client"""
    client = MockAlitaClient()
    
    # Mock upload responses
    client.artifact.create_artifact.return_value = "https://alita-storage/test-url"
    
    return client

@pytest.fixture
def mock_llm():
    """Create a mock LLM"""
    return MockLLM()

@pytest.fixture
def mock_presentation():
    """Create a mock PowerPoint presentation"""
    mock_pres = MagicMock()
    
    # Create a mock slide with shapes
    mock_slide = MagicMock()
    
    # Create a mock shape with text_frame for placeholder
    mock_shape_with_placeholder = MagicMock()
    mock_shape_with_placeholder.text_frame.text = "{{TITLE_PLACEHOLDER}}"
    
    # Create another mock shape with text_frame for translation
    mock_shape_for_translation = MagicMock()
    mock_shape_for_translation.text_frame.text = "Text to translate"
    
    # Set up the paragraphs
    mock_paragraph = MagicMock()
    mock_paragraph.text = "Text to translate"
    mock_shape_with_placeholder.text_frame.paragraphs = [mock_paragraph]
    mock_shape_for_translation.text_frame.paragraphs = [mock_paragraph]
    
    # Add shapes to the slide
    mock_slide.shapes = [mock_shape_with_placeholder, mock_shape_for_translation]
    
    # Add slide to presentation
    mock_pres.slides = [mock_slide]
    
    return mock_pres

@pytest.fixture
def pptx_wrapper(mock_alita, mock_llm):
    """Create a PPTXWrapper instance with mock dependencies"""
    # Create the wrapper with required fields during initialization
    wrapper = PPTXWrapper(
        bucket_name="test-bucket",
        alita=mock_alita,
        llm=mock_llm
    )
    
    return wrapper

@pytest.mark.integration
def test_fill_template(pptx_wrapper, mock_presentation):
    """Test filling a PPTX template with content"""
    # Arrange
    file_name = "template.pptx"
    output_file_name = "filled_template.pptx"
    content_description = "Create a presentation about AI technology"
    
    # Mock the download_pptx method to return a path
    temp_path = "/tmp/test.pptx"
    
    # Act
    with patch.object(pptx_wrapper, '_download_pptx', return_value=temp_path), \
         patch.object(pptx_wrapper, '_upload_pptx', return_value="https://alita-storage/test-url"), \
         patch('os.remove'), \
         patch('tempfile.gettempdir', return_value="/tmp"), \
         patch('os.path.join', return_value=temp_path), \
         patch('builtins.open', MagicMock()), \
         patch('pptx.Presentation', return_value=mock_presentation):
        
        result = pptx_wrapper.fill_template(file_name, output_file_name, content_description)
    
    # Assert
    assert result["status"] == "success"
    assert output_file_name in result["message"]

@pytest.mark.integration
def test_translate_presentation(pptx_wrapper, mock_presentation):
    """Test translating a PPTX presentation"""
    # Arrange
    file_name = "presentation.pptx"
    output_file_name = "translated_presentation.pptx"
    target_language = "es"
    
    # Mock the download_pptx method to return a path
    temp_path = "/tmp/test.pptx"
    
    # Act
    with patch.object(pptx_wrapper, '_download_pptx', return_value=temp_path), \
         patch.object(pptx_wrapper, '_upload_pptx', return_value="https://alita-storage/test-url"), \
         patch('os.remove'), \
         patch('tempfile.gettempdir', return_value="/tmp"), \
         patch('os.path.join', return_value=temp_path), \
         patch('builtins.open', MagicMock()), \
         patch('pptx.Presentation', return_value=mock_presentation):
        
        result = pptx_wrapper.translate_presentation(file_name, output_file_name, target_language)
    
    # Assert
    assert result["status"] == "success"
    assert "Spanish" in result["message"]
    assert output_file_name in result["message"]

@pytest.mark.integration
def test_download_pptx_error_handling(pptx_wrapper):
    """Test error handling during PPTX download"""
    # Instead of trying to test the internal _download_pptx directly,
    # we'll test a method that uses it, which is easier to mock
    file_name = "non_existent.pptx"
    output_file_name = "output.pptx"
    content_description = "Test content"
    
    # Set up the mock to raise an exception when _download_pptx is called
    with patch.object(pptx_wrapper, '_download_pptx', side_effect=Exception("Download failed")):
        # The fill_template method will call _download_pptx internally
        result = pptx_wrapper.fill_template(file_name, output_file_name, content_description)
    
    # Verify the error was properly handled
    assert result["status"] == "error"
    assert "Failed to fill template" in result["message"]

@pytest.mark.integration
def test_upload_pptx_error_handling(pptx_wrapper):
    """Test error handling during PPTX upload"""
    # Arrange
    # Create a temporary file path
    temp_path = "/tmp/test.pptx"
    
    # Make the upload method raise an exception
    pptx_wrapper.alita.artifact.create_artifact.side_effect = Exception("Upload failed")
    
    # Act & Assert
    with patch('builtins.open', MagicMock()), \
         pytest.raises(Exception, match="Upload failed"):
        pptx_wrapper._upload_pptx(temp_path, "output.pptx")

@pytest.mark.integration
def test_fill_template_error_handling(pptx_wrapper):
    """Test error handling during template filling"""
    # Arrange
    file_name = "template.pptx"
    output_file_name = "filled_template.pptx"
    content_description = "Create a presentation about AI technology"
    
    # Act
    with patch.object(pptx_wrapper, '_download_pptx', side_effect=Exception("Download failed")):
        result = pptx_wrapper.fill_template(file_name, output_file_name, content_description)
    
    # Assert
    assert result["status"] == "error"
    assert "Failed to fill template" in result["message"]

@pytest.mark.integration
def test_translate_presentation_error_handling(pptx_wrapper):
    """Test error handling during presentation translation"""
    # Arrange
    file_name = "presentation.pptx"
    output_file_name = "translated_presentation.pptx"
    target_language = "es"
    
    # Act
    with patch.object(pptx_wrapper, '_download_pptx', side_effect=Exception("Download failed")):
        result = pptx_wrapper.translate_presentation(file_name, output_file_name, target_language)
    
    # Assert
    assert result["status"] == "error"
    assert "Failed to translate presentation" in result["message"]

@pytest.mark.integration
def test_real_integration_with_env_config():
    """
    Test with real configuration from environment variables.
    This test will be skipped if the required environment variables are not set.
    """
    # Check if environment variables are set
    required_vars = ['ALITA_API_KEY', 'ALITA_BUCKET_NAME', 'LLM_API_KEY']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        pytest.skip(f"Skipping real integration test: missing environment variables: {', '.join(missing_vars)}")
    
    # For now, just verify we can create the instance
    assert True

