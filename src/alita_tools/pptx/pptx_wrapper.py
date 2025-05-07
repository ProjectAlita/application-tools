from typing import Dict, Any
import os
import tempfile
import chardet
from pydantic import create_model, BaseModel, Field
from ..elitea_base import BaseToolApiWrapper
from logging import getLogger

logger = getLogger(__name__)

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

    def fill_template(self, file_name: str, output_file_name: str, content_description: str) -> Dict[str, Any]:
        """
        Fill a PPTX template with content based on the provided description.
        
        Args:
            file_name: PPTX file name in the bucket
            output_file_name: Output PPTX file name to save in the bucket
            content_description: Detailed description of what content to put where in the template
            
        Returns:
            Dictionary with result information
        """
        import pptx
        
        try:
            # Download the PPTX file
            local_path = self._download_pptx(file_name)
            
            # Load the presentation
            presentation = pptx.Presentation(local_path)
            
            # Process each slide based on the content description
            for slide_idx, slide in enumerate(presentation.slides):
                # Get all shapes that contain text
                for shape in slide.shapes:
                    if hasattr(shape, "text_frame") and shape.text_frame:
                        # Check if this is a placeholder that needs to be filled
                        text = shape.text_frame.text
                        if text and ("{{" in text or "[PLACEHOLDER]" in text):
                            # Use LLM to generate content for this placeholder
                            prompt = f"""
                            I need content for a PowerPoint slide {slide_idx + 1}.
                            The current placeholder text is: "{text}"
                            
                            Based on this description of what's needed: "{content_description}"
                            
                            Please provide appropriate content to replace this placeholder.
                            Placeholder may be replaced with the same text in case no action required.
                            Keep it concise and formatted appropriately for a presentation slide.
                            """
                            
                            new_content = self.llm.invoke(prompt)
                            
                            # Clear existing paragraphs and add new content
                            shape.text_frame.clear()
                            p = shape.text_frame.paragraphs[0]
                            p.text = new_content
            
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
                "message": f"Failed to fill template: {str(e)}"
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
                                    
                                    translated_text = self.llm.invoke(prompt)
                                    
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
                content_description=(str, Field(description="Detailed description of what content to put where in the template"))
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
        