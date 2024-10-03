import logging
from typing import Any

import swagger_client
from langchain_core.pydantic_v1 import root_validator, BaseModel
from langchain_core.tools import ToolException
from pydantic import create_model
from pydantic.fields import FieldInfo
from sklearn.feature_extraction.text import strip_tags
from swagger_client import TestCaseApi, SearchApi, PropertyResource
from swagger_client.rest import ApiException

logger = logging.getLogger(__name__)

QtestDataQuerySearch = create_model(
    "QtestDataQuerySearch",
    dql=(str, FieldInfo(description="Qtest Data Query Language (DQL) query string")))

QtestCreateTestCase = create_model(
    "QtestCreateTestCase",
    test_case_content=(str, FieldInfo(
        description="Test case content in Markdown format as table and contain following columns:  Id, Name, Description, Type, Status, Priority, Test Type, Precondition, Test Step Number, Test Step Description, Test Step Expected Result"))
)

UpdateTestCase = create_model(
    "UpdateTestCase",
    test_id=(str, FieldInfo(description="Test ID e.g. TC-1234")),
    test_case_content=(str, FieldInfo(
        description="Test case content in Markdown format as table and contain following columns:  Id, Name, Description, Type, Status, Priority, Test Type, Precondition, Test Step Number, Test Step Description, Test Step Expected Result"))
)

FindTestCaseById = create_model(
    "FindTestCaseById",
    test_id=(str, FieldInfo(description="Test case ID e.g. TC-1234")),
)

DeleteTestCase = create_model(
    "DeleteTestCase",
    id=(int, FieldInfo(description="Qtest id e.g. 3253490123")),
)


