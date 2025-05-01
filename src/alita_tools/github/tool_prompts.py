CREATE_FILE_PROMPT = """Create new file in your github repository."""

UPDATE_FILE_PROMPT = """Updates the contents of a file in repository. Input MUST strictly follow these rules:
Specify the file to modify by passing a full file path (the path must not start with a slash); Specify at lest 2 lines of the old contents which you would like to replace wrapped in OLD <<<< and >>>> OLD; Specify the new contents which you would like to replace the old contents with wrapped in NEW <<<< and >>>> NEW; NEW content may contain lines from OLD content in case you want to add content without removing the old content

Example 1: Replace "old contents" to "new contents" in the file /test/test.txt from , pass in the following string:

test/test.txt

This is text that will not be changed
OLD <<<<
old contents
>>>> OLD
NEW <<<<
new contents
>>>> NEW

Example 2: Extend "existing contents" with new contents" in the file /test/test.txt, pass in the following string:

test/test.txt

OLD <<<<
existing contents
>>>> OLD
NEW <<<<
existing contents
new contents
>>>> NEW"""

CREATE_ISSUE_PROMPT = """
Tool allows to create a new issue in a GitHub repository.
**IMPORTANT**: Input to this tool MUST strictly follow these rules:
- First, you must specify the title of the issue.
Optionally you can specify:
- a detailed description or body of the issue
- labels for the issue, each separated by a comma. For labels, write `labels:` followed by a comma-separated list of labels.
- assignees for the issue, each separated by a comma. For assignees, write `assignees:` followed by a comma-separated 
list of GitHub usernames.

Ensure that each command (`labels:` and `assignees:`) starts in a new line, if used.

For example, if you would like to create an issue titled "Fix login bug" with a body explaining the problem and tagged with `bug` 
and `urgent` labels, plus assigned to `user123`, you would pass in the following string:

Fix login bug

The login button isn't responding on the main page. Reproduced on various devices.

labels: bug, urgent
assignees: user123
"""

UPDATE_ISSUE_PROMPT = """
Tool allows you to update an existing issue in a GitHub repository. **IMPORTANT**: Input MUST follow 
these rules:
- You must specify the repository name where the issue exists.
- You must specify the issue ID that you wish to update.

Optional fields:
- You can then provide the new title of the issue.
- You can provide a new detailed description or body of the issue.
- You can specify new labels for the issue, each separated by a comma.
- You can specify new assignees for the issue, each separated by a comma.
- You can change the state of the issue to either 'open' or 'closed'.

If assignees or labels are not passed or passed as empty lists they will be removed from the issue.

For example, to update an issue in the 'octocat/Hello-World' repository with ID 42, changing the title and closing the issue, the input should be:

octocat/Hello-World

42

New Issue Title

New detailed description goes here.

labels: bug, ui

assignees: user1, user2

closed
"""

CREATE_ISSUE_ON_PROJECT_PROMPT = """
Tool allows for creating GitHub issues within specified projects. Adhere to these steps:

1. Specify both project and issue titles.
2. Optionally, include a detailed issue description and any additional required fields in JSON format.

Ensure JSON fields are correctly named as expected by the project.

**Example**:
For an issue titled "Fix Navigation Bar" in the "WebApp Redesign" project, addressing mobile view responsiveness, set as medium priority, in staging, and assigned to "dev_lead":

Project: WebApp Redesign
Issue Title: Fix Navigation Bar
Description: The navigation bar disappears on mobile view. Needs responsive fix.
JSON:
{
  "Environment": "Staging",
  "Priority": "Medium",
  "Labels": ["bug", "UI"],
  "Assignees": ["dev_lead"]
}
"""

UPDATE_ISSUE_ON_PROJECT_PROMPT = """
Tool updates GitHub issues for the specified project. Follow these steps:

- Provide the issue number and project title.
- Optionally, adjust the issue's title, description, and other fields.
- Use JSON key-value pairs to update or clear fields, setting empty strings to clear.

Ensure field names align with project requirements.

**Example**:
Update issue 42 in "WebApp Redesign," change its title, modify the description, and update settings:

Issue Number: 42
Project: WebApp Redesign
New Title: Update Navigation Bar

Description:
Implement dropdown menus based on user roles for full device compatibility.

JSON:
{
  "Environment": "Production",
  "Type": "Enhancement",
  "Priority": "High",
  "Labels": ["UI"],
  "Assignees": ["ui_team"]
}
"""