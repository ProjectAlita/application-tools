from typing import List, Literal, Union

from langchain_core.tools import BaseTool

from .repos import AzureDevOpsReposToolkit, name as ado_repos_name, get_tools as ado_repos_get_tools
from .test_plan import AzureDevOpsPlansToolkit, name as ado_plans_name, name_alias as ado_plans_name_alias, \
    get_tools as ado_plans_get_tools
from .wiki import AzureDevOpsWikiToolkit, name as ado_wiki_name, name_alias as ado_wiki_name_alias, \
    get_tools as ado_wiki_get_tools
from .work_item import AzureDevOpsWorkItemsToolkit, name as ado_work_items_name, \
    name_alias as ado_work_items_name_alias, get_tools as ado_work_items_get_tools

name = "azure_devops"


supported_types: set = {
    ado_plans_name, ado_plans_name_alias,
    ado_wiki_name, ado_wiki_name_alias,
    ado_repos_name, ado_work_items_name,
    ado_work_items_name_alias
}


def get_tools(
        tool_type: Union[*supported_types],
        tool: dict
) -> List[BaseTool]:
    if tool_type in (ado_plans_name, ado_plans_name_alias):
        return ado_plans_get_tools(tool)
    elif tool_type in (ado_wiki_name, ado_wiki_name_alias):
        return ado_wiki_get_tools(tool)
    elif tool_type == ado_repos_name:
        return ado_repos_get_tools(tool)
    elif tool_type in (ado_work_items_name, ado_work_items_name_alias):
        return ado_work_items_get_tools(tool)
    raise ValueError(f"Unsupported tool type: {tool_type}")
