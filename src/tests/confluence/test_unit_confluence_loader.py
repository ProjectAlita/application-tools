import pytest
from unittest.mock import MagicMock, patch
import io
from PIL import Image
import base64

from alita_tools.confluence.loader import AlitaConfluenceLoader
from langchain_core.messages import HumanMessage


@pytest.mark.unit
@pytest.mark.confluence
class TestAlitaConfluenceLoader:
    
    @pytest.fixture
    def mock_confluence_client(self):
        """Create a mock Confluence client for testing."""
        mock_client = MagicMock()
        return mock_client
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM for testing."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="This is an image description")
        return mock_llm
    
    @pytest.fixture
    def confluence_loader(self, mock_confluence_client, mock_llm):
        """Create an AlitaConfluenceLoader with mocked dependencies."""
        return AlitaConfluenceLoader(
            confluence_client=mock_confluence_client,
            llm=mock_llm,
            bins_with_llm=True,
            url="https://confluence.example.com",
            space_key="TEST"
        )
    
    @pytest.mark.positive
    def test_init(self, confluence_loader, mock_confluence_client, mock_llm):
        """Test initialization of AlitaConfluenceLoader."""
        assert confluence_loader.confluence == mock_confluence_client
        assert confluence_loader.llm == mock_llm
        assert confluence_loader.bins_with_llm is True
        assert confluence_loader.base_url == "https://confluence.example.com"
        assert confluence_loader.space_key == "TEST"
    
    @pytest.mark.positive
    @patch('alita_tools.confluence.loader.Image')
    def test_process_image_with_llm(self, mock_pil_image, confluence_loader, mock_llm):
        """Test processing an image with LLM."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'fake_image_data'
        
        # Setup mock request
        confluence_loader.confluence.request.return_value = mock_response
        
        # Setup mock PIL Image
        mock_image = MagicMock()
        mock_pil_image.open.return_value = mock_image
        
        # Call the method
        result = confluence_loader.process_image("https://confluence.example.com/download/attachments/12345/test.png")
        
        # Verify the result
        assert result == "This is an image description"
        confluence_loader.confluence.request.assert_called_once_with(
            path="https://confluence.example.com/download/attachments/12345/test.png", 
            absolute=True
        )
        mock_llm.invoke.assert_called_once()
    
    @pytest.mark.negative
    def test_process_image_request_error(self, confluence_loader):
        """Test processing an image with a request error."""
        # Setup mock response with error
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.content = b''
        
        # Setup mock request
        confluence_loader.confluence.request.return_value = mock_response
        
        # Call the method
        result = confluence_loader.process_image("https://confluence.example.com/download/attachments/12345/test.png")
        
        # Verify the result
        assert result == ""
        confluence_loader.confluence.request.assert_called_once()
        confluence_loader.llm.invoke.assert_not_called()
    
    @pytest.mark.positive
    @patch('alita_tools.confluence.loader.convert_from_bytes')
    def test_process_pdf_with_llm(self, mock_convert_from_bytes, confluence_loader, mock_llm):
        """Test processing a PDF with LLM."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'fake_pdf_data'
        
        # Setup mock request
        confluence_loader.confluence.request.return_value = mock_response
        
        # Setup mock PDF conversion
        mock_image1 = MagicMock()
        mock_image2 = MagicMock()
        mock_convert_from_bytes.return_value = [mock_image1, mock_image2]
        
        # Setup mock LLM responses for each page
        mock_llm.invoke.side_effect = [
            MagicMock(content="Description of page 1"),
            MagicMock(content="Description of page 2")
        ]
        
        # Call the method
        result = confluence_loader.process_pdf("https://confluence.example.com/download/attachments/12345/test.pdf")
        
        # Verify the result
        assert "Page 1:" in result
        assert "Description of page 1" in result
        assert "Page 2:" in result
        assert "Description of page 2" in result
        confluence_loader.confluence.request.assert_called_once()
        assert mock_llm.invoke.call_count == 2
        mock_convert_from_bytes.assert_called_once_with(b'fake_pdf_data')
    
    @pytest.mark.negative
    def test_process_pdf_conversion_error(self, confluence_loader):
        """Test processing a PDF with conversion error."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'fake_pdf_data'
        
        # Setup mock request
        confluence_loader.confluence.request.return_value = mock_response
        
        # Setup mock PDF conversion to raise error
        with patch('alita_tools.confluence.loader.convert_from_bytes', side_effect=ValueError("Invalid PDF")):
            # Call the method
            result = confluence_loader.process_pdf("https://confluence.example.com/download/attachments/12345/test.pdf")
            
            # Verify the result
            assert result == ""
            confluence_loader.confluence.request.assert_called_once()
            confluence_loader.llm.invoke.assert_not_called()
    
    @pytest.mark.positive
    @patch('alita_tools.confluence.loader.svg2rlg')
    @patch('alita_tools.confluence.loader.renderPM')
    @patch('alita_tools.confluence.loader.Image')
    def test_process_svg_with_llm(self, mock_pil_image, mock_render_pm, mock_svg2rlg, confluence_loader, mock_llm):
        """Test processing an SVG with LLM."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'<svg>fake_svg_data</svg>'
        
        # Setup mock request
        confluence_loader.confluence.request.return_value = mock_response
        
        # Setup mock SVG conversion
        mock_drawing = MagicMock()
        mock_svg2rlg.return_value = mock_drawing
        
        # Setup mock PIL Image
        mock_image = MagicMock()
        mock_pil_image.open.return_value = mock_image
        
        # Call the method
        result = confluence_loader.process_svg("https://confluence.example.com/download/attachments/12345/test.svg")
        
        # Verify the result
        assert result == "This is an image description"
        confluence_loader.confluence.request.assert_called_once()
        mock_svg2rlg.assert_called_once()
        mock_render_pm.drawToFile.assert_called_once()
        mock_llm.invoke.assert_called_once()
    
    @pytest.mark.positive
    @patch('alita_tools.confluence.loader.image_to_byte_array')
    @patch('alita_tools.confluence.loader.bytes_to_base64')
    def test_perform_llm_prediction_for_image(self, mock_bytes_to_base64, mock_image_to_byte_array, confluence_loader, mock_llm):
        """Test the __perform_llm_prediction_for_image method."""
        # Setup mocks
        mock_image = MagicMock()
        mock_image_to_byte_array.return_value = b'fake_image_bytes'
        mock_bytes_to_base64.return_value = 'fake_base64_string'
        
        # Call the method
        result = confluence_loader._AlitaConfluenceLoader__perform_llm_prediction_for_image(mock_image)
        
        # Verify the result
        assert result == "This is an image description"
        mock_image_to_byte_array.assert_called_once_with(mock_image)
        mock_bytes_to_base64.assert_called_once_with(b'fake_image_bytes')
        mock_llm.invoke.assert_called_once()
        
        # Verify the LLM was called with the correct arguments
        call_args = mock_llm.invoke.call_args[0][0]
        assert isinstance(call_args[0], HumanMessage)
        assert len(call_args[0].content) == 2
        assert call_args[0].content[0]['type'] == 'text'
        assert call_args[0].content[1]['type'] == 'image_url'
        assert 'fake_base64_string' in call_args[0].content[1]['image_url']['url']
