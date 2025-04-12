import io
import os
import logging
import fitz  # PyMuPDF
from PIL import Image
import numpy as np
from typing import Optional, Any, Dict, List
import tempfile
import subprocess


from pydantic import BaseModel, Field, model_validator
from langchain_core.tools import ToolException

from ..elitea_base import BaseToolApiWrapper
from ..utils import create_pydantic_model

logger = logging.getLogger(__name__)

MIME_TO_EXTENSION = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/gif": [".gif"],
    "image/bmp": [".bmp"],
    "image/tiff": [".tiff", ".tif"],
    "application/pdf": [".pdf"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx", '.doc'],
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx", '.ppt']
}

# Helper to map Office extensions to their MIME types for easier lookup
OFFICE_EXTENSIONS = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation"
}

IMAGE_OCR_PROMPT_TEMPLATE = """Please extract all text from the image."""


# Models for tool arguments
class RecognizeArgs(BaseModel):
    file_path: str = Field(..., description="Path to the specific image, PDF, DOCX, or PPTX file to process")
    prompt: Optional[str] = Field(None, description="Optional prompt to guide OCR extraction")
    prepare_text: Optional[bool] = Field(False, description="Enhance image contrast and clarity before OCR (for images only)")

class RecognizeAllArgs(BaseModel):
    prompt: Optional[str] = Field(None, description="Optional prompt to guide OCR extraction")
    prepare_text: Optional[bool] = Field(False, description="Enhance image contrast and clarity before OCR")

class PrepareTextArgs(BaseModel):
    image_path: str = Field(..., description="Path to the image file to enhance")

class PdfToImagesArgs(BaseModel):
    pdf_path: str = Field(..., description="Path to the PDF file to convert to images")

class PdfsToImagesArgs(BaseModel):
    prepare_text: Optional[bool] = Field(False, description="Enhance image contrast and clarity after conversion")

class ProcessPdfArgs(BaseModel):
    prompt: Optional[str] = Field(None, description="Optional prompt to guide OCR extraction")
    prepare_text: Optional[bool] = Field(False, description="Enhance image contrast and clarity before OCR")

class FolderPathArgs(BaseModel):
    artifacts_folder: Optional[str] = Field(None, description="Path to the artifacts folder containing images or PDFs")

class ConvertOfficeArgs(BaseModel):
    file_path: str = Field(..., description="Path to the Office document (DOCX or PPTX) to convert to PDF")


