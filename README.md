# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/ProjectAlita/application-tools/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                         |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------------- | -------: | -------: | ------: | --------: |
| src/alita\_tools/github/api\_wrapper.py                      |      129 |       88 |     32% |70-124, 130, 136, 146-157, 162-196, 200-204, 208-234, 238-255, 258-277 |
| src/alita\_tools/github/executor/github\_code\_executor.py   |       24 |       13 |     46% |12, 16, 20-25, 29-35, 39 |
| src/alita\_tools/github/generator/github\_code\_generator.py |       41 |       28 |     32% |46-50, 54, 58-82, 87-104 |
| src/alita\_tools/github/github\_client.py                    |      484 |      422 |     13% |105-150, 166-169, 183-203, 216, 229-246, 258, 270, 295-327, 340-395, 408-431, 447-487, 500-526, 530-578, 600-634, 647-672, 687-695, 710-748, 765-780, 801-835, 848-854, 866, 893-915, 927-933, 946-963, 978-1008, 1021-1061, 1077-1137, 1151-1158, 1175-1189, 1202-1222, 1234-1255, 1258 |
| src/alita\_tools/github/graphql\_client\_wrapper.py          |      206 |      177 |     14% |51-53, 67-68, 81-82, 99, 119-120, 134, 149-150, 170, 197-265, 286-366, 381-397, 401-455, 460-477, 483-502, 506-510, 514-518, 521 |
| src/alita\_tools/github/graphql\_github.py                   |      304 |      264 |     13% |596-597, 630-647, 665-684, 706-720, 752-845, 869-889, 911-936, 960-970, 1005-1087, 1107-1117, 1120-1150, 1178-1209, 1213-1231, 1235-1325, 1350-1377, 1381-1429, 1459-1499 |
| src/alita\_tools/github/schemas.py                           |       40 |        0 |    100% |           |
| src/alita\_tools/github/tool\_prompts.py                     |       10 |        0 |    100% |           |
|                                                    **TOTAL** | **1238** |  **992** | **20%** |           |


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