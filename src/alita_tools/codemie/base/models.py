from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, model_validator


class ToolMetadata(BaseModel):
    name: str
    description: Optional[str] = ''
    label: Optional[str] = ''
    react_description: Optional[str] = ''
    user_description: Optional[str] = ''


class ToolSet(str, Enum):
    GIT = "Git"
    VCS = "VCS"
    CODEBASE_TOOLS = "Codebase Tools"
    KB_TOOLS = "Knowledge Base"
    CODE_PLAN = "Code plan"
    GENERAL = "General"
    RESEARCH = "Research"
    CLOUD = "Cloud"
    PLUGIN = "Plugin"
    ADMIN = "CodeMie admin"
    ACCESS_MANAGEMENT = "Access Management"
    PROJECT_MANAGEMENT = "Project Management"
    OPEN_API = "OpenAPI"
    DATA_MANAGEMENT = "Data Management"
    VISION = "Vision"
    FILE_SYSTEM = "FileSystem"
    PANDAS = "Pandas"
    PDF = "PDF"
    POWER_POINT = "PowerPoint"
    NOTIFICATION = "Notification"
    CODE_QUALITY = "Code Quality"
    OPEN_API_LABEL = "Open API"
    FILE_SYSTEM_LABEL = "File System"
    FILE_MANAGEMENT_LABEL = "File Management"
    QUALITY_ASSURANCE = "Quality Assurance"
    AZURE_DEVOPS_WIKI = "Azure DevOps Wiki"
    AZURE_DEVOPS_WORK_ITEM = "Azure DevOps Work Item"
    AZURE_DEVOPS_TEST_PLAN = "Azure DevOps Test Plan"


class Tool(BaseModel):
    name: str
    label: Optional[str] = None
    settings_config: bool = False
    user_description: Optional[str] = None

    @model_validator(mode="before")
    def set_label(cls, values):
        name = values.get('name', '')
        label = values.get('label', '')
        if not label:
            values['label'] = ' '.join(word.capitalize() for word in name.split('_'))
        else:
            values['label'] = label
        return values

    @classmethod
    def from_metadata(cls, metadata: 'ToolMetadata', **kwargs):
        return cls(
            name=metadata.name,
            label=metadata.label or None,
            user_description=metadata.user_description or None,
            **kwargs
        )


class ToolKit(BaseModel):
    toolkit: str
    tools: List[Tool]
    label: Optional[str] = ""
    settings_config: bool = False
    is_external: bool = False
