import logging
from traceback import format_exc
import json
from typing import List, Optional, Any, Dict
from langchain_core.tools import ToolException
from langchain_core.pydantic_v1 import root_validator, BaseModel
from pydantic import create_model
from pydantic.fields import FieldInfo
import requests
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
logger = logging.getLogger(__name__)
from requests.exceptions import HTTPError



NoInput = create_model(
    "NoInput"
)

XraySearch = create_model(
    "XraySearchModel",
    jql=(str, FieldInfo(description="""Jira Query Language (JQL) query string.  If you are asked to get test then jql might look like 
                        "issueid=TEST-1234", if you are asked to find tests relevant to a story - then jql may look like "issueLink in (STORY-1234) and issueLinkType ='tests'".
                        you must provide it as jql query as is like in example, don't make a jql json, only string. 
                        Invoking `get_tests` should happen  `{'jql': "issueLink in (CRFRMOBI-119) and issueLinkType ='tests'"}`
                        """))
    )

XrayCreateTest= create_model(
    "XrayCreateTestModel",
    gql_query=(str, FieldInfo(description='''
To create a test and link it to an existing story, you can use the `linkedIssues` field in the mutation to associate the test case with a Jira issue (like a story):

GraphQL Schema definition
1	Mutation createTest {
2	
3	# Mutation used to create a new Test.
4	#
5	#
6	# Arguments
7	# testType: the Test Type of the Test.
8	# steps: the Step definition of the test.
9	# unstructured: the unstructured definition of the Test.
10	# gherkin: the gherkin definition of the Test.
11	# preconditionIssueIds: the Precondition ids that be associated with the Test.
12	# folderPath: the Test repository folder for the Test.
13	# jira: the Jira object that will be used to create the Test.
14	# Check this Jira endpoint for more information related with this field.
15	createTest(testType: UpdateTestTypeInput, steps: [CreateStepInput], unstructured: String, gherkin: String, preconditionIssueIds: [String], folderPath: String, jira: JSON!): CreateTestResult
16	
17	}
linkExample
The mutation below will create a new Test.

mutation {
    createTest(
        testType: { name: "Generic" },
        unstructured: "Perform exploratory tests on calculator.",
        jira: {
            fields: { summary:"Exploratory Test", project: {key: "CALC"} }
        }
    ) {
        test {
            issueId
            testType {
                name
            }
            unstructured
            jira(fields: ["key"])
        }
        warnings
    }
}
The mutation below will create a new Test.

mutation {
    createTest(
        testType: { name: "Manual" },
        steps: [
            {
                action: "Create first example step",
                result: "First step was created"
            },
            {
                action: "Create second example step with data",
                data: "Data for the step",
                result: "Second step was created with data"
            }
        ],
        jira: {
            fields: { summary:"Exploratory Test", project: {key: "CALC"} }
        }
    ) {
        test {
            issueId
            testType {
                name
            }
            steps {
                action
                data
                result
            }
            jira(fields: ["key"])
        }
        warnings
    }
}
                              
Gherking /cucumber test example: 
mutation {
  createTest(
    testType: { name: "Cucumber" }, 
    gherkin: """
      Feature: Sample Feature
        Scenario: User logs in
          Given the application is opened
          When the user enters valid credentials
          Then the user is logged in and navigated to the dashboard
    """,
    jira: {
      fields: { summary: "Sample Gherkin Test", project: { key: "YOUR_PROJECT_KEY" } }
    }
  ) {
    test {
          issueId
          testType {
                name
            }
      gherkin
      jira(fields: ["key"])
    }
    warnings
  }
}                              

CALC/ YOUR_PROJECT_KEY -  project key should be replaced to actual value and  should be driven by the user input or context. If he provides a user story STORY-456, then  project key is STORY. If project key is not known - ask user.
''')),
    story=(str, FieldInfo(description="""User provide story (if provided) e.g. TEST-1234
                        """)),
    )





