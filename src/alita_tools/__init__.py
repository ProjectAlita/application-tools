import logging
from importlib import import_module

from .github import AlitaGitHubToolkit
from .gitlab import AlitaGitlabToolkit
from .openapi import AlitaOpenAPIToolkit
from .jira import JiraToolkit
from .confluence import ConfluenceToolkit
from .browser import BrowserToolkit
from .zephyr import ZephyrToolkit
from .yagmail import AlitaYagmailToolkit
from .yagmail.yagmail_wrapper import SMTP_SERVER

logger = logging.getLogger(__name__)

def get_tools(tools_list, *args, **kwargs):
    tools = []
    for tool in tools_list:
        if tool['type'] == 'openapi':
            headers = {}
            if tool['settings'].get('authentication'):
                if tool['settings']['authentication']['type'] == 'api_key':
                    auth_type = tool['settings']['authentication']['settings']['auth_type']
                    auth_key = tool["settings"]["authentication"]["settings"]["api_key"]
                    if auth_type.lower() == 'bearer':
                        headers['Authorization'] = f'Bearer {auth_key}'
                    if auth_type.lower() == 'basic':
                        headers['Authorization'] = f'Basic {auth_key}'
                    if auth_type.lower() == 'custom':
                        headers[
                            tool["settings"]["authentication"]["settings"]["custom_header_name"]] = f'{auth_key}'
            tools.extend(AlitaOpenAPIToolkit.get_toolkit(
                openapi_spec=tool['settings']['schema_settings'],
                selected_tools=tool['settings'].get('selected_tools', []),
                headers={}
            ).get_tools())
        elif tool['type'] == 'github':
            github_toolkit = AlitaGitHubToolkit().get_toolkit(
                selected_tools=tool['settings'].get('selected_tools', []),
                github_repository=tool['settings']['repository'],
                active_branch=tool['settings']['active_branch'],
                github_base_branch=tool['settings']['base_branch'],
                github_access_token=tool['settings'].get('access_token', ''),
                github_username=tool['settings'].get('username', ''),
                github_password=tool['settings'].get('password', '')
            )
            tools.extend(github_toolkit.get_tools())
        elif tool['type'] == 'jira':
            jira_tools = JiraToolkit().get_toolkit(
                selected_tools=tool['settings'].get('selected_tools', []),
                base_url=tool['settings']['base_url'],
                cloud=tool['settings'].get('cloud', True),
                api_key=tool['settings'].get('api_key', None),
                username=tool['settings'].get('username', None),
                token=tool['settings'].get('token', None),
                limit=tool['settings'].get('limit', 5),
                additional_fields=tool['settings'].get('additional_fields', []),
                verify_ssl=tool['settings'].get('verify_ssl', True))
            tools.extend(jira_tools.get_tools())
        elif tool['type'] == 'confluence':
            confluence_tools = ConfluenceToolkit().get_toolkit(
                selected_tools=tool['settings'].get('selected_tools', []),
                base_url=tool['settings']['base_url'],
                cloud=tool['settings'].get('cloud', True),
                api_key=tool['settings'].get('api_key', None),
                username=tool['settings'].get('username', None),
                token=tool['settings'].get('token', None),
                limit=tool['settings'].get('limit', 5),
                additional_fields=tool['settings'].get('additional_fields', []),
                verify_ssl=tool['settings'].get('verify_ssl', True))
            tools.extend(confluence_tools.get_tools())
        elif tool['type'] == 'gitlab':
            gitlab_tools = AlitaGitlabToolkit().get_toolkit(
                selected_tools=tool['settings'].get('selected_tools', []),
                url=tool['settings']['url'],
                repository=tool['settings']['repository'],
                branch=tool['settings']['branch'],
                private_token=tool['settings']['private_token']
            )
            tools.extend(gitlab_tools.get_tools())
        elif tool['type'] == 'zephyr':
            zephyr_tools = ZephyrToolkit().get_toolkit(
                selected_tools=tool['settings'].get('selected_tools', []),
                base_url=tool['settings']['base_url'],
                user_name=tool['settings']['user_name'],
                password=tool['settings']['password'])
            tools.extend(zephyr_tools.get_tools())
        elif tool['type'] == 'browser':
            browser_tools = BrowserToolkit().get_toolkit(
                selected_tools=tool['settings'].get('selected_tools', []),
                google_api_key=tool['settings'].get('google_api_key'),
                google_cse_id=tool['settings'].get("google_cse_id")
            )
            tools.extend(browser_tools.get_tools())
        elif tool['type'] == 'yagmail':
            yagmailToolkit = AlitaYagmailToolkit().get_toolkit(
                selected_tools=tool['settings'].get('selected_tools', []),
                host=tool['settings'].get('host', SMTP_SERVER),
                username=tool['settings'].get('username'),
                password=tool['settings'].get("password")
            )
            tools.extend(yagmailToolkit.get_tools())
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