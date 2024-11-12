import logging
from traceback import format_exc
import json
from typing import List, Optional, Any, Dict
from langchain_core.tools import ToolException
from langchain_core.pydantic_v1 import root_validator, BaseModel
from pydantic import create_model
from pydantic.fields import FieldInfo

logger = logging.getLogger(__name__)


NoInput = create_model(
    "NoInput"
)

#https://pyral.readthedocs.io/_/downloads/en/stable/pdf/

RallySearch = create_model(
    "RallySearchModel",
        entity_name=(str, FieldInfo(
        description=("Rally Item type - 'Defect''Task','TestCase','HierarchicalRequirement' or 'Feature'. User story is HierarchicalRequirement type"))),
        fetch=(bool|str,  FieldInfo(
        description=("Describes if it's required to fetch fields from Rally. Use defaults fetch=True if not asked. If asked about specific fields - use List of fields to be fetched e.g. 'ObjectID,FormattedID,Name,CreatedDate,LastUpdateDate' or 'FormattedID,Name,Description,State,Severity,Priority,CreationDate,LastUpdateDate'. Do not provide input if not asked explicitely."))),   
        query=(str, FieldInfo(
        description=("""Use default =None if not asked. If asked  - use Rally query. E.g. 'State != Closed', 'FieldName = "some value"' or ['fld1 = 19', 'fld27 != "Shamu"', etc.]. Another example of such query: '((Iteration.Name contains "Iteration 6")OR(Iteration.Name contains "Iteration 7")) AND (Feature != null)'."""))),   
        order=(str, FieldInfo(
        description=("Use default = None if not asked. If asked to order - user Rally results order by. E.g 'FormattedID','fieldName ASC|DESC', ''. Don't provide if now asked explicitely"))),   
        limit=(int, FieldInfo(
        description=("Use default limit=5. If asked top 5 or top 10 - change to asked value.")))
        )
RallyCreate = create_model(
    "RallyCreatehModel",
        entity_name=(str, FieldInfo(
        description=("Item type - 'Defect''Task','TestCase','HierarchicalRequirement' or 'Feature'. User story is HierarchicalRequirement type"))),
        fetch=(str,  FieldInfo(
        description=("""Example for task create:
{
             "Project"     : target_project.ref,
             "WorkProduct" : target_story.ref,
             "Name"        : "BigTaters",
             "State"       : "Defined",
             "TaskIndex"   : 1,
             "Description" : "Fly to Chile next week to investigate the home of potatoes.  Find the absolute gigantoidist spuds and bring home the eyes to Idaho.  Plant, water, wonder, harvest, wash, slice, plunge in and out of hot oil, drain and enjoy! Repeat as needed.",
             "Estimate"    : 62.0,
             "Actuals"     :  1.0,
             "ToDo"        : 61.0,
             "Notes"       : "I have really only done some daydreaming wrt this task.  Sorry Jane, I knew you had big plans for Frankie's blowout BBQ next month, but the honeycomb harvest project is taking all my time."
           }
target story can be obtained useing search rally query : get('UserStory', query='FormattedID =storyID' % , instance=True)
target project - useing RallyGetProject tool. 
""")))  
        )
RallyUpdate = create_model(
    "RallyUpdateModel",
        entity_name=(str, FieldInfo(
        description=("Item type - 'Defect''Task','TestCase','HierarchicalRequirement' or 'Feature'. User story is HierarchicalRequirement type"))),
        entity_json=(str,  FieldInfo(
        description=("""Example for task update:
            {
             "Workspace"     : target_workspace.ref,
             "Project"       : target_project.ref,
             "FormattedID"   : taskID,
             "Name"          : "Stamp logo watermark on all chapter header images",
             "Owner"         : target_owner.ref,
             "Release"       : release.ref,
             "Iteration"     : iteration.ref,
             "WorkProduct"   : target_story.ref,
             "State"         : "Completed",
             "Rank"          : 2,
             "TaskIndex"     : 2,
             "Estimate"      : 18.0,
             "Actuals"       : 2.5,
             "ToDo"          : 15.5,
             "Notes"         : "Bypass any GIFs, they are past end of life date",
             "Blocked"       : "false"
           }
            Release, iteration and target story references case be obtained using RallySearch RallySearchModel:
            get('Release',   query='Name = release_target' ,   instance=True)
            get('Iteration', query='Name = iteration_target' , instance=True)
            get('UserStory', query='FormattedID = toryID',   instance=True)         
                     """)))  
        )
RallyGetProject = create_model(
    "RallyGetProjectModel")

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        # Convert non-serializable objects to string representations
        return str(obj)
    

class RallyApiWrapper(BaseModel):
    server: str
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    workspace: Optional[str] = None
    project: Optional[str] = None

    @root_validator()
    def validate_toolkit(cls, values):
        try:
            from pyral import Rally
        except ImportError:
            raise ImportError(
                "`pyral` package not found, please run "
                "`pip install pyral`"
            )

        server = values['server']
        username = values.get('username')
        password = values.get('password')
        api_key = values.get('api_key')
        workspace = values.get('workspace')
        project = values.get('project')
        if api_key:
            values['client'] = Rally(server, apikey=api_key, workspace=workspace, project=project, isolated_workspace=True)
        else:
            values['client'] = Rally(server, user=username, password=password, workspace=workspace, project=project, isolated_workspace=True)        
        return values

    def get(self, entity_name, fetch=False, query=None, order=None,limit:int=10, **kwargs):
        """ Search for Rally entities using Rally query."""
        #get top 5 stories order by formattedid desc, fields: FormattedID, Description, Owner, Project, ScheduleState, Name
        response = self.client.get(entity_name, fetch=fetch, query=query,limit=limit, pagesize=limit, instance = False,**kwargs)
        # dir(response) results: ['_RallyRESTResponse__retrieveNextPage', '_RallyRESTResponse__retrievePages', '__bool__', '__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__getstate__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__iter__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__next__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__', '_curIndex', '_determineRequestResponseType', '_item', '_item_type', '_limit', '_page', '_servable', '_served', '_stdFormat', 'content', 'context', 'data', 'debug', 'errors', 'first_page', 'headers', 'hydrator', 'max_threads', 'next', 'pageSize', 'request_type', 'resource', 'resultCount', 'session', 'showNextItem', 'startIndex', 'status_code', 'target', 'threads', 'warnings']
        try:
            # Pretty-print `content` if it’s JSON-like
            return(json.dumps(response.content, indent=4))
        except (TypeError, ValueError):
            try:
                return(json.dumps(response.data, indent=4))
            except (TypeError, ValueError):
                return("`data` is not JSON serializable.")
    #not tested: 
    def update(self, entity_name, entity_json):
        """ Search for Jira issues using JQL."""
        response = self.client.update(entity_name, entity_json)
        return(self._handle_response(response))
    #not tested: 
    def create(self, entity_name,entity_json):
        """ Search for Jira issues using JQL."""
        response = self.client.put(entity_name, entity_json)
        return(self._handle_response(response))
    def get_context(self):
        """ Get information about current project, user and workspace. Just in case you need it."""
        return([self.client.getWorkspace().__dict__, self.client.get('User', fetch=True).__dict__, self.client.getProject().__dict__])
    

    def get_available_tools(self):
        return [
            {
                "name": "search",
                "description": self.get.__doc__,
                "args_schema": RallySearch,
                "ref": self.get,
            },
                        {
                "name": "get_context",
                "description": self.get_context.__doc__,
                "args_schema": RallyGetProject,
                "ref": self.get_context,
            },
        ]

    def run(self, mode: str, *args: Any, **kwargs: Any):
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {mode}")