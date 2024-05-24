import logging
from typing import Dict, List, Any, Optional

import requests
from jinja2 import Environment, DebugUndefined
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    BaseMessage,
    ToolMessage
)
from langchain_core.prompts import ChatPromptTemplate
from pydantic import create_model

logger = logging.getLogger(__name__)


class Jinja2TemplatedChatMessagesTemplate(ChatPromptTemplate):

    def _resolve_variables(self, message: BaseMessage, kwargs: Dict) -> BaseMessage:
        environment = Environment(undefined=DebugUndefined)
        template = environment.from_string(message.content)
        content = template.render(kwargs)
        if isinstance(message, SystemMessage):
            return SystemMessage(content=content)
        elif isinstance(message, AIMessage):
            return AIMessage(content=content)
        elif isinstance(message, HumanMessage):
            return HumanMessage(content=content)
        elif isinstance(message, ToolMessage):
            return ToolMessage(content=content)
        else:
            return BaseMessage(content=content)

    def format_messages(self, **kwargs: Any) -> List[BaseMessage]:
        """Format the chat template into a list of finalized messages.

        Args:
            **kwargs: keyword arguments to use for filling in template variables
                      in all the template messages in this chat template.

        Returns:
            list of formatted messages
        """
        kwargs = self._merge_partial_and_user_variables(**kwargs)
        result = []
        for message_template in self.messages:
            if isinstance(message_template, BaseMessage):
                message = self._resolve_variables(message_template, kwargs)
                logger.debug(message.content)
                result.append(message)
        return result


class AlitaPrompt:
    def __init__(self, alita: Any, prompt: ChatPromptTemplate, name: str, description: str, llm_settings: dict):
        self.alita = alita
        self.prompt = prompt
        self.name = name
        self.llm_settings = llm_settings
        self.description = description

    def create_pydantic_model(self):
        fields = {}
        for variable in self.prompt.input_variables:
            fields[variable] = (str, None)
        if "input" not in list(fields.keys()):
            fields["input"] = (str, None)
        return create_model("PromptVariables", **fields)

    def predict(self, variables: Optional[dict] = None):
        if variables is None:
            variables = {}
        user_input = variables.pop("input", '')
        alita_vars = []
        for key, value in variables.items():
            alita_vars.append({
                "name": key,
                "value": value
            })
        messages = [SystemMessage(content=self.prompt.messages[0].content), HumanMessage(content=user_input)]
        result = []
        for message in self.alita.predict(messages, self.llm_settings, variables=alita_vars):
            result.append(message.content)
        return "\n\n".join(result)


class AlitaClient:
    def __init__(self, base_url: str, project_id: int, auth_token: str):
        self.base_url = base_url.rstrip('/')
        self.api_path = '/api/v1'
        self.project_id = project_id
        self.auth_token = auth_token
        self.headers = {
            "Authorization": f"Bearer {auth_token}"
        }
        self.predict_url = f"{self.base_url}{self.api_path}/prompt_lib/predict/prompt_lib/{self.project_id}"
        self.prompt_versions = f"{self.base_url}{self.api_path}/prompt_lib/version/prompt_lib/{self.project_id}"
        self.prompts = f"{self.base_url}{self.api_path}/prompt_lib/prompt/prompt_lib/{self.project_id}"

    def prompt(self, prompt_id, prompt_version_id, chat_history=None, return_tool=False):
        url = f"{self.prompt_versions}/{prompt_id}/{prompt_version_id}"
        data = requests.get(url, headers=self.headers).json()
        model_settings = data['model_settings']
        messages = [SystemMessage(content=data['context'])]
        variables = {}
        if data['messages']:
            for message in data['messages']:
                if message.get('role') == 'assistant':
                    messages.append(AIMessage(content=message['content']))
                elif message.get('role') == 'user':
                    messages.append(HumanMessage(content=message['content']))
                else:
                    messages.append(SystemMessage(content=message['content']))
        if chat_history and isinstance(chat_history, list):
            messages.extend(chat_history)
        input_variables = []
        for variable in data['variables']:
            if variable['value']:
                variables[variable['name']] = variable['value']
            else:
                input_variables.append(variable['name'])
        template = Jinja2TemplatedChatMessagesTemplate(messages=messages)
        if input_variables and not variables:
            template.input_variables = input_variables
        if variables:
            template.partial_variables = variables
        if not return_tool:
            return template
        else:
            url = f"{self.prompts}/{prompt_id}"
            data = requests.get(url, headers=self.headers).json()
            return AlitaPrompt(self, template, data['name'], data['description'], model_settings)

    def _prepare_messages(self, messages: list[BaseMessage]):
        context = ''
        chat_history = []
        if messages[0].type == "system":
            context = messages[0].content
        for message in messages[1:-1]:
            if message.type == 'human':
                chat_history.append({
                    'role': 'user',
                    'content': message.content
                })
            elif message.type == 'system':
                chat_history.append({
                    'role': 'system',
                    'content': message.content
                })
            else:
                chat_history.append({
                    'role': 'assistant',
                    'content': message.content
                })
        user_input = messages[-1].content
        return context, chat_history, user_input

    def _prepare_payload(self, messages: list[BaseMessage], model_settings: dict, variables: list[dict]):
        context, chat_history, user_input = self._prepare_messages(messages)
        if not variables:
            variables = []
        return {
            "type": "chat",
            "project_id": self.project_id,
            "context": context,
            "model_settings": model_settings,
            "user_input": user_input,
            "chat_history": chat_history,
            "variables": variables,
            "format_response": True
        }

    def async_predict(self, messages: list[BaseMessage], model_settings: dict, variables: list[dict] = None):
        # TODO: Modify to make it appropriate stream response
        prompt_data = self._prepare_payload(messages, model_settings, variables)
        response = requests.post(self.predict_url, headers=self.headers, json=prompt_data)
        logger.info(response.content)
        response_data = response.json()
        for message in response_data['messages']:
            if message.get('role') == 'user':
                yield HumanMessage(content=message['content'])
            else:
                yield AIMessage(content=message['content'])

    def predict(self, messages: list[BaseMessage], model_settings: dict, variables: list[dict] = None):
        prompt_data = self._prepare_payload(messages, model_settings, variables)

        response = requests.post(self.predict_url, headers=self.headers, json=prompt_data)
        if response.status_code != 200:
            logger.error("Error in response of predict: {response.content}")
            raise requests.exceptions.HTTPError(response.content)
        try:
            response_data = response.json()
            response_messages = []
            print(response_data['messages'])
            for message in response_data['messages']:
                if message.get('type') == 'user':
                    response_messages.append(HumanMessage(content=message['content']))
                else:
                    response_messages.append(AIMessage(content=message['content']))
            return response_messages
        except TypeError:
            logger.error(f"TypeError in response of predict: {response.content}")
            raise
