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