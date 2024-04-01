import os
from typing import Dict, Any, Optional
from pydantic import root_validator
from langchain.utils import get_from_dict_or_env

from langchain_community.utilities.github import GitHubAPIWrapper

class AlitaGitHubAPIWrapper(GitHubAPIWrapper):
    github: Any  #: :meta private:
    github_repo_instance: Any  #: :meta private:
    github_repository: Optional[str] = None
    active_branch: Optional[str] = None
    github_base_branch: Optional[str] = None
    
    
    @root_validator()
    def validate_environment(cls, values: Dict) -> Dict:
         
        github_app_id = get_from_dict_or_env(values, 
                                             "github_app_id", 
                                             "GITHUB_APP_ID",
                                             default='')
        
        github_app_private_key = get_from_dict_or_env(
            values, 
            "github_app_private_key", 
            "GITHUB_APP_PRIVATE_KEY", 
            default=''
        )
        
        github_access_token = get_from_dict_or_env(
            values, "github_access_token",  "GITHUB_ACCESS_TOKEN", default='')
        
        github_username = get_from_dict_or_env(
            values, "github_username", "GITHUB_USERNAME", default='')
        github_password = get_from_dict_or_env(
            values, "github_password", "GITHUB_PASSWORD", default='')

        github_repository = get_from_dict_or_env(
            values, "github_repository", "GITHUB_REPOSITORY")

        active_branch = get_from_dict_or_env(
            values, "active_branch", "ACTIVE_BRANCH", default='ai')
        github_base_branch = get_from_dict_or_env(
            values, "github_base_branch", "GITHUB_BASE_BRANCH", default="main")

        if github_app_private_key and os.path.exists(github_app_private_key):    
            with open(github_app_private_key, "r") as f:
                private_key = f.read()
        else:
            private_key = github_app_private_key
        
        try:
            from github import Auth, GithubIntegration, Github
            from github.Consts import DEFAULT_BASE_URL
        except ImportError:
            raise ImportError(
                "PyGithub is not installed. "
                "Please install it with `pip install PyGithub`"
            )
            
        github_base_url = get_from_dict_or_env(
            values, "github_base_url", "GITHUB_BASE_URL", default=DEFAULT_BASE_URL)        
        if github_access_token:
            auth = Auth.Token(github_access_token)
        elif github_username and github_password:
            auth = Auth.Login(github_username, github_password)
        elif github_app_id and private_key:
            auth = Auth.AppAuth(github_app_id, private_key)
        else:
            auth = None
            
        if auth is None:
            g = Github(base_url=github_base_url)
        else:
            gi = GithubIntegration(base_url=github_base_url, auth=auth)
            installation = gi.get_installations()[0]

            # create a GitHub instance:
            g = installation.get_github_for_installation()

        values["github"] = g
        values["github_repo_instance"] = g.get_repo(github_repository)
        values["github_repository"] = github_repository
        values["active_branch"] = active_branch
        values["github_base_branch"] = github_base_branch
        return values