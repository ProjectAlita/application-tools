# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/ProjectAlita/application-tools/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                         |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------------- | -------: | -------: | ------: | --------: |
| src/alita\_tools/github/api\_wrapper.py                      |      134 |       92 |     31% |73-125, 131, 137, 141-168, 173-204, 208-212, 216-242, 246-264, 267-285 |
| src/alita\_tools/github/executor/github\_code\_executor.py   |       24 |       13 |     46% |12, 16, 20-25, 29-35, 39 |
| src/alita\_tools/github/generator/github\_code\_generator.py |       41 |       28 |     32% |46-50, 54, 58-82, 87-104 |
| src/alita\_tools/github/github\_client.py                    |      496 |      434 |     12% |105-152, 168-171, 185-205, 218, 231-248, 260, 272, 297-329, 342-397, 410-433, 449-489, 502-528, 532-580, 602-636, 649-674, 689-697, 712-750, 767-782, 803-837, 850-856, 868, 895-917, 929-935, 948-965, 980-1010, 1023-1063, 1079-1139, 1153-1160, 1177-1191, 1204-1224, 1236-1257, 1272-1285, 1288 |
| src/alita\_tools/github/graphql\_client\_wrapper.py          |      648 |      606 |      6% |54-56, 90-107, 124-143, 165-179, 210-303, 326-346, 367-392, 415-425, 460-541, 560-570, 584-595, 598-681, 685-734, 752-783, 787-802, 821-903, 923-1041, 1059-1107, 1121-1175, 1188-1213, 1230-1263, 1267-1319, 1323-1327, 1331-1335, 1354-1422, 1442-1522, 1533-1554, 1565-1628, 1631 |
| src/alita\_tools/github/schemas.py                           |       41 |        0 |    100% |           |
| src/alita\_tools/github/tool.py                              |       21 |        5 |     76% | 22, 31-34 |
| src/alita\_tools/github/tool\_prompts.py                     |       30 |        0 |    100% |           |
|                                                    **TOTAL** | **1435** | **1178** | **18%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/ProjectAlita/application-tools/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/ProjectAlita/application-tools/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/ProjectAlita/application-tools/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/ProjectAlita/application-tools/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2FProjectAlita%2Fapplication-tools%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/ProjectAlita/application-tools/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.