def _check_libreoffice_installed() -> bool:
    """Check if LibreOffice is installed on the system"""
    try:
        # Try to run a simple command to check if LibreOffice is available
        subprocess.run(["libreoffice", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        return True
    except FileNotFoundError:
        return False


class OCRApiWrapper(BaseToolApiWrapper):
    """Wrapper for OCR tools that can use either LLM-based vision capabilities or tesseract"""
    
    llm: Any = None
    struct_llm: Any = None
    alita: Any = None
    artifacts_folder: str = ""
    tesseract_settings: Dict[str, Any] = {}
    structured_output: bool = False
    expected_fields: Dict[str, Any] = {}
    
    
    @model_validator(mode='after')
    def validate_settings(self):
        """Validate that either LLM or tesseract is properly configured"""
        # self.artifact = self.alita.artifact(self.artifacts_folder)
        if self.structured_output and len(self.expected_fields.keys()) > 0:
            stuct_model = create_pydantic_model(f"OCR_{self.artifacts_folder}_Output", self.expected_fields)
            self.struct_llm = self.llm.with_structured_output(stuct_model)
        else:
            self.struct_llm = self.llm
        
        return self
    
    def _process_images_with_llm(self, images: List[str] | str, prompt: Optional[str] = None) -> Any:
        """
        Process one or more images with the LLM.
        
        Args:
            images: Either a single image path or a list of image paths to process
            prompt: Optional prompt to guide OCR extraction
            
        Returns:
            The LLM response (either structured or plain text)
        """
        if not self.struct_llm:
            raise ToolException("LLM not configured for OCR processing")
            
        try:
            import base64
            
            # Convert single image to list for uniform processing
            if isinstance(images, str):
                images = [images]
            
            # Set default prompt if not provided
            if not prompt:
                prompt = IMAGE_OCR_PROMPT_TEMPLATE
            
            # Prepare content array with text prompt and all images
            content = [{"type": "text", "text": prompt}]
            
            # Add all images to the message
            for img_path in images:
                # Download the image
                image_data = self.alita.download_artifact(self.artifacts_folder, img_path)
                
                # Determine MIME type based on file extension
                file_extension = os.path.splitext(img_path.lower())[1]
                mime_type = "image/jpeg"  # Default
                
                # Find the correct MIME type for this extension
                for mime, extensions in MIME_TO_EXTENSION.items():
                    if file_extension in extensions:
                        mime_type = mime
                        break
                
                # Encode image to base64
                base64_image = base64.b64encode(image_data).decode('utf-8')
                
                # Add to content
                content.append({
                    "type": "image_url", 
                    "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}
                })
            
            # Create the messages array with user role
            messages = [{"role": "user", "content": content}]
            
            # Process with LLM
            logger.info(f"Processing {len(images)} image(s) with LLM")
            response = self.struct_llm.invoke(messages)
            
            if self.structured_output:
                return response.model_dump()
            return response.content
                
        except Exception as e:
            raise ToolException(f"Error processing image(s) with LLM: {e}")

    def _process_with_tesseract(self, image_path: str) -> str:
        """Process image with Tesseract OCR"""
        try:
            import pytesseract
            from PIL import Image
            
            # Get data directly without context manager
            data = self.alita.download_artifact(self.artifacts_folder, image_path)
            image = Image.open(io.BytesIO(data))
            
            # Apply any tesseract settings
            config = self.tesseract_settings.get('config', '')
            lang = self.tesseract_settings.get('lang', 'eng')
            return pytesseract.image_to_string(image, lang=lang, config=config)
        except Exception as e:
            raise ToolException(f"Error processing image with Tesseract: {e}")
    
    def recognize(self, file_path: str, prompt: Optional[str] = None, prepare_text: Optional[bool] = False) -> Dict[str, Any]:
        """
        Recognize text in a specific image, PDF, or Office document.
        Uses LLM if configured, otherwise falls back to Tesseract OCR.
        
        Args:
            file_path: Path to the image, PDF, DOCX, or PPTX file to process
            prompt: Optional prompt to guide OCR extraction
            prepare_text: Whether to enhance image contrast before OCR (for images only)
            
        Returns:
            Dictionary containing the extracted text and other metadata
        """
        # Check if the file exists
        file_exists = False
        for f in self.alita.list_artifacts(self.artifacts_folder).get('rows', []):
            if f['name'] == file_path:
                file_exists = True
                break
                
        if not file_exists:
            raise ToolException(f"File not found: {file_path} in {self.artifacts_folder}")
            
        # Determine file type based on extension
        file_extension = os.path.splitext(file_path.lower())[1]
        result = {
            "filename": file_path,
            "file_type": "unknown",
            "images": [],
            "total_pages": 0,
            "extracted_text": None
        }
        
        # Handle Office documents by converting them to PDF first
        if file_extension in OFFICE_EXTENSIONS:
            logger.info(f"Converting Office document {file_path} to PDF")
            pdf_path = self.office_to_pdf(file_path)
            if pdf_path:
                # Update file_path to the converted PDF
                file_path = pdf_path
                file_extension = ".pdf"
                # Mark the result as converted from Office
                result["original_file_type"] = "office"
            else:
                logger.error(f"Failed to convert {file_path} to PDF")
                result['error'] = "Failed to convert Office document to PDF"
                return result
                
        # Process as PDF
        if file_extension == ".pdf":
            # Process the PDF
            pdf_data = self.process_single_pdf(file_path, prepare_text)
            result['file_type'] = "pdf"
            result['total_pages'] = pdf_data['total_pages']
            result['images'] = pdf_data['page_images']
        else:        
            supported = False
            for exts in MIME_TO_EXTENSION.values():
                if file_extension in exts:
                    supported = True
                    break
            result['file_type'] = "image"
            if not supported:
                logger.error(f"Unsupported file format: {file_extension}")
                raise ToolException(f"Unsupported file format: {file_extension}")
                
            # Enhance image if requested
            img_path = file_path
            if prepare_text:
                img_path = self.prepare_text(file_path)
            result['images'].append(img_path)
            result['total_pages'] = 1
                
        if result['total_pages'] == 0:
            return result
        if self.tesseract_settings:
            text = []
            for img_path in result['images']:
                text_result = self._process_with_tesseract(img_path)
                text.append(text_result)
            extracted_text = " ".join(text)
        else:
            extracted_text = self._process_images_with_llm(result['images'], prompt)    
        
        result['extracted_text'] = extracted_text
            
        # Clean up temporary images after processing
        logger.info(f"Cleaning up temporary image files")
        for img_path in result['images']:
            try:
                self.alita.delete_artifact(self.artifacts_folder, img_path)
                if img_path.endswith("_enhanced.png"):
                    # Remove the original image if it was enhanced
                    original_path = img_path.replace("_enhanced.png", ".png")
                    self.alita.delete_artifact(self.artifacts_folder, original_path)
                logger.debug(f"Deleted temporary image: {img_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temporary image {img_path}: {e}")
                
        # Also clean up temporary PDF if this was converted from an Office document
        if "original_file_type" in result and result["original_file_type"] == "office":
            try:
                self.alita.delete_artifact(self.artifacts_folder, file_path)
                logger.debug(f"Deleted temporary PDF converted from Office: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temporary PDF {file_path}: {e}")
                
        return result
        
        

    def recognize_all(self, prompt: Optional[str] = None, prepare_text: Optional[bool] = False) -> List[Dict[str, Any]]:
        """
        Recognize text in all images and PDF files in the artifacts folder.
        Uses LLM if configured, otherwise falls back to Tesseract OCR.
        
        Args:
            prompt: Optional prompt to guide OCR extraction
            prepare_text: Whether to enhance image contrast before OCR
            
        Returns:
            List of dictionaries containing the extracted text and other metadata for each file
        """
        # Find all supported files in artifacts folder
        results = []
        supported_extensions = [ext for exts in MIME_TO_EXTENSION.values() for ext in exts]
        for f in self.alita.list_artifacts(self.artifacts_folder).get('rows', []):
            file_extension = os.path.splitext(f['name'].lower())[1]
            if file_extension == '.pdf' or file_extension in supported_extensions:
               results.append(self.recognize(f['name'], prompt, prepare_text)) 
        return results
    
    def pdfs_to_images(self, prepare_text: Optional[bool] = False) -> List[Dict[str, Any]]:
        pdf_files = []
        result = []
        for f in self.alita.list_artifacts(self.artifacts_folder).get('rows', []):
            file_extension = os.path.splitext(f['name'].lower())[1]
            if file_extension == ".pdf":
                pdf_files.append(f['name'])
        if not pdf_files:
            raise ToolException(f"No PDF files found in {self.artifacts_folder}")
        for pdf_path in pdf_files:
            result.append(self.process_single_pdf(pdf_path, prepare_text))    
        return result
    
    def process_single_pdf(self, pdf_path: str, prepare_text: Optional[bool] = False) -> Dict[str, Any]:
        images = self.pdf_to_images(pdf_path)
        if not images:
            return {"pdf_filename": pdf_path, "page_images": [], "total_pages": 0}
        if prepare_text:
            for img_path in images:
                # Prepare text for each image
                prepared_image_path = self.prepare_text(img_path)
                images[images.index(img_path)] = prepared_image_path
        return {
            "pdf_filename": pdf_path,
            "page_images": images,
            "total_pages": len(images)
        }
        
    
    def prepare_text(self, image_path: str) -> str:
        """
        Enhance image contrast and clarity to improve text recognition on blurred scans.
        Applies a series of image processing techniques to make text more recognizable.
        
        Args:
            image_path: Path to the image file in the artifacts folder
            
        Returns:
            Path to the enhanced image saved in the artifacts folder
        """
        try:
            import cv2
            
            # Download the image
            image_data = self.alita.download_artifact(self.artifacts_folder, image_path)
            
            # Load the image
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply bilateral filter to reduce noise while preserving edges
            denoised = cv2.bilateralFilter(gray, 9, 75, 75)
            
            # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)
            
            # Apply adaptive thresholding for better text separation
            binary = cv2.adaptiveThreshold(
                enhanced, 
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11,  # Block size
                2    # Constant subtracted from mean
            )
            
            # Optionally sharpen the image to make text clearer
            kernel = np.array([[-1,-1,-1],[-1,9,-1],[-1,-1,-1]])
            sharpened = cv2.filter2D(binary, -1, kernel)
            
            # Create a filename for the enhanced image
            base_name = os.path.splitext(image_path)[0]
            enhanced_filename = f"{base_name}_enhanced.png"
            
            # Encode the processed image
            _, enhanced_buffer = cv2.imencode(".png", sharpened)
            enhanced_bytes = enhanced_buffer.tobytes()
            
            # Upload the enhanced image to artifacts folder
            self.alita.create_artifact(self.artifacts_folder, enhanced_filename, enhanced_bytes)
            
            logger.info(f"Enhanced image saved as {enhanced_filename}")
            
            return enhanced_filename
            
        except Exception as e:
            raise ToolException(f"Error enhancing image text: {e}")
    
    def pdf_to_images(self, pdf_path: str) -> List[str]:
        """Convert PDF pages to images and store them in artifacts folder, removing white borders and skipping blank pages.
        Detects and splits multiple images on a single page, and corrects image rotation for each segment to ensure text is horizontal."""
        try:
            # Get PDF data
            pdf_data = self.alita.download_artifact(self.artifacts_folder, pdf_path)
            
            # Open PDF from memory
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            image_paths = []
            
            # Create base filename without extension
            base_filename = os.path.splitext(pdf_path)[0]
            
            # Convert each page to an image
            for page_num, page in enumerate(doc):
                # Render page to an image with higher resolution
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                
                # Convert to PIL Image
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Convert to numpy array
                img_array = np.array(img)
                
                # Detect if page is blank by checking pixel values
                # Calculate the average brightness of the image
                gray = np.mean(img_array, axis=2)
                avg_brightness = np.mean(gray)
                
                # Count non-white pixels (pixels below threshold)
                threshold = 245  # Threshold for considering a pixel as non-white
                non_white_pixels = np.sum(gray < threshold)
                non_white_ratio = non_white_pixels / (img_array.shape[0] * img_array.shape[1])
                
                # Skip if page is mostly blank (high brightness and few non-white pixels)
                if avg_brightness > 250 and non_white_ratio < 0.01:
                    logger.info(f"Skipping blank page {page_num + 1} in {pdf_path}")
                    continue
                
                # Detect and segment multiple images on the page
                try:
                    import cv2
                    import pytesseract
                    
                    # Convert to grayscale if not already
                    if len(img_array.shape) == 3:
                        gray_img = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                    else:
                        gray_img = img_array
                    
                    # Apply threshold to get binary image
                    _, binary = cv2.threshold(gray_img, 240, 255, cv2.THRESH_BINARY_INV)
                    
                    # Find contours
                    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    # Filter significant contours (ignore small noise)
                    min_area = img_array.shape[0] * img_array.shape[1] * 0.01  # 1% of image area
                    significant_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]
                    
                    # If multiple significant areas detected
                    if len(significant_contours) > 1:
                        logger.info(f"Found {len(significant_contours)} distinct areas on page {page_num + 1}")
                        
                        for i, contour in enumerate(significant_contours):
                            # Get bounding box
                            x, y, w, h = cv2.boundingRect(contour)
                            
                            # Add padding
                            padding = 10
                            x = max(0, x - padding)
                            y = max(0, y - padding)
                            w = min(img_array.shape[1] - x, w + 2*padding)
                            h = min(img_array.shape[0] - y, h + 2*padding)
                            
                            # Crop the image
                            cropped = img.crop((x, y, x+w, y+h))
                            cropped_array = np.array(cropped)
                            
                            # Detect text orientation for this segment and rotate if needed
                            angle, success = self._detect_text_orientation(cropped_array, segment_id=i+1, page_num=page_num+1)
                            if success and angle != 0:
                                logger.info(f"Rotating segment {i+1} of page {page_num+1} by {angle} degrees")
                                cropped = cropped.rotate(angle, expand=True, fillcolor=(255, 255, 255))
                            
                            # Save as separate image
                            img_byte_arr = io.BytesIO()
                            cropped.save(img_byte_arr, format='PNG')
                            img_bytes = img_byte_arr.getvalue()
                            
                            # Create unique filename for this region
                            image_filename = f"{base_filename}_page_{page_num + 1}_region_{i + 1}.png"
                            
                            # Upload to artifacts folder
                            self.alita.create_artifact(self.artifacts_folder, image_filename, img_bytes)
                            image_paths.append(image_filename)
                        # Skip the default processing below since we've handled each region
                        continue
                except Exception as e:
                    logger.warning(f"Error detecting multiple images on page: {e}")
                
                # Default processing for single image or when multi-image detection fails
                # Detect the background color (usually white)
                bg_color = img_array[0, 0, :]  # Top-left pixel color
                
                # Find non-white pixels for cropping
                non_white = np.where(gray < 250)  # Threshold for white
                
                # If there are non-white pixels, crop
                if len(non_white[0]) > 0:
                    min_row, max_row = np.min(non_white[0]), np.max(non_white[0])
                    min_col, max_col = np.min(non_white[1]), np.max(non_white[1])
                    
                    # Add some padding
                    padding = 10
                    min_row = max(0, min_row - padding)
                    min_col = max(0, min_col - padding)
                    max_row = min(img_array.shape[0], max_row + padding)
                    max_col = min(img_array.shape[1], max_col + padding)
                    
                    # Crop the image
                    cropped = img.crop((min_col, min_row, max_col, max_row))
                    cropped_array = np.array(cropped)
                    
                    # Detect text orientation and rotate if needed
                    angle, success = self._detect_text_orientation(cropped_array)
                    if success and angle != 0:
                        logger.info(f"Rotating image of page {page_num+1} by {angle} degrees")
                        cropped = cropped.rotate(angle, expand=True)
                    
                    # Use cropped image instead of the original
                    img = cropped
                else:
                    # Try to detect orientation for the full page if no cropping occurred
                    angle, success = self._detect_text_orientation(img_array)
                    if success and angle != 0:
                        logger.info(f"Rotating page {page_num+1} by {angle} degrees")
                        img = img.rotate(angle, expand=True)
                
                # Convert to bytes
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_bytes = img_byte_arr.getvalue()
                
                # Create a unique filename for the page image
                image_filename = f"{base_filename}_page_{page_num + 1}.png"
                
                # Upload to artifacts folder
                self.alita.create_artifact(self.artifacts_folder, image_filename, img_bytes)
                image_paths.append(image_filename)
            
            return image_paths

        except Exception as e:
            raise ToolException(f"Error converting PDF to images: {e}")
    
    def _detect_text_orientation(self, image_array, segment_id=None, page_num=None) -> tuple:
        """
        Helper method to detect text orientation in an image.
        
        Args:
            image_array: Numpy array of the image
            segment_id: Optional segment identifier for logging
            page_num: Optional page number for logging
            
        Returns:
            tuple: (angle, success_flag)
        """
        import cv2
        import pytesseract
        
        try:
            # Convert to grayscale if needed
            if len(image_array.shape) == 3:
                gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = image_array
            
            # Check if there's enough text content
            nonzero_pixels = np.count_nonzero(gray < 240)
            pixel_ratio = nonzero_pixels / (gray.shape[0] * gray.shape[1])
            
            segment_info = f"segment {segment_id} of page {page_num}" if segment_id is not None else "image"
            
            # Only run OSD if there's enough text content
            if pixel_ratio <= 0.01:  # Minimum 1% of non-white pixels
                logger.info(f"{segment_info} has insufficient text content for OCR orientation detection (pixel ratio: {pixel_ratio:.4f})")
                return 0, False
                
            # Use pytesseract to detect orientation with more robust config
            osd = pytesseract.image_to_osd(gray, config='--psm 0 -c min_characters_to_try=5')
            angle = int(osd.splitlines()[1].split(':')[1].strip())
            script = osd.splitlines()[2].split(':')[1].strip()
            orientation_conf = float(osd.splitlines()[3].split(':')[1].strip())
            
            logger.info(f"Detected orientation for {segment_info}: angle={angle}, script={script}, confidence={orientation_conf}")
            return angle, True
            
        except Exception as e:
            logger.warning(f"Primary orientation detection failed: {str(e)}")
            return self._fallback_orientation_detection(image_array, segment_id, page_num)
    
    def _fallback_orientation_detection(self, image_array, segment_id=None, page_num=None) -> tuple:
        """
        Fallback method for text orientation detection using computer vision techniques.
        
        Args:
            image_array: Numpy array of the image
            segment_id: Optional segment identifier for logging
            page_num: Optional page number for logging
            
        Returns:
            tuple: (angle, success_flag)
        """
        import cv2
        
        try:
            segment_info = f"segment {segment_id} of page {page_num}" if segment_id is not None else "image"
            
            # Convert to grayscale if needed
            if len(image_array.shape) == 3:
                gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = image_array
            
            # Apply adaptive thresholding for better text detection
            binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                         cv2.THRESH_BINARY_INV, 11, 2)
            
            # Dilate to connect nearby text
            kernel = np.ones((3, 3), np.uint8)
            dilated = cv2.dilate(binary, kernel, iterations=1)
            
            # Find contours in the processed image
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter out very small contours that are likely noise
            min_contour_area = (image_array.shape[0] * image_array.shape[1]) * 0.001  # 0.1% of image
            significant_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_contour_area]
            
            # If we have significant contours, analyze them
            if not significant_contours:
                logger.info(f"No significant contours found for orientation detection in {segment_info}")
                return 0, False
                
            # Method 1: Use minimum area rectangle
            all_points = []
            for cnt in significant_contours:
                all_points.extend([point[0] for point in cnt])
            
            if not all_points:
                logger.info(f"No valid points found for orientation detection in {segment_info}")
                return 0, False
                
            all_points = np.array(all_points)
            rect = cv2.minAreaRect(all_points)
            angle = rect[2]
            
            # Adjust angle (OpenCV angles can be confusing)
            if angle < -45:
                angle = 90 + angle
            
            logger.info(f"Fallback orientation detection for {segment_info}: angle={angle}")
            
            # Only return non-zero angle if it's significant
            if abs(angle) <= 1:
                return 0, True
                
            return angle, True
            
        except Exception as e:
            logger.warning(f"Fallback orientation detection failed: {str(e)}")
            return 0, False

    def office_to_pdf(self, file_path: str) -> Optional[str]:
        """
        Convert an Office document (DOCX or PPTX) to PDF using LibreOffice.
        
        Args:
            file_path: Path to the Office document
            
        Returns:
            Path to the converted PDF file or None if conversion failed
        """
        if not _check_libreoffice_installed():
            logger.error("LibreOffice is not installed. It is required for Office document conversion.")
            return None
            
        try:
            # Create a temporary directory to work in
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download the Office document
                office_data = self.alita.download_artifact(self.artifacts_folder, file_path)
                
                # Save the document to the temp directory
                temp_file_path = os.path.join(temp_dir, file_path)
                os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
                
                with open(temp_file_path, "wb") as f:
                    f.write(office_data)
                
                # Convert to PDF using LibreOffice
                pdf_dir = os.path.join(temp_dir, "pdf")
                os.makedirs(pdf_dir, exist_ok=True)
                
                # Run LibreOffice headless to convert the document
                subprocess.run([
                    "libreoffice", "--headless", "--convert-to", "pdf",
                    "--outdir", pdf_dir, temp_file_path
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                
                # Get the name of the PDF file (same as original with .pdf extension)
                pdf_filename = f"{os.path.splitext(file_path)[0]}.pdf"
                pdf_path = os.path.join(pdf_dir, os.path.basename(pdf_filename))
                
                # Check if the conversion was successful
                if os.path.exists(pdf_path):
                    # Read the PDF file
                    with open(pdf_path, "rb") as f:
                        pdf_data = f.read()
                    
                    # Save the PDF to the artifacts folder
                    self.alita.create_artifact(self.artifacts_folder, pdf_filename, pdf_data)
                    
                    logger.info(f"Successfully converted {file_path} to {pdf_filename}")
                    return pdf_filename
                else:
                    logger.error(f"Failed to convert {file_path} to PDF. Output file not found.")
                    return None
                    
        except subprocess.SubprocessError as e:
            logger.error(f"LibreOffice conversion failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error converting Office document to PDF: {e}")
            return None
    
    def convert_office_to_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        Convert an Office document (DOCX or PPTX) to PDF and return metadata about the conversion.
        
        Args:
            file_path: Path to the Office document
            
        Returns:
            Dictionary with metadata about the conversion
        """
        # Check if the file exists
        file_exists = False
        for f in self.alita.list_artifacts(self.artifacts_folder).get('rows', []):
            if f['name'] == file_path:
                file_exists = True
                break
                
        if not file_exists:
            raise ToolException(f"File not found: {file_path} in {self.artifacts_folder}")
        
        # Check if it's a supported Office format
        file_extension = os.path.splitext(file_path.lower())[1]
        if file_extension not in OFFICE_EXTENSIONS:
            raise ToolException(f"Unsupported file format: {file_extension}. Expected .docx or .pptx")
        
        # Convert to PDF
        pdf_path = self.office_to_pdf(file_path)
        if not pdf_path:
            logger.error(f"Failed to convert {file_path} to PDF")
            return None        
        return {
            "original_file": file_path,
            "converted_pdf": pdf_path,
            "success": True
        }

    def get_available_tools(self):
        """Get available OCR tools"""
        return [
            {
                "name": "recognize",
                "description": "Recognize text in a specific image, PDF, DOCX, or PPTX file",
                "args_schema": RecognizeArgs,
                "ref": self.recognize
            },
            {
                "name": "recognize_all",
                "description": "Recognize text in all supported files in the artifacts folder",
                "args_schema": RecognizeAllArgs,
                "ref": self.recognize_all
            },
            {
                "name": "convert_office_to_pdf",
                "description": "Convert an Office document (DOCX or PPTX) to PDF",
                "args_schema": ConvertOfficeArgs,
                "ref": self.convert_office_to_pdf
            },
            {
                "name": "pdf_to_images",
                "description": "Convert PDF pages to images and store in artifacts folder",
                "args_schema": PdfToImagesArgs,
                "ref": self.pdf_to_images
            },
            {
                "name": "pdfs_to_images",
                "description": "Convert all PDF files in folder to images",
                "args_schema": PdfsToImagesArgs,
                "ref": self.pdfs_to_images
            },
            {
                "name": "prepare_text",
                "description": "Enhance image contrast and clarity to improve text recognition on blurred scans",
                "args_schema": PrepareTextArgs,
                "ref": self.prepare_text
            }
        ]