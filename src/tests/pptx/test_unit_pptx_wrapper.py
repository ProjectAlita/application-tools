import pytest
from unittest.mock import MagicMock, patch, mock_open, call
import tempfile
import os
from io import BytesIO
from pydantic import BaseModel

from alita_tools.pptx.pptx_wrapper import PPTXWrapper, INTRO_PROMPT

@pytest.mark.unit
@pytest.mark.pptx
class TestPPTXWrapper:
    """Test cases for PPTXWrapper class"""

    @pytest.fixture
    def mock_alita_client(self):
        """Mock Alita client for testing"""
        mock_client = MagicMock()
        mock_client.download_artifact.return_value = b"mock pptx data"
        mock_client.create_artifact.return_value = "http://mock-url.com/file.pptx"
        return mock_client

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM for testing"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Mock LLM response"
        mock_response.model_dump.return_value = {"placeholder_0": "Generated content"}
        mock_llm.invoke.return_value = mock_response
        mock_llm.with_structured_output.return_value = mock_llm
        return mock_llm

    @pytest.fixture
    def pptx_wrapper(self, mock_alita_client, mock_llm):
        """Create PPTXWrapper instance for testing"""
        return PPTXWrapper(
            bucket_name="test-bucket",
            alita=mock_alita_client,
            llm=mock_llm
        )

    @pytest.mark.positive
    def test_init(self, mock_alita_client, mock_llm):
        """Test PPTXWrapper initialization"""
        wrapper = PPTXWrapper(
            bucket_name="test-bucket",
            alita=mock_alita_client,
            llm=mock_llm
        )

        assert wrapper.bucket_name == "test-bucket"
        assert wrapper.alita == mock_alita_client
        assert wrapper.llm == mock_llm

    @pytest.mark.positive
    def test_bytes_content_with_bytes(self, pptx_wrapper):
        """Test _bytes_content with bytes input"""
        test_bytes = b"test content"
        result = pptx_wrapper._bytes_content(test_bytes)
        assert result == test_bytes

    @pytest.mark.positive
    def test_bytes_content_with_string(self, pptx_wrapper):
        """Test _bytes_content with string input"""
        test_string = "test content"
        result = pptx_wrapper._bytes_content(test_string)
        assert result == test_string.encode('utf-8')

    @pytest.mark.positive
    def test_get_success(self, pptx_wrapper):
        """Test successful get operation"""
        # The wrapper uses self.alita directly, not self.client
        pptx_wrapper.alita.download_artifact.return_value = b"test content"

        with patch('chardet.detect', return_value={'encoding': 'utf-8'}):
            result = pptx_wrapper.get("test.pptx")
            assert result == "test content"

    @pytest.mark.negative
    def test_get_empty_file(self, pptx_wrapper):
        """Test get operation with empty file"""
        pptx_wrapper.alita.download_artifact.return_value = b""

        result = pptx_wrapper.get("empty.pptx")
        assert result == ""

    @pytest.mark.negative
    def test_get_error_response(self, pptx_wrapper):
        """Test get operation with error response"""
        pptx_wrapper.alita.download_artifact.return_value = {
            'error': 'File not found',
            'content': 'Additional info'
        }

        result = pptx_wrapper.get("nonexistent.pptx")
        assert "File not found" in result
        assert "Additional info" in result

    @pytest.mark.positive
    @patch('tempfile.gettempdir')
    @patch('builtins.open', new_callable=mock_open)
    def test_download_pptx_success(self, mock_file, mock_tempdir, pptx_wrapper):
        """Test successful PPTX download"""
        mock_tempdir.return_value = "/tmp"
        pptx_wrapper.alita.download_artifact.return_value = b"pptx data"

        result = pptx_wrapper._download_pptx("test.pptx")

        assert result == "/tmp/test.pptx"
        pptx_wrapper.alita.download_artifact.assert_called_once_with("test-bucket", "test.pptx")
        mock_file.assert_called_once_with("/tmp/test.pptx", 'wb')

    @pytest.mark.negative
    def test_download_pptx_error(self, pptx_wrapper):
        """Test PPTX download with error response"""
        pptx_wrapper.alita.download_artifact.return_value = {
            'error': 'Download failed',
            'content': None
        }

        with pytest.raises(NameError, match="Download failed"):
            pptx_wrapper._download_pptx("test.pptx")

    @pytest.mark.positive
    @patch('builtins.open', new_callable=mock_open, read_data=b"pptx data")
    def test_upload_pptx_success(self, mock_file, pptx_wrapper):
        """Test successful PPTX upload"""
        pptx_wrapper.alita.create_artifact.return_value = "http://mock-url.com/test.pptx"

        result = pptx_wrapper._upload_pptx("/tmp/test.pptx", "test.pptx")

        assert result == "http://mock-url.com/test.pptx"
        pptx_wrapper.alita.create_artifact.assert_called_once_with(
            bucket_name="test-bucket",
            artifact_name="test.pptx",
            artifact_data=b"pptx data"
        )

    @pytest.mark.positive
    def test_get_structured_output_llm(self, pptx_wrapper):
        """Test _get_structured_output_llm method"""
        mock_model = MagicMock()

        result = pptx_wrapper._get_structured_output_llm(mock_model)

        pptx_wrapper.llm.with_structured_output.assert_called_once_with(mock_model)
        assert result == pptx_wrapper.llm

    @pytest.mark.positive
    def test_create_slide_model(self, pptx_wrapper):
        """Test _create_slide_model method"""
        placeholders = ["{{title}}", "{{content}}"]

        model_class = pptx_wrapper._create_slide_model(placeholders)

        assert issubclass(model_class, BaseModel)
        assert 'placeholder_0' in model_class.model_fields
        assert 'placeholder_1' in model_class.model_fields

    @pytest.mark.positive
    @patch('pptx.Presentation')
    @patch('tempfile.gettempdir')
    @patch('os.remove')
    def test_fill_template_success(self, mock_remove, mock_tempdir, mock_pptx, pptx_wrapper):
        """Test successful template filling"""
        mock_tempdir.return_value = "/tmp"

        # Mock presentation and slides
        mock_presentation = MagicMock()
        mock_slide = MagicMock()
        mock_shape = MagicMock()
        mock_text_frame = MagicMock()
        mock_paragraph = MagicMock()

        mock_text_frame.text = "{{placeholder}}"
        mock_text_frame.paragraphs = [mock_paragraph]
        mock_text_frame.clear = MagicMock()
        mock_shape.text_frame = mock_text_frame
        mock_slide.shapes = [mock_shape]
        mock_presentation.slides = [mock_slide]
        mock_pptx.return_value = mock_presentation

        # Mock LLM response
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {"placeholder_0": "Generated content"}
        pptx_wrapper.llm.invoke.return_value = mock_response
        pptx_wrapper._upload_pptx = MagicMock(return_value="http://output-url.com")

        with patch.object(pptx_wrapper, '_download_pptx', return_value="/tmp/input.pptx"):
            result = pptx_wrapper.fill_template(
                "input.pptx",
                "output.pptx",
                "Fill with content"
            )

        assert result["status"] == "success"
        assert "output.pptx" in result["message"]
        assert result["url"] == "http://output-url.com"

    @pytest.mark.positive
    @patch('pptx.Presentation')
    @patch('tempfile.gettempdir')
    @patch('os.remove')
    def test_translate_presentation_success(self, mock_remove, mock_tempdir, mock_pptx, pptx_wrapper):
        """Test successful presentation translation"""
        mock_tempdir.return_value = "/tmp"

        # Mock presentation and slides
        mock_presentation = MagicMock()
        mock_slide = MagicMock()
        mock_shape = MagicMock()
        mock_text_frame = MagicMock()
        mock_paragraph = MagicMock()

        mock_text_frame.text = "Hello World"
        mock_paragraph.text = "Hello World"
        mock_text_frame.paragraphs = [mock_paragraph]
        mock_shape.text_frame = mock_text_frame
        mock_slide.shapes = [mock_shape]
        mock_presentation.slides = [mock_slide]
        mock_pptx.return_value = mock_presentation

        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = "Hola Mundo"
        pptx_wrapper.llm.invoke.return_value = mock_response
        pptx_wrapper._upload_pptx = MagicMock(return_value="http://output-url.com")

        with patch.object(pptx_wrapper, '_download_pptx', return_value="/tmp/input.pptx"):
            result = pptx_wrapper.translate_presentation(
                "input.pptx",
                "output.pptx",
                "es"
            )

        assert result["status"] == "success"
        assert "Spanish" in result["message"]
        assert result["url"] == "http://output-url.com"

    @pytest.mark.negative
    @patch('pptx.Presentation')
    def test_fill_template_exception(self, mock_pptx, pptx_wrapper):
        """Test fill_template with exception"""
        mock_pptx.side_effect = Exception("PPTX error")

        with patch.object(pptx_wrapper, '_download_pptx', return_value="/tmp/input.pptx"):
            result = pptx_wrapper.fill_template(
                "input.pptx",
                "output.pptx",
                "Fill with content"
            )

        assert result["status"] == "error"
        assert "Failed to fill template" in result["message"]

    @pytest.mark.negative
    @patch('pptx.Presentation')
    def test_translate_presentation_exception(self, mock_pptx, pptx_wrapper):
        """Test translate_presentation with exception"""
        mock_pptx.side_effect = Exception("PPTX error")

        with patch.object(pptx_wrapper, '_download_pptx', return_value="/tmp/input.pptx"):
            result = pptx_wrapper.translate_presentation(
                "input.pptx",
                "output.pptx",
                "es"
            )

        assert result["status"] == "error"
        assert "Failed to translate presentation" in result["message"]

    @pytest.mark.positive
    def test_get_available_tools(self, pptx_wrapper):
        """Test get_available_tools method"""
        tools = pptx_wrapper.get_available_tools()

        assert isinstance(tools, list)
        assert len(tools) == 2

        tool_names = [tool["name"] for tool in tools]
        assert "fill_template" in tool_names
        assert "translate_presentation" in tool_names

        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "ref" in tool
            assert "args_schema" in tool
            assert callable(tool["ref"])

    @pytest.mark.skip(reason="PDF processing requires PyMuPDF and PIL dependencies which may not be available in test environment")
    def test_fill_template_with_pdf(self, pptx_wrapper):
        """Test fill_template with PDF file processing - skipped due to dependencies"""
        pass

    @pytest.mark.positive
    def test_translate_presentation_with_table(self, pptx_wrapper):
        """Test translate_presentation with table content"""
        with patch('pptx.Presentation') as mock_pptx:
            # Mock presentation with table
            mock_presentation = MagicMock()
            mock_slide = MagicMock()
            mock_shape = MagicMock()
            mock_table = MagicMock()
            mock_row = MagicMock()
            mock_cell = MagicMock()
            mock_text_frame = MagicMock()
            mock_paragraph = MagicMock()

            mock_paragraph.text = "Table content"
            mock_text_frame.text = "Table content"
            mock_text_frame.paragraphs = [mock_paragraph]
            mock_cell.text_frame = mock_text_frame
            mock_row.cells = [mock_cell]
            mock_table.rows = [mock_row]
            mock_shape.table = mock_table
            mock_shape.text_frame = None  # No text frame on table shape itself
            mock_slide.shapes = [mock_shape]
            mock_presentation.slides = [mock_slide]
            mock_pptx.return_value = mock_presentation

            # Mock LLM response
            mock_response = MagicMock()
            mock_response.content = "Contenido de tabla"
            pptx_wrapper.llm.invoke.return_value = mock_response
            pptx_wrapper._upload_pptx = MagicMock(return_value="http://output-url.com")

            with patch.object(pptx_wrapper, '_download_pptx', return_value="/tmp/input.pptx"):
                with patch('tempfile.gettempdir', return_value="/tmp"):
                    with patch('os.remove'):
                        result = pptx_wrapper.translate_presentation(
                            "input.pptx",
                            "output.pptx",
                            "es"
                        )

            assert result["status"] == "success"
            assert mock_paragraph.text == "Contenido de tabla"

    @pytest.mark.positive
    def test_language_code_mapping(self, pptx_wrapper):
        """Test language code to name mapping in translate_presentation"""
        with patch('pptx.Presentation') as mock_pptx:
            mock_presentation = MagicMock()
            mock_presentation.slides = []  # Empty slides for simplicity
            mock_pptx.return_value = mock_presentation
            pptx_wrapper._upload_pptx = MagicMock(return_value="http://output-url.com")

            with patch.object(pptx_wrapper, '_download_pptx', return_value="/tmp/input.pptx"):
                with patch('tempfile.gettempdir', return_value="/tmp"):
                    with patch('os.remove'):
                        # Test known language code
                        result = pptx_wrapper.translate_presentation(
                            "input.pptx",
                            "output.pptx",
                            "ua"
                        )

                        assert result["status"] == "success"
                        assert "Ukrainian" in result["message"]

                        # Test unknown language code
                        result = pptx_wrapper.translate_presentation(
                            "input.pptx",
                            "output.pptx",
                            "xyz"
                        )

                        assert result["status"] == "success"
                        # Should use the code itself when not found in mapping
