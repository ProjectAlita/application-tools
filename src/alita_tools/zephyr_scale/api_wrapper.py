import json
import logging
from typing import Any, Optional, List, Dict

from pydantic import model_validator, BaseModel, SecretStr
from langchain_core.tools import ToolException
from pydantic import create_model, PrivateAttr
from pydantic.fields import Field

from ..elitea_base import BaseToolApiWrapper

logger = logging.getLogger(__name__)

ZephyrGetTestCases = create_model(
    "ZephyrGetTestCases",
    project_key=(str, Field(description="Jira project key filter")),
    folder_id=(Optional[str], Field(description="Folder ID filter", default=None)),
    maxResults=(Optional[int], Field(
        description="A hint as to the maximum number of results to return in each call. Must be an integer >= 1.", 
        default=10)),
    startAt=(Optional[int], Field(
        description="Zero-indexed starting position. Should be a multiple of maxResults.",
        default=0))
)

ZephyrGetTestCase = create_model(
    "ZephyrGetTestCase",
    test_case_key=(str, Field(description="Test case key")),
)

ZephyrCreateTestCase = create_model(
    "TestCaseInput",
    project_key=(str, Field(description="Jira project key.")),
    test_case_name=(str, Field(description="Name of the test case.")),
    additional_fields=(str, Field(
        description=("JSON string containing additional optional fields such as: "
                     "'objective' (description of the objective), "
                     "'precondition' (any conditions that need to be met), "
                     "'estimatedTime' (estimated duration in milliseconds), "
                     "'componentId' (ID of a component from Jira), "
                     "'priorityName' (the priority name), "
                     "'statusName' (the status name), "
                     "'folderId' (ID of a folder to place the entity within), "
                     "'ownerId' (Atlassian Account ID of the Jira user), "
                     "'labels' (array of labels associated to this entity), "
                     "'customFields' (object containing custom fields such as build number, release date, etc.)."
                     "Dates should be in the format 'yyyy-MM-dd', and multi-line text fields should denote a new line with the <br> syntax."),
        default="{}"
    ))
)

ZephyrTestStepsInputModel = create_model(
    "ZephyrTestStepsInputModel",
    test_case_key=(str, Field(
        description="The key of the test case. Test case keys are of the format [A-Z]+-T[0-9]+")),
    tc_mode=(str, Field(
        description=("Valid values: 'APPEND', 'OVERWRITE'. "
                     "'OVERWRITE' deletes and recreates the test steps and associated custom field values using the provided input. "
                     "Attachments for existing steps are kept, but those for missing steps are deleted permanently. "
                     "'APPEND' only adds extra steps to your test steps."))),
    items=(str, Field(
        description=("JSON string representing the list of test steps. Each step should be an object containing either 'inline' or 'testCase'. "
                     "They should only include one of these fields at a time. Example: "
                     "[{'inline': {'description': 'Attempt to login to the application', 'testData': 'Username = SmartBear Password = weLoveAtlassian', "
                     "'expectedResult': 'Login succeeds, web-app redirects to the dashboard view', 'customFields': {'Build Number': 20, "
                     "'Release Date': '2020-01-01', 'Pre-Condition(s)': 'User should have logged in. <br> User should have navigated to the administration panel.', "
                     "'Implemented': false, 'Category': ['Performance', 'Regression'], 'Tester': 'fa2e582e-5e15-521e-92e3-47e6ca2e7256'}, 'reflectRef': 'Not available yet'}, "
                     "'testCase': {'self': 'string', 'testCaseKey': 'PROJ-T123', 'parameters': [{'name': 'username', 'type': 'DEFAULT_VALUE', 'value': 'admin'}]}}]")
    ))
)

ZephyrGetFolders = create_model(
    "ZephyrGetFolders",
    maxResults=(Optional[int], Field(
        description=("A hint as to the maximum number of results to return in each call. "
                     "Must be an integer >= 1. Default is 10. Note that the server may impose a lower limit."),
        default=10)),
    startAt=(Optional[int], Field(
        description=("Zero-indexed starting position. Should be a multiple of maxResults. "
                     "Must be an integer >= 0. Default is 0."),
        default=0)),
    projectKey=(Optional[str], Field(
        description="Jira project key filter. Must match the pattern [A-Z][A-Z_0-9]+.",
        default=None)),
    folderType=(Optional[str], Field(
        description=("Folder type filter. Valid values are 'TEST_CASE', 'TEST_PLAN', or 'TEST_CYCLE'."),
        default=None))
)

ZephyrUpdateTestCase = create_model(
    "ZephyrUpdateTestCase",
    test_case_key=(str, Field(description="The key of the test case")),
    test_case_id=(int, Field(description="Integer id of the test")),
    name=(str, Field(description="Test case name")),
    project_id=(int, Field(description="Project id")),
    priority_id=(int, Field(description="Priority id")),
    status_id=(int, Field(description="Status id")),
    additional_fields=(str, Field(
        description="JSON string containing any additional fields that need to be updated",
        default="{}")
    )
)

ZephyrGetLinks = create_model(
    "ZephyrGetLinks",
    test_case_key=(str, Field(description="The key of the test case"))
)

ZephyrCreateIssueLinks = create_model(
    "ZephyrCreateIssueLinks",
    test_case_key=(str, Field(description="The key of the test case")),
    issue_id=(int, Field(description="The ID of the Jira issue to link"))
)

ZephyrCreateWebLinks = create_model(
    "ZephyrCreateWebLinks",
    test_case_key=(str, Field(description="The key of the test case")),
    url=(str, Field(description="The URL to link")),
    additional_fields=(str, Field(
        description="JSON string containing any additional fields for the web link",
        default="{}")
    )
)

