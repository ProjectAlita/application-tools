import logging
from importlib import import_module

from .github import get_tools as get_github, AlitaGitHubToolkit
from .openapi import get_tools as get_openapi
from .jira import get_tools as get_jira, JiraToolkit
from .confluence import get_tools as get_confluence
from .gitlab import get_tools as get_gitlab
from .gitlab_org import get_tools as get_gitlab_org
from .zephyr import get_tools as get_zephyr
from .browser import get_tools as get_browser
from .report_portal import get_tools as get_report_portal, ReportPortalToolkit
from .bitbucket import get_tools as get_bitbucket
from .testrail import get_tools as get_testrail, TestrailToolkit
from .testio import get_tools as get_testio, TestIOToolkit
from .xray import get_tools as get_xray_cloud
from .sharepoint import get_tools as get_sharepoint
from .qtest import get_tools as get_qtest, QtestToolkit
from .zephyr_scale import get_tools as get_zephyr_scale
from .ado import get_tools as get_ado
from .ado.test_plan import AzureDevOpsPlansToolkit
from .ado.work_item import AzureDevOpsWorkItemsToolkit
from .ado.wiki import AzureDevOpsWikiToolkit
from .rally import get_tools as get_rally, RallyToolkit


from .yagmail import get_tools as get_yagmail

logger = logging.getLogger(__name__)

def get_tools(tools_list, *args, **kwargs):
    tools = []
    for tool in tools_list:
        if tool['type'] == 'openapi':
            tools.extend(get_openapi(tool))
        elif tool['type'] == 'github':
            tools.extend(get_github(tool))
        elif tool['type'] == 'jira':
            tools.extend(get_jira(tool))
        elif tool['type'] == 'confluence':
            tools.extend(get_confluence(tool))
        elif tool['type'] == 'gitlab':
            tools.extend(get_gitlab(tool))
        elif tool['type'] == 'gitlab_org':
            tools.extend(get_gitlab_org(tool))
        elif tool['type'] == 'zephyr':
            tools.extend(get_zephyr(tool))
        elif tool['type'] == 'browser':
            tools.extend(get_browser(tool))
        elif tool['type'] == 'yagmail':
            tools.extend(get_yagmail(tool))
        elif tool['type'] == 'report_portal':
            tools.extend(get_report_portal(tool))
        elif tool['type'] == 'bitbucket':
            tools.extend(get_bitbucket(tool))
        elif tool['type'] == 'testrail':
            tools.extend(get_testrail(tool))
        elif tool['type'] == 'ado_boards' or tool['type'] == 'ado_wiki' or tool['type'] == 'ado_plans':
            tools.extend(get_ado(tool['type'], tool))
        elif tool['type'] == 'testio':
            tools.extend(get_testio(tool))
        elif tool['type'] == 'xray_cloud':
            tools.extend(get_xray_cloud(tool))
        elif tool['type'] == 'sharepoint':
            tools.extend(get_sharepoint(tool))
        elif tool['type'] == 'qtest':
            tools.extend(get_qtest(tool))
        elif tool['type'] == 'zephyr_scale':
            tools.extend(get_zephyr_scale(tool))
        elif tool['type'] == 'rally':
            tools.extend(get_rally(tool))
        else:
            if tool.get("settings", {}).get("module"):
                try:
                    settings = tool.get("settings", {})
                    mod = import_module(settings.pop("module"))
                    tkitclass = getattr(mod, settings.pop("class"))
                    toolkit = tkitclass.get_toolkit(**tool["settings"])
                    tools.extend(toolkit.get_tools())
                except Exception as e:
                    logger.error(f"Error in getting toolkit: {e}")
    return tools

def get_toolkits():
    return [
        AlitaGitHubToolkit.toolkit_config_schema(),
        TestrailToolkit.toolkit_config_schema(),
        JiraToolkit.toolkit_config_schema(),
        AzureDevOpsPlansToolkit.toolkit_config_schema(),
        AzureDevOpsWikiToolkit.toolkit_config_schema(),
        AzureDevOpsWorkItemsToolkit.toolkit_config_schema(),
        RallyToolkit.toolkit_config_schema(),
        QtestToolkit.toolkit_config_schema(),
        ReportPortalToolkit.toolkit_config_schema(),
        TestIOToolkit.toolkit_config_schema()
    ]