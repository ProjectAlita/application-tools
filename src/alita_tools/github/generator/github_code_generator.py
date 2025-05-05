from typing import Any, Dict, List, Optional
import re
import logging

logger = logging.getLogger(__name__)

class GitHubCodeGenerator:
    """Generates Python code to interact with GitHub tools using an LLM."""
    llm: Any
    prompt_addon: str = ""
    tools_info: List[Dict[str, str]]

    # Updated prompt template with parameter examples for common tools
    _prompt_template = """
You are an expert Python programmer tasked with generating code to interact with a GitHub repository using a provided toolkit.
The toolkit allows you to perform actions via the `self.run('tool_name', **kwargs)` method.

IMPORTANT: Each tool requires specific parameter names. Here are the exact parameter names for common tools:

Available tools:
{tool_list}

{prompt_addon}

Your goal is to write a Python code snippet that accomplishes the following task:
Task: {task}

Instructions:
1. Use ONLY the provided tools via `self.run()`. Do NOT attempt to import other libraries or use direct API calls.
2. IMPORTANT: Use EXACTLY the parameter names shown in the examples above. Do not modify them or use alternatives.
3. Chain multiple `self.run()` calls if necessary to complete the task.
4. Store the final desired output or confirmation message in a variable named `result`.
5. Handle potential outputs from intermediate steps if they are needed for subsequent steps.
6. Focus on generating only the Python code block required. Do not include explanations or surrounding text.

{error_context}

Python Code:
```python
# Start your Python code here
# Remember to assign the final output to the 'result' variable
```
"""

    def __init__(self, tools_info: List[Dict[str, str]], prompt_addon:str, llm: Any):
        if not llm:
            raise ValueError("LLM instance is required for GitHubCodeGenerator.")
        self.llm = llm
        self.prompt_addon = prompt_addon
        self.tools_info = tools_info

    def _format_tool_list(self) -> str:
        """Formats the tool information for the prompt."""
        return "\n".join([f"- {tool['name']}: {tool['args_schema']}" for tool in self.tools_info])

    def generate_code(self, task: str, error_trace: Optional[str] = None) -> str:
        """Generates the Python code snippet."""
        tool_list_str = self._format_tool_list()
        error_context_str = f"Context from previous failed attempt:\n{error_trace}\nPlease correct the code based on this error." if error_trace else ""

        prompt = self._prompt_template.format(
            tool_list=tool_list_str,
            task=task,
            prompt_addon=self.prompt_addon,
            error_context=error_context_str
        )

        print(f"Generating GitHub code with prompt:\n{prompt}")

        # Assuming the LLM has a method like `invoke` or `generate`
        # Replace with the actual method call for your LLM
        response = self.llm.invoke(prompt) # Or self.llm.generate(prompt), etc.

        # Extract Python code from the response (assuming it's in a markdown block)
        code = self._extract_python_code(response)

        if not code:
            logger.error(f"LLM failed to generate Python code. Response: {response}")
            raise ValueError("LLM failed to generate Python code.")

        logger.debug(f"Generated GitHub code:\n{code}")
        return code

    def _extract_python_code(self, response: Any) -> Optional[str]:
        """Extracts Python code from the LLM response."""
        # Handle potential response object structure (e.g., response.content)
        if hasattr(response, 'content'):
            response_text = str(response.content)
        else:
            response_text = str(response)

        # Find Python code block
        match = re.search(r"```python\n(.*?)```", response_text, re.DOTALL)
        if match:
            return match.group(1).strip()
        else:
            # Fallback: maybe the LLM just returned code directly
            # Be cautious with this fallback, ensure it's actually code
            if "self.run(" in response_text and "def " not in response_text:
                 logger.warning("Extracted code using fallback method (no markdown block found).")
                 return response_text.strip()
            else:
                logger.warning(f"Could not extract Python code from LLM response: {response_text}")
        return None
