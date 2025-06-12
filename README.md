# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/ProjectAlita/application-tools/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                         |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------------- | -------: | -------: | ------: | --------: |
| src/alita\_tools/base/tool.py                                |       15 |        4 |     73% |     25-28 |
| src/alita\_tools/confluence/api\_wrapper.py                  |      647 |      631 |      2% |   20-1447 |
| src/alita\_tools/elitea\_base.py                             |       53 |       37 |     30% |23, 26-35, 41, 44, 51-66, 91-113 |
| src/alita\_tools/github/api\_wrapper.py                      |      132 |       90 |     32% |73-119, 125, 131, 135-162, 167-198, 202-206, 210-236, 240-258, 261-279 |
| src/alita\_tools/github/executor/github\_code\_executor.py   |       24 |       13 |     46% |12, 16, 20-25, 29-35, 39 |
| src/alita\_tools/github/generator/github\_code\_generator.py |       41 |       28 |     32% |46-50, 54, 58-82, 87-104 |
| src/alita\_tools/github/github\_client.py                    |      499 |      439 |     12% |103-150, 166-169, 183-203, 216, 229-246, 258, 270, 295-327, 340-395, 408-431, 447-487, 500-526, 530-578, 600-634, 647-672, 687-695, 710-748, 765-780, 801-835, 848-854, 867, 894-916, 928-934, 947-964, 979-1009, 1022-1062, 1078-1138, 1152-1159, 1176-1190, 1203-1223, 1235-1256, 1271-1298, 1301 |
| src/alita\_tools/github/graphql\_client\_wrapper.py          |      648 |      606 |      6% |54-56, 90-107, 124-143, 165-179, 210-303, 326-346, 367-392, 415-425, 460-541, 560-570, 584-595, 598-681, 685-734, 752-783, 787-802, 821-903, 923-1041, 1059-1107, 1121-1175, 1188-1213, 1230-1263, 1267-1319, 1323-1327, 1331-1335, 1354-1422, 1442-1522, 1533-1554, 1565-1628, 1631 |
| src/alita\_tools/github/schemas.py                           |       41 |        0 |    100% |           |
| src/alita\_tools/github/tool.py                              |       21 |        5 |     76% | 22, 31-34 |
| src/alita\_tools/github/tool\_prompts.py                     |       30 |        0 |    100% |           |
| src/alita\_tools/jira/api\_wrapper.py                        |      629 |      531 |     16% |169-174, 179-212, 217-240, 253-296, 308-312, 315-322, 326-327, 331-335, 339-352, 356-359, 363-369, 373-376, 380-389, 410-438, 441-492, 496-506, 511-518, 522-525, 529-532, 541-544, 551-561, 566-572, 576-577, 581-583, 587-602, 606-625, 631-647, 651-655, 660-672, 676-689, 693-703, 707-718, 724-733, 737-764, 769-773, 789-813, 823, 873-948, 960-1005, 1011-1013, 1036-1112, 1132-1222, 1225 |
| src/alita\_tools/llm/img\_utils.py                           |       21 |       16 |     24% |8-9, 13-22, 26-43 |
|                                                    **TOTAL** | **2801** | **2400** | **14%** |           |


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