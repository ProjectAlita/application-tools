import os
import pytest
from dotenv import load_dotenv # Reverted import style

# --- Updated LLM Import for Azure ---
from langchain_openai import AzureChatOpenAI
# --- End LLM Import ---

# Corrected import path based on workspace structure
from alita_tools.github.api_wrapper import AlitaGitHubAPIWrapper

# Load environment variables from .env file
load_dotenv() # Reverted call style

# --- Debugging: Print loaded environment variables --- 
print("--- Debugging .env loading ---")
print(f"AZURE_OPENAI_API_KEY loaded: {'AZURE_OPENAI_API_KEY' in os.environ}")
print(f"AZURE_OPENAI_ENDPOINT loaded: {'AZURE_OPENAI_ENDPOINT' in os.environ}")
print(f"AZURE_OPENAI_API_VERSION loaded: {'AZURE_OPENAI_API_VERSION' in os.environ}")
print(f"AZURE_OPENAI_DEPLOYMENT_NAME loaded: {'AZURE_OPENAI_DEPLOYMENT_NAME' in os.environ}")
print(f"GITHUB_ACCESS_TOKEN loaded: {'GITHUB_ACCESS_TOKEN' in os.environ}")
print(f"GITHUB_REPO loaded: {'GITHUB_REPOSITORY' in os.environ}")
print("-----------------------------")
# --- End Debugging ---

# --- Configuration ---
# Add Azure OpenAI specific environment variables
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY") # Your Azure OpenAI Key
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT") # Your Azure OpenAI Endpoint URL
# Correctly read AZURE_OPENAI_API_VERSION from .env
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01") # Use the AZURE_ variable name
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") # Your Azure deployment name (e.g., gpt-4)

# Add GitHub specific environment variables
GITHUB_TOKEN = os.getenv("GITHUB_ACCESS_TOKEN") # Your GitHub token
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY") # Your GitHub repository

print(AZURE_OPENAI_API_KEY)

# --- Check for necessary environment variables ---
azure_config_present = all([AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME, AZURE_OPENAI_API_VERSION]) # Added version check
github_config_present = all([GITHUB_TOKEN, GITHUB_REPO])
skip_reason = "Missing Azure OpenAI or GitHub configuration in environment variables."

# --- Test Setup ---
@pytest.fixture(scope="module")
def github_api_wrapper() -> AlitaGitHubAPIWrapper:
    """Fixture to initialize the AlitaGitHubAPIWrapper with Azure LLM."""
    if not azure_config_present:
        pytest.skip("Azure OpenAI configuration not found in environment variables.")
    if not github_config_present:
        pytest.skip("GitHub configuration not found in environment variables.")

    # --- Initialize Azure LLM ---
    try:
        print("Creating AzureChatOpenAI instance...")
        llm_instance = AzureChatOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            openai_api_version=AZURE_OPENAI_API_VERSION,
            deployment_name=AZURE_OPENAI_DEPLOYMENT_NAME,
            openai_api_key=AZURE_OPENAI_API_KEY,
            temperature=0
        )
        print("AzureChatOpenAI instance created successfully")
        
        print("Creating AlitaGitHubAPIWrapper instance...")
        # Initialize the wrapper with debug output
        wrapper = AlitaGitHubAPIWrapper(
            llm=llm_instance,
            github_access_token=GITHUB_TOKEN,
            github_repository=GITHUB_REPO
        )
        print("AlitaGitHubAPIWrapper created successfully")
        return wrapper
    except Exception as e:
        print(f"Error during initialization: {e}")
        print(traceback.format_exc())
        raise

# --- Test Case --- 
# Re-added the test function and skipif decorator
@pytest.mark.skipif(not (azure_config_present and github_config_present), reason=skip_reason)
def test_process_github_query_create_branch_and_file(github_api_wrapper: AlitaGitHubAPIWrapper):
    """
    Test the process_github_query tool for a multi-step task using Azure OpenAI.
    NOTE: This test will perform *real* actions on the configured GitHub repository.
          Ensure the target repository and credentials are appropriate for testing.
    """
    # Define the complex task in natural language
    # Using a slightly different name to avoid conflicts if run multiple times
    branch_name = "test-az-branch-from-query"
    file_name = "test_az_query_file.md"
    query = f"Create a branch named '{branch_name}', then create a file named '{file_name}' in that branch with the content '# Test File from Azure Query'."

    print(f"\nRunning process_github_query with query: \"{query}\"")

    try:
        # Execute the query using the run method
        result = github_api_wrapper.run("process_github_query", query=query)

        # --- Verification ---
        print("\nResult from process_github_query:")
        print(result)

        # Add assertions based on the expected outcome.
        # The exact result format depends heavily on the LLM's generated code
        # and what it assigns to the 'result' variable.
        # This is a basic check assuming the LLM includes confirmation in the result.
        # assert isinstance(result, str)
        # assert branch_name in result or "branch created" in result.lower() # Check if branch name or confirmation is in result
        # assert file_name in result or "file created" in result.lower() # Check if file name or confirmation is in result

        # More robust checks would involve using the GitHub API wrapper again
        # to verify the branch and file exist, e.g.:
        branches = github_api_wrapper.run("list_branches_in_repo")
        assert branch_name in branches
        file_content = github_api_wrapper.run("read_file", file_path=file_name, repo_name=GITHUB_REPO) # May need branch specified
        assert "# Test File from Azure Query" in file_content


    except Exception as e:
        pytest.fail(f"process_github_query raised an exception: {e}\n{traceback.format_exc()}") # Added traceback

    # --- Optional Cleanup ---
    print("\nAttempting cleanup...")
    try:
        # Example: Delete the branch (requires delete_branch tool or similar)
        # Ensure the active branch is NOT the one being deleted first
        github_api_wrapper.run("set_active_branch", branch_name=github_api_wrapper.github_base_branch)
        github_api_wrapper.run("delete_branch", branch_name=branch_name) # Assuming delete_branch exists
        print(f"Cleanup skipped (delete branch '{branch_name}' manually if needed).")
        pass
    except Exception as cleanup_e:
        print(f"Cleanup failed: {cleanup_e}")

# Added import for traceback
import traceback