import logging
from importlib import import_module
from typing import Dict, List

# ado is an exceptional toolkit, unfortunately
from .ado import get_tools as get_ado_tools, supported_types as ado_supported_types


logger = logging.getLogger(__name__)

# Registry that holds the name of the toolkit, import path, get_tools function, and toolkit class
TOOLKIT_REGISTRY: list[Dict[str, str]] = [
    {
        "import_path": ".github",
        "get_function_name": "get_tools",
        "toolkit_class_name": "AlitaGitHubToolkit",
    },
    {
        "import_path": ".openapi",
        "get_function_name": "get_tools",
        "toolkit_class_name": "AlitaOpenAPIToolkit",
    },
    {
        "import_path": ".jira",
        "get_function_name": "get_tools",
        "toolkit_class_name": "JiraToolkit",
    },
    {
        "import_path": ".confluence",
        "get_function_name": "get_tools",
        "toolkit_class_name": "ConfluenceToolkit",
    },
    {
        "import_path": ".servicenow",
        "get_function_name": "get_tools",
        "toolkit_class_name": "ServiceNowToolkit",
    },
    {
        "import_path": ".gitlab",
        "get_function_name": "get_tools",
        "toolkit_class_name": "AlitaGitlabToolkit",
    },
    {
        "import_path": ".gitlab_org",
        "get_function_name": "get_tools",
        "toolkit_class_name": "AlitaGitlabSpaceToolkit",
    },
    {
        "import_path": ".zephyr",
        "get_function_name": "get_tools",
        "toolkit_class_name": "ZephyrToolkit",
    },
    {
        "import_path": ".browser",
        "get_function_name": "get_tools",
        "toolkit_class_name": "BrowserToolkit",
    },
    {
        "import_path": ".yagmail",
        "get_function_name": "get_tools",
        "toolkit_class_name": "AlitaYagmailToolkit",
    },
    {
        "import_path": ".report_portal",
        "get_function_name": "get_tools",
        "toolkit_class_name": "ReportPortalToolkit",
    },
    {
        "import_path": ".bitbucket",
        "get_function_name": "get_tools",
        "toolkit_class_name": "AlitaBitbucketToolkit",
    },
    {
        "import_path": ".testrail",
        "get_function_name": "get_tools",
        "toolkit_class_name": "TestrailToolkit",
    },
    {
        "import_path": ".testio",
        "get_function_name": "get_tools",
        "toolkit_class_name": "TestIOToolkit",
    },
    {
        "import_path": ".xray",
        "get_function_name": "get_tools",
        "toolkit_class_name": "XrayToolkit",
    },
    {
        "import_path": ".sharepoint",
        "get_function_name": "get_tools",
        "toolkit_class_name": "SharepointToolkit",
    },
    {
        "import_path": ".qtest",
        "get_function_name": "get_tools",
        "toolkit_class_name": "QtestToolkit",
    },
    {
        "import_path": ".zephyr_scale",
        "get_function_name": "get_tools",
        "toolkit_class_name": "ZephyrScaleToolkit",
    },
    {
        "import_path": ".zephyr_enterprise",
        "get_function_name": "get_tools",
        "toolkit_class_name": "ZephyrEnterpriseToolkit",
    },
    {
        "import_path": ".rally",
        "get_function_name": "get_tools",
        "toolkit_class_name": "RallyToolkit",
    },
    {
        "import_path": ".sql",
        "get_function_name": "get_tools",
        "toolkit_class_name": "SQLToolkit",
    },
    {
        "import_path": ".code.sonar",
        "get_function_name": "get_tools",
        "toolkit_class_name": "SonarToolkit",
    },
    {
        "import_path": ".google_places",
        "get_function_name": "get_tools",
        "toolkit_class_name": "GooglePlacesToolkit",
    },
    {
        "import_path": ".azure_ai.search",
        "get_function_name": "get_tools",
        "toolkit_class_name": "AzureSearchToolkit",
    },
    {
        "import_path": ".pandas",
        "get_function_name": "get_tools",
        "toolkit_class_name": "PandasToolkit",
    },
    {
        "import_path": ".figma",
        "get_function_name": "get_tools",
        "toolkit_class_name": "FigmaToolkit",
    },
    {
        "import_path": ".salesforce",
        "get_function_name": "get_tools",
        "toolkit_class_name": "SalesforceToolkit",
    },
    {
        "import_path": ".carrier",
        "get_function_name": "get_tools",
        "toolkit_class_name": "AlitaCarrierToolkit",
    },
    {
        "import_path": ".ocr",
        "get_function_name": "get_tools",
        "toolkit_class_name": "OCRToolkit",
    },
    {
        "import_path": ".pptx",
        "get_function_name": "get_tools",
        "toolkit_class_name": "PPTXToolkit",
    },
    {
        "import_path": ".ado.repos",
        "get_function_name": "get_tools",
        "toolkit_class_name": "AzureDevOpsReposToolkit",
    },
    {
        "import_path": ".ado.work_item",
        "get_function_name": "get_tools",
        "toolkit_class_name": "AzureDevOpsWorkItemsToolkit",
    },
    {
        "import_path": ".ado.wiki",
        "get_function_name": "get_tools",
        "toolkit_class_name": "AzureDevOpsWikiToolkit",
    },
    {
        "import_path": ".ado.test_plan",
        "get_function_name": "get_tools",
        "toolkit_class_name": "AzureDevOpsPlansToolkit",
    },
    {
        "import_path": ".elastic",
        "get_function_name": "get_tools",
        "toolkit_class_name": "ElasticToolkit",
    },
    {
        "import_path": ".custom_open_api",
        "get_function_name": "get_tools",
        "toolkit_class_name": "OpenApiToolkit",
    },
    {
        "import_path": ".localgit",
        "get_function_name": "get_tools",
        "toolkit_class_name": "AlitaLocalGitToolkit",
    },
    {
        "import_path": ".cloud.aws",
        "get_function_name": "get_tools",
        "toolkit_class_name": "AWSToolkit",
    },
    {
        "import_path": ".cloud.azure",
        "get_function_name": "get_tools",
        "toolkit_class_name": "AzureToolkit",
    },
    {
        "import_path": ".cloud.gcp",
        "get_function_name": "get_tools",
        "toolkit_class_name": "GCPToolkit",
    },
    {
        "import_path": ".cloud.k8s",
        "get_function_name": "get_tools",
        "toolkit_class_name": "KubernetesToolkit",
    },
    {
        "import_path": ".keycloak",
        "get_function_name": "get_tools",
        "toolkit_class_name": "KeycloakToolkit",
    }
]


