import pytest
from unittest.mock import MagicMock, patch
import io
import base64

from alita_tools.confluence.utils import bytes_to_base64, path_to_base64, image_to_byte_array


@pytest.mark.unit
@pytest.mark.confluence
class TestConfluenceUtils:
    
    @pytest.mark.positive
    def test_bytes_to_base64(self):
        """Test bytes_to_base64 function."""
        test_bytes = b'test data'
        expected_base64 = base64.b64encode(test_bytes).decode('utf-8')
        
        result = bytes_to_base64(test_bytes)
        
        assert result == expected_base64
    
    @pytest.mark.positive
    @patch('builtins.open', new_callable=MagicMock)
    def test_path_to_base64(self, mock_open):
        """Test path_to_base64 function."""
        # Setup mock file
        mock_file = MagicMock()
        mock_file.read.return_value = b'test file content'
        mock_open.return_value.__enter__.return_value = mock_file
        
        # Expected result
        expected_base64 = base64.b64encode(b'test file content').decode('utf-8')
        
        # Call the function
        result = path_to_base64('test/path.png')
        
        # Verify the result
        assert result == expected_base64
        mock_open.assert_called_once_with('test/path.png', 'rb')
        mock_file.read.assert_called_once()
    
    @pytest.mark.positive
    def test_image_to_byte_array(self):
        """Test image_to_byte_array function."""
        # Create a mock PIL Image
        mock_image = MagicMock()
        
        # Mock the save method to capture the BytesIO object
        def mock_save(buffer, format):
            buffer.write(b'fake_png_data')
        
        mock_image.save.side_effect = mock_save
        
        # Call the function
        result = image_to_byte_array(mock_image)
        
        # Verify the result
        assert result == b'fake_png_data'
        mock_image.save.assert_called_once()
        
        # Verify save was called with the right format
        args, kwargs = mock_image.save.call_args
        assert kwargs.get('format') == 'PNG'