class XrayApiWrapper(BaseModel):
    base_url: str='https://xray.cloud.getxray.app'
    api_key: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    limit: Optional[int] = 5

    jira_url: str
    jira_api_key: Optional[str] = None,
    jira_username: Optional[str] = None
    jira_token: Optional[str] = None
    cloud: Optional[bool] = True
    verify_ssl: Optional[bool] = True
    

    @root_validator()
    def validate_toolkit(cls, values):
        try:
            from gql import gql, Client
            from gql.transport.requests import RequestsHTTPTransport
        except ImportError:
            raise ImportError(
                "`gql` package not found, please run "
                "`pip install gql`"
            )
        try:
            from atlassian import Jira  # noqa: F401
        except ImportError:
            raise ImportError(
                "`atlassian` package not found, please run "
                "`pip install atlassian-python-api`"
            )
        #Authenticate to get the token
        auth_url = f"{values['base_url']}/api/v1/authenticate"
        auth_data = {
            "client_id": values['client_id'],
            "client_secret": values['client_secret']
        }
        auth_response = requests.post(auth_url, json=auth_data)
        token = auth_response.json()  # Extract token from the response
        transport=RequestsHTTPTransport(
            url=f"{values['base_url']}/api/v2/graphql",
            headers={'Authorization': f'Bearer {token}'},
            use_json=True
        )
        # Setup the GraphQL client with the token
        values['client'] =  Client(transport=transport, fetch_schema_from_transport=True)
        jira_url = values['jira_url']
        jira_api_key = values.get('jira_api_key')
        jira_username = values.get('jira_username')
        jira_token = values.get('jira_token')
        cloud = values.get('cloud')
        if jira_token:
            values['jira_client'] = Jira(url=jira_url, token=jira_token, cloud=cloud, verify_ssl=values['verify_ssl'])
        else:
            values['jira_client'] = Jira(url=jira_url, username=jira_username, password=jira_api_key, cloud=cloud, verify_ssl=values['verify_ssl'])
        return values
    def _fetch(self, query):
        # if isinstance(query, str):
        #     q=gql(query)
        # else:
        #     q=query

        try:
            response = self.client.execute(query)
            return response
        except Exception as e:
            print(f"Error executing query: {e}")

    def create_test(self, gql_query:str, story=''):
            "Create tests based on qlg input"
            query= gql(gql_query)
            response = self._fetch(query)
            issue_id = response['createTest']['test']['issueId']
            jira_key=response['createTest']['test']['jira']['key']
            if story:
                # Define the issue link
                inward_issue_key = response['createTest']['test']['jira']['key'] 
                outward_issue_key = story 
                link_data = {
    "type": {"name": "Test"},  # Use the appropriate issue link type (e.g., "Tests", "Relates")
    "inwardIssue": {"key": f"{inward_issue_key}"},  # The story (inward issue)
    "outwardIssue": {"key": f"{outward_issue_key}"},  # The test (outward issue)
    "comment": {
        "body": "This test is linked to the story."
    }
}
                


            try:
                self.jira_client.create_issue_link(link_data)
            except HTTPError as http_err:
                # Check if the response object is available
                if hasattr(http_err, 'response') and http_err.response is not None:
                    logging.error(f"HTTP Error: {http_err}")
                    logging.error(f"Response Status Code: {http_err.response.status_code}")
                    logging.error(f"Response Content: {http_err.response.content}")
                    print(f"HTTP Error: {http_err}")
                    print(f"Status Code: {http_err.response.status_code}")
                    print(f"Response Content: {http_err.response.content}")
                else:
                    logging.error(f"HTTP Error without response: {http_err}")
                    print(f"HTTP Error without response: {http_err}")
            except Exception as e:
                logging.error(f"General Error: {repr(e)}")
                print(f"General Error: {repr(e)}")

            return (f"Test created with issueId: {issue_id}, JIRA:{jira_key} ")
    #create sample test case for CRFRMOBI-119
    def get_tests(self, jql: str):
        """get all tests
        """
        has_more = True
        start_at = 0
        all_tests = []
        print (jql)
        while has_more:
            query_with_pagination = gql(f"""
            {{
            getTests(jql: "{jql}", limit: {self.limit}, start: {start_at}) {{
                total
                results {{
                issueId
                jira(fields: ["key"])
            testType {{
                name
                kind
            }}
                steps {{
 id
                data
                action
                result
                attachments {{
                    id
                    filename
                }}
                customFields {{
                    id
                    value
                }}
                }}
                gherkin
                }}
            }}
            }}
            """)

            response = self._fetch(query_with_pagination)
            
            tests = response["getTests"]["results"]
            all_tests.extend(tests)

            # Check if more results are available
            if len(tests) < 100:
                has_more = False
            else:
                start_at += 100

        return all_tests


    def get_available_tools(self):
        return [
            {
                "name": "get_tests",
                "description": self.get_tests.__doc__,
                "args_schema": XraySearch,
                "ref": self.get_tests,
            },
                      {
                "name": "create_test",
                "description": self.create_test.__doc__,
                "args_schema": XrayCreateTest,
                "ref": self.create_test,
            }
        ]

    def run(self, mode: str, *args: Any, **kwargs: Any):
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {mode}")