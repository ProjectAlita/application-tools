from .test_plan import AzureDevOpsPlansToolkit
from .wiki import AzureDevOpsWikiToolkit
from .work_item import AzureDevOpsWorkItemsToolkit
from .repos import AzureDevOpsReposToolkit

name = "azure_devops"


def get_tools(tool_type, tool):
    config_dict = {
        # common
        "selected_tools": tool['settings'].get('selected_tools', []),
        "organization_url": tool['settings']['organization_url'],
        "project": tool['settings'].get('project', None),
        "token": tool['settings'].get('token', None),
        "limit": tool['settings'].get('limit', 5),
        # repos only
        "repository_id": tool['settings'].get('repository_id', None),
        "base_branch": tool['settings'].get('base_branch', None),
        "active_branch": tool['settings'].get('active_branch', None),
        "toolkit_name": tool.get('toolkit_name', ''),
    }
    if tool_type == 'ado_plans':
        return AzureDevOpsPlansToolkit().get_toolkit(**config_dict).get_tools()
    elif tool_type == 'ado_wiki':
        return AzureDevOpsWikiToolkit().get_toolkit(**config_dict).get_tools()
    elif tool_type == 'ado_repos' or tool_type == 'azure_devops_repos':
        return AzureDevOpsReposToolkit().get_toolkit(**config_dict).get_tools()
    else:
        return AzureDevOpsWorkItemsToolkit().get_toolkit(**config_dict).get_tools()