class QtestApiWrapper(BaseModel):
    base_url: str
    project_id: int
    qtest_api_token: str
    no_of_items_per_page: int = 100
    page: int = 1
    no_of_tests_shown_in_dql_search = 10

    @root_validator()
    def validate_toolkit(cls, values):
        try:
            import swagger_client  # noqa: F401
        except ImportError:
            raise ImportError(
                "`swagger_client` package not found, please run "
                "`pip install git+https://github.com/Roman-Mitusov/qtest-api.git`"
            )

        url = values['base_url']
        api_token = values.get('qtest_api_token')
        if api_token:
            configuration = swagger_client.Configuration()
            configuration.host = url
            configuration.api_key['Authorization'] = api_token
            configuration.api_key_prefix['Authorization'] = 'Bearer'
            values['client'] = swagger_client.ApiClient(configuration)
        return values

    def __instantiate_test_api_instance(self) -> TestCaseApi:
        # Instantiate the TestCaseApi instance according to the qtest api documentation and swagger client
        return swagger_client.TestCaseApi(self.client)

    def __convert_markdown_test_steps_data_to_dict(self, test_cases: str) -> list[dict]:
        # Split the table into lines
        lines = test_cases.strip().split('\n')

        # Extract the headers
        headers = [header.strip() for header in lines[0].split('|')[1:-1]]

        # Initialize a list to hold the test case data
        test_cases_data = []
        current_test_case = None

        # Process each line except the first two header lines
        for line in lines[2:]:
            # Split the line into cells and trim whitespace
            cells = [cell.strip() for cell in line.split('|')[1:-1]]

            # Create a dictionary for the test case step
            test_step = dict(zip(headers, cells))

            # Check if a new test case starts
            if test_step['Id']:
                if current_test_case:
                    test_cases_data.append(current_test_case)
                current_test_case = {
                    'Id': test_step['Id'],
                    'Name': test_step['Name'],
                    'Description': test_step['Description'],
                    'Type': test_step['Type'],
                    'Status': test_step['Status'],
                    'Priority': test_step['Priority'],
                    'Test Type': test_step['Test Type'],
                    'Precondition': test_step['Precondition'],
                    'Steps': []
                }

            # Add the step to the current test case
            if current_test_case:
                current_test_case['Steps'].append({
                    'Test Step Number': test_step['Test Step Number'],
                    'Test Step Description': test_step['Test Step Description'],
                    'Test Step Expected Result': test_step['Test Step Expected Result']
                })

        # Add the last test case
        if current_test_case:
            test_cases_data.append(current_test_case)
        return test_cases_data

    def __build_body_for_create_test_case(self, test_cases_data: list[dict]) -> list:
        initial_project_properties = self.__get_properties_form_project()
        props = []
        for prop in initial_project_properties:
            props.append(PropertyResource(field_id=prop['field_id'], field_name=prop['field_name'],
                                          field_value_name=prop.get('field_value_name', None), field_value=prop['field_value']))
        bodies = []
        for test_case in test_cases_data:
            body = swagger_client.TestCaseWithCustomFieldResource(properties=props)
            body.name = test_case.get('Name')
            body.precondition = test_case.get('Precondition')
            body.description = test_case.get('Description')
            test_steps_resources = []
            for step in test_case.get('Steps'):
                test_steps_resources.append(
                    swagger_client.TestStepResource(description=step.get('Test Step Description'),
                                                    expected=step.get('Test Step Expected Result')))
            body.test_steps = test_steps_resources
            bodies.append(body)
        return bodies

    def __execute_single_create_test_case_request(self, test_case_api_instance: TestCaseApi, body,
                                                  test_case_content: str) -> tuple:
        try:
            response = test_case_api_instance.create_test_case(self.project_id, body)
            test_case_id = response.pid
            return f"The test case successfully created have been created in project-{self.project_id} with Id - {test_case_id}.", test_case_id
        except ApiException as e:
            logger.error("Exception when calling TestCaseApi->create_test_case: %s\n" % e)
            raise ToolException(
                f"Unable to create test case in project - {self.project_id} with the following content:\n{test_case_content}.")

    def __parse_data(self, response_to_parse: dict, parsed_data: list):
        import html
        for item in response_to_parse['items']:
            parsed_data_row = {
                'Id': item['pid'],
                'Description': html.unescape(strip_tags(item['description'])),
                'Precondition': html.unescape(strip_tags(item['precondition'])),
                'Name': item['name'],
                'Qtest Id': item['id'],
                'Test Step Description': '\n'.join(map(str,
                                                       [html.unescape(
                                                           strip_tags(str(item['order']) + '. ' + item['description']))
                                                           for item in item['test_steps']
                                                           for key in item if key == 'description'])),
                'Test Expected Result': '\n'.join(map(str,
                                                      [html.unescape(
                                                          strip_tags(str(item['order']) + '. ' + item['expected']))
                                                          for item in item['test_steps']
                                                          for key in item if key == 'expected'])),
                'Status': ''.join([properties['field_value_name'] for properties in item['properties']
                                   if properties['field_name'] == 'Status']),
                'Automation': ''.join([properties['field_value_name'] for properties in item['properties']
                                       if properties['field_name'] == 'Automation']),
                'Type': ''.join([properties['field_value_name'] for properties in item['properties']
                                 if properties['field_name'] == 'Type']),
                'Priority': ''.join([properties['field_value_name'] for properties in item['properties']
                                     if properties['field_name'] == 'Priority']),
            }
            parsed_data.append(parsed_data_row)

    def __perform_search_by_dql(self, dql: str) -> list:
        search_instance: SearchApi = swagger_client.SearchApi(self.client)
        body = swagger_client.ArtifactSearchParams(object_type='test-cases', fields=['*'],
                                                   query=dql)
        append_test_steps = 'true'
        include_external_properties = 'true'
        parsed_data = []
        try:
            api_response = search_instance.search_artifact(self.project_id, body, append_test_steps=append_test_steps,
                                                           include_external_properties=include_external_properties,
                                                           page_size=self.no_of_items_per_page, page=self.page)
            self.__parse_data(api_response, parsed_data)

            if api_response['links']:
                while api_response['links'][0]['rel'] == 'next':
                    next_page = self.page + 1
                    api_response = search_instance.search_artifact(self.project_id, body,
                                                                   append_test_steps=append_test_steps,
                                                                   include_external_properties=include_external_properties,
                                                                   page_size=self.no_of_items_per_page, page=next_page)
                    self.__parse_data(api_response, parsed_data)
        except ApiException as e:
            logger.error("Exception when calling SearchApi->search_artifact: %s\n" % e)
            raise ToolException(
                f"""Unable to get the test cases by dql: {dql} from following qTest project - {self.project_id}.
                    Exception: \n%s""" % e)
        return parsed_data

    def __find_qtest_id_by_test_id(self, test_id: str) -> int:
        """ Search for a qtest id using the test id. Test id should be in format TC-123. """
        dql = f"Id = '{test_id}'"
        parsed_data = self.__perform_search_by_dql(dql)
        return parsed_data[0]['Qtest Id']

    def __get_properties_form_project(self) -> list[dict]:
        test_api_instance = self.__instantiate_test_api_instance()
        expand_props = 'true'
        try:
            response = test_api_instance.get_test_cases(self.project_id, 1, 1, expand_props=expand_props)
            return response[0]['properties']
        except ApiException as e:
            logger.error("Exception when calling TestCaseApi->get_test_cases: %s\n" % e)

    def search_by_dql(self, dql: str):
        """Search for the test cases in qTest using Data Query Language """
        parsed_data = self.__perform_search_by_dql(dql)
        return "Found " + str(
            len(parsed_data)) + f" Qtest test cases:\n" + str(parsed_data[:self.no_of_tests_shown_in_dql_search])

    def create_test_cases(self, test_case_content: str) -> str:
        """ Create the tes case base on the incoming content. The input should be in Markdown format. """
        test_cases_api_instance: TestCaseApi = self.__instantiate_test_api_instance()
        test_cases = self.__convert_markdown_test_steps_data_to_dict(test_case_content)
        bodies = self.__build_body_for_create_test_case(test_cases)
        if len(bodies) == 1:
            return \
                self.__execute_single_create_test_case_request(test_cases_api_instance, bodies[0], test_case_content)[0]
        else:
            test_case_ids = []
            for body in bodies:
                _, test_case_id = self.__execute_single_create_test_case_request(test_cases_api_instance, body,
                                                                                 test_case_content)
                test_case_ids.append(test_case_id)
            return f'Successfully created {len(bodies)} test case(s) in project with id - {self.project_id}. The ids of created test cases are - {test_case_ids}.'

    def update_test_case(self, test_id: str, test_case_content: str) -> str:
        """ Update the test case base on the incoming content. The input should be in Markdown format. Also test id should be passed in following format TC-786. """
        qtest_id = self.__find_qtest_id_by_test_id(test_id)
        test_cases_api_instance: TestCaseApi = self.__instantiate_test_api_instance()
        tests = self.__convert_markdown_test_steps_data_to_dict(test_case_content)
        bodies = self.__build_body_for_create_test_case(tests)
        try:
            response = test_cases_api_instance.update_test_case(self.project_id, qtest_id, bodies[0])
            return f"""Successfully updated test case in project with id - {self.project_id}.
            Updated test case id - {response['pid']}.
            Test id of updated test case - {test_id}.
            Updated with content:\n{test_case_content}"""
        except ApiException as e:
            logger.error("Exception when calling TestCaseApi->update_test_case: %s\n" % e)
            raise ToolException(
                f"Unable to update test case in project with id - {self.project_id} and test id - {test_id}.") from e

    def find_test_case_by_id(self, test_id: str) -> str:
        """ Find the test case by its id. Id should be in format TC-123. """
        dql: str = f"Id = '{test_id}'"
        return f"{self.search_by_dql(dql=dql)}"

    def delete_test_case(self, qtest_id: int) -> str:
        """ Delete the test case by its id. Id should be in format 3534653120. """
        test_cases_api_instance: TestCaseApi = self.__instantiate_test_api_instance()
        try:
            test_cases_api_instance.delete_test_case(self.project_id, qtest_id)
            return f"Successfully deleted test case in project with id - {self.project_id} and qtest id - {qtest_id}."
        except ApiException as e:
            logger.error("Exception when calling TestCaseApi->delete_test_case: %s\n" % e)
            raise ToolException(
                f"Unable to delete test case in project with id - {self.project_id} and qtest_id - {qtest_id}") from e

    def get_available_tools(self):
        return [
            {
                "name": "search_by_dql",
                "mode": "search_by_dql",
                "description": 'Search the test cases in qTest using Data Query Language. The input of the tool will be in fowwoing format - Module in \'MD-78 Master Test Suite\' and Type = \'Automation - UTAF\'. If keyword or value to check against has 2 words in it it should be surrounded with single quotes',
                "args_schema": QtestDataQuerySearch,
                "ref": self.search_by_dql,
            },
            {
                "name": "create_test_cases",
                "mode": "create_test_cases",
                "description": "Create multiple test cases in the particular project in Qtest. The input requirement is that the content should be in Markdown format as a table and contain following columns:  Id, Name, Description, Type, Status, Priority, Test Type, Precondition, Test Step Number, Test Step Description, Test Step Expected Result",
                "args_schema": QtestCreateTestCase,
                "ref": self.create_test_cases,
            },
            {
                "name": "update_test_case",
                "mode": "update_test_case",
                "description": "Update the test case base on the incoming content and test id e.g. TC-1234.",
                "args_schema": UpdateTestCase,
                "ref": self.create_test_cases,
            },
            {
                "name": "find_test_case_by_id",
                "mode": "find_test_case_by_id",
                "description": "Find the test case by its id. Id should be in format TC-123",
                "args_schema": FindTestCaseById,
                "ref": self.find_test_case_by_id,
            },
            {
                "name": "delete_test_case",
                "mode": "delete_test_case",
                "description": "Delete test case by its id. Id should be in format 3534653120.",
                "args_schema": DeleteTestCase,
                "ref": self.delete_test_case,
            },
        ]

    def run(self, mode: str, *args: Any, **kwargs: Any):
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {mode}")
