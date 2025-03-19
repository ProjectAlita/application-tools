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

Install all dependencies:

```bash
python -m venv .venv && . .venv/bin/activate &&
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r dev-requirements.txt
pip install pytest coverage allure-pytest
```

Run tests:
```bash
pytest .
```

Open Allure report:
```bash
allure open docs -h localhost
```
where: docs folder is generated in `conftest.py` automatically from `allure-results` which are being removed during execution

Run Coverage report:
```bash
coverage run -m pytest &&
coverage report &&
coverage html --show-context
```
Open `<full_directory_path>/htmlcov/index.html` in the browser