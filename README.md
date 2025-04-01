# application-tools
Default set of tools available in ELITEA for Agents

Link other dependencies to alita-sdk as source code
---

Create any python file in the root folder (for instance, **_link.py_**) with the content below:
```python
import os

# Example for application-tools
# WIN
source_file = 'C:\\\\myProjects\\application-tools\\src\\alita_tools'
symlink_path = 'C:\\\\myProjects\\alita-sdk\\alita_tools'

os.symlink(source_file, symlink_path)
```
Then execute it:
```bash
python link.py
```
Expected result is linked **_alita_tools_** folder in project structure.

**alita-sdk**  
|-- ...  
|-- **aliata_tools**   
|-- ...  
|-- **src**  
|-- ...  

# PyTest
### Dependencies
- pytest
- allure-pytest==2.13.5

### How to run
##### Install all dependencies:

```bash
python -m venv .venv && . .venv/bin/activate &&
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r dev-requirements.txt
pip install pytest coverage allure-pytest
```

##### Run tests:
```bash
pytest .
```
> Make sure you run them from virtual env and from root directory

##### (Optional) Open Allure report:
```bash
allure open docs -h localhost
```
where: docs folder is generated in `conftest.py` automatically from `allure-results` which are being removed during execution
> allure report creates and removes folders **locally** in conftest.py file. Remotely it uses simple-elf/allure-report-action@master

##### (Optional) Run Coverage report:
```bash
coverage run -m pytest 
coverage report
coverage html --show-contexts
```
Open `<full_directory_path>/htmlcov/index.html` in the browser

##### Run specific pytests:
- Keyword
```
pytest -k "test_link_work_items_api_error"
```

- Quit mode
```
pytest -q
```

- With mark
```
pytest -m "positive"
```

- Collect only without running
```
pytest --collect-only
```

- Last failed only
```
pytest --ff
```

- Coverage for specific module
```
coverage erase
coverage run --source=src/alita_tools/ado/work_item/ -m pytest src/tests/ado/work_item/test_unit_ado_wrapper.py
coverage report
coverage html --show-contexts
```

### Add new tests
- Follow the guide for the tests which are already developed.
- Don't forget to add new marker description in markers if any.
- Make sure your tests are using code from src/ but not from virtual env.
- Check the coverage as acceptance criteria for added tests.