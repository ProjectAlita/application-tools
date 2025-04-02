import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

import pytest

ALLURE_RESULTS_DIR = Path("allure-results")
ALLURE_REPORT_DIR = Path("docs")


@pytest.fixture(scope="session")
def check_env_vars(env_vars):
    """Ensure all required environment variables are set."""
    missing_vars = [var.name for var in env_vars if var.get_value() is None]
    if missing_vars:
        pytest.skip(f"Required environment variables are not set: {', '.join(missing_vars)}")


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    src_path = Path("src").resolve()
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    # Create results directory without removing existing files
    ALLURE_RESULTS_DIR.mkdir(exist_ok=True)
    
    config.option.allure_report_dir = str(ALLURE_RESULTS_DIR)


@pytest.fixture(scope="session", autouse=True)
def test_suite_cleanup():
    # Clean up allure results before test session starts
    if ALLURE_RESULTS_DIR.exists():
        for file in ALLURE_RESULTS_DIR.glob("*"):
            try:
                if file.is_file():
                    file.unlink()
                elif file.is_dir():
                    shutil.rmtree(file)
            except Exception:
                pass
    else:
        ALLURE_RESULTS_DIR.mkdir(exist_ok=True)
    
    yield


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    print(f"\nTest suite finished.\nExit status: {exitstatus}")
    if not os.environ.get("GITHUB_ACTIONS"):
        generate_allure_report()


def generate_allure_report() -> None:
    if not ALLURE_RESULTS_DIR.is_dir() or not any(ALLURE_RESULTS_DIR.iterdir()):
        print(f"No Allure results found for generating report in '{ALLURE_RESULTS_DIR}'.")
        return
    
    ALLURE_REPORT_DIR.mkdir(exist_ok=True)
    
    try:
        subprocess.run(
            [
                "allure",
                "generate",
                str(ALLURE_RESULTS_DIR),
                "--output",
                str(ALLURE_REPORT_DIR),
                "-c",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        print("Allure report generated successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to generate Allure report. Error: {e.stderr}")
    finally:
        # Don't delete the results directory immediately after generating the report
        # This prevents issues with file access during teardown
        pass


# Add a cleanup hook that runs after all pytest hooks are done
@pytest.hookimpl(hookwrapper=True, trylast=True)
def pytest_unconfigure(config):
    yield
    # Clean up allure results after all hooks have completed
    if ALLURE_RESULTS_DIR.exists() and not os.environ.get("PRESERVE_ALLURE_RESULTS"):
        try:
            shutil.rmtree(ALLURE_RESULTS_DIR)
            print(f"Cleaned up '{ALLURE_RESULTS_DIR}' directory.")
        except Exception as e:
            print(f"Warning: Failed to clean up '{ALLURE_RESULTS_DIR}': {e}")