ZephyrGetVersions = create_model(
    "ZephyrGetVersions",
    test_case_key=(str, Field(description="The key of the test case")),
    maxResults=(Optional[int], Field(
        description="A hint as to the maximum number of results to return in each call", 
        default=10)),
    startAt=(Optional[int], Field(
        description="Zero-indexed starting position. Should be a multiple of maxResults.",
        default=0))
)

ZephyrGetVersion = create_model(
    "ZephyrGetVersion",
    test_case_key=(str, Field(description="The key of the test case")),
    version=(str, Field(description="The version number"))
)

ZephyrGetTestScript = create_model(
    "ZephyrGetTestScript",
    test_case_key=(str, Field(description="The key of the test case"))
)

ZephyrCreateTestScript = create_model(
    "ZephyrCreateTestScript",
    test_case_key=(str, Field(description="The key of the test case")),
    script_type=(str, Field(description="The type of the script")),
    text=(str, Field(description="The text content of the script"))
)

ZephyrSearchTestCases = create_model(
    "ZephyrSearchTestCases",
    project_id=(str, Field(description="Jira project key filter")),
    search_term=(Optional[str], Field(description="Optional search term to filter test cases", default=None)),
    max_results=(Optional[int], Field(description="Maximum number of results to query from the API", default=1000)),
    start_at=(Optional[int], Field(description="Zero-indexed starting position", default=0)),
    order_by=(Optional[str], Field(description="Field to order results by", default="name")),
    order_direction=(Optional[str], Field(description="Order direction", default="ASC")),
    archived=(Optional[bool], Field(description="Include archived test cases", default=False)),
    fields=(Optional[List[str]], Field(description="Fields to include in the response (default: key, name)", default=["key", "name"])),
    limit_results=(Optional[int], Field(description="Maximum number of filtered results to return", default=10)),
    folder_id=(Optional[str], Field(description="Filter test cases by folder ID", default=None)),
    folder_name=(Optional[str], Field(description="Filter test cases by folder name (full or partial)", default=None)),
    exact_folder_match=(Optional[bool], Field(description="Whether to match the folder name exactly or allow partial matches", default=False)),
    folder_path=(Optional[str], Field(description="Filter test cases by folder path (e.g., 'Root/Parent/Child')", default=None)),
    include_subfolders=(Optional[bool], Field(description="Include test cases from subfolders of matching folders", default=True)),
    labels=(Optional[List[str]], Field(description="Filter test cases by labels", default=None))
)

ZephyrGetTestsRecursive = create_model(
    "ZephyrGetTestsRecursive",
    project_key=(Optional[str], Field(description="Jira project key filter", default=None)),
    folder_id=(Optional[str], Field(description="Parent folder ID to start the recursive search from", default=None)),
    maxResults=(Optional[int], Field(
        description="A hint as to the maximum number of results to return in each call. Must be an integer >= 1.", 
        default=100)),
    startAt=(Optional[int], Field(
        description="Zero-indexed starting position. Should be a multiple of maxResults.",
        default=0))
)

ZephyrGetTestsByFolderName = create_model(
    "ZephyrGetTestsByFolderName",
    project_key=(str, Field(description="Jira project key filter")),
    folder_name=(str, Field(description="Full or partial folder name to search for")),
    exact_match=(Optional[bool], Field(
        description="Whether to match the folder name exactly or allow partial matches",
        default=False)),
    include_subfolders=(Optional[bool], Field(
        description="Whether to include test cases from subfolders",
        default=True)),
    maxResults=(Optional[int], Field(
        description="A hint as to the maximum number of results to return in each call. Must be an integer >= 1.",
        default=100)),
    startAt=(Optional[int], Field(
        description="Zero-indexed starting position. Should be a multiple of maxResults.",
        default=0))
)

ZephyrGetTestsByFolderPath = create_model(
    "ZephyrGetTestsByFolderPath",
    project_key=(str, Field(description="Jira project key filter")),
    folder_path=(str, Field(description="Full folder path (e.g., 'Root/Parent/Child')")),
    include_subfolders=(Optional[bool], Field(
        description="Whether to include test cases from subfolders",
        default=True)),
    maxResults=(Optional[int], Field(
        description="A hint as to the maximum number of results to return in each call. Must be an integer >= 1.",
        default=100)),
    startAt=(Optional[int], Field(
        description="Zero-indexed starting position. Should be a multiple of maxResults.",
        default=0))
)


