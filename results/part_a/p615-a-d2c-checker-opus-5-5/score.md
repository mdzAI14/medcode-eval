Code set: ICD-10-CM FY2027 (October 1, 2026 release). Source run: runs/part_a/p65-a-changes-opus-5-5. Model: claude-opus-5-5. Reader: 2. Probes: description_to_code.

| Answer | n | Correct | Wrong | Invalid | Missing |
|---|---|---|---|---|---|
| first | 188 | 43 | 71 | 74 | 0 |
| final | 188 | 65 | 33 | 90 | 0 |

First-answer counts equal the source run's stored score: yes.

Probes with a second turn:

| Rule | n | final_correct | final_wrong_still_rule | final_wrong_no_rule | final_invalid | final_same_as_first |
|---|---|---|---|---|---|---|
| not_in_code_set | 50 | 14 | 5 | 16 | 15 | 0 |
| header_not_billable | 10 | 8 | 0 | 1 | 1 | 0 |
| total | 60 | 22 | 5 | 17 | 16 | 0 |