# Dynamically import everything once and store references
IMPORTED_TOOLKITS = {}
for toolkit_info in TOOLKIT_REGISTRY:
    import_path = toolkit_info['import_path']
    try:
        mod = import_module(import_path, package=__name__)
        try:
            toolkit_name = getattr(mod, 'name')
            get_function = getattr(mod, toolkit_info["get_function_name"])
            toolkit_class = getattr(mod, toolkit_info["toolkit_class_name"])
        except AttributeError as e:
            logger.error(f'Error importing toolkit {toolkit_info["import_path"]}: {e}')
            raise
        if toolkit_name and get_function and toolkit_class:
            IMPORTED_TOOLKITS[toolkit_name] = {
                "get_function": get_function,
                "toolkit_class": toolkit_class,
                'name': toolkit_name
            }
    except ImportError as e:
        logger.warning(
            "Could not import '%s' library; skipping. Reason: %s",
            toolkit_info['import_path'], e
        )


def get_tools(tools_list: list[dict], alita: "AlitaClient", llm: "LLMLikeObject", *args, **kwargs) -> List[dict]:


    tools = []
    for tool in tools_list:
        tool.setdefault("settings", {})
        tool["settings"]["alita"] = alita
        tool["settings"]["llm"] = llm

        # Identify the toolkit name or type
        ttype: str = tool["type"]

        # If we have a dynamic import function for the type
        if ttype in IMPORTED_TOOLKITS:
            toolkit_info = IMPORTED_TOOLKITS[ttype]
            try:
                toolkit_tools = toolkit_info["get_function"](tool)
                tools.extend(toolkit_tools)
            except Exception as e:
                logger.warning("Error getting tools for '%s'. Reason: %s", ttype, e)
        elif ttype in ado_supported_types:
            try:
                toolkit_tools = get_ado_tools(tool_type=ttype, tool=tool)
                tools.extend(toolkit_tools)
            except Exception as e:
                logger.warning("Error getting tools for '%s'. Reason: %s", ttype, e)
        else:
            # Fallback for custom modules
            if tool.get("settings", {}).get("module"):
                try:
                    settings = tool.get("settings", {})
                    mod = import_module(settings.pop("module"))
                    tkitclass = getattr(mod, settings.pop("class"))
                    toolkit = tkitclass.get_toolkit(**settings)
                    tools.extend(toolkit.get_tools())
                except Exception as e:
                    logger.warning(
                        "Error in getting custom toolkit [%s]. Skipping. Reason: %s",
                        tool.get("type"), e
                    )
            else:
                logger.warning(
                    "Unrecognized toolkit '%s' and no custom module provided. Skipping.",
                    ttype
                )
    return tools


def get_toolkits():
    schemas = []
    for ttype, info in IMPORTED_TOOLKITS.items():
        # If we have a valid class ref, call the .toolkit_config_schema(), etc.
        if info.get("toolkit_class"):
            try:
                config_schema = info["toolkit_class"].toolkit_config_schema()
                schemas.append(config_schema)
            except AttributeError:
                logger.warning(
                    "Toolkit class for '%s' does not have 'toolkit_config_schema'. Skipping.",
                    ttype
                )
    return schemas


def get_supported_tool_types() -> List[str]:
    """
    Get a list of all supported tool types.
    
    Returns:
        List of supported tool type strings
    """
    result = set(IMPORTED_TOOLKITS.keys())
    result.update(ado_supported_types)
    return list(result)
