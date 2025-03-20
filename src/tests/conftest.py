import os
import shutil
import subprocess
import sys

import pytest

ALLURE_RESULTS_DIR = "allure-results"
ALLURE_REPORT_DIR = "docs"


@pytest.fixture(scope="session")
def check_env_vars(env_vars):
    """Ensure all required environment variables are set."""
    missing_vars = [var.name for var in env_vars if var.get_value() is None]
    if missing_vars:
        pytest.skip(f"Required environment variables are not set: {missing_vars}\n")


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    abs = os.path.abspath("src")
    if abs not in sys.path:
        sys.path.insert(0, abs)
    if not os.path.exists(ALLURE_RESULTS_DIR):
        os.makedirs(ALLURE_RESULTS_DIR)
    config.option.allure_report_dir = ALLURE_RESULTS_DIR


@pytest.fixture(scope="session", autouse=True)
def test_suite_cleanup():
    yield


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    print(f"\nTest suite finished.\nExit status: {exitstatus}")
    if not os.getenv("GITHUB_ACTIONS"):
        generate_allure_report()


def generate_allure_report():
    if os.path.isdir(ALLURE_RESULTS_DIR):
        os.makedirs(ALLURE_REPORT_DIR, exist_ok=True)
        try:
            subprocess.run(
                [
                    "allure",
                    "generate",
                    ALLURE_RESULTS_DIR,
                    "--output",
                    ALLURE_REPORT_DIR,
                    "-c",
                ],
                check=True,
            )
            print("Allure report generated.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to generate Allure report. Error: {str(e)}")
        finally:
            shutil.rmtree(ALLURE_RESULTS_DIR)
            print(f"Cleaned up '{ALLURE_RESULTS_DIR}' directory.")
    else:
        print(
            f"No Allure results found for generating report in '{ALLURE_RESULTS_DIR}'."
        )
