# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/ProjectAlita/application-tools/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                      |    Stmts |     Miss |   Cover |   Missing |
|---------------------------------------------------------- | -------: | -------: | ------: | --------: |
| src/alita\_tools/ado/test\_plan/test\_plan\_wrapper.py    |      118 |       77 |     35% |131-137, 141-148, 152-157, 161-170, 174-181, 185-190, 194-203, 207-214, 218-227, 231-236, 240 |
| src/alita\_tools/ado/utils.py                             |       20 |       15 |     25% |13-19, 23-29, 32-38 |
| src/alita\_tools/ado/wiki/ado\_wrapper.py                 |      117 |       79 |     32% |70-82, 86-90, 94-99, 103-108, 112-117, 121-126, 140-162, 166-217, 221 |
| src/alita\_tools/ado/work\_item/ado\_wrapper.py           |      259 |      207 |     20% |110-123, 127-151, 154-172, 176-194, 199-204, 210-215, 220-249, 253-279, 284-313, 318-340, 344-371, 375-427, 431-501, 505 |
| src/alita\_tools/base/tool.py                             |       15 |        4 |     73% |     25-28 |
| src/alita\_tools/bitbucket/api\_wrapper.py                |       82 |       45 |     45% |19, 48-70, 74-75, 79, 83-93, 103-110, 122-126, 147-151, 162, 173-176 |
| src/alita\_tools/bitbucket/cloud\_api\_wrapper.py         |      118 |       72 |     39% |17, 24, 28, 32, 36, 40, 44, 51-56, 59-60, 63, 71, 77, 81-86, 89, 99-116, 130-140, 143-145, 148, 154-157, 160-161, 164, 167-174, 177-181, 185-198 |
| src/alita\_tools/bitbucket/tools.py                       |      111 |       46 |     59% |26-32, 46-53, 75-76, 109-110, 121-127, 140-146, 164-169, 196-201, 215 |
| src/alita\_tools/browser/crawler.py                       |       40 |       12 |     70% |20-24, 35-36, 46, 54-57 |
| src/alita\_tools/browser/duck\_duck\_go\_search.py        |       40 |       22 |     45% |26-43, 47-52 |
| src/alita\_tools/browser/google\_search\_rag.py           |       28 |        8 |     71% | 24, 38-44 |
| src/alita\_tools/browser/utils.py                         |       50 |       38 |     24% |10-11, 19-32, 36-48, 52-69 |
| src/alita\_tools/browser/wiki.py                          |       12 |        1 |     92% |        31 |
| src/alita\_tools/confluence/api\_wrapper.py               |      659 |      547 |     17% |268-274, 313-336, 339-347, 351-356, 363-392, 396-406, 411-432, 436-445, 450-493, 498-502, 507-519, 524-527, 531-538, 542-546, 550-564, 568-569, 573, 577, 582-597, 601-603, 611-629, 633-636, 645, 648-649, 652-668, 672-676, 681-686, 691-693, 697-715, 718-775, 785-828, 832-851, 854-858, 881-907, 915-936, 958-1016, 1029-1153, 1162, 1193-1206, 1223-1299, 1320-1470, 1473 |
| src/alita\_tools/confluence/loader.py                     |      124 |      103 |     17% |24-71, 74-87, 99-142, 149-169, 176-193, 200-220 |
| src/alita\_tools/confluence/utils.py                      |       12 |        6 |     50% |7, 10-11, 14-16 |
| src/alita\_tools/elitea\_base.py                          |      115 |       92 |     20% |25, 28-104, 112-142, 161-162, 176-177, 184, 187, 194-209, 234-256, 266-277 |
| src/alita\_tools/github/api\_wrapper.py                   |      105 |       56 |     47% |150-196, 202, 208, 213-247, 250-268, 279-291 |
| src/alita\_tools/github/github\_client.py                 |      499 |      439 |     12% |103-150, 166-169, 183-203, 216, 229-246, 258, 270, 295-327, 340-395, 408-431, 447-487, 500-526, 530-578, 600-634, 647-672, 687-695, 710-748, 765-780, 801-835, 848-854, 867, 894-916, 928-934, 947-964, 979-1009, 1022-1062, 1078-1138, 1152-1159, 1176-1190, 1203-1223, 1235-1256, 1271-1298, 1301 |
| src/alita\_tools/github/graphql\_client\_wrapper.py       |      648 |      606 |      6% |54-56, 90-107, 124-143, 165-179, 210-303, 326-346, 367-392, 415-425, 460-541, 560-570, 584-595, 598-681, 685-734, 752-783, 787-802, 821-903, 923-1041, 1059-1107, 1121-1175, 1188-1213, 1230-1263, 1267-1319, 1323-1327, 1331-1335, 1354-1422, 1442-1522, 1533-1554, 1565-1628, 1631 |
| src/alita\_tools/github/schemas.py                        |       40 |        0 |    100% |           |
| src/alita\_tools/github/tool.py                           |       21 |        5 |     76% | 22, 31-34 |
| src/alita\_tools/github/tool\_prompts.py                  |       29 |        0 |    100% |           |
| src/alita\_tools/gitlab/api\_wrapper.py                   |      199 |      159 |     20% |13, 37-56, 61-63, 68-69, 73-76, 80-83, 86-87, 92-105, 115-120, 130-138, 149-163, 180-196, 209-216, 230-243, 253-255, 275-313, 326-353, 364-371, 375-423, 446-476 |
| src/alita\_tools/gitlab/tools.py                          |      227 |      104 |     54% |56-62, 77-84, 98-103, 121-122, 133-139, 151-157, 171-191, 210-224, 250-255, 270-275, 285-290, 300-305, 320-325, 354-359 |
| src/alita\_tools/gitlab/utils.py                          |       43 |       40 |      7% |5-45, 50-67 |
| src/alita\_tools/gitlab\_org/api\_wrapper.py              |      267 |      203 |     24% |166-183, 187, 190-205, 209-210, 214-219, 225-242, 247-256, 261-267, 272-289, 294-309, 313-324, 328-343, 348-353, 371-399, 403-410, 414-441, 455-475, 480-492, 497-499, 504-506, 509, 534-564, 568 |
| src/alita\_tools/jira/api\_wrapper.py                     |      629 |      531 |     16% |169-174, 179-212, 217-240, 253-296, 308-312, 315-322, 326-327, 331-335, 339-352, 356-359, 363-369, 373-376, 380-389, 410-438, 441-492, 496-506, 511-518, 522-525, 529-532, 541-544, 551-561, 566-572, 576-577, 581-583, 587-602, 606-625, 631-647, 651-655, 660-672, 676-689, 693-703, 707-718, 724-733, 737-764, 769-773, 789-813, 823, 873-948, 960-1005, 1011-1013, 1036-1112, 1132-1222, 1225 |
| src/alita\_tools/llm/img\_utils.py                        |       21 |       16 |     24% |8-9, 13-22, 26-43 |
| src/alita\_tools/qtest/api\_wrapper.py                    |      226 |      174 |     23% |114-116, 121-137, 141, 145-171, 174-184, 187-207, 211-220, 224-246, 249-275, 279-281, 284-292, 296-308, 312-315, 320-334, 338-339, 344-360, 364-384, 389-390, 394-401, 405 |
| src/alita\_tools/qtest/tool.py                            |       14 |        1 |     93% |        21 |
| src/alita\_tools/report\_portal/api\_wrapper.py           |       67 |       32 |     52% |65-69, 75-79, 88-105, 113, 122, 130, 139, 148, 155, 163, 166 |
| src/alita\_tools/report\_portal/report\_portal\_client.py |       51 |       39 |     24% |7-10, 13, 19-26, 29-33, 36-40, 43-47, 50-54, 57-61, 64-68, 71-75 |
| src/alita\_tools/servicenow/api\_wrapper.py               |       77 |       52 |     32% |57-62, 67-82, 85-90, 94-103, 114-123, 126-131, 134 |
| src/alita\_tools/sharepoint/api\_wrapper.py               |       83 |       58 |     30% |46-76, 81-93, 98-120, 124-133, 136 |
| src/alita\_tools/sharepoint/authorization\_helper.py      |       40 |       32 |     20% |9-17, 20-37, 40-43, 47-57 |
| src/alita\_tools/sharepoint/utils.py                      |       12 |        9 |     25% |      6-14 |
| src/alita\_tools/testio/api\_wrapper.py                   |      188 |      142 |     24% |57-67, 70-74, 82-88, 97-103, 111-122, 129-137, 144-150, 158-167, 175-182, 190-199, 207-210, 217-224, 232-236, 251-268, 277-286, 294-300, 309-318, 328-335, 338 |
| src/alita\_tools/testrail/api\_wrapper.py                 |      107 |       76 |     29% |296-308, 333-339, 343-347, 365-391, 414-455, 482-488, 503-517, 520 |
| src/alita\_tools/utils/content\_parser.py                 |       91 |       72 |     21% |13-24, 28-31, 34-40, 43-51, 54-61, 64-73, 77-85, 88-98, 101-105 |
| src/alita\_tools/xray/api\_wrapper.py                     |       81 |       49 |     40% |96-100, 117-142, 147-168, 173-178, 183-187, 190 |
| src/alita\_tools/zephyr/Zephyr.py                         |       16 |        9 |     44% |18-21, 32-33, 42-48 |
| src/alita\_tools/zephyr/api\_wrapper.py                   |       51 |       27 |     47% |44-50, 53-68, 72-75, 79, 84-90, 93 |
| src/alita\_tools/zephyr/rest\_client.py                   |       92 |       64 |     30% |12-13, 38-42, 45, 48, 51, 57-65, 74, 78-85, 89-92, 95, 98, 136-165, 175-194 |
| src/alita\_tools/zephyr\_enterprise/api\_wrapper.py       |       73 |       53 |     27% |20-23, 28-31, 36-39, 49-59, 67-70, 80-121, 124 |
| src/alita\_tools/zephyr\_enterprise/zephyr\_enterprise.py |       50 |       27 |     46% |26-27, 39-47, 59-73, 83, 93, 103, 112, 121, 140-153, 178 |
| src/alita\_tools/zephyr\_scale/api\_wrapper.py            |      486 |      412 |     15% |258-282, 295-308, 317-321, 331-337, 349-357, 368-376, 386-390, 405-429, 438-442, 453-457, 468-473, 484-490, 495-499, 504-508, 513-517, 534-544, 555-577, 590-600, 613-643, 655-658, 671-687, 704-721, 735-747, 762-815, 830-876, 893-926, 959-1062, 1076-1119, 1124-1162, 1180-1205, 1221-1254, 1272-1319, 1322 |
|                                                 **TOTAL** | **6453** | **4861** | **25%** |           |


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