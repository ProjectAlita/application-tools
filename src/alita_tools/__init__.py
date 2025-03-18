import logging
from importlib import import_module

from .ado import get_tools as get_ado
from .ado.repos import AzureDevOpsReposToolkit
from .ado.test_plan import AzureDevOpsPlansToolkit
from .ado.wiki import AzureDevOpsWikiToolkit
from .ado.work_item import AzureDevOpsWorkItemsToolkit
from .azure_ai.search import AzureSearchToolkit, get_tools as get_azure_search
from .bitbucket import get_tools as get_bitbucket, AlitaBitbucketToolkit
from .browser import get_tools as get_browser, BrowserToolkit
from .cloud.aws import AWSToolkit
from .cloud.azure import AzureToolkit
from .cloud.gcp import GCPToolkit
from .cloud.k8s import KubernetesToolkit
from .code.sonar import get_tools as get_sonar, SonarToolkit
from .confluence import get_tools as get_confluence, ConfluenceToolkit
from .custom_open_api import OpenApiToolkit as CustomOpenApiToolkit
from .elastic import ElasticToolkit
from .figma import get_tools as get_figma, FigmaToolkit
from .github import get_tools as get_github, AlitaGitHubToolkit
from .gitlab import get_tools as get_gitlab, AlitaGitlabToolkit
from .gitlab_org import get_tools as get_gitlab_org, AlitaGitlabSpaceToolkit
from .google_places import get_tools as get_google_places, GooglePlacesToolkit
from .jira import get_tools as get_jira, JiraToolkit
from .keycloak import KeycloakToolkit
from .localgit import AlitaLocalGitToolkit
from .openapi import get_tools as get_openapi
from .pandas import get_tools as get_pandas, PandasToolkit
from .qtest import get_tools as get_qtest, QtestToolkit
from .rally import get_tools as get_rally, RallyToolkit
from .report_portal import get_tools as get_report_portal, ReportPortalToolkit
from .salesforce import get_tools as get_salesforce, SalesforceToolkit
from .sharepoint import get_tools as get_sharepoint, SharepointToolkit
from .sql import get_tools as get_sql, SQLToolkit
from .testio import get_tools as get_testio, TestIOToolkit
from .testrail import get_tools as get_testrail, TestrailToolkit
from .utils import get_codemie_toolkits
from .xray import get_tools as get_xray_cloud, XrayToolkit
from .yagmail import get_tools as get_yagmail, AlitaYagmailToolkit
from .zephyr import get_tools as get_zephyr, ZephyrToolkit
from .zephyr_enterprise import get_tools as get_zephyr_enterprise, ZephyrEnterpriseToolkit
from .zephyr_scale import get_tools as get_zephyr_scale, ZephyrScaleToolkit

logger = logging.getLogger(__name__)

def get_tools(tools_list, alita: 'AlitaClient', llm: 'LLMLikeObject', *args, **kwargs):
    tools = []
    for tool in tools_list:
        tool['settings']['alita'] = alita
        tool['settings']['llm'] = llm
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
        elif tool['type'] in ['ado_boards', 'ado_wiki', 'ado_plans', 'ado_repos', 'azure_devops_repos']:
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
        elif tool['type'] == 'zephyr_enterprise':
            tools.extend(get_zephyr_enterprise(tool))
        elif tool['type'] == 'rally':
            tools.extend(get_rally(tool))
        elif tool['type'] == 'sql':
            tools.extend(get_sql(tool))
        elif tool['type'] == 'sonar':
            tools.extend(get_sonar(tool))
        elif tool['type'] == 'google_places':
            tools.extend(get_google_places(tool))
        elif tool['type'] == 'azure_search':
            tools.extend(get_azure_search(tool))
        elif tool['type'] == 'pandas':
            tools.extend(get_pandas(tool))
        elif tool['type'] == 'figma':
            tools.extend(get_figma(tool))
        elif tool['type'] == 'salesforce':
            tools.extend(get_salesforce(tool))
        elif tool['type'] == 'codemie':
            tools.extend(init_codemie_toolkit(tool).get_tools())
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
        TestIOToolkit.toolkit_config_schema(),
        SQLToolkit.toolkit_config_schema(),
        SonarToolkit.toolkit_config_schema(),
        GooglePlacesToolkit.toolkit_config_schema(),
        BrowserToolkit.toolkit_config_schema(),
        XrayToolkit.toolkit_config_schema(),
        AlitaGitlabToolkit.toolkit_config_schema(),
        ConfluenceToolkit.toolkit_config_schema(),
        AlitaBitbucketToolkit.toolkit_config_schema(),
        AlitaGitlabSpaceToolkit.toolkit_config_schema(),
        ZephyrScaleToolkit.toolkit_config_schema(),
        ZephyrEnterpriseToolkit.toolkit_config_schema(),
        ZephyrToolkit.toolkit_config_schema(),
        AlitaYagmailToolkit.toolkit_config_schema(),
        SharepointToolkit.toolkit_config_schema(),
        AzureDevOpsReposToolkit.toolkit_config_schema(),
        AWSToolkit.toolkit_config_schema(),
        AzureToolkit.toolkit_config_schema(),
        GCPToolkit.toolkit_config_schema(),
        KubernetesToolkit.toolkit_config_schema(),
        CustomOpenApiToolkit.toolkit_config_schema(),
        ElasticToolkit.toolkit_config_schema(),
        KeycloakToolkit.toolkit_config_schema(),
        AlitaLocalGitToolkit.toolkit_config_schema(),
        PandasToolkit.toolkit_config_schema(),
        AzureSearchToolkit.toolkit_config_schema(),
        FigmaToolkit.toolkit_config_schema(),
        SalesforceToolkit.toolkit_config_schema(),

    ]

def init_codemie_toolkit(tool):
    """ Initialize Codemie toolkit per given tool's settings """

    tool_settings = tool['settings']
    # Find required codemie toolkit based on passed tool's class name
    required_toolkit = [toolkit for toolkit in get_codemie_toolkits() if
                        toolkit.__name__ == tool_settings['class']]
    required_toolkit = required_toolkit[0] if required_toolkit else None
    # Extract model fields for specific toolkit
    fields = required_toolkit.model_fields.keys()
    selected_tools = tool_settings.get('selected_tools', [])
    arguments = {}
    for field in fields:
        # Whether we need to verify its presence in settings???
        arguments.update({ field: tool_settings.get(field) })
    return required_toolkit.get_toolkit(configs = arguments)