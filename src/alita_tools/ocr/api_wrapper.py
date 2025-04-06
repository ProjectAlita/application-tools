import io
import os
import logging
import json
from typing import Optional, Any, Dict, List
import tempfile

from pydantic import BaseModel, Field, model_validator, PrivateAttr
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
    "application/pdf": [".pdf"]
}


PAGE_DESCRIPTION_PROMPT_TEMPLATE = """
Please create detailed description of provided image.
Ignore page header, footer, basic logo and background.
Describe all images (illustration), tables.
Text with bullet points is NOT a table or image.

Use only provided information.
DO NOT make up answer.

Provide answer in JSON format with fields:
{{
    "page_summary": "page summary here",
    "keyfact"     : "the most important fact from the image",
    "image_quality": {{
        "level": "level of image quality (normal, detailed)", 
        "explanation": "explain why this detailisation is required"
    }},
    "images":[
        {{
            "description": "image description",
            "type"       : "image type (photo, illustration, diagram, etc.)",
            "keyfact"    : "the most important fact from the image"
        }}
    ],
    "tables":[
        {{
            "description": "table description",
            "keyfact"    : "the most important fact from the table"
        }}
    ]
}}
"""

IMAGE_OCR_PROMPT_TEMPLATE = """Please extract all text from the image."""


# Models for tool arguments
class RecognizeArgs(BaseModel):
    prompt: Optional[str] = Field(None, description="Optional prompt to guide OCR extraction")

class ExtractPDFArgs(BaseModel):
    prompt: Optional[str] = Field(None, description="Optional prompt to guide PDF extraction")

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
        if not self.artifacts_folder:
            logger.warning("No artifacts folder specified. OCR functionality will be limited.")
        
        if not os.path.exists(self.artifacts_folder):
            logger.warning(f"Artifacts folder {self.artifacts_folder} does not exist. OCR functionality will be limited.")

        # self.artifact = self.alita.artifact(self.artifacts_folder)
        if self.structured_output and len(self.expected_fields.keys()) > 0:
            stuct_model = create_pydantic_model(f"OCR_{self.artifacts_folder}_Output", self.expected_fields)
            self.struct_llm = self.llm.with_structured_output(stuct_model)
        else:
            self.struct_llm = self.llm
        
        return self
    
    def _process_with_llm(self, image_path: str, prompt: Optional[str] = None) -> str:
        """Process image with LLM-based vision capabilities"""
        if not self.struct_llm:
            raise ToolException("LLM not configured for OCR processing")
        try:
            # Read image as base64
            import base64
            
            # Determine the correct MIME type based on file extension
            file_extension = os.path.splitext(image_path.lower())[1]
            mime_type = "image/jpeg"  # Default
            
            # Find the correct MIME type for this extension
            for mime, extensions in MIME_TO_EXTENSION.items():
                if file_extension in extensions:
                    mime_type = mime
                    break
            
            # Get the data directly without using context manager
            data = self.alita.download_artifact(self.artifacts_folder, image_path)
            base64_image = base64.b64encode(data).decode('utf-8')
                
            if not prompt:
                prompt = IMAGE_OCR_PROMPT_TEMPLATE
            
            messages = [
                {"role": "user", 
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", 
                    "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
                ]}
            ]
            logger.info(f"LLM messages: {messages}")
            response = self.struct_llm.invoke(messages)
            if self.structured_output:
                return response.model_dump()
            return response.contents
            
        except Exception as e:
            raise ToolException(f"Error processing image with LLM: {e}")
    
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
    
    def recognize(self, prompt: Optional[str] = None) -> str:
        """
        Recognize text in images from the artifacts folder.
        Uses LLM if configured, otherwise falls back to Tesseract OCR.
        """
        # Find images in artifacts folder
        image_files = []
        supported_extensions = [ext for exts in MIME_TO_EXTENSION.values() for ext in exts]
        
        for f in self.alita.list_artifacts(self.artifacts_folder).get('rows', []):
            file_extension = os.path.splitext(f['name'].lower())[1]
            if file_extension in supported_extensions:
                image_files.append(f['name'])
        
        if not image_files:
            raise ToolException(f"No image files found in {self.artifacts_folder}")
        
        results = []
        for img_path in image_files:
            if self.tesseract_settings:
                result = self._process_with_tesseract(img_path)
            else:
                result = self._process_with_llm(img_path, prompt)
            results.append({
                "filename": img_path,
                "text": result
            })
        return results
    

    def get_available_tools(self):
        """Get available OCR tools"""
        return [
            {
                "name": "recognize",
                "description": "Recognize text in images from the artifacts folder",
                "args_schema": RecognizeArgs,
                "ref": self.recognize
            }
        ]