class ZephyrScaleApiWrapper(BaseToolApiWrapper):
    # url for a Zephyr server
    base_url: Optional[str] = ""
    # auth with Jira token (cloud & server)
    token: Optional[SecretStr] = ""
    # auth with username and password
    username: Optional[str] = ""
    password: Optional[SecretStr] = ""
    # auth with a session cookie dict
    cookies: Optional[str] = ""

    # max results to show
    max_results: Optional[int] = 100

    _is_cloud: bool = False
    _api: Any = PrivateAttr()

    class Config:
        arbitrary_types_allowed = True

    @model_validator(mode='before')
    @classmethod
    def validate_toolkit(cls, values):
        try:
            from zephyr import ZephyrScale
        except ImportError:
            raise ImportError(
                "`zephyr scale package` package not found, please run "
                "`pip install zephyr-python-api`"
            )

        # Verify authentication
        if not (values.get('token') or (values.get('username') and values.get('password')) or values.get('cookies')):
            raise ToolException(
                f"Define correct authentication flow: 1) token, 2) credential (username + password), 3) cookies")

        # auth = {"token": values['token']}
        # if values['username'] and values['password']:
        #     auth = {"username": values['username'], "password": values['password']}
        # elif 'cookies' in values and values['cookies']:
        #     auth = {"cookies": values['cookies']}
        #
        # if 'base_url' in values and values['base_url']:
        #     cls._api = ZephyrScale.server_api(base_url=values['base_url'], **auth).api
        # else:
        # Cloud version is enabled for now
        cls._api = ZephyrScale(token=values['token']).api
        return values

    def get_tests(self, project_key: str = None, folder_id: str = None, maxResults: Optional[int] = 10, startAt: Optional[int] = 0):
        """Retrieves all test cases. Query parameters can be used to filter the results.
        
        Args:
            project_key: Jira project key filter
            folder_id: Folder ID filter
            maxResults: A hint as to the maximum number of results to return in each call
            startAt: Zero-indexed starting position. Should be a multiple of maxResults
        """

        kwargs = {}
        if project_key:
            kwargs["projectKey"] = project_key
        if folder_id:
            kwargs["folderId"] = folder_id
        if maxResults:
            kwargs["maxResults"] = maxResults
        if startAt:
            kwargs["startAt"] = startAt

        test_cases = self._api.test_cases.get_test_cases(**kwargs)
        # Convert each test case to a string and join them with new line
        test_cases_str = str(self._parse_tests(test_cases))
        return f"Extracted tests: {test_cases_str}"

    def get_test(self, test_case_key: str):
        """Returns a test case for the given key
        
        Args:
            test_case_key: The key of the test case
        """

        try:
            test_case = self._api.test_cases.get_test_case(test_case_key)
        except Exception as e:
            return ToolException(f"Unable to extract test case with key: {test_case_key}:\n{str(e)}")
        return f"Extracted tests: {str(test_case)}"

    def get_test_steps(self, test_case_key: str, **kwargs):
        """Returns the test steps for the given test case. Provides a paged response.
        
        Args:
            test_case_key: The key of the test case
            **kwargs: Additional parameters like maxResults and startAt
        """

        try:
            test_case_steps = self._api.test_cases.get_test_steps(test_case_key, **kwargs)
            steps_list = [str(step) for step in test_case_steps]
            all_steps_concatenated = '\n'.join(steps_list)
        except Exception as e:
            return ToolException(f"Unable to extract test case steps from test case with key: {test_case_key}:\n{str(e)}")
        return f"Extracted test steps: {all_steps_concatenated}"

    def create_test_case(self, project_key: str, test_case_name: str, additional_fields: str) -> str:
        """Creates a test case. Fields priorityName and statusName will be set to default values if not informed.
        Args:
            project_key: Jira project key
            test_case_name: Test case name
            additional_fields: JSON string containing additional optional fields
        
        NOTE: Please note that if the user specifies a folder name, it is necessary to execute the get_folders() function first to find the correct mapping
        """

        try:
            create_test_case_response = self._api.test_cases.create_test_case(
                project_key=project_key,
                name=test_case_name,
                **json.loads(additional_fields) if additional_fields else {}
            )
            return f"Test case with name `{test_case_name}` was created: {str(create_test_case_response)}"
        except Exception as e:
            return ToolException(f"Unable to create test case with name: {test_case_name}:\n{str(e)}")

    def add_test_steps(self, test_case_key: str, tc_mode: str, items: str) -> str:
        """Assigns a series of test steps to a test case.
        
        Args:
            test_case_key: The key of the test case
            tc_mode: Valid values: 'APPEND', 'OVERWRITE'
            items: JSON string representing the list of test steps
        """

        try:
            add_steps_response = self._api.test_cases.post_test_steps(
                test_case_key,
                tc_mode,
                json.loads(items)
            )
            return f"Steps for test case `{test_case_key}` were added/updated: {str(add_steps_response)}"
        except Exception as e:
            return ToolException(f"Unable to add/update steps for test case with key: {test_case_key}:\n{str(e)}")

    def get_folders(self,
            maxResults: Optional[int] = 10,
            startAt: Optional[int] = 0,
            projectKey: Optional[str] = None,
            folderType: Optional[str] = None
    ):
        """Retrieves all folders. Query parameters can be used to filter the results: maxResults, startAt, projectKey, folderType"""

        folders_str = []
        for folder in self._api.folders.get_folders(maxResults=maxResults, startAt=startAt,
                                                    projectKey=projectKey, folderType=folderType):
            folders_str.append(folder)
        return f"Extracted folders: {folders_str}"

    def update_test_case(self, test_case_key: str, test_case_id: int, name: str, project_id: int, priority_id: int, status_id: int, **kwargs) -> str:
        """Updates an existing test case.
        
        Args:
            test_case_key: The key of the test case
            test_case_id: Integer id of the test
            name: Test case name
            project_id: Project id
            priority_id: Priority id
            status_id: Status id
            **kwargs: Additional parameters to update
        """
        
        try:
            json_data = {
                "id": test_case_id,
                "key": test_case_key,
                "name": name,
                "project": {"id": project_id},
                "priority": {"id": priority_id},
                "status": {"id": status_id}
            }
            
            if kwargs:
                json_data.update(kwargs)
                
            update_response = self._api.test_cases.update_test_case(
                test_case_key,
                test_case_id,
                name,
                project_id,
                priority_id,
                status_id,
                **kwargs
            )
            return f"Test case `{test_case_key}` was updated: {str(update_response)}"
        except Exception as e:
            return ToolException(f"Unable to update test case with key: {test_case_key}:\n{str(e)}")
            
    def get_links(self, test_case_key: str) -> str:
        """Returns links for a test case with specified key
        
        Args:
            test_case_key: The key of the test case
        """
        
        try:
            links = self._api.test_cases.get_links(test_case_key)
            return f"Links for test case `{test_case_key}`: {str(links)}"
        except Exception as e:
            return ToolException(f"Unable to get links for test case with key: {test_case_key}:\n{str(e)}")
            
    def create_issue_links(self, test_case_key: str, issue_id: int) -> str:
        """Creates a link between a test case and a Jira issue
        
        Args:
            test_case_key: The key of the test case
            issue_id: The ID of the Jira issue to link
        NOTE: The issue ID should be a valid Jira issue ID. If JIRA issue key is provided instead, it's requrid to get issue id first either by asking user or by using JIRA tooking (if avialable).
        """
        
        try:
            link_response = self._api.test_cases.create_issue_links(test_case_key, issue_id)
            return f"Issue link created for test case `{test_case_key}` with issue ID `{issue_id}`: {str(link_response)}"
        except Exception as e:
            return ToolException(f"Unable to create issue link for test case with key: {test_case_key}:\n{str(e)}")
    
    def create_web_links(self, test_case_key: str, url: str, additional_fields: str) -> str:
        """Creates a link between a test case and a generic URL
        
        Args:
            test_case_key: The key of the test case
            url: The URL to link
            additional_fields: JSON string containing any additional fields for the web link
        """
        
        try:
            additional_params = json.loads(additional_fields) if additional_fields else {}
            web_link_response = self._api.test_cases.create_web_links(test_case_key, url, **additional_params)
            return f"Web link created for test case `{test_case_key}` with URL `{url}`: {str(web_link_response)}"
        except Exception as e:
            return ToolException(f"Unable to create web link for test case with key: {test_case_key}:\n{str(e)}")
    
    def get_versions(self, test_case_key: str, maxResults: Optional[int] = 10, startAt: Optional[int] = 0) -> str:
        """Returns all test case versions for a test case with specified key. Response is ordered by most recent first.
        
        Args:
            test_case_key: The key of the test case
            maxResults: A hint as to the maximum number of results to return in each call
            startAt: Zero-indexed starting position. Should be a multiple of maxResults
        """
        
        try:
            versions = self._api.test_cases.get_versions(test_case_key, maxResults=maxResults, startAt=startAt)
            versions_list = [str(version) for version in versions]
            all_versions = '\n'.join(versions_list)
            return f"Versions for test case `{test_case_key}`: {all_versions}"
        except Exception as e:
            return ToolException(f"Unable to get versions for test case with key: {test_case_key}:\n{str(e)}")
    
    def get_version(self, test_case_key: str, version: str) -> str:
        """Retrieves a specific version of a test case"""
        
        try:
            version_data = self._api.test_cases.get_version(test_case_key, version)
            return f"Version {version} of test case `{test_case_key}`: {str(version_data)}"
        except Exception as e:
            return ToolException(f"Unable to get version {version} for test case with key: {test_case_key}:\n{str(e)}")
    
    def get_test_script(self, test_case_key: str) -> str:
        """Returns the test script for the given test case"""
        
        try:
            test_script = self._api.test_cases.get_test_script(test_case_key)
            return f"Test script for test case `{test_case_key}`: {str(test_script)}"
        except Exception as e:
            return ToolException(f"Unable to get test script for test case with key: {test_case_key}:\n{str(e)}")
    
    def create_test_script(self, test_case_key: str, script_type: str, text: str) -> str:
        """Creates or updates the test script for a test case"""
        
        try:
            script_response = self._api.test_cases.create_test_script(test_case_key, script_type, text)
            return f"Test script created/updated for test case `{test_case_key}`: {str(script_response)}"
        except Exception as e:
            return ToolException(f"Unable to create/update test script for test case with key: {test_case_key}:\n{str(e)}")
            
    def search_test_cases(self, project_id: str, search_term: Optional[str] = None, 
                         max_results: Optional[int] = 1000, start_at: Optional[int] = 0,
                         order_by: Optional[str] = "name", order_direction: Optional[str] = "ASC", 
                         archived: Optional[bool] = False, fields: Optional[List[str]] = ["key", "name"],
                         limit_results: Optional[int] = None, folder_id: Optional[str] = None,
                         folder_name: Optional[str] = None, exact_folder_match: Optional[bool] = False,
                         folder_path: Optional[str] = None, include_subfolders: Optional[bool] = True,
                         labels: Optional[List[str]] = None) -> str:
        """Searches for test cases using custom search API.
        
        Args:
            project_id: Jira project key (e.g., "SIT", "PROJ")
            search_term: Optional search term to filter test cases
            max_results: Maximum number of results to query from the API
            start_at: Zero-indexed starting position
            order_by: Field to order results by
            order_direction: Order direction (ASC or DESC)
            archived: Include archived test cases
            fields: Fields to include in the response (default: key, name)
            limit_results: Maximum number of filtered results to return
            folder_id: Filter test cases by folder ID
            folder_name: Filter test cases by folder name (full or partial)
            exact_folder_match: Whether to match the folder name exactly or allow partial matches
            folder_path: Filter test cases by folder path (e.g., 'Root/Parent/Child')
            include_subfolders: Include test cases from subfolders of matching folders
            labels: Filter test cases by labels
        """
        try:
            # Use the Python SDK for searching test cases
            logger.debug("Searching test cases using the Python SDK")
            
            # First, handle folder name and folder path search
            target_folder_ids = []
            
            # If we have folder_name or folder_path, we need to build the folder hierarchy
            if folder_name or folder_path:
                # Get all folders in the project
                all_folders = []
                try:
                    for folder in self._api.folders.get_folders(
                        maxResults=max_results, 
                        projectKey=project_id, 
                        folderType="TEST_CASE"
                    ):
                        all_folders.append(folder)
                except Exception as e:
                    return ToolException(f"Error getting folders: {str(e)}")
                
                # Build folder hierarchy
                folder_hierarchy = {}
                for folder in all_folders:
                    folder_id_val = folder.get('id')
                    parent_id = folder.get('parentId')
                    if folder_id_val not in folder_hierarchy:
                        folder_hierarchy[folder_id_val] = {
                            'folder': folder,
                            'children': []
                        }
                    else:
                        folder_hierarchy[folder_id_val]['folder'] = folder
                    
                    if parent_id:
                        if parent_id not in folder_hierarchy:
                            folder_hierarchy[parent_id] = {
                                'folder': None,
                                'children': [folder_id_val]
                            }
                        else:
                            folder_hierarchy[parent_id]['children'].append(folder_id_val)
                
                # Handle folder name search
                if folder_name:
                    # Find folders matching the name
                    for folder in all_folders:
                        folder_name_val = folder.get('name', '')
                        if exact_folder_match:
                            if folder_name_val == folder_name:
                                target_folder_ids.append(folder.get('id'))
                        else:
                            if folder_name.lower() in folder_name_val.lower():
                                target_folder_ids.append(folder.get('id'))
                
                # Handle folder path search
                if folder_path:
                    folder_paths = {}
                    root_folders = []
                    
                    # Identify root folders
                    for folder in all_folders:
                        if not folder.get('parentId'):
                            root_folders.append(folder.get('id'))
                    
                    # Function to build full paths for each folder
                    def build_folder_paths(folder_id, current_path=""):
                        if folder_id not in folder_hierarchy or not folder_hierarchy[folder_id]['folder']:
                            return
                        
                        folder_name = folder_hierarchy[folder_id]['folder'].get('name', '')
                        if current_path:
                            full_path = f"{current_path}/{folder_name}"
                        else:
                            full_path = folder_name
                        
                        folder_paths[folder_id] = full_path
                        
                        # Process children
                        for child_id in folder_hierarchy[folder_id]['children']:
                            build_folder_paths(child_id, full_path)
                    
                    # Build paths starting from root folders
                    for root_id in root_folders:
                        build_folder_paths(root_id)
                    
                    # Find the folder matching the exact path
                    for folder_id, path in folder_paths.items():
                        if path == folder_path:
                            target_folder_ids.append(folder_id)
                            break
                
                # If include_subfolders is True, add all subfolders of matching folders
                if include_subfolders and target_folder_ids:
                    # Function to recursively collect subfolders
                    def collect_subfolders(parent_folder_id, collected_folders=None):
                        if collected_folders is None:
                            collected_folders = set()
                        
                        if parent_folder_id not in folder_hierarchy or parent_folder_id in collected_folders:
                            return
                        
                        collected_folders.add(parent_folder_id)
                        
                        for child_id in folder_hierarchy[parent_folder_id].get('children', []):
                            if child_id not in collected_folders:
                                target_folder_ids.append(child_id)
                                collect_subfolders(child_id, collected_folders)
                    
                    # Start recursive collection for each matching folder
                    original_target_ids = target_folder_ids.copy()
                    for folder_id in original_target_ids:
                        collect_subfolders(folder_id)
                
                # Remove duplicates from target folder IDs
                target_folder_ids = list(set(target_folder_ids))
                
                # If we have target folder IDs but no folder_id is specified, use the first one
                if target_folder_ids and not folder_id:
                    folder_id = target_folder_ids[0]
            
            # Prepare parameters for the SDK call
            params = {
                "projectKey": project_id,
                "maxResults": max_results,
                "startAt": start_at
            }
            
            # Add folder_id if provided or found through folder name/path search
            if folder_id:
                params["folderId"] = folder_id
            
            # Get test cases from the API
            all_test_cases = []
            
            # If we have multiple target folder IDs, get test cases from each folder
            if target_folder_ids and include_subfolders:
                for target_id in target_folder_ids:
                    folder_params = params.copy()
                    folder_params["folderId"] = target_id
                    try:
                        test_cases = self._api.test_cases.get_test_cases(**folder_params)
                        all_test_cases.extend(test_cases)
                    except Exception as e:
                        logger.warning(f"Error getting test cases from folder {target_id}: {str(e)}")
            else:
                # Just use the standard params (which might include a single folder_id)
                all_test_cases = self._api.test_cases.get_test_cases(**params)
            
            # Apply filtering based on search term and labels
            filtered_cases = []
            for tc in all_test_cases:
                # Apply search term filter if provided
                search_match = True
                if search_term:
                    search_match = (search_term.lower() in tc.get('name', '').lower() or 
                                    search_term.lower() in tc.get('key', '').lower())
                
                # Apply labels filter if provided
                labels_match = True
                if labels and len(labels) > 0:
                    tc_labels = tc.get('labels', [])
                    # Check if at least one of the specified labels exists in the test case
                    labels_match = any(label in tc_labels for label in labels)
                
                # Add test case if it matches all filters
                if search_match and labels_match:
                    filtered_cases.append(tc)
            
            # Sort the results if needed
            if order_by and filtered_cases:
                reverse = order_direction.upper() == "DESC"
                filtered_cases.sort(key=lambda x: x.get(order_by, ''), reverse=reverse)
            
            # Limit the number of results if specified
            if limit_results is not None and limit_results < len(filtered_cases):
                filtered_cases = filtered_cases[:limit_results]
            
            # Keep only the requested fields for each test case
            result_cases = []
            for tc in filtered_cases:
                result_case = {}
                for field in fields:
                    if field in tc:
                        result_case[field] = tc[field]
                result_cases.append(result_case)
            
            # Build a helpful response message
            response_details = []
            if folder_name:
                response_details.append(f"folder name '{folder_name}'")
            if folder_path:
                response_details.append(f"folder path '{folder_path}'")
            if folder_id:
                response_details.append(f"folder ID '{folder_id}'")
            if search_term:
                response_details.append(f"search term '{search_term}'")
            if labels:
                response_details.append(f"labels {labels}")
            
            search_details = " and ".join(response_details)
            message = f"Found {len(result_cases)} test cases"
            if search_details:
                message += f" matching {search_details}"
            
            return f"{message}: {json.dumps(result_cases, indent=2)}"
                
        except Exception as e:
            return ToolException(f"Error searching test cases: {str(e)}")

    def get_tests_recursive(self, project_key: str = None, folder_id: str = None, maxResults: Optional[int] = 100, startAt: Optional[int] = 0):
        """Retrieves all test cases recursively from a folder and all its subfolders.
        
        Args:
            project_key: Jira project key filter
            folder_id: Parent folder ID to start the recursive search from
            maxResults: A hint as to the maximum number of results to return in each call
            startAt: Zero-indexed starting position. Should be a multiple of maxResults
            
        Returns:
            A string with all test cases found in the folder and its subfolders
        """
        # Store all test cases
        all_test_cases = []
        
        # First, get all test cases from the specified folder
        kwargs = {}
        if project_key:
            kwargs["projectKey"] = project_key
        if folder_id:
            kwargs["folderId"] = folder_id
        kwargs["maxResults"] = maxResults
        kwargs["startAt"] = startAt
        
        # Get test cases from the specified folder
        try:
            test_cases = self._api.test_cases.get_test_cases(**kwargs)
            all_test_cases.extend(test_cases)
        except Exception as e:
            return ToolException(f"Error getting test cases from folder {folder_id}: {str(e)}")
        
        # Get all folders in the project
        all_folders = []
        try:
            for folder in self._api.folders.get_folders(
                maxResults=100, 
                projectKey=project_key, 
                folderType="TEST_CASE"
            ):
                all_folders.append(folder)
        except Exception as e:
            return ToolException(f"Error getting folders: {str(e)}")
        
        # Build folder hierarchy
        folder_hierarchy = {}
        for folder in all_folders:
            folder_id_val = folder.get('id')
            parent_id = folder.get('parentId')
            if folder_id_val not in folder_hierarchy:
                folder_hierarchy[folder_id_val] = {
                    'folder': folder,
                    'children': []
                }
            else:
                folder_hierarchy[folder_id_val]['folder'] = folder
                
            if parent_id:
                if parent_id not in folder_hierarchy:
                    folder_hierarchy[parent_id] = {
                        'folder': None,
                        'children': [folder_id_val]
                    }
                else:
                    folder_hierarchy[parent_id]['children'].append(folder_id_val)
        
        # Function to recursively collect test cases from subfolders
        def collect_subfolder_tests(parent_folder_id):
            if parent_folder_id not in folder_hierarchy:
                return
            
            for child_id in folder_hierarchy[parent_folder_id]['children']:
                # Get test cases from this subfolder
                subfolder_kwargs = kwargs.copy()
                subfolder_kwargs["folderId"] = child_id
                try:
                    subfolder_test_cases = self._api.test_cases.get_test_cases(**subfolder_kwargs)
                    all_test_cases.extend(subfolder_test_cases)
                except Exception as e:
                    logger.warning(f"Error getting test cases from subfolder {child_id}: {str(e)}")
                
                # Recursively process this subfolder's children
                collect_subfolder_tests(child_id)
        
        # Start recursive collection if a folder ID was specified
        if folder_id:
            collect_subfolder_tests(folder_id)
        
        # Convert the test cases to a string
        parsed_tests = self._parse_tests(all_test_cases)
        return f"Extracted {len(all_test_cases)} tests recursively: {str(parsed_tests)}"

    @staticmethod
    def _parse_tests(tests) -> list:
        """Parses test cases information"""
        parsed_tests = []
        for test in tests:
            test_item = []
            # Adding extracted information to the list
            test_item.append(f"Test ID: {test.get('id')}")
            test_item.append(f"Key: {test.get('key')}")
            test_item.append(f"Name: {test.get('name')}")

            # For project ID
            project = test.get('project')
            if project is not None:
                test_item.append(f"Project ID: {project.get('id')}")
            else:
                test_item.append("Project ID: None")

            test_item.append(f"Precondition: {test.get('precondition')}")

            # For priority ID
            priority = test.get('priority')
            if priority is not None:
                test_item.append(f"Priority ID: {priority.get('id')}")
            else:
                test_item.append("Priority ID: None")

            # For status ID
            status = test.get('status')
            if status is not None:
                test_item.append(f"Status ID: {status.get('id')}")
            else:
                test_item.append("Status ID: None")

            # For owner account ID
            owner = test.get('owner')
            if owner is not None:
                test_item.append(f"Owner Account ID: {owner.get('accountId')}")
            else:
                test_item.append("Owner Account ID: None")
            parsed_tests.append(test_item)
        return parsed_tests
    
    def get_tests_by_folder_name(self, project_key: str, folder_name: str, exact_match: Optional[bool] = False, 
                             include_subfolders: Optional[bool] = True, maxResults: Optional[int] = 100, 
                             startAt: Optional[int] = 0):
        """Retrieves all test cases from folders matching the specified name.
        
        Args:
            project_key: Jira project key filter
            folder_name: Full or partial folder name to search for
            exact_match: Whether to match the folder name exactly or allow partial matches
            include_subfolders: Whether to include test cases from subfolders of matching folders
            maxResults: A hint as to the maximum number of results to return in each call
            startAt: Zero-indexed starting position. Should be a multiple of maxResults
            
        Returns:
            A string with all test cases found in matching folders
        """
        # Store all test cases and matching folder IDs
        all_test_cases = []
        matching_folder_ids = []
        
        # Get all folders in the project
        all_folders = []
        try:
            for folder in self._api.folders.get_folders(
                maxResults=100, 
                projectKey=project_key, 
                folderType="TEST_CASE"
            ):
                all_folders.append(folder)
        except Exception as e:
            return ToolException(f"Error getting folders: {str(e)}")
        
        # Find folders matching the name
        for folder in all_folders:
            folder_name_val = folder.get('name', '')
            if exact_match:
                if folder_name_val == folder_name:
                    matching_folder_ids.append(folder.get('id'))
            else:
                if folder_name.lower() in folder_name_val.lower():
                    matching_folder_ids.append(folder.get('id'))
        
        if not matching_folder_ids:
            return f"No folders found matching name: {folder_name}"
            
        # Build folder hierarchy if we need to include subfolders
        folder_hierarchy = {}
        if include_subfolders:
            for folder in all_folders:
                folder_id_val = folder.get('id')
                parent_id = folder.get('parentId')
                if folder_id_val not in folder_hierarchy:
                    folder_hierarchy[folder_id_val] = {
                        'folder': folder,
                        'children': []
                    }
                else:
                    folder_hierarchy[folder_id_val]['folder'] = folder
                
                if parent_id:
                    if parent_id not in folder_hierarchy:
                        folder_hierarchy[parent_id] = {
                            'folder': None,
                            'children': [folder_id_val]
                        }
                    else:
                        folder_hierarchy[parent_id]['children'].append(folder_id_val)
        
        # Function to recursively collect test cases from subfolders
        def collect_subfolder_tests(parent_folder_id, collected_folders=None):
            if collected_folders is None:
                collected_folders = set()
                
            if parent_folder_id not in folder_hierarchy or parent_folder_id in collected_folders:
                return
                
            collected_folders.add(parent_folder_id)
            
            for child_id in folder_hierarchy[parent_folder_id].get('children', []):
                if child_id not in collected_folders:
                    # Add this subfolder ID to our list of folders to search
                    matching_folder_ids.append(child_id)
                    # Recursively process this subfolder's children
                    collect_subfolder_tests(child_id, collected_folders)
        
        # Start recursive collection for each matching folder if including subfolders
        if include_subfolders:
            original_matching_ids = matching_folder_ids.copy()
            for folder_id in original_matching_ids:
                collect_subfolder_tests(folder_id)
        
        # Remove duplicates from matching folder IDs
        matching_folder_ids = list(set(matching_folder_ids))
        
        # Get test cases from all matching folders
        for folder_id in matching_folder_ids:
            try:
                folder_test_cases = self._api.test_cases.get_test_cases(
                    projectKey=project_key,
                    folderId=folder_id,
                    maxResults=maxResults,
                    startAt=startAt
                )
                all_test_cases.extend(folder_test_cases)
            except Exception as e:
                logger.warning(f"Error getting test cases from folder {folder_id}: {str(e)}")
        
        # Convert the test cases to a string
        parsed_tests = self._parse_tests(all_test_cases)
        return f"Extracted {len(all_test_cases)} tests from {len(matching_folder_ids)} folders matching '{folder_name}': {str(parsed_tests)}"

    def get_tests_by_folder_path(self, project_key: str, folder_path: str, include_subfolders: Optional[bool] = True,
                                maxResults: Optional[int] = 100, startAt: Optional[int] = 0):
        """Retrieves all test cases from a folder specified by its path.
        
        Args:
            project_key: Jira project key filter
            folder_path: Full folder path (e.g., 'Root/Parent/Child')
            include_subfolders: Whether to include test cases from subfolders
            maxResults: A hint as to the maximum number of results to return in each call
            startAt: Zero-indexed starting position. Should be a multiple of maxResults
            
        Returns:
            A string with all test cases found in the specified folder path
        """
        # Store all test cases
        all_test_cases = []
        
        # Get all folders in the project
        all_folders = []
        try:
            for folder in self._api.folders.get_folders(
                maxResults=100, 
                projectKey=project_key, 
                folderType="TEST_CASE"
            ):
                all_folders.append(folder)
        except Exception as e:
            return ToolException(f"Error getting folders: {str(e)}")
        
        # Build folder hierarchy with paths
        folder_hierarchy = {}
        folder_paths = {}
        root_folders = []
        
        # First pass: collect all folders and their basic relationships
        for folder in all_folders:
            folder_id = folder.get('id')
            parent_id = folder.get('parentId')
            
            if folder_id not in folder_hierarchy:
                folder_hierarchy[folder_id] = {
                    'folder': folder,
                    'children': []
                }
            else:
                folder_hierarchy[folder_id]['folder'] = folder
                
            if parent_id:
                if parent_id not in folder_hierarchy:
                    folder_hierarchy[parent_id] = {
                        'folder': None,
                        'children': [folder_id]
                    }
                else:
                    folder_hierarchy[parent_id]['children'].append(folder_id)
            else:
                # This is a root folder
                root_folders.append(folder_id)
        
        # Function to build full paths for each folder
        def build_folder_paths(folder_id, current_path=""):
            if folder_id not in folder_hierarchy or not folder_hierarchy[folder_id]['folder']:
                return
                
            folder_name = folder_hierarchy[folder_id]['folder'].get('name', '')
            if current_path:
                full_path = f"{current_path}/{folder_name}"
            else:
                full_path = folder_name
                
            folder_paths[folder_id] = full_path
            
            # Process children
            for child_id in folder_hierarchy[folder_id]['children']:
                build_folder_paths(child_id, full_path)
        
        # Build paths starting from root folders
        for root_id in root_folders:
            build_folder_paths(root_id)
        
        # Find the folder matching the exact path
        target_folder_id = None
        for folder_id, path in folder_paths.items():
            if path == folder_path:
                target_folder_id = folder_id
                break
        
        if not target_folder_id:
            return f"No folder found with path: {folder_path}"
        
        # Get test cases from the target folder
        try:
            folder_test_cases = self._api.test_cases.get_test_cases(
                projectKey=project_key,
                folderId=target_folder_id,
                maxResults=maxResults,
                startAt=startAt
            )
            all_test_cases.extend(folder_test_cases)
        except Exception as e:
            return ToolException(f"Error getting test cases from folder path {folder_path}: {str(e)}")
        
        # If including subfolders, recursively get test cases from subfolders
        if include_subfolders:
            # Function to recursively collect test cases from subfolders
            def collect_subfolder_tests(parent_folder_id, collected_folders=None):
                if collected_folders is None:
                    collected_folders = set()
                    
                if parent_folder_id not in folder_hierarchy or parent_folder_id in collected_folders:
                    return
                    
                collected_folders.add(parent_folder_id)
                
                for child_id in folder_hierarchy[parent_folder_id].get('children', []):
                    if child_id not in collected_folders:
                        # Get test cases from this subfolder
                        try:
                            subfolder_test_cases = self._api.test_cases.get_test_cases(
                                projectKey=project_key,
                                folderId=child_id,
                                maxResults=maxResults,
                                startAt=startAt
                            )
                            all_test_cases.extend(subfolder_test_cases)
                        except Exception as e:
                            logger.warning(f"Error getting test cases from subfolder {child_id}: {str(e)}")
                        
                        # Recursively process this subfolder's children
                        collect_subfolder_tests(child_id, collected_folders)
            
            # Start recursive collection from the target folder
            collect_subfolder_tests(target_folder_id)
        
        # Convert the test cases to a string
        parsed_tests = self._parse_tests(all_test_cases)
        return f"Extracted {len(all_test_cases)} tests from folder path '{folder_path}': {str(parsed_tests)}"
    

    def get_available_tools(self):
        return [
            {
                "name": "get_tests",
                "description": self.get_tests.__doc__,
                "args_schema": ZephyrGetTestCases,
                "ref": self.get_tests,
            },
            {
                "name": "get_test",
                "description": self.get_test.__doc__,
                "args_schema": ZephyrGetTestCase,
                "ref": self.get_test,
            },
            {
                "name": "get_test_steps",
                "description": self.get_test_steps.__doc__,
                "args_schema": ZephyrGetTestCase,
                "ref": self.get_test_steps,
            },
            {
                "name": "create_test_case",
                "description": self.create_test_case.__doc__,
                "args_schema": ZephyrCreateTestCase,
                "ref": self.create_test_case,
            },
            {
                "name": "add_test_steps",
                "description": self.add_test_steps.__doc__,
                "args_schema": ZephyrTestStepsInputModel,
                "ref": self.add_test_steps,
            },
            {
                "name": "get_folders",
                "description": self.get_folders.__doc__,
                "args_schema": ZephyrGetFolders,
                "ref": self.get_folders,
            },
            {
                "name": "update_test_case",
                "description": self.update_test_case.__doc__,
                "args_schema": ZephyrUpdateTestCase,
                "ref": self.update_test_case,
            },
            {
                "name": "get_links",
                "description": self.get_links.__doc__,
                "args_schema": ZephyrGetLinks,
                "ref": self.get_links,
            },
            {
                "name": "create_issue_links",
                "description": self.create_issue_links.__doc__,
                "args_schema": ZephyrCreateIssueLinks,
                "ref": self.create_issue_links,
            },
            {
                "name": "create_web_links",
                "description": self.create_web_links.__doc__,
                "args_schema": ZephyrCreateWebLinks,
                "ref": self.create_web_links,
            },
            {
                "name": "get_versions",
                "description": self.get_versions.__doc__,
                "args_schema": ZephyrGetVersions,
                "ref": self.get_versions,
            },
            {
                "name": "get_version",
                "description": self.get_version.__doc__,
                "args_schema": ZephyrGetVersion,
                "ref": self.get_version,
            },
            {
                "name": "get_test_script",
                "description": self.get_test_script.__doc__,
                "args_schema": ZephyrGetTestScript,
                "ref": self.get_test_script,
            },
            {
                "name": "create_test_script",
                "description": self.create_test_script.__doc__,
                "args_schema": ZephyrCreateTestScript,
                "ref": self.create_test_script,
            },
            {
                "name": "search_test_cases",
                "description": self.search_test_cases.__doc__,
                "args_schema": ZephyrSearchTestCases,
                "ref": self.search_test_cases,
            },
            {
                "name": "get_tests_recursive",
                "description": self.get_tests_recursive.__doc__,
                "args_schema": ZephyrGetTestsRecursive,
                "ref": self.get_tests_recursive,
            },
            {
                "name": "get_tests_by_folder_name",
                "description": self.get_tests_by_folder_name.__doc__,
                "args_schema": ZephyrGetTestsByFolderName,
                "ref": self.get_tests_by_folder_name,
            },
            {
                "name": "get_tests_by_folder_path",
                "description": self.get_tests_by_folder_path.__doc__,
                "args_schema": ZephyrGetTestsByFolderPath,
                "ref": self.get_tests_by_folder_path,
            }
        ]