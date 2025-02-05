import logging
from importlib import import_module

from .ado import get_tools as get_ado
from .ado.repos import AzureDevOpsReposToolkit
from .ado.test_plan import AzureDevOpsPlansToolkit
from .ado.wiki import AzureDevOpsWikiToolkit
from .ado.work_item import AzureDevOpsWorkItemsToolkit
from .bitbucket import AlitaBitbucketToolkit
from .bitbucket import get_tools as get_bitbucket
from .browser import BrowserToolkit
from .browser import get_tools as get_browser
from .cloud import get_tools as get_cloud
from .cloud.aws import AWSToolkit
from .cloud.azure import AzureToolkit
from .cloud.gcp import GCPToolkit
from .cloud.k8s import KubernetesToolkit
from .code.sonar import SonarToolkit
from .code.sonar import get_tools as get_sonar
from .confluence import ConfluenceToolkit
from .confluence import get_tools as get_confluence
from .custom_open_api import OpenApiToolkit as CustomOpenApiToolkit
from .custom_open_api import get_tools as get_custom_open_api
from .elastic import ElasticToolkit
from .elastic import get_tools as get_elastic
from .github import AlitaGitHubToolkit
from .github import get_tools as get_github
from .gitlab import AlitaGitlabToolkit
from .gitlab import get_tools as get_gitlab
from .gitlab_org import AlitaGitlabSpaceToolkit
from .gitlab_org import get_tools as get_gitlab_org
from .google_places import GooglePlacesToolkit
from .google_places import get_tools as get_google_places
from .jira import JiraToolkit
from .jira import get_tools as get_jira
from .keycloak import KeycloakToolkit
from .keycloak import get_tools as get_keycloack
from .localgit import AlitaLocalGitToolkit
from .localgit import get_tools as get_localgit
from .pandas import PandasToolkit
from .pandas import get_tools as get_pandas
from .openapi import get_tools as get_openapi
from .qtest import QtestToolkit
from .qtest import get_tools as get_qtest
from .rally import RallyToolkit
from .rally import get_tools as get_rally
from .report_portal import ReportPortalToolkit
from .report_portal import get_tools as get_report_portal
from .sharepoint import SharepointToolkit
from .sharepoint import get_tools as get_sharepoint
from .sql import SQLToolkit
from .sql import get_tools as get_sql
from .testio import TestIOToolkit
from .testio import get_tools as get_testio
from .testrail import TestrailToolkit
from .testrail import get_tools as get_testrail
from .xray import XrayToolkit
from .xray import get_tools as get_xray_cloud
from .yagmail import AlitaYagmailToolkit
from .yagmail import get_tools as get_yagmail
from .zephyr import ZephyrToolkit
from .zephyr import get_tools as get_zephyr
from .zephyr_scale import ZephyrScaleToolkit
from .zephyr_scale import get_tools as get_zephyr_scale

logger = logging.getLogger(__name__)

def get_tools(tools_list, *args, **kwargs):
    tools = []
    for tool in tools_list:
        if tool['type'] in ['ado_boards', 'ado_wiki', 'ado_plans', 'ado_repos']:
            tools.extend(get_ado(tool['type'], tool))
        elif tool['type'] == 'bitbucket':
            tools.extend(get_bitbucket(tool))
        elif tool['type'] == 'browser':
            tools.extend(get_browser(tool))
        elif tool['type'] == 'confluence':
            tools.extend(get_confluence(tool))
        elif tool['type'] == 'custom_open_api':
            tools.extend(get_custom_open_api(tool))
        elif tool['type'] == 'elastic':
            tools.extend(get_elastic(tool))
        elif tool['type'] == 'github':
            tools.extend(get_github(tool))
        elif tool['type'] == 'gitlab':
            tools.extend(get_gitlab(tool))
        elif tool['type'] == 'gitlab_org':
            tools.extend(get_gitlab_org(tool))
        elif tool['type'] == 'google_places':
            tools.extend(get_google_places(tool))
        elif tool['type'] == 'jira':
            tools.extend(get_jira(tool))
        elif tool['type'] == 'keycloack':
            tools.extend(get_keycloack(tool))
        elif tool['type'] == 'localgit':
            tools.extend(get_localgit(tool))
        elif tool['type'] == 'openapi':
            tools.extend(get_openapi(tool))
        elif tool['type'] == 'pandas':
            tools.extend(get_pandas(tool))
        elif tool['type'] == 'qtest':
            tools.extend(get_qtest(tool))
        elif tool['type'] == 'rally':
            tools.extend(get_rally(tool))
        elif tool['type'] == 'report_portal':
            tools.extend(get_report_portal(tool))
        elif tool['type'] in ['aws', 'azure', 'gcp', 'k8s']:
            tools.extend(get_cloud(tool['type'], tool))
        elif tool['type'] == 'sharepoint':
            tools.extend(get_sharepoint(tool))
        elif tool['type'] == 'sonar':
            tools.extend(get_sonar(tool))
        elif tool['type'] == 'sql':
            tools.extend(get_sql(tool))
        elif tool['type'] == 'testio':
            tools.extend(get_testio(tool))
        elif tool['type'] == 'testrail':
            tools.extend(get_testrail(tool))
        elif tool['type'] == 'xray_cloud':
            tools.extend(get_xray_cloud(tool))
        elif tool['type'] == 'yagmail':
            tools.extend(get_yagmail(tool))
        elif tool['type'] == 'zephyr':
            tools.extend(get_zephyr(tool))
        elif tool['type'] == 'zephyr_scale':
            tools.extend(get_zephyr_scale(tool))
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
        AlitaBitbucketToolkit.toolkit_config_schema(),
        AlitaGitHubToolkit.toolkit_config_schema(),
        AlitaGitlabSpaceToolkit.toolkit_config_schema(),
        AlitaGitlabToolkit.toolkit_config_schema(),
        AlitaLocalGitToolkit.toolkit_config_schema(),
        AlitaYagmailToolkit.toolkit_config_schema(),
        AWSToolkit.toolkit_config_schema(),
        AzureDevOpsPlansToolkit.toolkit_config_schema(),
        AzureDevOpsReposToolkit.toolkit_config_schema(),
        AzureDevOpsWikiToolkit.toolkit_config_schema(),
        AzureDevOpsWorkItemsToolkit.toolkit_config_schema(),
        AzureToolkit.toolkit_config_schema(),
        BrowserToolkit.toolkit_config_schema(),
        ConfluenceToolkit.toolkit_config_schema(),
        CustomOpenApiToolkit.toolkit_config_schema(),
        ElasticToolkit.toolkit_config_schema(),
        GCPToolkit.toolkit_config_schema(),
        GooglePlacesToolkit.toolkit_config_schema(),
        JiraToolkit.toolkit_config_schema(),
        KeycloakToolkit.toolkit_config_schema(),
        KubernetesToolkit.toolkit_config_schema(),
        PandasToolkit.toolkit_config_schema(),
        QtestToolkit.toolkit_config_schema(),
        RallyToolkit.toolkit_config_schema(),
        ReportPortalToolkit.toolkit_config_schema(),
        SharepointToolkit.toolkit_config_schema(),
        SonarToolkit.toolkit_config_schema(),
        SQLToolkit.toolkit_config_schema(),
        TestIOToolkit.toolkit_config_schema(),
        TestrailToolkit.toolkit_config_schema(),
        XrayToolkit.toolkit_config_schema(),
        ZephyrScaleToolkit.toolkit_config_schema(),
        ZephyrToolkit.toolkit_config_schema(),
    ]

