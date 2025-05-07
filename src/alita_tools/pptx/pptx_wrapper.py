from typing import Dict, Any, List, Optional
from copy import copy
import os
import tempfile
import chardet
from pydantic import create_model, BaseModel, Field
from ..elitea_base import BaseToolApiWrapper
from logging import getLogger
import traceback
from langchain_core.messages import HumanMessage
logger = getLogger(__name__)


INTRO_PROMPT = """I need content for PowerPoint slide {slide_idx}.
Based on the image of the slide and the data available for use 
Please provide replacements for ALL these placeholders in the slide

<Data Available for use>
{content_description}
</Data Available for use>"""


class PPTXWrapper(BaseToolApiWrapper):
    """
    API wrapper for PPTX file manipulation.
    Uses the Alita artifact API to download and upload PPTX files from/to buckets.
    """
    bucket_name: str
    alita: Any  # AlitaClient
    llm: Any  # LLMLikeObject

    def _bytes_content(self, content: Any) -> bytes:
        """
        Returns the content of the file as bytes
        """
        if isinstance(content, bytes):
            return content
        return content.encode('utf-8')

    def get(self, artifact_name: str, bucket_name: str = None):
        if not bucket_name:
            bucket_name = self.bucket_name
        data = self.client.download_artifact(bucket_name, artifact_name)
        if len(data) == 0:
            # empty file might be created
            return ""
        if isinstance(data, dict) and data['error']:
            return f"{data['error']}. {data['content'] if data['content'] else ''}"
        detected = chardet.detect(data)
        if detected['encoding'] is not None:
            return data.decode(detected['encoding'])
        else:
            return "Could not detect encoding"

    def _download_pptx(self, file_name: str) -> str:
        """
        Download PPTX from bucket to a temporary file.
        
        Args:
            file_name: The name of the file in the bucket
            
        Returns:
            Path to the temporary file
        """
        try:
            # Create a temporary file
            temp_dir = tempfile.gettempdir()
            local_path = os.path.join(temp_dir, file_name)
            data = self.alita.download_artifact(self.bucket_name, file_name)
            if isinstance(data, dict) and data['error']:
                raise NameError(f"{data['error']}. {data['content'] if data['content'] else ''}")
            with open(local_path, 'wb') as f:
                f.write(data)
            logger.info(f"Downloaded PPTX from bucket {self.bucket_name} to {local_path}")
            return local_path
        except Exception as e:
            logger.error(f"Error downloading PPTX file {file_name}: {str(e)}")
            raise e

    def _upload_pptx(self, local_path: str, file_name: str) -> str:
        """
        Upload PPTX to bucket from a local file.
        
        Args:
            local_path: Path to the local file
            file_name: The name to give the file in the bucket
            
        Returns:
            URL of the uploaded file
        """
        try:
            # Upload file to the bucket
            response = None
            with open(local_path, 'rb') as f:
                response = self.alita.create_artifact(
                    bucket_name=self.bucket_name,
                    artifact_name=file_name,
                    artifact_data=f.read()
                )
            
            logger.info(f"Uploaded PPTX to bucket {self.bucket_name} as {file_name}")
            return response
        except Exception as e:
            logger.error(f"Error uploading PPTX file {file_name}: {str(e)}")
            raise e

    def _get_structured_output_llm(self, stuct_model):
        """
        Returns the structured output LLM if available, otherwise returns the regular LLM
        """
        shalow_llm = copy(self.llm)
        return shalow_llm.with_structured_output(stuct_model)

    def _create_slide_model(self, placeholders: List[str]) -> type:
        """
        Dynamically creates a Pydantic model for a slide based on its placeholders
        
        Args:
            placeholders: List of placeholder texts found in the slide
            
        Returns:
            A Pydantic model class for the slide
        """
        field_dict = {}
        for i, placeholder in enumerate(placeholders):
            # Clean placeholder text for field name
            field_name = f"placeholder_{i}"
            # Add a field for each placeholder
            field_dict[field_name] = (str, Field(description=f"Content for: {placeholder}"))
            
        # Create and return the model
        return create_model(f"SlideModel", **field_dict)

    def fill_template(self, file_name: str, output_file_name: str, content_description: str, pdf_file_name: str = None) -> Dict[str, Any]:
        """
        Fill a PPTX template with content based on the provided description.
        
        Args:
            file_name: PPTX file name in the bucket
            output_file_name: Output PPTX file name to save in the bucket
            content_description: Detailed description of what content to put where in the template
            pdf_file_name: Optional PDF file name in the bucket that matches the PPTX template 1:1
            
        Returns:
            Dictionary with result information
        """
        import pptx
        import base64
        from io import BytesIO
        
        try:
            # Download the PPTX file
            local_path = self._download_pptx(file_name)
            
            # Load the presentation
            presentation = pptx.Presentation(local_path)
            
            # If PDF file is provided, download and extract images from it
            pdf_pages = {}
            if pdf_file_name:
                try:
                    import fitz  # PyMuPDF
                    from PIL import Image
                    
                    # Download PDF file
                    pdf_data = self.alita.download_artifact(self.bucket_name, pdf_file_name)
                    if isinstance(pdf_data, dict) and pdf_data.get('error'):
                        raise ValueError(f"Error downloading PDF: {pdf_data.get('error')}")
                    
                    # Create a temporary memory buffer for PDF
                    pdf_buffer = BytesIO(pdf_data)
                    
                    # Open the PDF
                    pdf_doc = fitz.open(stream=pdf_buffer, filetype="pdf")
                    
                    # Extract images from each page
                    for page_idx in range(len(pdf_doc)):
                        page = pdf_doc.load_page(page_idx)
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scale for better readability
                        
                        # Convert to PIL Image
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        
                        # Convert to base64 for LLM
                        buffered = BytesIO()
                        img.save(buffered, format="PNG")
                        img_str = base64.b64encode(buffered.getvalue()).decode()
                        
                        # Store image for later use
                        pdf_pages[page_idx] = img_str
                    
                    logger.info(f"Successfully extracted {len(pdf_pages)} pages from PDF {pdf_file_name}")
                except ImportError:
                    logger.warning("PyMuPDF (fitz) or PIL not installed. PDF processing skipped. Install with 'pip install PyMuPDF Pillow'")
                except Exception as e:
                    logger.warning(f"Failed to process PDF {pdf_file_name}: {str(e)}")
            
            # Process each slide based on the content description
            for slide_idx, slide in enumerate(presentation.slides):
                # Collect all placeholders in this slide
                placeholders = []
                placeholder_shapes = []
                
                # Get all shapes that contain text
                for shape in slide.shapes:
                    if hasattr(shape, "text_frame") and shape.text_frame:
                        # Check if this is a placeholder that needs to be filled
                        text = shape.text_frame.text
                        if text and ("{{" in text or "[PLACEHOLDER]" in text):
                            placeholders.append(text)
                            placeholder_shapes.append(shape)
                logger.info(f"Found {len(placeholders)} placeholders in slide {slide_idx + 1}")
                if placeholders:
                    # Create a dynamic Pydantic model for this slide
                    slide_model = self._create_slide_model(placeholders)
                    # Create a prompt with image and all placeholders on this slide
                    prompt_parts = [
                        {
                            "type": "text", 
                            "text": INTRO_PROMPT.format(slide_idx=slide_idx + 1,
                                                        content_description=content_description)
                        }
                    ]
                    
                    # Add each placeholder text
                    for i, placeholder in enumerate(placeholders):
                        prompt_parts.append({
                            "type": "text",
                            "text": f"Placeholder {i+1}: {placeholder}"
                        })
                    
                    # Add PDF image if available
                    if pdf_pages and slide_idx in pdf_pages:
                        prompt_parts.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{pdf_pages[slide_idx]}"
                            }
                        })
                    
                    # Get the structured output LLM
                    structured_llm = self._get_structured_output_llm(slide_model)
                    result = structured_llm.invoke([HumanMessage(content=prompt_parts)])
                    # response = result.content
                    for key, value in result.model_dump().items():
                        # Replace the placeholder text with the generated content
                        for i, shape in enumerate(placeholder_shapes):
                            if key == f"placeholder_{i}":
                                shape.text_frame.clear()
                                p = shape.text_frame.paragraphs[0]
                                p.text = value
            # Save the modified presentation
            temp_output_path = os.path.join(tempfile.gettempdir(), output_file_name)
            presentation.save(temp_output_path)
            
            # Upload the modified file
            result_url = self._upload_pptx(temp_output_path, output_file_name)
            
            # Clean up temporary files
            try:
                os.remove(local_path)
                os.remove(temp_output_path)
            except:
                pass
            
            return {
                "status": "success",
                "message": f"Successfully filled template and saved as {output_file_name}",
                "url": result_url
            }
            
        except Exception as e:
            logger.error(f"Error filling PPTX template: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to fill template: {traceback.format_exc()}"
            }

    def translate_presentation(self, file_name: str, output_file_name: str, target_language: str) -> Dict[str, Any]:
        """
        Translate text in a PowerPoint presentation to another language.
        
        Args:
            file_name: PPTX file name in the bucket
            output_file_name: Output PPTX file name to save in the bucket
            target_language: Target language code (e.g., 'es' for Spanish, 'ua' for Ukrainian)
            
        Returns:
            Dictionary with result information
        """
        import pptx
        
        try:
            # Download the PPTX file
            local_path = self._download_pptx(file_name)
            
            # Load the presentation
            presentation = pptx.Presentation(local_path)
            
            # Map of language codes to full language names
            language_names = {
                'en': 'English',
                'es': 'Spanish',
                'fr': 'French',
                'de': 'German',
                'it': 'Italian',
                'pt': 'Portuguese',
                'ru': 'Russian',
                'ja': 'Japanese',
                'zh': 'Chinese',
                'ar': 'Arabic',
                'hi': 'Hindi',
                'ko': 'Korean',
                'ua': 'Ukrainian'
            }
            
            # Get the full language name if available, otherwise use the code
            target_language_name = language_names.get(target_language.lower(), target_language)
            
            # Process each slide and translate text
            for slide in presentation.slides:
                # Get all shapes that contain text
                for shape in slide.shapes:
                    if hasattr(shape, "text_frame") and shape.text_frame:
                        # Check if there's text to translate
                        if shape.text_frame.text:
                            # Translate each paragraph
                            for paragraph in shape.text_frame.paragraphs:
                                if paragraph.text:
                                    # Use LLM to translate the text
                                    prompt = f"""
                                    Please translate the following text to {target_language_name}:
                                    
                                    "{paragraph.text}"
                                    
                                    Provide only the translated text without quotes or explanations.
                                    """
                                    
                                    result = self.llm.invoke([ HumanMessage(content=[ {"type": "text", "text": prompt} ] ) ])
                                    translated_text = result.content
                                    # Clean up any extra quotes or whitespace
                                    translated_text = translated_text.strip().strip('"\'')
                                    
                                    # Replace the text
                                    paragraph.text = translated_text
            
            # Save the translated presentation
            temp_output_path = os.path.join(tempfile.gettempdir(), output_file_name)
            presentation.save(temp_output_path)
            
            # Upload the translated file
            result_url = self._upload_pptx(temp_output_path, output_file_name)
            
            # Clean up temporary files
            try:
                os.remove(local_path)
                os.remove(temp_output_path)
            except:
                pass
            
            return {
                "status": "success",
                "message": f"Successfully translated presentation to {target_language_name} and saved as {output_file_name}",
                "url": result_url
            }
            
        except Exception as e:
            logger.error(f"Error translating PPTX: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to translate presentation: {str(e)}"
            }
    
    
    def get_available_tools(self):
        """
        Return list of available tools.
        """
        return [{
            "name": "fill_template",
            "description": "Fill a PPTX template with content based on the provided description",
            "ref": self.fill_template,
            "args_schema": create_model(
                "FillTemplateArgs",
                file_name=(str, Field(description="PPTX file name in the bucket")),
                output_file_name=(str, Field(description="Output PPTX file name to save in the bucket")),
                content_description=(str, Field(description="Detailed description of what content to put where in the template")),
                pdf_file_name=(str, Field(description="Optional PDF file name in the bucket that matches the PPTX template 1:1", default=None))
            )
        },{
            "name": "translate_presentation",
            "description": "Translate text in a PowerPoint presentation to another language",
            "ref": self.translate_presentation,
            "args_schema": create_model(
                "TranslatePresentationArgs",
                file_name=(str, Field(description="PPTX file name in the bucket")),
                output_file_name=(str, Field(description="Output PPTX file name to save in the bucket")),
                target_language=(str, Field(description="Target language code (e.g., 'es' for Spanish, 'ua' for Ukrainian)"))
            )
        }]
