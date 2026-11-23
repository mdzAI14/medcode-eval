# Results

Code set: ICD-10-CM FY2027 (October 1, 2026 release).

Every figure below is computed by medcode_eval.results from the stored files in results/part_a/, results/part_b/ and results/part_c/ and from data/ and refdata/. Rebuild with `venv/bin/python -m medcode_eval.results --write`; check with `venv/bin/python -m medcode_eval.results --check`. Codes are shown with the dot after the third character.

## S0. Reported runs

| Run | What | Model | Backend | Effort | Temperature | Seed | Prompt suffix | Reader | Started | Items answered |
|---|---|---|---|---|---|---|---|---|---|---|
| p62-a-lite-opus-5-5-reader2 | Part A lite | claude-opus-5-5 | remote | medium | - | - | - | Part A reader 2 | 2026-11-11 | 151 |
| lite-nothink-qwen3-4b-reader2 | Part A lite | qwen3:4b | ollama | - | 0 | 20261001 | `/no_think` | Part A reader 2 | 2026-11-11 | 151 |
| p65-a-changes-opus-5-5 | Part A changes | claude-opus-5-5 | remote | medium | - | - | - | Part A reader 2 | 2026-11-11 | 462 |
| changes-nothink-qwen3-4b-reader2 | Part A changes | qwen3:4b | ollama | - | 0 | 20261001 | `/no_think` | Part A reader 2 | 2026-11-11 | 462 |
| p615-a-d2c-checker-opus-5-5 | Part A changes, description-to-code with checker | claude-opus-5-5 | remote | medium | - | - | - | Part A reader 2 | 2026-11-16 | 188 |
| p612-b-plain-opus-5-5 | Part B plain | claude-opus-5-5 | remote | medium | - | - | - | Part B JSON list | 2026-11-16 | 25 |
| p613-b-plain-qwen3-4b | Part B plain | qwen3:4b | ollama | - | 0 | 20261001 | `/no_think` | Part B JSON list | 2026-11-16 | 25 |
| p612-b-checker-opus-5-5 | Part B with checker | claude-opus-5-5 | remote | medium | - | - | - | Part B JSON list | 2026-11-16 | 25 |
| p613-b-checker-qwen3-4b | Part B with checker | qwen3:4b | ollama | - | 0 | 20261001 | `/no_think` | Part B JSON list | 2026-11-16 | 25 |

## S1. Part A lite

### p62-a-lite-opus-5-5-reader2 (claude-opus-5-5, reader 2)

| Group | Value | n | Correct | Accuracy | Invalid | Missing |
|---|---|---|---|---|---|---|
| overall |  | 151 | 147 | 0.9735 | 0 | 0 |
| type | code_to_description | 50 | 50 | 1.0000 | 0 | 0 |
| type | description_to_code | 50 | 50 | 1.0000 | 0 | 0 |
| type | status | 51 | 47 | 0.9216 | 0 | 0 |

Status probes, answer by response:

| Answer \ response | billable | header | not_a_code | invalid | missing |
|---|---|---|---|---|---|
| billable | 16 | 0 | 1 | 0 | 0 |
| header | 0 | 17 | 0 | 0 | 0 |
| not_a_code | 1 | 2 | 14 | 0 | 0 |

### lite-nothink-qwen3-4b-reader2 (qwen3:4b, reader 2)

| Group | Value | n | Correct | Accuracy | Invalid | Missing |
|---|---|---|---|---|---|---|
| overall |  | 151 | 41 | 0.2715 | 2 | 0 |
| type | code_to_description | 50 | 21 | 0.4200 | 0 | 0 |
| type | description_to_code | 50 | 0 | 0.0000 | 2 | 0 |
| type | status | 51 | 20 | 0.3922 | 0 | 0 |

Status probes, answer by response:

| Answer \ response | billable | header | not_a_code | invalid | missing |
|---|---|---|---|---|---|
| billable | 3 | 1 | 13 | 0 | 0 |
| header | 5 | 0 | 12 | 0 | 0 |
| not_a_code | 0 | 0 | 17 | 0 | 0 |

## S2. Part A changes

### p65-a-changes-opus-5-5 (claude-opus-5-5, reader 2)

Overall, by type and by change (all probe types):

| Group | Value | n | Correct | Accuracy | Invalid | Missing |
|---|---|---|---|---|---|---|
| overall |  | 462 | 100 | 0.2165 | 74 | 0 |
| type | description_to_code | 188 | 43 | 0.2287 | 74 | 0 |
| type | status | 274 | 57 | 0.2080 | 0 | 0 |
| change | added_billable | 378 | 92 | 0.2434 | 74 | 0 |
| change | added_header | 48 | 6 | 0.1250 | 0 | 0 |
| change | billable_to_header | 15 | 1 | 0.0667 | 0 | 0 |
| change | removed | 21 | 1 | 0.0476 | 0 | 0 |

Status probes by change:

| Change | n | Correct |
|---|---|---|
| added_billable | 190 | 49 |
| added_header | 48 | 6 |
| billable_to_header | 15 | 1 |
| removed | 21 | 1 |

Status probes, answer by response:

| Answer \ response | billable | header | not_a_code | invalid | missing |
|---|---|---|---|---|---|
| billable | 49 | 1 | 140 | 0 | 0 |
| header | 15 | 7 | 41 | 0 | 0 |
| not_a_code | 15 | 5 | 1 | 0 | 0 |

Description-to-code:

| n | Correct | Wrong code | No single code | Missing |
|---|---|---|---|---|
| 188 | 43 | 71 | 74 | 0 |

Pattern count (not a reading): of the 74 no-single-code replies, 71 open (think blocks dropped) with "I can't", "I'm not" or "I don't" (straight or curly apostrophe).

### changes-nothink-qwen3-4b-reader2 (qwen3:4b, reader 2)

Overall, by type and by change (all probe types):

| Group | Value | n | Correct | Accuracy | Invalid | Missing |
|---|---|---|---|---|---|---|
| overall |  | 462 | 28 | 0.0606 | 10 | 0 |
| type | description_to_code | 188 | 0 | 0.0000 | 10 | 0 |
| type | status | 274 | 28 | 0.1022 | 0 | 0 |
| change | added_billable | 378 | 5 | 0.0132 | 10 | 0 |
| change | added_header | 48 | 2 | 0.0417 | 0 | 0 |
| change | billable_to_header | 15 | 0 | 0.0000 | 0 | 0 |
| change | removed | 21 | 21 | 1.0000 | 0 | 0 |

Status probes by change:

| Change | n | Correct |
|---|---|---|
| added_billable | 190 | 5 |
| added_header | 48 | 2 |
| billable_to_header | 15 | 0 |
| removed | 21 | 21 |

Status probes, answer by response:

| Answer \ response | billable | header | not_a_code | invalid | missing |
|---|---|---|---|---|---|
| billable | 5 | 1 | 184 | 0 | 0 |
| header | 3 | 2 | 58 | 0 | 0 |
| not_a_code | 0 | 0 | 21 | 0 | 0 |

Description-to-code:

| n | Correct | Wrong code | No single code | Missing |
|---|---|---|---|---|
| 188 | 0 | 178 | 10 | 0 |

Pattern count (not a reading): of the 10 no-single-code replies, 0 open (think blocks dropped) with "I can't", "I'm not" or "I don't" (straight or curly apostrophe).

## S3. The checker on the stored Part A answers

Description-to-code probes only. Each answered code is checked alone. A wrong code is classed not_in_code_set if that finding is present, else header_not_billable, else another error rule, else no error finding.

| Run | Model | Answered | Correct | Invalid | Wrong | not_in_code_set | header_not_billable | Other error rule | No error finding | Correct with an error finding |
|---|---|---|---|---|---|---|---|---|---|---|
| p62-a-lite-opus-5-5-reader2 | claude-opus-5-5 | 50 | 50 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| lite-nothink-qwen3-4b-reader2 | qwen3:4b | 50 | 0 | 2 | 48 | 26 | 10 | 0 | 12 | 0 |
| p65-a-changes-opus-5-5 | claude-opus-5-5 | 188 | 43 | 74 | 71 | 50 | 10 | 0 | 11 | 0 |
| changes-nothink-qwen3-4b-reader2 | qwen3:4b | 188 | 0 | 10 | 178 | 105 | 33 | 0 | 40 | 0 |

Correct answers that draw an error finding:

| Run | Probe | Code | Error rules |
|---|---|---|---|
| p62-a-lite-opus-5-5-reader2 | d2c-0379 | H62.8X1 | manifestation_first |

## S4. The Part A checker condition

### p615-a-d2c-checker-opus-5-5 (claude-opus-5-5, source run p65-a-changes-opus-5-5)

| Answer | n | Correct | Wrong | Invalid | Missing |
|---|---|---|---|---|---|
| first | 188 | 43 | 71 | 74 | 0 |
| final | 188 | 65 | 33 | 90 | 0 |

First-answer counts equal the source run's stored score: yes.

Second turns by rule (from the stored score):

| Rule | n | final_correct | final_wrong_still_rule | final_wrong_no_rule | final_invalid | final_same_as_first |
|---|---|---|---|---|---|---|
| header_not_billable | 10 | 8 | 0 | 1 | 1 | 0 |
| not_in_code_set | 50 | 14 | 5 | 16 | 15 | 0 |
| total | 60 | 22 | 5 | 17 | 16 | 0 |

Final answers equal to the longest stored prefix named in their not_in_code_set finding: 8, of which correct: 0.

Final answers that are one of the codes listed in their header_not_billable finding: 9, of which correct: 8.

Wrong codes that draw neither rule: first answers 11, final answers 28.

#### Sensitivity figure, made after the results were seen; not the reported score

A lenient reading, applied only where the stored reading is invalid: on the first non-empty line of the reply (think blocks dropped) with the characters * _ and ` removed, the first token matching `(?<![A-Za-z0-9.])[A-Z][0-9][0-9A-Z](?:\.?[0-9A-Z]{1,4})?(?![A-Za-z0-9])`, compared with the expected code without dots.

| Answer | Invalid replies | With such a token | Token equals the expected code | Correct if they were counted |
|---|---|---|---|---|
| first | 74 | 25 | 1 | 44 |
| final | 90 | 41 | 1 | 66 |

## S5. Part B

### p612-b-plain-opus-5-5 (claude-opus-5-5, plain)

Gold sha256: 3ba94808da8b7970192a1c4f391aa106855125fb7e2abcede50716039abed633 (equals the gold files as they are: yes). Cases: 25. Second turns: 0. Error findings: first answers 3, final answers 3. Required codes found: first 40 of 43, final 40 of 43.

First answer:

| Group | Value | n | Exact | First-listed | Correct | Missing | Extra | Optional given | Precision | Recall | Invalid | No answer | Error findings | Review findings | Cases with an error finding | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| overall |  | 25 | 21 | 24 | 40 | 3 | 5 | 3 | 0.8889 | 0.9302 | 0 | 0 | 3 | 2 | 3 |  |
| target trap | combination | 5 | 5 | 5 | 8 | 0 | 0 | 0 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | fewer than 10 cases |
| target trap | excludes1 | 5 | 4 | 5 | 6 | 0 | 2 | 0 | 0.7500 | 1.0000 | 0 | 0 | 0 | 2 | 0 | fewer than 10 cases |
| target trap | laterality | 5 | 5 | 5 | 7 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | fewer than 10 cases |
| target trap | sequencing | 5 | 4 | 5 | 10 | 1 | 1 | 0 | 0.9091 | 0.9091 | 0 | 0 | 1 | 0 | 1 | fewer than 10 cases |
| target trap | seventh_character | 5 | 3 | 4 | 9 | 2 | 2 | 2 | 0.8182 | 0.8182 | 0 | 0 | 2 | 0 | 2 | fewer than 10 cases |
| specialty | ed | 5 | 5 | 5 | 10 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | fewer than 10 cases |
| specialty | ent | 5 | 4 | 5 | 6 | 1 | 1 | 0 | 0.8571 | 0.8571 | 0 | 0 | 1 | 0 | 1 | fewer than 10 cases |
| specialty | gi | 5 | 4 | 5 | 8 | 0 | 2 | 0 | 0.8000 | 1.0000 | 0 | 0 | 0 | 2 | 0 | fewer than 10 cases |
| specialty | ophtho | 5 | 4 | 5 | 9 | 1 | 1 | 2 | 0.9000 | 0.9000 | 0 | 0 | 1 | 0 | 1 | fewer than 10 cases |
| specialty | ortho | 5 | 4 | 4 | 7 | 1 | 1 | 0 | 0.8750 | 0.8750 | 0 | 0 | 1 | 0 | 1 | fewer than 10 cases |

Final answer:

| Group | Value | n | Exact | First-listed | Correct | Missing | Extra | Optional given | Precision | Recall | Invalid | No answer | Error findings | Review findings | Cases with an error finding | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| overall |  | 25 | 21 | 24 | 40 | 3 | 5 | 3 | 0.8889 | 0.9302 | 0 | 0 | 3 | 2 | 3 |  |
| target trap | combination | 5 | 5 | 5 | 8 | 0 | 0 | 0 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | fewer than 10 cases |
| target trap | excludes1 | 5 | 4 | 5 | 6 | 0 | 2 | 0 | 0.7500 | 1.0000 | 0 | 0 | 0 | 2 | 0 | fewer than 10 cases |
| target trap | laterality | 5 | 5 | 5 | 7 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | fewer than 10 cases |
| target trap | sequencing | 5 | 4 | 5 | 10 | 1 | 1 | 0 | 0.9091 | 0.9091 | 0 | 0 | 1 | 0 | 1 | fewer than 10 cases |
| target trap | seventh_character | 5 | 3 | 4 | 9 | 2 | 2 | 2 | 0.8182 | 0.8182 | 0 | 0 | 2 | 0 | 2 | fewer than 10 cases |
| specialty | ed | 5 | 5 | 5 | 10 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | fewer than 10 cases |
| specialty | ent | 5 | 4 | 5 | 6 | 1 | 1 | 0 | 0.8571 | 0.8571 | 0 | 0 | 1 | 0 | 1 | fewer than 10 cases |
| specialty | gi | 5 | 4 | 5 | 8 | 0 | 2 | 0 | 0.8000 | 1.0000 | 0 | 0 | 0 | 2 | 0 | fewer than 10 cases |
| specialty | ophtho | 5 | 4 | 5 | 9 | 1 | 1 | 2 | 0.9000 | 0.9000 | 0 | 0 | 1 | 0 | 1 | fewer than 10 cases |
| specialty | ortho | 5 | 4 | 4 | 7 | 1 | 1 | 0 | 0.8750 | 0.8750 | 0 | 0 | 1 | 0 | 1 | fewer than 10 cases |

### p613-b-plain-qwen3-4b (qwen3:4b, plain)

Gold sha256: 3ba94808da8b7970192a1c4f391aa106855125fb7e2abcede50716039abed633 (equals the gold files as they are: yes). Cases: 25. Second turns: 0. Error findings: first answers 116, final answers 116. Required codes found: first 1 of 43, final 1 of 43.

First answer:

| Group | Value | n | Exact | First-listed | Correct | Missing | Extra | Optional given | Precision | Recall | Invalid | No answer | Error findings | Review findings | Cases with an error finding | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| overall |  | 25 | 0 | 0 | 1 | 42 | 127 | 0 | 0.0078 | 0.0233 | 1 | 0 | 116 | 0 | 22 |  |
| target trap | combination | 5 | 0 | 0 | 0 | 8 | 11 | 0 | 0.0000 | 0.0000 | 0 | 0 | 10 | 0 | 5 | fewer than 10 cases |
| target trap | excludes1 | 5 | 0 | 0 | 0 | 6 | 10 | 0 | 0.0000 | 0.0000 | 0 | 0 | 7 | 0 | 4 | fewer than 10 cases |
| target trap | laterality | 5 | 0 | 0 | 1 | 6 | 6 | 0 | 0.1429 | 0.1429 | 1 | 0 | 6 | 0 | 4 | fewer than 10 cases |
| target trap | sequencing | 5 | 0 | 0 | 0 | 11 | 90 | 0 | 0.0000 | 0.0000 | 0 | 0 | 87 | 0 | 5 | fewer than 10 cases |
| target trap | seventh_character | 5 | 0 | 0 | 0 | 11 | 10 | 0 | 0.0000 | 0.0000 | 0 | 0 | 6 | 0 | 4 | fewer than 10 cases |
| specialty | ed | 5 | 0 | 0 | 1 | 9 | 10 | 0 | 0.0909 | 0.1000 | 0 | 0 | 7 | 0 | 5 | fewer than 10 cases |
| specialty | ent | 5 | 0 | 0 | 0 | 7 | 89 | 0 | 0.0000 | 0.0000 | 0 | 0 | 87 | 0 | 4 | fewer than 10 cases |
| specialty | gi | 5 | 0 | 0 | 0 | 8 | 9 | 0 | 0.0000 | 0.0000 | 0 | 0 | 5 | 0 | 4 | fewer than 10 cases |
| specialty | ophtho | 5 | 0 | 0 | 0 | 10 | 11 | 0 | 0.0000 | 0.0000 | 0 | 0 | 10 | 0 | 5 | fewer than 10 cases |
| specialty | ortho | 5 | 0 | 0 | 0 | 8 | 8 | 0 | 0.0000 | 0.0000 | 1 | 0 | 7 | 0 | 4 | fewer than 10 cases |

Final answer:

| Group | Value | n | Exact | First-listed | Correct | Missing | Extra | Optional given | Precision | Recall | Invalid | No answer | Error findings | Review findings | Cases with an error finding | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| overall |  | 25 | 0 | 0 | 1 | 42 | 127 | 0 | 0.0078 | 0.0233 | 1 | 0 | 116 | 0 | 22 |  |
| target trap | combination | 5 | 0 | 0 | 0 | 8 | 11 | 0 | 0.0000 | 0.0000 | 0 | 0 | 10 | 0 | 5 | fewer than 10 cases |
| target trap | excludes1 | 5 | 0 | 0 | 0 | 6 | 10 | 0 | 0.0000 | 0.0000 | 0 | 0 | 7 | 0 | 4 | fewer than 10 cases |
| target trap | laterality | 5 | 0 | 0 | 1 | 6 | 6 | 0 | 0.1429 | 0.1429 | 1 | 0 | 6 | 0 | 4 | fewer than 10 cases |
| target trap | sequencing | 5 | 0 | 0 | 0 | 11 | 90 | 0 | 0.0000 | 0.0000 | 0 | 0 | 87 | 0 | 5 | fewer than 10 cases |
| target trap | seventh_character | 5 | 0 | 0 | 0 | 11 | 10 | 0 | 0.0000 | 0.0000 | 0 | 0 | 6 | 0 | 4 | fewer than 10 cases |
| specialty | ed | 5 | 0 | 0 | 1 | 9 | 10 | 0 | 0.0909 | 0.1000 | 0 | 0 | 7 | 0 | 5 | fewer than 10 cases |
| specialty | ent | 5 | 0 | 0 | 0 | 7 | 89 | 0 | 0.0000 | 0.0000 | 0 | 0 | 87 | 0 | 4 | fewer than 10 cases |
| specialty | gi | 5 | 0 | 0 | 0 | 8 | 9 | 0 | 0.0000 | 0.0000 | 0 | 0 | 5 | 0 | 4 | fewer than 10 cases |
| specialty | ophtho | 5 | 0 | 0 | 0 | 10 | 11 | 0 | 0.0000 | 0.0000 | 0 | 0 | 10 | 0 | 5 | fewer than 10 cases |
| specialty | ortho | 5 | 0 | 0 | 0 | 8 | 8 | 0 | 0.0000 | 0.0000 | 1 | 0 | 7 | 0 | 4 | fewer than 10 cases |

### p612-b-checker-opus-5-5 (claude-opus-5-5, with_checker)

Gold sha256: 3ba94808da8b7970192a1c4f391aa106855125fb7e2abcede50716039abed633 (equals the gold files as they are: yes). Cases: 25. Second turns: 2. Error findings: first answers 1, final answers 0. Required codes found: first 42 of 43, final 42 of 43.

First answer:

| Group | Value | n | Exact | First-listed | Correct | Missing | Extra | Optional given | Precision | Recall | Invalid | No answer | Error findings | Review findings | Cases with an error finding | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| overall |  | 25 | 23 | 25 | 42 | 1 | 3 | 3 | 0.9333 | 0.9767 | 0 | 0 | 1 | 2 | 1 |  |
| target trap | combination | 5 | 5 | 5 | 8 | 0 | 0 | 0 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | fewer than 10 cases |
| target trap | excludes1 | 5 | 4 | 5 | 6 | 0 | 2 | 0 | 0.7500 | 1.0000 | 0 | 0 | 0 | 2 | 0 | fewer than 10 cases |
| target trap | laterality | 5 | 5 | 5 | 7 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | fewer than 10 cases |
| target trap | sequencing | 5 | 4 | 5 | 10 | 1 | 1 | 0 | 0.9091 | 0.9091 | 0 | 0 | 1 | 0 | 1 | fewer than 10 cases |
| target trap | seventh_character | 5 | 5 | 5 | 11 | 0 | 0 | 2 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | fewer than 10 cases |
| specialty | ed | 5 | 5 | 5 | 10 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | fewer than 10 cases |
| specialty | ent | 5 | 5 | 5 | 7 | 0 | 0 | 0 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | fewer than 10 cases |
| specialty | gi | 5 | 4 | 5 | 8 | 0 | 2 | 0 | 0.8000 | 1.0000 | 0 | 0 | 0 | 2 | 0 | fewer than 10 cases |
| specialty | ophtho | 5 | 4 | 5 | 9 | 1 | 1 | 2 | 0.9000 | 0.9000 | 0 | 0 | 1 | 0 | 1 | fewer than 10 cases |
| specialty | ortho | 5 | 5 | 5 | 8 | 0 | 0 | 0 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | fewer than 10 cases |

Final answer:

| Group | Value | n | Exact | First-listed | Correct | Missing | Extra | Optional given | Precision | Recall | Invalid | No answer | Error findings | Review findings | Cases with an error finding | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| overall |  | 25 | 23 | 25 | 42 | 1 | 3 | 3 | 0.9333 | 0.9767 | 0 | 0 | 0 | 2 | 0 |  |
| target trap | combination | 5 | 5 | 5 | 8 | 0 | 0 | 0 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | fewer than 10 cases |
| target trap | excludes1 | 5 | 4 | 5 | 6 | 0 | 2 | 0 | 0.7500 | 1.0000 | 0 | 0 | 0 | 2 | 0 | fewer than 10 cases |
| target trap | laterality | 5 | 5 | 5 | 7 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | fewer than 10 cases |
| target trap | sequencing | 5 | 4 | 5 | 10 | 1 | 1 | 0 | 0.9091 | 0.9091 | 0 | 0 | 0 | 0 | 0 | fewer than 10 cases |
| target trap | seventh_character | 5 | 5 | 5 | 11 | 0 | 0 | 2 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | fewer than 10 cases |
| specialty | ed | 5 | 5 | 5 | 10 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | fewer than 10 cases |
| specialty | ent | 5 | 5 | 5 | 7 | 0 | 0 | 0 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | fewer than 10 cases |
| specialty | gi | 5 | 4 | 5 | 8 | 0 | 2 | 0 | 0.8000 | 1.0000 | 0 | 0 | 0 | 2 | 0 | fewer than 10 cases |
| specialty | ophtho | 5 | 4 | 5 | 9 | 1 | 1 | 2 | 0.9000 | 0.9000 | 0 | 0 | 0 | 0 | 0 | fewer than 10 cases |
| specialty | ortho | 5 | 5 | 5 | 8 | 0 | 0 | 0 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | fewer than 10 cases |

### p613-b-checker-qwen3-4b (qwen3:4b, with_checker)

Gold sha256: 3ba94808da8b7970192a1c4f391aa106855125fb7e2abcede50716039abed633 (equals the gold files as they are: yes). Cases: 25. Second turns: 22. Error findings: first answers 116, final answers 26. Required codes found: first 1 of 43, final 1 of 43.

First answer:

| Group | Value | n | Exact | First-listed | Correct | Missing | Extra | Optional given | Precision | Recall | Invalid | No answer | Error findings | Review findings | Cases with an error finding | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| overall |  | 25 | 0 | 0 | 1 | 42 | 127 | 0 | 0.0078 | 0.0233 | 1 | 0 | 116 | 0 | 22 |  |
| target trap | combination | 5 | 0 | 0 | 0 | 8 | 11 | 0 | 0.0000 | 0.0000 | 0 | 0 | 10 | 0 | 5 | fewer than 10 cases |
| target trap | excludes1 | 5 | 0 | 0 | 0 | 6 | 10 | 0 | 0.0000 | 0.0000 | 0 | 0 | 7 | 0 | 4 | fewer than 10 cases |
| target trap | laterality | 5 | 0 | 0 | 1 | 6 | 6 | 0 | 0.1429 | 0.1429 | 1 | 0 | 6 | 0 | 4 | fewer than 10 cases |
| target trap | sequencing | 5 | 0 | 0 | 0 | 11 | 90 | 0 | 0.0000 | 0.0000 | 0 | 0 | 87 | 0 | 5 | fewer than 10 cases |
| target trap | seventh_character | 5 | 0 | 0 | 0 | 11 | 10 | 0 | 0.0000 | 0.0000 | 0 | 0 | 6 | 0 | 4 | fewer than 10 cases |
| specialty | ed | 5 | 0 | 0 | 1 | 9 | 10 | 0 | 0.0909 | 0.1000 | 0 | 0 | 7 | 0 | 5 | fewer than 10 cases |
| specialty | ent | 5 | 0 | 0 | 0 | 7 | 89 | 0 | 0.0000 | 0.0000 | 0 | 0 | 87 | 0 | 4 | fewer than 10 cases |
| specialty | gi | 5 | 0 | 0 | 0 | 8 | 9 | 0 | 0.0000 | 0.0000 | 0 | 0 | 5 | 0 | 4 | fewer than 10 cases |
| specialty | ophtho | 5 | 0 | 0 | 0 | 10 | 11 | 0 | 0.0000 | 0.0000 | 0 | 0 | 10 | 0 | 5 | fewer than 10 cases |
| specialty | ortho | 5 | 0 | 0 | 0 | 8 | 8 | 0 | 0.0000 | 0.0000 | 1 | 0 | 7 | 0 | 4 | fewer than 10 cases |

Final answer:

| Group | Value | n | Exact | First-listed | Correct | Missing | Extra | Optional given | Precision | Recall | Invalid | No answer | Error findings | Review findings | Cases with an error finding | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| overall |  | 25 | 0 | 0 | 1 | 42 | 46 | 0 | 0.0213 | 0.0233 | 2 | 0 | 26 | 0 | 17 |  |
| target trap | combination | 5 | 0 | 0 | 0 | 8 | 11 | 0 | 0.0000 | 0.0000 | 0 | 0 | 9 | 0 | 5 | fewer than 10 cases |
| target trap | excludes1 | 5 | 0 | 0 | 0 | 6 | 10 | 0 | 0.0000 | 0.0000 | 0 | 0 | 6 | 0 | 4 | fewer than 10 cases |
| target trap | laterality | 5 | 0 | 0 | 1 | 6 | 6 | 0 | 0.1429 | 0.1429 | 1 | 0 | 5 | 0 | 4 | fewer than 10 cases |
| target trap | sequencing | 5 | 0 | 0 | 0 | 11 | 9 | 0 | 0.0000 | 0.0000 | 1 | 0 | 3 | 0 | 2 | fewer than 10 cases |
| target trap | seventh_character | 5 | 0 | 0 | 0 | 11 | 10 | 0 | 0.0000 | 0.0000 | 0 | 0 | 3 | 0 | 2 | fewer than 10 cases |
| specialty | ed | 5 | 0 | 0 | 1 | 9 | 10 | 0 | 0.0909 | 0.1000 | 0 | 0 | 6 | 0 | 4 | fewer than 10 cases |
| specialty | ent | 5 | 0 | 0 | 0 | 7 | 8 | 0 | 0.0000 | 0.0000 | 1 | 0 | 4 | 0 | 3 | fewer than 10 cases |
| specialty | gi | 5 | 0 | 0 | 0 | 8 | 9 | 0 | 0.0000 | 0.0000 | 0 | 0 | 5 | 0 | 4 | fewer than 10 cases |
| specialty | ophtho | 5 | 0 | 0 | 0 | 10 | 11 | 0 | 0.0000 | 0.0000 | 0 | 0 | 6 | 0 | 3 | fewer than 10 cases |
| specialty | ortho | 5 | 0 | 0 | 0 | 8 | 8 | 0 | 0.0000 | 0.0000 | 1 | 0 | 5 | 0 | 3 | fewer than 10 cases |

## S6. Part B per case

An answer with more than 8 codes is shown as its first 5 codes and the count.

### p612-b-plain-opus-5-5

| Case | Trap | Gold | Optional | First | Final | Exact first / final | Optional given first / final |
|---|---|---|---|---|---|---|---|
| b-ed-001 | seventh_character | S52.501A W11.XXXA Y92.014 Y93.H9 | Y99.8 | S52.501A W11.XXXA Y92.014 Y93.H9 Y99.8 | S52.501A W11.XXXA Y92.014 Y93.H9 Y99.8 | yes / yes | 1 / 1 |
| b-ed-002 | sequencing | A41.9 N39.0 | R41.0 | A41.9 N39.0 | A41.9 N39.0 | yes / yes | 0 / 0 |
| b-ed-003 | laterality | L03.115 I10 | Z79.899 | L03.115 I10 | L03.115 I10 | yes / yes | 0 / 0 |
| b-ed-004 | excludes1 | N13.2 | - | N13.2 | N13.2 | yes / yes | 0 / 0 |
| b-ed-005 | combination | K80.00 | - | K80.00 | K80.00 | yes / yes | 0 / 0 |
| b-ent-001 | sequencing | A40.0 J36 | B95.0 | A40.0 J36 | A40.0 J36 | yes / yes | 0 / 0 |
| b-ent-002 | excludes1 | H66.011 | - | H66.011 | H66.011 | yes / yes | 0 / 0 |
| b-ent-003 | combination | J35.3 | - | J35.3 | J35.3 | yes / yes | 0 / 0 |
| b-ent-004 | seventh_character | S01.411D V18.4XXD | - | S01.411D V18.49XD | S01.411D V18.49XD | no / no | 0 / 0 |
| b-ent-005 | laterality | H90.42 | - | H90.42 | H90.42 | yes / yes | 0 / 0 |
| b-gi-001 | excludes1 | K25.4 | - | K25.4 K29.01 B96.81 | K25.4 K29.01 B96.81 | no / no | 0 / 0 |
| b-gi-002 | combination | K21.00 | R13.10 | K21.00 | K21.00 | yes / yes | 0 / 0 |
| b-gi-003 | sequencing | E11.43 K31.84 Z79.4 | - | E11.43 K31.84 Z79.4 | E11.43 K31.84 Z79.4 | yes / yes | 0 / 0 |
| b-gi-004 | laterality | K40.90 | - | K40.90 | K40.90 | yes / yes | 0 / 0 |
| b-gi-005 | seventh_character | K25.3 T39.315A | - | K25.3 T39.315A | K25.3 T39.315A | yes / yes | 0 / 0 |
| b-ophtho-001 | combination | E11.3511 E11.3292 Z79.4 Z79.84 | - | E11.3511 E11.3292 Z79.4 Z79.84 | E11.3511 E11.3292 Z79.4 Z79.84 | yes / yes | 0 / 0 |
| b-ophtho-002 | laterality | H25.11 Z96.1 | Z98.42 | H25.11 Z98.42 Z96.1 | H25.11 Z98.42 Z96.1 | yes / yes | 1 / 1 |
| b-ophtho-003 | seventh_character | H40.1112 | Z83.511 | H40.1112 Z83.511 | H40.1112 Z83.511 | yes / yes | 1 / 1 |
| b-ophtho-004 | sequencing | L71.9 H10.823 | - | L71.9 H13 | L71.9 H13 | no / no | 0 / 0 |
| b-ophtho-005 | excludes1 | H10.811 | - | H10.811 | H10.811 | yes / yes | 0 / 0 |
| b-ortho-001 | laterality | M17.11 | - | M17.11 | M17.11 | yes / yes | 0 / 0 |
| b-ortho-002 | seventh_character | S82.61XD W18.30XD | - | S82.611D W18.30XD | S82.611D W18.30XD | no / no | 0 / 0 |
| b-ortho-003 | excludes1 | M80.051A I10 | Z79.899 W18.30XA Y92.009 Y93.01 Y99.8 | M80.051A I10 | M80.051A I10 | yes / yes | 0 / 0 |
| b-ortho-004 | combination | M51.16 | - | M51.16 | M51.16 | yes / yes | 0 / 0 |
| b-ortho-005 | sequencing | D66 M36.2 | - | D66 M36.2 | D66 M36.2 | yes / yes | 0 / 0 |

### p613-b-plain-qwen3-4b

| Case | Trap | Gold | Optional | First | Final | Exact first / final | Optional given first / final |
|---|---|---|---|---|---|---|---|
| b-ed-001 | seventh_character | S52.501A W11.XXXA Y92.014 Y93.H9 | Y99.8 | S82.812A Y92.11 | S82.812A Y92.11 | no / no | 0 / 0 |
| b-ed-002 | sequencing | A41.9 N39.0 | R41.0 | B96.89 N39.2 R65.8 | B96.89 N39.2 R65.8 | no / no | 0 / 0 |
| b-ed-003 | laterality | L03.115 I10 | Z79.899 | B95.81 I10 | B95.81 I10 | no / no | 0 / 0 |
| b-ed-004 | excludes1 | N13.2 | - | N31.1 N25.2 | N31.1 N25.2 | no / no | 0 / 0 |
| b-ed-005 | combination | K80.00 | - | K86.10 K81.91 | K86.10 K81.91 | no / no | 0 / 0 |
| b-ent-001 | sequencing | A40.0 J36 | B95.0 | R21.11 R21.12 R21.13 R21.14 R21.15 ... (81 codes) | R21.11 R21.12 R21.13 R21.14 R21.15 ... (81 codes) | no / no | 0 / 0 |
| b-ent-002 | excludes1 | H66.011 | - | H66.91 H66.11 | H66.91 H66.11 | no / no | 0 / 0 |
| b-ent-003 | combination | J35.3 | - | R05 J36.9 | R05 J36.9 | no / no | 0 / 0 |
| b-ent-004 | seventh_character | S01.411D V18.4XXD | - | Z85.811 W14.811XA | Z85.811 W14.811XA | no / no | 0 / 0 |
| b-ent-005 | laterality | H90.42 | - | H91.41 Z85.7 | H91.41 Z85.7 | no / no | 0 / 0 |
| b-gi-001 | excludes1 | K25.4 | - | K25.11 K25.21 | K25.11 K25.21 | no / no | 0 / 0 |
| b-gi-002 | combination | K21.00 | R13.10 | K21.9 K52.11 | K21.9 K52.11 | no / no | 0 / 0 |
| b-gi-003 | sequencing | E11.43 K31.84 Z79.4 | - | K56.40 E11.9 | K56.40 E11.9 | no / no | 0 / 0 |
| b-gi-004 | laterality | K40.90 | - | K40.9, Y42.119 | K40.9, Y42.119 | no / no | 0 / 0 |
| b-gi-005 | seventh_character | K25.3 T39.315A | - | K29.81 T36.3X1A | K29.81 T36.3X1A | no / no | 0 / 0 |
| b-ophtho-001 | combination | E11.3511 E11.3292 Z79.4 Z79.84 | - | H40.11 H40.12 H40.119 | H40.11 H40.12 H40.119 | no / no | 0 / 0 |
| b-ophtho-002 | laterality | H25.11 Z96.1 | Z98.42 | H36.422 H36.421 | H36.422 H36.421 | no / no | 0 / 0 |
| b-ophtho-003 | seventh_character | H40.1112 | Z83.511 | H40.121 Z82.0 | H40.121 Z82.0 | no / no | 0 / 0 |
| b-ophtho-004 | sequencing | L71.9 H10.823 | - | H02.11 H02.12 | H02.11 H02.12 | no / no | 0 / 0 |
| b-ophtho-005 | excludes1 | H10.811 | - | H11.11 H11.1 | H11.11 H11.1 | no / no | 0 / 0 |
| b-ortho-001 | laterality | M17.11 | - | invalid | invalid | no / no | 0 / 0 |
| b-ortho-002 | seventh_character | S82.61XD W18.30XD | - | M22.51 Y92.31 | M22.51 Y92.31 | no / no | 0 / 0 |
| b-ortho-003 | excludes1 | M80.051A I10 | Z79.899 W18.30XA Y92.009 Y93.01 Y99.8 | S72.219A M81.81 | S72.219A M81.81 | no / no | 0 / 0 |
| b-ortho-004 | combination | M51.16 | - | M51.82 G70.13 | M51.82 G70.13 | no / no | 0 / 0 |
| b-ortho-005 | sequencing | D66 M36.2 | - | H61.11 D60.1 | H61.11 D60.1 | no / no | 0 / 0 |

### p612-b-checker-opus-5-5

| Case | Trap | Gold | Optional | First | Final | Exact first / final | Optional given first / final |
|---|---|---|---|---|---|---|---|
| b-ed-001 | seventh_character | S52.501A W11.XXXA Y92.014 Y93.H9 | Y99.8 | S52.501A W11.XXXA Y92.014 Y93.H9 Y99.8 | S52.501A W11.XXXA Y92.014 Y93.H9 Y99.8 | yes / yes | 1 / 1 |
| b-ed-002 | sequencing | A41.9 N39.0 | R41.0 | A41.9 N39.0 | A41.9 N39.0 | yes / yes | 0 / 0 |
| b-ed-003 | laterality | L03.115 I10 | Z79.899 | L03.115 I10 | L03.115 I10 | yes / yes | 0 / 0 |
| b-ed-004 | excludes1 | N13.2 | - | N13.2 | N13.2 | yes / yes | 0 / 0 |
| b-ed-005 | combination | K80.00 | - | K80.00 | K80.00 | yes / yes | 0 / 0 |
| b-ent-001 | sequencing | A40.0 J36 | B95.0 | A40.0 J36 | A40.0 J36 | yes / yes | 0 / 0 |
| b-ent-002 | excludes1 | H66.011 | - | H66.011 | H66.011 | yes / yes | 0 / 0 |
| b-ent-003 | combination | J35.3 | - | J35.3 | J35.3 | yes / yes | 0 / 0 |
| b-ent-004 | seventh_character | S01.411D V18.4XXD | - | S01.411D V18.4XXD | S01.411D V18.4XXD | yes / yes | 0 / 0 |
| b-ent-005 | laterality | H90.42 | - | H90.42 | H90.42 | yes / yes | 0 / 0 |
| b-gi-001 | excludes1 | K25.4 | - | K25.4 K29.01 B96.81 | K25.4 K29.01 B96.81 | no / no | 0 / 0 |
| b-gi-002 | combination | K21.00 | R13.10 | K21.00 | K21.00 | yes / yes | 0 / 0 |
| b-gi-003 | sequencing | E11.43 K31.84 Z79.4 | - | E11.43 K31.84 Z79.4 | E11.43 K31.84 Z79.4 | yes / yes | 0 / 0 |
| b-gi-004 | laterality | K40.90 | - | K40.90 | K40.90 | yes / yes | 0 / 0 |
| b-gi-005 | seventh_character | K25.3 T39.315A | - | K25.3 T39.315A | K25.3 T39.315A | yes / yes | 0 / 0 |
| b-ophtho-001 | combination | E11.3511 E11.3292 Z79.4 Z79.84 | - | E11.3511 E11.3292 Z79.4 Z79.84 | E11.3511 E11.3292 Z79.4 Z79.84 | yes / yes | 0 / 0 |
| b-ophtho-002 | laterality | H25.11 Z96.1 | Z98.42 | H25.11 Z96.1 Z98.42 | H25.11 Z96.1 Z98.42 | yes / yes | 1 / 1 |
| b-ophtho-003 | seventh_character | H40.1112 | Z83.511 | H40.1112 Z83.511 | H40.1112 Z83.511 | yes / yes | 1 / 1 |
| b-ophtho-004 | sequencing | L71.9 H10.823 | - | L71.9 H13 | L71.9 H10.403 | no / no | 0 / 0 |
| b-ophtho-005 | excludes1 | H10.811 | - | H10.811 | H10.811 | yes / yes | 0 / 0 |
| b-ortho-001 | laterality | M17.11 | - | M17.11 | M17.11 | yes / yes | 0 / 0 |
| b-ortho-002 | seventh_character | S82.61XD W18.30XD | - | S82.61XD W18.30XD | S82.61XD W18.30XD | yes / yes | 0 / 0 |
| b-ortho-003 | excludes1 | M80.051A I10 | Z79.899 W18.30XA Y92.009 Y93.01 Y99.8 | M80.051A I10 | M80.051A I10 | yes / yes | 0 / 0 |
| b-ortho-004 | combination | M51.16 | - | M51.16 | M51.16 | yes / yes | 0 / 0 |
| b-ortho-005 | sequencing | D66 M36.2 | - | D66 M36.2 | D66 M36.2 | yes / yes | 0 / 0 |

### p613-b-checker-qwen3-4b

| Case | Trap | Gold | Optional | First | Final | Exact first / final | Optional given first / final |
|---|---|---|---|---|---|---|---|
| b-ed-001 | seventh_character | S52.501A W11.XXXA Y92.014 Y93.H9 | Y99.8 | S82.812A Y92.11 | S82.812A Y92.111 | no / no | 0 / 0 |
| b-ed-002 | sequencing | A41.9 N39.0 | R41.0 | B96.89 N39.2 R65.8 | B96.89 N39.2 R65.8 | no / no | 0 / 0 |
| b-ed-003 | laterality | L03.115 I10 | Z79.899 | B95.81 I10 | B95.81 I10 | no / no | 0 / 0 |
| b-ed-004 | excludes1 | N13.2 | - | N31.1 N25.2 | N31.1 N25.2 | no / no | 0 / 0 |
| b-ed-005 | combination | K80.00 | - | K86.10 K81.91 | K86.10 K81.91 | no / no | 0 / 0 |
| b-ent-001 | sequencing | A40.0 J36 | B95.0 | R21.11 R21.12 R21.13 R21.14 R21.15 ... (81 codes) | invalid | no / no | 0 / 0 |
| b-ent-002 | excludes1 | H66.011 | - | H66.91 H66.11 | H66.91 H66.11 | no / no | 0 / 0 |
| b-ent-003 | combination | J35.3 | - | R05 J36.9 | R05.1 J36.9 | no / no | 0 / 0 |
| b-ent-004 | seventh_character | S01.411D V18.4XXD | - | Z85.811 W14.811XA | Z85.811 W14.811XA | no / no | 0 / 0 |
| b-ent-005 | laterality | H90.42 | - | H91.41 Z85.7 | H91.41 Z85.71 | no / no | 0 / 0 |
| b-gi-001 | excludes1 | K25.4 | - | K25.11 K25.21 | K25.11 K25.21 | no / no | 0 / 0 |
| b-gi-002 | combination | K21.00 | R13.10 | K21.9 K52.11 | K21.9 K52.11 | no / no | 0 / 0 |
| b-gi-003 | sequencing | E11.43 K31.84 Z79.4 | - | K56.40 E11.9 | K56.40 E11.9 | no / no | 0 / 0 |
| b-gi-004 | laterality | K40.90 | - | K40.9, Y42.119 | K40.9, Y42.119 | no / no | 0 / 0 |
| b-gi-005 | seventh_character | K25.3 T39.315A | - | K29.81 T36.3X1A | K29.81 T36.3X1A | no / no | 0 / 0 |
| b-ophtho-001 | combination | E11.3511 E11.3292 Z79.4 Z79.84 | - | H40.11 H40.12 H40.119 | H40.111 H40.121 H40.119 | no / no | 0 / 0 |
| b-ophtho-002 | laterality | H25.11 Z96.1 | Z98.42 | H36.422 H36.421 | H36.422 H36.421 | no / no | 0 / 0 |
| b-ophtho-003 | seventh_character | H40.1112 | Z83.511 | H40.121 Z82.0 | H40.1212 Z82.0 | no / no | 0 / 0 |
| b-ophtho-004 | sequencing | L71.9 H10.823 | - | H02.11 H02.12 | H02.111 H02.121 | no / no | 0 / 0 |
| b-ophtho-005 | excludes1 | H10.811 | - | H11.11 H11.1 | H11.111 H11.11 | no / no | 0 / 0 |
| b-ortho-001 | laterality | M17.11 | - | invalid | invalid | no / no | 0 / 0 |
| b-ortho-002 | seventh_character | S82.61XD W18.30XD | - | M22.51 Y92.31 | M22.51 Y92.310 | no / no | 0 / 0 |
| b-ortho-003 | excludes1 | M80.051A I10 | Z79.899 W18.30XA Y92.009 Y93.01 Y99.8 | S72.219A M81.81 | S72.219A M81.81 | no / no | 0 / 0 |
| b-ortho-004 | combination | M51.16 | - | M51.82 G70.13 | M51.82 G70.13 | no / no | 0 / 0 |
| b-ortho-005 | sequencing | D66 M36.2 | - | H61.11 D60.1 | H61.111 D60.1 | no / no | 0 / 0 |

## S7. Part B derived

### claude-opus-5-5

Cases whose first answer differs between the plain and the with-checker run: b-ent-004, b-ophtho-002 (order only), b-ortho-002.

p612-b-plain-opus-5-5: cases whose final answer differs from the first: none.

p612-b-checker-opus-5-5: cases whose final answer differs from the first: b-ophtho-004.

p612-b-plain-opus-5-5: cases with a runner error: none.

p612-b-checker-opus-5-5: cases with a runner error: none.

p612-b-checker-opus-5-5, leaving out: nothing.

| Cases | n | Error findings first | Error findings final | Changed answers |
|---|---|---|---|---|
| all cases | 25 | 1 | 0 | 1 |
| without a runner error | 25 | 1 | 0 | 1 |

### qwen3:4b

Cases whose first answer differs between the plain and the with-checker run: none.

p613-b-plain-qwen3-4b: cases whose final answer differs from the first: none.

p613-b-checker-qwen3-4b: cases whose final answer differs from the first: b-ed-001, b-ent-001, b-ent-003, b-ent-005, b-ophtho-001, b-ophtho-003, b-ophtho-004, b-ophtho-005, b-ortho-002, b-ortho-005.

p613-b-plain-qwen3-4b: cases with a runner error: none.

p613-b-checker-qwen3-4b: cases with a runner error: b-ent-001 (TimeoutError).

p613-b-checker-qwen3-4b, leaving out: b-ent-001.

| Cases | n | Error findings first | Error findings final | Changed answers |
|---|---|---|---|---|
| all cases | 25 | 116 | 26 | 10 |
| without a runner error | 24 | 35 | 26 | 9 |

## S8. Usage and cost

Runs with a usage.json; cost at the prices recorded in run.json, recomputed from raw.jsonl by medcode_eval.run.usage.

| Run | Model | Replies | Cost (USD) | Price in / out (USD per million tokens) | Equals the stored usage.json |
|---|---|---|---|---|---|
| p65-a-changes-opus-5-5 | claude-opus-5-5 | 462 | 4.8602 | 4.0 / 20.0 | yes |
| p615-a-d2c-checker-opus-5-5 | claude-opus-5-5 | 60 | 0.7349 | 4.0 / 20.0 | yes |
| p612-b-plain-opus-5-5 | claude-opus-5-5 | 25 | 0.2894 | 4.0 / 20.0 | yes |
| p612-b-checker-opus-5-5 | claude-opus-5-5 | 27 | 0.3148 | 4.0 / 20.0 | yes |
| total |  | 574 | 6.1993 |  |  |

## S9. Part C reported runs

The reported Part C runs, then the repeat run, which is not a reported score.

| Run | What | Model | Backend | Effort | Temperature | Seed | Prompt suffix | Started | Cases answered |
|---|---|---|---|---|---|---|---|---|---|
| p101-c-plain-opus-5-5 | Part C plain | claude-opus-5-5 | remote | medium | - | - | - | 2026-11-23 | 30 |
| p101-c-plain-qwen3-4b | Part C plain | qwen3:4b | ollama | - | 0 | 20261001 | `/no_think` | 2026-11-23 | 30 |
| p101-c-reminded-opus-5-5 | Part C reminded | claude-opus-5-5 | remote | medium | - | - | - | 2026-11-23 | 30 |
| p101-c-reminded-qwen3-4b | Part C reminded | qwen3:4b | ollama | - | 0 | 20261001 | `/no_think` | 2026-11-23 | 30 |
| p101-c-checker-opus-5-5 | Part C with checker | claude-opus-5-5 | remote | medium | - | - | - | 2026-11-23 | 30 |
| p101-c-checker-qwen3-4b | Part C with checker | qwen3:4b | ollama | - | 0 | 20261001 | `/no_think` | 2026-11-23 | 30 |
| p101-c-reminded2-opus-5-5 | Part C reminded, repeat (run-to-run variation only; not a reported score) | claude-opus-5-5 | remote | medium | - | - | - | 2026-11-23 | 30 |

## S10. Part C

A gap case leaves out what a more specific code would need, and an answer code counts as unsupported when it equals an entry of the case's unsupported_codes or starts with one (the case's optional codes are not counted). Counter-cases are scored by exact match only. Reported runs only; the repeat run is not in this section.

| Run | Model | Condition | Answer | Exact (of 30) | Exact gap cases (of 25) | Exact counter-cases (of 5) | Gap cases with an unsupported code (of 25) | Required codes found | Extra codes | Optional given | Invalid | Second turns |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| p101-c-plain-opus-5-5 | claude-opus-5-5 | plain | first | 29 | 24 | 5 | 1 | 38 of 39 | 1 | 4 | 0 | 0 |
| p101-c-plain-qwen3-4b | qwen3:4b | plain | first | 0 | 0 | 0 | 4 | 1 of 39 | 59 | 0 | 2 | 0 |
| p101-c-reminded-opus-5-5 | claude-opus-5-5 | reminded | first | 29 | 24 | 5 | 1 | 38 of 39 | 1 | 4 | 0 | 0 |
| p101-c-reminded-qwen3-4b | qwen3:4b | reminded | first | 0 | 0 | 0 | 5 | 1 of 39 | 60 | 0 | 1 | 0 |
| p101-c-checker-opus-5-5 | claude-opus-5-5 | with_checker | first | 29 | 24 | 5 | 1 | 38 of 39 | 1 | 4 | 0 | 0 |
| p101-c-checker-opus-5-5 | claude-opus-5-5 | with_checker | final | 29 | 24 | 5 | 1 | 38 of 39 | 1 | 4 | 0 | 0 |
| p101-c-checker-qwen3-4b | qwen3:4b | with_checker | first | 0 | 0 | 0 | 4 | 1 of 39 | 59 | 0 | 2 | 27 |
| p101-c-checker-qwen3-4b | qwen3:4b | with_checker | final | 0 | 0 | 0 | 4 | 2 of 39 | 55 | 0 | 2 | 27 |

Each specialty row holds 6 cases: 5 gap cases and 1 counter-case.

### p101-c-plain-opus-5-5 (claude-opus-5-5, plain)

Gold sha256: 76efde06e58d269baae2dcbdff5446c85aca0c64da57fca94ef74ffd72686258 (equals the gold files as they are: yes). Cases: 30. Gap cases: 25. Second turns: 0.

Gave an unsupported code in 1 of 25 gap cases (first answer), 1 of 25 (final answer).

First answer:

| Group | Value | n | Exact | First-listed | Correct | Missing | Extra | Optional given | Precision | Recall | Invalid | No answer | Error findings | Review findings | Cases with an error finding | Gap cases | Gap cases with an unsupported code | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| overall |  | 30 | 29 | 29 | 38 | 1 | 1 | 4 | 0.9744 | 0.9744 | 0 | 0 | 0 | 0 | 0 | 25 | 1 |  |
| case kind | gap cases | 25 | 24 | 24 | 32 | 1 | 1 | 3 | 0.9697 | 0.9697 | 0 | 0 | 0 | 0 | 0 | 25 | 1 |  |
| case kind | counter-cases | 5 | 5 | 5 | 6 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | fewer than 10 cases |
| gap type | not_current | 5 | 5 | 5 | 10 | 0 | 0 | 2 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| gap type | provider_statement | 5 | 5 | 5 | 5 | 0 | 0 | 0 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| gap type | uncertain_diagnosis | 5 | 5 | 5 | 5 | 0 | 0 | 0 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| gap type | unspecified_detail | 5 | 4 | 4 | 5 | 1 | 1 | 0 | 0.8333 | 0.8333 | 0 | 0 | 0 | 0 | 0 | 5 | 1 | fewer than 10 cases |
| gap type | unstated_link | 5 | 5 | 5 | 7 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| specialty | ed | 6 | 6 | 6 | 7 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| specialty | ent | 6 | 6 | 6 | 7 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| specialty | gi | 6 | 6 | 6 | 9 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| specialty | ophtho | 6 | 5 | 5 | 7 | 1 | 1 | 0 | 0.8750 | 0.8750 | 0 | 0 | 0 | 0 | 0 | 5 | 1 | fewer than 10 cases |
| specialty | ortho | 6 | 6 | 6 | 8 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |

### p101-c-plain-qwen3-4b (qwen3:4b, plain)

Gold sha256: 76efde06e58d269baae2dcbdff5446c85aca0c64da57fca94ef74ffd72686258 (equals the gold files as they are: yes). Cases: 30. Gap cases: 25. Second turns: 0.

Gave an unsupported code in 4 of 25 gap cases (first answer), 4 of 25 (final answer).

First answer:

| Group | Value | n | Exact | First-listed | Correct | Missing | Extra | Optional given | Precision | Recall | Invalid | No answer | Error findings | Review findings | Cases with an error finding | Gap cases | Gap cases with an unsupported code | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| overall |  | 30 | 0 | 0 | 1 | 38 | 59 | 0 | 0.0167 | 0.0256 | 2 | 0 | 43 | 0 | 27 | 25 | 4 |  |
| case kind | gap cases | 25 | 0 | 0 | 1 | 32 | 48 | 0 | 0.0204 | 0.0303 | 2 | 0 | 34 | 0 | 22 | 25 | 4 |  |
| case kind | counter-cases | 5 | 0 | 0 | 0 | 6 | 11 | 0 | 0.0000 | 0.0000 | 0 | 0 | 9 | 0 | 5 | 0 | 0 | fewer than 10 cases |
| gap type | not_current | 5 | 0 | 0 | 0 | 10 | 10 | 0 | 0.0000 | 0.0000 | 0 | 0 | 9 | 0 | 5 | 5 | 1 | fewer than 10 cases |
| gap type | provider_statement | 5 | 0 | 0 | 0 | 5 | 8 | 0 | 0.0000 | 0.0000 | 1 | 0 | 7 | 0 | 4 | 5 | 0 | fewer than 10 cases |
| gap type | uncertain_diagnosis | 5 | 0 | 0 | 0 | 5 | 10 | 0 | 0.0000 | 0.0000 | 0 | 0 | 6 | 0 | 5 | 5 | 3 | fewer than 10 cases |
| gap type | unspecified_detail | 5 | 0 | 0 | 0 | 6 | 12 | 0 | 0.0000 | 0.0000 | 0 | 0 | 7 | 0 | 5 | 5 | 0 | fewer than 10 cases |
| gap type | unstated_link | 5 | 0 | 0 | 1 | 6 | 8 | 0 | 0.1111 | 0.1429 | 1 | 0 | 5 | 0 | 3 | 5 | 0 | fewer than 10 cases |
| specialty | ed | 6 | 0 | 0 | 0 | 7 | 15 | 0 | 0.0000 | 0.0000 | 0 | 0 | 9 | 0 | 5 | 5 | 1 | fewer than 10 cases |
| specialty | ent | 6 | 0 | 0 | 0 | 7 | 10 | 0 | 0.0000 | 0.0000 | 1 | 0 | 7 | 0 | 5 | 5 | 1 | fewer than 10 cases |
| specialty | gi | 6 | 0 | 0 | 0 | 9 | 10 | 0 | 0.0000 | 0.0000 | 1 | 0 | 7 | 0 | 5 | 5 | 1 | fewer than 10 cases |
| specialty | ophtho | 6 | 0 | 0 | 1 | 7 | 12 | 0 | 0.0769 | 0.1250 | 0 | 0 | 10 | 0 | 6 | 5 | 0 | fewer than 10 cases |
| specialty | ortho | 6 | 0 | 0 | 0 | 8 | 12 | 0 | 0.0000 | 0.0000 | 0 | 0 | 10 | 0 | 6 | 5 | 1 | fewer than 10 cases |

### p101-c-reminded-opus-5-5 (claude-opus-5-5, reminded)

Gold sha256: 76efde06e58d269baae2dcbdff5446c85aca0c64da57fca94ef74ffd72686258 (equals the gold files as they are: yes). Cases: 30. Gap cases: 25. Second turns: 0.

Gave an unsupported code in 1 of 25 gap cases (first answer), 1 of 25 (final answer).

First answer:

| Group | Value | n | Exact | First-listed | Correct | Missing | Extra | Optional given | Precision | Recall | Invalid | No answer | Error findings | Review findings | Cases with an error finding | Gap cases | Gap cases with an unsupported code | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| overall |  | 30 | 29 | 29 | 38 | 1 | 1 | 4 | 0.9744 | 0.9744 | 0 | 0 | 0 | 0 | 0 | 25 | 1 |  |
| case kind | gap cases | 25 | 24 | 24 | 32 | 1 | 1 | 3 | 0.9697 | 0.9697 | 0 | 0 | 0 | 0 | 0 | 25 | 1 |  |
| case kind | counter-cases | 5 | 5 | 5 | 6 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | fewer than 10 cases |
| gap type | not_current | 5 | 5 | 5 | 10 | 0 | 0 | 2 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| gap type | provider_statement | 5 | 5 | 5 | 5 | 0 | 0 | 0 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| gap type | uncertain_diagnosis | 5 | 5 | 5 | 5 | 0 | 0 | 0 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| gap type | unspecified_detail | 5 | 4 | 4 | 5 | 1 | 1 | 0 | 0.8333 | 0.8333 | 0 | 0 | 0 | 0 | 0 | 5 | 1 | fewer than 10 cases |
| gap type | unstated_link | 5 | 5 | 5 | 7 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| specialty | ed | 6 | 6 | 6 | 7 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| specialty | ent | 6 | 6 | 6 | 7 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| specialty | gi | 6 | 6 | 6 | 9 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| specialty | ophtho | 6 | 5 | 5 | 7 | 1 | 1 | 0 | 0.8750 | 0.8750 | 0 | 0 | 0 | 0 | 0 | 5 | 1 | fewer than 10 cases |
| specialty | ortho | 6 | 6 | 6 | 8 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |

### p101-c-reminded-qwen3-4b (qwen3:4b, reminded)

Gold sha256: 76efde06e58d269baae2dcbdff5446c85aca0c64da57fca94ef74ffd72686258 (equals the gold files as they are: yes). Cases: 30. Gap cases: 25. Second turns: 0.

Gave an unsupported code in 5 of 25 gap cases (first answer), 5 of 25 (final answer).

First answer:

| Group | Value | n | Exact | First-listed | Correct | Missing | Extra | Optional given | Precision | Recall | Invalid | No answer | Error findings | Review findings | Cases with an error finding | Gap cases | Gap cases with an unsupported code | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| overall |  | 30 | 0 | 0 | 1 | 38 | 60 | 0 | 0.0164 | 0.0256 | 1 | 0 | 46 | 0 | 29 | 25 | 5 |  |
| case kind | gap cases | 25 | 0 | 0 | 1 | 32 | 50 | 0 | 0.0196 | 0.0303 | 1 | 0 | 38 | 0 | 24 | 25 | 5 |  |
| case kind | counter-cases | 5 | 0 | 0 | 0 | 6 | 10 | 0 | 0.0000 | 0.0000 | 0 | 0 | 8 | 0 | 5 | 0 | 0 | fewer than 10 cases |
| gap type | not_current | 5 | 0 | 0 | 0 | 10 | 10 | 0 | 0.0000 | 0.0000 | 0 | 0 | 8 | 0 | 5 | 5 | 1 | fewer than 10 cases |
| gap type | provider_statement | 5 | 0 | 0 | 0 | 5 | 10 | 0 | 0.0000 | 0.0000 | 0 | 0 | 9 | 0 | 5 | 5 | 1 | fewer than 10 cases |
| gap type | uncertain_diagnosis | 5 | 0 | 0 | 0 | 5 | 10 | 0 | 0.0000 | 0.0000 | 0 | 0 | 6 | 0 | 5 | 5 | 3 | fewer than 10 cases |
| gap type | unspecified_detail | 5 | 0 | 0 | 0 | 6 | 12 | 0 | 0.0000 | 0.0000 | 0 | 0 | 9 | 0 | 5 | 5 | 0 | fewer than 10 cases |
| gap type | unstated_link | 5 | 0 | 0 | 1 | 6 | 8 | 0 | 0.1111 | 0.1429 | 1 | 0 | 6 | 0 | 4 | 5 | 0 | fewer than 10 cases |
| specialty | ed | 6 | 0 | 0 | 0 | 7 | 14 | 0 | 0.0000 | 0.0000 | 0 | 0 | 10 | 0 | 6 | 5 | 1 | fewer than 10 cases |
| specialty | ent | 6 | 0 | 0 | 0 | 7 | 12 | 0 | 0.0000 | 0.0000 | 0 | 0 | 10 | 0 | 6 | 5 | 3 | fewer than 10 cases |
| specialty | gi | 6 | 0 | 0 | 0 | 9 | 10 | 0 | 0.0000 | 0.0000 | 1 | 0 | 6 | 0 | 5 | 5 | 1 | fewer than 10 cases |
| specialty | ophtho | 6 | 0 | 0 | 1 | 7 | 12 | 0 | 0.0769 | 0.1250 | 0 | 0 | 9 | 0 | 6 | 5 | 0 | fewer than 10 cases |
| specialty | ortho | 6 | 0 | 0 | 0 | 8 | 12 | 0 | 0.0000 | 0.0000 | 0 | 0 | 11 | 0 | 6 | 5 | 0 | fewer than 10 cases |

### p101-c-checker-opus-5-5 (claude-opus-5-5, with_checker)

Gold sha256: 76efde06e58d269baae2dcbdff5446c85aca0c64da57fca94ef74ffd72686258 (equals the gold files as they are: yes). Cases: 30. Gap cases: 25. Second turns: 0.

Gave an unsupported code in 1 of 25 gap cases (first answer), 1 of 25 (final answer).

First answer:

| Group | Value | n | Exact | First-listed | Correct | Missing | Extra | Optional given | Precision | Recall | Invalid | No answer | Error findings | Review findings | Cases with an error finding | Gap cases | Gap cases with an unsupported code | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| overall |  | 30 | 29 | 29 | 38 | 1 | 1 | 4 | 0.9744 | 0.9744 | 0 | 0 | 0 | 0 | 0 | 25 | 1 |  |
| case kind | gap cases | 25 | 24 | 24 | 32 | 1 | 1 | 3 | 0.9697 | 0.9697 | 0 | 0 | 0 | 0 | 0 | 25 | 1 |  |
| case kind | counter-cases | 5 | 5 | 5 | 6 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | fewer than 10 cases |
| gap type | not_current | 5 | 5 | 5 | 10 | 0 | 0 | 2 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| gap type | provider_statement | 5 | 5 | 5 | 5 | 0 | 0 | 0 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| gap type | uncertain_diagnosis | 5 | 5 | 5 | 5 | 0 | 0 | 0 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| gap type | unspecified_detail | 5 | 4 | 4 | 5 | 1 | 1 | 0 | 0.8333 | 0.8333 | 0 | 0 | 0 | 0 | 0 | 5 | 1 | fewer than 10 cases |
| gap type | unstated_link | 5 | 5 | 5 | 7 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| specialty | ed | 6 | 6 | 6 | 7 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| specialty | ent | 6 | 6 | 6 | 7 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| specialty | gi | 6 | 6 | 6 | 9 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| specialty | ophtho | 6 | 5 | 5 | 7 | 1 | 1 | 0 | 0.8750 | 0.8750 | 0 | 0 | 0 | 0 | 0 | 5 | 1 | fewer than 10 cases |
| specialty | ortho | 6 | 6 | 6 | 8 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |

Final answer:

| Group | Value | n | Exact | First-listed | Correct | Missing | Extra | Optional given | Precision | Recall | Invalid | No answer | Error findings | Review findings | Cases with an error finding | Gap cases | Gap cases with an unsupported code | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| overall |  | 30 | 29 | 29 | 38 | 1 | 1 | 4 | 0.9744 | 0.9744 | 0 | 0 | 0 | 0 | 0 | 25 | 1 |  |
| case kind | gap cases | 25 | 24 | 24 | 32 | 1 | 1 | 3 | 0.9697 | 0.9697 | 0 | 0 | 0 | 0 | 0 | 25 | 1 |  |
| case kind | counter-cases | 5 | 5 | 5 | 6 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | fewer than 10 cases |
| gap type | not_current | 5 | 5 | 5 | 10 | 0 | 0 | 2 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| gap type | provider_statement | 5 | 5 | 5 | 5 | 0 | 0 | 0 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| gap type | uncertain_diagnosis | 5 | 5 | 5 | 5 | 0 | 0 | 0 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| gap type | unspecified_detail | 5 | 4 | 4 | 5 | 1 | 1 | 0 | 0.8333 | 0.8333 | 0 | 0 | 0 | 0 | 0 | 5 | 1 | fewer than 10 cases |
| gap type | unstated_link | 5 | 5 | 5 | 7 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| specialty | ed | 6 | 6 | 6 | 7 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| specialty | ent | 6 | 6 | 6 | 7 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| specialty | gi | 6 | 6 | 6 | 9 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |
| specialty | ophtho | 6 | 5 | 5 | 7 | 1 | 1 | 0 | 0.8750 | 0.8750 | 0 | 0 | 0 | 0 | 0 | 5 | 1 | fewer than 10 cases |
| specialty | ortho | 6 | 6 | 6 | 8 | 0 | 0 | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | fewer than 10 cases |

### p101-c-checker-qwen3-4b (qwen3:4b, with_checker)

Gold sha256: 76efde06e58d269baae2dcbdff5446c85aca0c64da57fca94ef74ffd72686258 (equals the gold files as they are: yes). Cases: 30. Gap cases: 25. Second turns: 27.

Gave an unsupported code in 4 of 25 gap cases (first answer), 4 of 25 (final answer).

First answer:

| Group | Value | n | Exact | First-listed | Correct | Missing | Extra | Optional given | Precision | Recall | Invalid | No answer | Error findings | Review findings | Cases with an error finding | Gap cases | Gap cases with an unsupported code | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| overall |  | 30 | 0 | 0 | 1 | 38 | 59 | 0 | 0.0167 | 0.0256 | 2 | 0 | 43 | 0 | 27 | 25 | 4 |  |
| case kind | gap cases | 25 | 0 | 0 | 1 | 32 | 48 | 0 | 0.0204 | 0.0303 | 2 | 0 | 34 | 0 | 22 | 25 | 4 |  |
| case kind | counter-cases | 5 | 0 | 0 | 0 | 6 | 11 | 0 | 0.0000 | 0.0000 | 0 | 0 | 9 | 0 | 5 | 0 | 0 | fewer than 10 cases |
| gap type | not_current | 5 | 0 | 0 | 0 | 10 | 10 | 0 | 0.0000 | 0.0000 | 0 | 0 | 9 | 0 | 5 | 5 | 1 | fewer than 10 cases |
| gap type | provider_statement | 5 | 0 | 0 | 0 | 5 | 8 | 0 | 0.0000 | 0.0000 | 1 | 0 | 7 | 0 | 4 | 5 | 0 | fewer than 10 cases |
| gap type | uncertain_diagnosis | 5 | 0 | 0 | 0 | 5 | 10 | 0 | 0.0000 | 0.0000 | 0 | 0 | 6 | 0 | 5 | 5 | 3 | fewer than 10 cases |
| gap type | unspecified_detail | 5 | 0 | 0 | 0 | 6 | 12 | 0 | 0.0000 | 0.0000 | 0 | 0 | 7 | 0 | 5 | 5 | 0 | fewer than 10 cases |
| gap type | unstated_link | 5 | 0 | 0 | 1 | 6 | 8 | 0 | 0.1111 | 0.1429 | 1 | 0 | 5 | 0 | 3 | 5 | 0 | fewer than 10 cases |
| specialty | ed | 6 | 0 | 0 | 0 | 7 | 15 | 0 | 0.0000 | 0.0000 | 0 | 0 | 9 | 0 | 5 | 5 | 1 | fewer than 10 cases |
| specialty | ent | 6 | 0 | 0 | 0 | 7 | 10 | 0 | 0.0000 | 0.0000 | 1 | 0 | 7 | 0 | 5 | 5 | 1 | fewer than 10 cases |
| specialty | gi | 6 | 0 | 0 | 0 | 9 | 10 | 0 | 0.0000 | 0.0000 | 1 | 0 | 7 | 0 | 5 | 5 | 1 | fewer than 10 cases |
| specialty | ophtho | 6 | 0 | 0 | 1 | 7 | 12 | 0 | 0.0769 | 0.1250 | 0 | 0 | 10 | 0 | 6 | 5 | 0 | fewer than 10 cases |
| specialty | ortho | 6 | 0 | 0 | 0 | 8 | 12 | 0 | 0.0000 | 0.0000 | 0 | 0 | 10 | 0 | 6 | 5 | 1 | fewer than 10 cases |

Final answer:

| Group | Value | n | Exact | First-listed | Correct | Missing | Extra | Optional given | Precision | Recall | Invalid | No answer | Error findings | Review findings | Cases with an error finding | Gap cases | Gap cases with an unsupported code | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| overall |  | 30 | 0 | 1 | 2 | 37 | 55 | 0 | 0.0351 | 0.0513 | 2 | 0 | 24 | 0 | 19 | 25 | 4 |  |
| case kind | gap cases | 25 | 0 | 1 | 2 | 31 | 45 | 0 | 0.0426 | 0.0606 | 2 | 0 | 20 | 0 | 15 | 25 | 4 |  |
| case kind | counter-cases | 5 | 0 | 0 | 0 | 6 | 10 | 0 | 0.0000 | 0.0000 | 0 | 0 | 4 | 0 | 4 | 0 | 0 | fewer than 10 cases |
| gap type | not_current | 5 | 0 | 1 | 1 | 9 | 9 | 0 | 0.1000 | 0.1000 | 0 | 0 | 6 | 0 | 3 | 5 | 1 | fewer than 10 cases |
| gap type | provider_statement | 5 | 0 | 0 | 0 | 5 | 8 | 0 | 0.0000 | 0.0000 | 1 | 0 | 3 | 0 | 2 | 5 | 0 | fewer than 10 cases |
| gap type | uncertain_diagnosis | 5 | 0 | 0 | 0 | 5 | 9 | 0 | 0.0000 | 0.0000 | 0 | 0 | 3 | 0 | 3 | 5 | 3 | fewer than 10 cases |
| gap type | unspecified_detail | 5 | 0 | 0 | 0 | 6 | 11 | 0 | 0.0000 | 0.0000 | 0 | 0 | 5 | 0 | 4 | 5 | 0 | fewer than 10 cases |
| gap type | unstated_link | 5 | 0 | 0 | 1 | 6 | 8 | 0 | 0.1111 | 0.1429 | 1 | 0 | 3 | 0 | 3 | 5 | 0 | fewer than 10 cases |
| specialty | ed | 6 | 0 | 1 | 1 | 6 | 12 | 0 | 0.0769 | 0.1429 | 0 | 0 | 4 | 0 | 3 | 5 | 1 | fewer than 10 cases |
| specialty | ent | 6 | 0 | 0 | 0 | 7 | 10 | 0 | 0.0000 | 0.0000 | 1 | 0 | 6 | 0 | 5 | 5 | 1 | fewer than 10 cases |
| specialty | gi | 6 | 0 | 0 | 0 | 9 | 9 | 0 | 0.0000 | 0.0000 | 1 | 0 | 4 | 0 | 3 | 5 | 1 | fewer than 10 cases |
| specialty | ophtho | 6 | 0 | 0 | 1 | 7 | 12 | 0 | 0.0769 | 0.1250 | 0 | 0 | 4 | 0 | 3 | 5 | 0 | fewer than 10 cases |
| specialty | ortho | 6 | 0 | 0 | 0 | 8 | 12 | 0 | 0.0000 | 0.0000 | 0 | 0 | 6 | 0 | 5 | 5 | 1 | fewer than 10 cases |

## S11. Part C per case

Reported runs only. Answers are shown as in S6: a code that already holds a dot is shown as given, and an answer with more than 8 codes is shown as its first 5 codes and the count.

### p101-c-plain-opus-5-5 (claude-opus-5-5, plain)

| Case | Gap type | Gold | Optional | First | Final | Exact first / final | Unsupported given first / final |
|---|---|---|---|---|---|---|---|
| c-ed-001 | provider_statement | A08.4 | - | A08.4 | A08.4 | yes / yes | - / - |
| c-ed-002 | unstated_link | R33.9 | Z90.49 Z96.0 | R33.9 Z90.49 | R33.9 Z90.49 | yes / yes | - / - |
| c-ed-003 | not_current | J20.9 | Z87.09 | J20.9 | J20.9 | yes / yes | - / - |
| c-ed-004 | unspecified_detail | I50.9 | Z79.899 | I50.9 | I50.9 | yes / yes | - / - |
| c-ed-005 | uncertain_diagnosis | R30.0 | - | R30.0 | R30.0 | yes / yes | - / - |
| c-ed-006 | counter_case | I11.0 I50.33 | Z79.899 | I11.0 I50.33 | I11.0 I50.33 | yes / yes | - / - |
| c-ent-001 | unspecified_detail | J01.90 | - | J01.90 | J01.90 | yes / yes | - / - |
| c-ent-002 | uncertain_diagnosis | R42 | - | R42 | R42 | yes / yes | - / - |
| c-ent-003 | provider_statement | J03.90 | - | J03.90 | J03.90 | yes / yes | - / - |
| c-ent-004 | unstated_link | H90.3 | Z57.0 | H90.3 | H90.3 | yes / yes | - / - |
| c-ent-005 | not_current | Z09 Z86.69 | Z92.241 | Z09 Z86.69 | Z09 Z86.69 | yes / yes | - / - |
| c-ent-006 | counter_case | H81.01 | Z79.899 | H81.01 Z79.899 | H81.01 Z79.899 | yes / yes | - / - |
| c-gi-001 | unstated_link | K74.60 F10.20 | - | K74.60 F10.20 | K74.60 F10.20 | yes / yes | - / - |
| c-gi-002 | not_current | Z08 Z85.038 Z90.49 | Z92.21 | Z08 Z85.038 Z90.49 Z92.21 | Z08 Z85.038 Z90.49 Z92.21 | yes / yes | - / - |
| c-gi-003 | unspecified_detail | B19.20 | - | B19.20 | B19.20 | yes / yes | - / - |
| c-gi-004 | uncertain_diagnosis | R10.13 | - | R10.13 | R10.13 | yes / yes | - / - |
| c-gi-005 | provider_statement | K90.0 | Z71.3 | K90.0 | K90.0 | yes / yes | - / - |
| c-gi-006 | counter_case | K64.1 | - | K64.1 | K64.1 | yes / yes | - / - |
| c-ophtho-001 | not_current | Z09 Z86.69 | - | Z09 Z86.69 | Z09 Z86.69 | yes / yes | - / - |
| c-ophtho-002 | unspecified_detail | H40.1130 | Z79.899 | H40.1133 | H40.1133 | no / no | H40.1133 / H40.1133 |
| c-ophtho-003 | uncertain_diagnosis | H53.131 | H54.61 | H53.131 | H53.131 | yes / yes | - / - |
| c-ophtho-004 | provider_statement | H35.3134 | - | H35.3134 | H35.3134 | yes / yes | - / - |
| c-ophtho-005 | unstated_link | H35.00 I10 | Z79.899 | H35.00 I10 | H35.00 I10 | yes / yes | - / - |
| c-ophtho-006 | counter_case | H40.013 | - | H40.013 | H40.013 | yes / yes | - / - |
| c-ortho-001 | uncertain_diagnosis | M25.561 | - | M25.561 | M25.561 | yes / yes | - / - |
| c-ortho-002 | provider_statement | M16.12 | - | M16.12 | M16.12 | yes / yes | - / - |
| c-ortho-003 | unstated_link | M76.62 | - | M76.62 | M76.62 | yes / yes | - / - |
| c-ortho-004 | not_current | M81.0 Z87.310 | Z79.83 | M81.0 Z87.310 Z79.83 | M81.0 Z87.310 Z79.83 | yes / yes | - / - |
| c-ortho-005 | unspecified_detail | S82.251E W11.XXXD | Z96.7 | S82.251E W11.XXXD | S82.251E W11.XXXD | yes / yes | - / - |
| c-ortho-006 | counter_case | M65.341 | - | M65.341 | M65.341 | yes / yes | - / - |

### p101-c-plain-qwen3-4b (qwen3:4b, plain)

| Case | Gap type | Gold | Optional | First | Final | Exact first / final | Unsupported given first / final |
|---|---|---|---|---|---|---|---|
| c-ed-001 | provider_statement | A08.4 | - | B24.9 Y14.3 | B24.9 Y14.3 | no / no | - / - |
| c-ed-002 | unstated_link | R33.9 | Z90.49 Z96.0 | N39.0 Z85.71 | N39.0 Z85.71 | no / no | - / - |
| c-ed-003 | not_current | J20.9 | Z87.09 | J20 R05 | J20 R05 | no / no | - / - |
| c-ed-004 | unspecified_detail | I50.9 | Z79.899 | I11.9 I13.9 R05 I12.9 | I11.9 I13.9 R05 I12.9 | no / no | - / - |
| c-ed-005 | uncertain_diagnosis | R30.0 | - | N39.0 Z86.891 | N39.0 Z86.891 | no / no | N39.0 / N39.0 |
| c-ed-006 | counter_case | I11.0 I50.33 | Z79.899 | I10.9 I31.9 R05 | I10.9 I31.9 R05 | no / no | - / - |
| c-ent-001 | unspecified_detail | J01.90 | - | R01.1 R02.11 | R01.1 R02.11 | no / no | - / - |
| c-ent-002 | uncertain_diagnosis | R42 | - | H91.82 R45.82 | H91.82 R45.82 | no / no | - / - |
| c-ent-003 | provider_statement | J03.90 | - | invalid | invalid | no / no | - / - |
| c-ent-004 | unstated_link | H90.3 | Z57.0 | H91.90 R91.83 | H91.90 R91.83 | no / no | - / - |
| c-ent-005 | not_current | Z09 Z86.69 | Z92.241 | H91.89 R55.89 | H91.89 R55.89 | no / no | H91.89 / H91.89 |
| c-ent-006 | counter_case | H81.01 | Z79.899 | H91.82 Z87.0 | H91.82 Z87.0 | no / no | - / - |
| c-gi-001 | unstated_link | K74.60 F10.20 | - | invalid | invalid | no / no | - / - |
| c-gi-002 | not_current | Z08 Z85.038 Z90.49 | Z92.21 | C78.11 Z85.31 | C78.11 Z85.31 | no / no | - / - |
| c-gi-003 | unspecified_detail | B19.20 | - | B16.1 Z85.31 | B16.1 Z85.31 | no / no | - / - |
| c-gi-004 | uncertain_diagnosis | R10.13 | - | K25.9 Y54.3 | K25.9 Y54.3 | no / no | K25.9 / K25.9 |
| c-gi-005 | provider_statement | K90.0 | Z71.3 | E70.1 Z85.7 | E70.1 Z85.7 | no / no | - / - |
| c-gi-006 | counter_case | K64.1 | - | I87.11 R19.1 | I87.11 R19.1 | no / no | - / - |
| c-ophtho-001 | not_current | Z09 Z86.69 | - | H61.81 Z85.71 | H61.81 Z85.71 | no / no | - / - |
| c-ophtho-002 | unspecified_detail | H40.1130 | Z79.899 | H40.11 H40.12 | H40.11 H40.12 | no / no | - / - |
| c-ophtho-003 | uncertain_diagnosis | H53.131 | H54.61 | H40.11 I69.9 | H40.11 I69.9 | no / no | - / - |
| c-ophtho-004 | provider_statement | H35.3134 | - | H40.112 H40.113 | H40.112 H40.113 | no / no | - / - |
| c-ophtho-005 | unstated_link | H35.00 I10 | Z79.899 | H45.11 I10 Z87.0 | H45.11 I10 Z87.0 | no / no | - / - |
| c-ophtho-006 | counter_case | H40.013 | - | H40.129 Z82.3 | H40.129 Z82.3 | no / no | - / - |
| c-ortho-001 | uncertain_diagnosis | M25.561 | - | M23.21 Y93.31 | M23.21 Y93.31 | no / no | M23.21 / M23.21 |
| c-ortho-002 | provider_statement | M16.12 | - | M16.81 Z86.71 | M16.81 Z86.71 | no / no | - / - |
| c-ortho-003 | unstated_link | M76.62 | - | M715.21 Y54.11 | M715.21 Y54.11 | no / no | - / - |
| c-ortho-004 | not_current | M81.0 Z87.310 | Z79.83 | M81.811 M81.819 | M81.811 M81.819 | no / no | - / - |
| c-ortho-005 | unspecified_detail | S82.251E W11.XXXD | Z96.7 | M22.51 T82.111A | M22.51 T82.111A | no / no | - / - |
| c-ortho-006 | counter_case | M65.341 | - | M66.82 T82.899XA | M66.82 T82.899XA | no / no | - / - |

### p101-c-reminded-opus-5-5 (claude-opus-5-5, reminded)

| Case | Gap type | Gold | Optional | First | Final | Exact first / final | Unsupported given first / final |
|---|---|---|---|---|---|---|---|
| c-ed-001 | provider_statement | A08.4 | - | A08.4 | A08.4 | yes / yes | - / - |
| c-ed-002 | unstated_link | R33.9 | Z90.49 Z96.0 | R33.9 Z90.49 | R33.9 Z90.49 | yes / yes | - / - |
| c-ed-003 | not_current | J20.9 | Z87.09 | J20.9 | J20.9 | yes / yes | - / - |
| c-ed-004 | unspecified_detail | I50.9 | Z79.899 | I50.9 | I50.9 | yes / yes | - / - |
| c-ed-005 | uncertain_diagnosis | R30.0 | - | R30.0 | R30.0 | yes / yes | - / - |
| c-ed-006 | counter_case | I11.0 I50.33 | Z79.899 | I11.0 I50.33 | I11.0 I50.33 | yes / yes | - / - |
| c-ent-001 | unspecified_detail | J01.90 | - | J01.90 | J01.90 | yes / yes | - / - |
| c-ent-002 | uncertain_diagnosis | R42 | - | R42 | R42 | yes / yes | - / - |
| c-ent-003 | provider_statement | J03.90 | - | J03.90 | J03.90 | yes / yes | - / - |
| c-ent-004 | unstated_link | H90.3 | Z57.0 | H90.3 | H90.3 | yes / yes | - / - |
| c-ent-005 | not_current | Z09 Z86.69 | Z92.241 | Z09 Z86.69 | Z09 Z86.69 | yes / yes | - / - |
| c-ent-006 | counter_case | H81.01 | Z79.899 | H81.01 Z79.899 | H81.01 Z79.899 | yes / yes | - / - |
| c-gi-001 | unstated_link | K74.60 F10.20 | - | K74.60 F10.20 | K74.60 F10.20 | yes / yes | - / - |
| c-gi-002 | not_current | Z08 Z85.038 Z90.49 | Z92.21 | Z08 Z85.038 Z90.49 Z92.21 | Z08 Z85.038 Z90.49 Z92.21 | yes / yes | - / - |
| c-gi-003 | unspecified_detail | B19.20 | - | B19.20 | B19.20 | yes / yes | - / - |
| c-gi-004 | uncertain_diagnosis | R10.13 | - | R10.13 | R10.13 | yes / yes | - / - |
| c-gi-005 | provider_statement | K90.0 | Z71.3 | K90.0 | K90.0 | yes / yes | - / - |
| c-gi-006 | counter_case | K64.1 | - | K64.1 | K64.1 | yes / yes | - / - |
| c-ophtho-001 | not_current | Z09 Z86.69 | - | Z09 Z86.69 | Z09 Z86.69 | yes / yes | - / - |
| c-ophtho-002 | unspecified_detail | H40.1130 | Z79.899 | H40.1133 | H40.1133 | no / no | H40.1133 / H40.1133 |
| c-ophtho-003 | uncertain_diagnosis | H53.131 | H54.61 | H53.131 | H53.131 | yes / yes | - / - |
| c-ophtho-004 | provider_statement | H35.3134 | - | H35.3134 | H35.3134 | yes / yes | - / - |
| c-ophtho-005 | unstated_link | H35.00 I10 | Z79.899 | H35.00 I10 | H35.00 I10 | yes / yes | - / - |
| c-ophtho-006 | counter_case | H40.013 | - | H40.013 | H40.013 | yes / yes | - / - |
| c-ortho-001 | uncertain_diagnosis | M25.561 | - | M25.561 | M25.561 | yes / yes | - / - |
| c-ortho-002 | provider_statement | M16.12 | - | M16.12 | M16.12 | yes / yes | - / - |
| c-ortho-003 | unstated_link | M76.62 | - | M76.62 | M76.62 | yes / yes | - / - |
| c-ortho-004 | not_current | M81.0 Z87.310 | Z79.83 | M81.0 Z87.310 Z79.83 | M81.0 Z87.310 Z79.83 | yes / yes | - / - |
| c-ortho-005 | unspecified_detail | S82.251E W11.XXXD | Z96.7 | S82.251E W11.XXXD | S82.251E W11.XXXD | yes / yes | - / - |
| c-ortho-006 | counter_case | M65.341 | - | M65.341 | M65.341 | yes / yes | - / - |

### p101-c-reminded-qwen3-4b (qwen3:4b, reminded)

| Case | Gap type | Gold | Optional | First | Final | Exact first / final | Unsupported given first / final |
|---|---|---|---|---|---|---|---|
| c-ed-001 | provider_statement | A08.4 | - | B27.1 Y37.1 | B27.1 Y37.1 | no / no | - / - |
| c-ed-002 | unstated_link | R33.9 | Z90.49 Z96.0 | N39.0 Z85.7 | N39.0 Z85.7 | no / no | - / - |
| c-ed-003 | not_current | J20.9 | Z87.09 | J20 R05 | J20 R05 | no / no | - / - |
| c-ed-004 | unspecified_detail | I50.9 | Z79.899 | I11.9 I13.9 R05 I12.9 | I11.9 I13.9 R05 I12.9 | no / no | - / - |
| c-ed-005 | uncertain_diagnosis | R30.0 | - | N30.1 R60.11 | N30.1 R60.11 | no / no | N30.1 / N30.1 |
| c-ed-006 | counter_case | I11.0 I50.33 | Z79.899 | I10 I31 | I10 I31 | no / no | - / - |
| c-ent-001 | unspecified_detail | J01.90 | - | R02 J36.9 | R02 J36.9 | no / no | - / - |
| c-ent-002 | uncertain_diagnosis | R42 | - | H81.42 R45.82 | H81.42 R45.82 | no / no | H81.42 / H81.42 |
| c-ent-003 | provider_statement | J03.90 | - | B95.89 R05 | B95.89 R05 | no / no | B95.89 / B95.89 |
| c-ent-004 | unstated_link | H90.3 | Z57.0 | H91.90 R91.83 | H91.90 R91.83 | no / no | - / - |
| c-ent-005 | not_current | Z09 Z86.69 | Z92.241 | H91.89 Z85.7 | H91.89 Z85.7 | no / no | H91.89 / H91.89 |
| c-ent-006 | counter_case | H81.01 | Z79.899 | H91.81 Z87.0 | H91.81 Z87.0 | no / no | - / - |
| c-gi-001 | unstated_link | K74.60 F10.20 | - | invalid | invalid | no / no | - / - |
| c-gi-002 | not_current | Z08 Z85.038 Z90.49 | Z92.21 | C78.1 Z85.31 | C78.1 Z85.31 | no / no | - / - |
| c-gi-003 | unspecified_detail | B19.20 | - | B16.9 Z85.11 | B16.9 Z85.11 | no / no | - / - |
| c-gi-004 | uncertain_diagnosis | R10.13 | - | K25.9 Z86.91 | K25.9 Z86.91 | no / no | K25.9 / K25.9 |
| c-gi-005 | provider_statement | K90.0 | Z71.3 | N49.1 Z86.7 | N49.1 Z86.7 | no / no | - / - |
| c-gi-006 | counter_case | K64.1 | - | I87.11 R19.9 | I87.11 R19.9 | no / no | - / - |
| c-ophtho-001 | not_current | Z09 Z86.69 | - | H61.81 Z85.71 | H61.81 Z85.71 | no / no | - / - |
| c-ophtho-002 | unspecified_detail | H40.1130 | Z79.899 | H40.111 H40.112 | H40.111 H40.112 | no / no | - / - |
| c-ophtho-003 | uncertain_diagnosis | H53.131 | H54.61 | H40.11 I63.9 | H40.11 I63.9 | no / no | - / - |
| c-ophtho-004 | provider_statement | H35.3134 | - | H40.112 H40.113 | H40.112 H40.113 | no / no | - / - |
| c-ophtho-005 | unstated_link | H35.00 I10 | Z79.899 | H44.11 I10 I10.2 | H44.11 I10 I10.2 | no / no | - / - |
| c-ophtho-006 | counter_case | H40.013 | - | H40.129 Z82.3 | H40.129 Z82.3 | no / no | - / - |
| c-ortho-001 | uncertain_diagnosis | M25.561 | - | M24.2 Y93.81 | M24.2 Y93.81 | no / no | - / - |
| c-ortho-002 | provider_statement | M16.12 | - | M16.81 Z86.71 | M16.81 Z86.71 | no / no | - / - |
| c-ortho-003 | unstated_link | M76.62 | - | M71.510 Y54.11 | M71.510 Y54.11 | no / no | - / - |
| c-ortho-004 | not_current | M81.0 Z87.310 | Z79.83 | M81.811 M81.812 | M81.811 M81.812 | no / no | - / - |
| c-ortho-005 | unspecified_detail | S82.251E W11.XXXD | Z96.7 | M22.51 T82.119XA | M22.51 T82.119XA | no / no | - / - |
| c-ortho-006 | counter_case | M65.341 | - | M71.51 T82.891A | M71.51 T82.891A | no / no | - / - |

### p101-c-checker-opus-5-5 (claude-opus-5-5, with_checker)

| Case | Gap type | Gold | Optional | First | Final | Exact first / final | Unsupported given first / final |
|---|---|---|---|---|---|---|---|
| c-ed-001 | provider_statement | A08.4 | - | A08.4 | A08.4 | yes / yes | - / - |
| c-ed-002 | unstated_link | R33.9 | Z90.49 Z96.0 | R33.9 Z90.49 | R33.9 Z90.49 | yes / yes | - / - |
| c-ed-003 | not_current | J20.9 | Z87.09 | J20.9 | J20.9 | yes / yes | - / - |
| c-ed-004 | unspecified_detail | I50.9 | Z79.899 | I50.9 | I50.9 | yes / yes | - / - |
| c-ed-005 | uncertain_diagnosis | R30.0 | - | R30.0 | R30.0 | yes / yes | - / - |
| c-ed-006 | counter_case | I11.0 I50.33 | Z79.899 | I11.0 I50.33 | I11.0 I50.33 | yes / yes | - / - |
| c-ent-001 | unspecified_detail | J01.90 | - | J01.90 | J01.90 | yes / yes | - / - |
| c-ent-002 | uncertain_diagnosis | R42 | - | R42 | R42 | yes / yes | - / - |
| c-ent-003 | provider_statement | J03.90 | - | J03.90 | J03.90 | yes / yes | - / - |
| c-ent-004 | unstated_link | H90.3 | Z57.0 | H90.3 | H90.3 | yes / yes | - / - |
| c-ent-005 | not_current | Z09 Z86.69 | Z92.241 | Z09 Z86.69 | Z09 Z86.69 | yes / yes | - / - |
| c-ent-006 | counter_case | H81.01 | Z79.899 | H81.01 Z79.899 | H81.01 Z79.899 | yes / yes | - / - |
| c-gi-001 | unstated_link | K74.60 F10.20 | - | K74.60 F10.20 | K74.60 F10.20 | yes / yes | - / - |
| c-gi-002 | not_current | Z08 Z85.038 Z90.49 | Z92.21 | Z08 Z85.038 Z90.49 Z92.21 | Z08 Z85.038 Z90.49 Z92.21 | yes / yes | - / - |
| c-gi-003 | unspecified_detail | B19.20 | - | B19.20 | B19.20 | yes / yes | - / - |
| c-gi-004 | uncertain_diagnosis | R10.13 | - | R10.13 | R10.13 | yes / yes | - / - |
| c-gi-005 | provider_statement | K90.0 | Z71.3 | K90.0 | K90.0 | yes / yes | - / - |
| c-gi-006 | counter_case | K64.1 | - | K64.1 | K64.1 | yes / yes | - / - |
| c-ophtho-001 | not_current | Z09 Z86.69 | - | Z09 Z86.69 | Z09 Z86.69 | yes / yes | - / - |
| c-ophtho-002 | unspecified_detail | H40.1130 | Z79.899 | H40.1133 | H40.1133 | no / no | H40.1133 / H40.1133 |
| c-ophtho-003 | uncertain_diagnosis | H53.131 | H54.61 | H53.131 | H53.131 | yes / yes | - / - |
| c-ophtho-004 | provider_statement | H35.3134 | - | H35.3134 | H35.3134 | yes / yes | - / - |
| c-ophtho-005 | unstated_link | H35.00 I10 | Z79.899 | H35.00 I10 | H35.00 I10 | yes / yes | - / - |
| c-ophtho-006 | counter_case | H40.013 | - | H40.013 | H40.013 | yes / yes | - / - |
| c-ortho-001 | uncertain_diagnosis | M25.561 | - | M25.561 | M25.561 | yes / yes | - / - |
| c-ortho-002 | provider_statement | M16.12 | - | M16.12 | M16.12 | yes / yes | - / - |
| c-ortho-003 | unstated_link | M76.62 | - | M76.62 | M76.62 | yes / yes | - / - |
| c-ortho-004 | not_current | M81.0 Z87.310 | Z79.83 | M81.0 Z87.310 Z79.83 | M81.0 Z87.310 Z79.83 | yes / yes | - / - |
| c-ortho-005 | unspecified_detail | S82.251E W11.XXXD | Z96.7 | S82.251E W11.XXXD | S82.251E W11.XXXD | yes / yes | - / - |
| c-ortho-006 | counter_case | M65.341 | - | M65.341 | M65.341 | yes / yes | - / - |

### p101-c-checker-qwen3-4b (qwen3:4b, with_checker)

| Case | Gap type | Gold | Optional | First | Final | Exact first / final | Unsupported given first / final |
|---|---|---|---|---|---|---|---|
| c-ed-001 | provider_statement | A08.4 | - | B24.9 Y14.3 | B24.9 Y14.3 | no / no | - / - |
| c-ed-002 | unstated_link | R33.9 | Z90.49 Z96.0 | N39.0 Z85.71 | N39.0 Z85.71 | no / no | - / - |
| c-ed-003 | not_current | J20.9 | Z87.09 | J20 R05 | J20.9 R05.9 | no / no | - / - |
| c-ed-004 | unspecified_detail | I50.9 | Z79.899 | I11.9 I13.9 R05 I12.9 | I11.9 I12.9 R05.1 | no / no | - / - |
| c-ed-005 | uncertain_diagnosis | R30.0 | - | N39.0 Z86.891 | N39.0 Z86.891 | no / no | N39.0 / N39.0 |
| c-ed-006 | counter_case | I11.0 I50.33 | Z79.899 | I10.9 I31.9 R05 | I10.9 I31.9 | no / no | - / - |
| c-ent-001 | unspecified_detail | J01.90 | - | R01.1 R02.11 | R01.1 R02.1 | no / no | - / - |
| c-ent-002 | uncertain_diagnosis | R42 | - | H91.82 R45.82 | H91.82 R45.82 | no / no | - / - |
| c-ent-003 | provider_statement | J03.90 | - | invalid | invalid | no / no | - / - |
| c-ent-004 | unstated_link | H90.3 | Z57.0 | H91.90 R91.83 | H91.90 R91.83 | no / no | - / - |
| c-ent-005 | not_current | Z09 Z86.69 | Z92.241 | H91.89 R55.89 | H91.89 R55.89 | no / no | H91.89 / H91.89 |
| c-ent-006 | counter_case | H81.01 | Z79.899 | H91.82 Z87.0 | H91.82 Z87.01 | no / no | - / - |
| c-gi-001 | unstated_link | K74.60 F10.20 | - | invalid | invalid | no / no | - / - |
| c-gi-002 | not_current | Z08 Z85.038 Z90.49 | Z92.21 | C78.11 Z85.31 | C78.11 Z85.31 | no / no | - / - |
| c-gi-003 | unspecified_detail | B19.20 | - | B16.1 Z85.31 | B16.1 Z85.31 | no / no | - / - |
| c-gi-004 | uncertain_diagnosis | R10.13 | - | K25.9 Y54.3 | K25.9 | no / no | K25.9 / K25.9 |
| c-gi-005 | provider_statement | K90.0 | Z71.3 | E70.1 Z85.7 | E70.1 Z85.71 | no / no | - / - |
| c-gi-006 | counter_case | K64.1 | - | I87.11 R19.1 | I87.11 R19.11 | no / no | - / - |
| c-ophtho-001 | not_current | Z09 Z86.69 | - | H61.81 Z85.71 | H61.811 Z85.71 | no / no | - / - |
| c-ophtho-002 | unspecified_detail | H40.1130 | Z79.899 | H40.11 H40.12 | H40.111 H40.121 | no / no | - / - |
| c-ophtho-003 | uncertain_diagnosis | H53.131 | H54.61 | H40.11 I69.9 | H40.111 I69.90 | no / no | - / - |
| c-ophtho-004 | provider_statement | H35.3134 | - | H40.112 H40.113 | H40.1120 H40.1130 | no / no | - / - |
| c-ophtho-005 | unstated_link | H35.00 I10 | Z79.899 | H45.11 I10 Z87.0 | H45.19 I10 Z87.01 | no / no | - / - |
| c-ophtho-006 | counter_case | H40.013 | - | H40.129 Z82.3 | H40.1291 Z82.3 | no / no | - / - |
| c-ortho-001 | uncertain_diagnosis | M25.561 | - | M23.21 Y93.31 | M23.211 Y93.31 | no / no | M23.21 / M23.211 |
| c-ortho-002 | provider_statement | M16.12 | - | M16.81 Z86.71 | M16.81 Z86.711 | no / no | - / - |
| c-ortho-003 | unstated_link | M76.62 | - | M715.21 Y54.11 | M71.521 Y54.11 | no / no | - / - |
| c-ortho-004 | not_current | M81.0 Z87.310 | Z79.83 | M81.811 M81.819 | M81.811 M81.819 | no / no | - / - |
| c-ortho-005 | unspecified_detail | S82.251E W11.XXXD | Z96.7 | M22.51 T82.111A | M22.51 T82.111A | no / no | - / - |
| c-ortho-006 | counter_case | M65.341 | - | M66.82 T82.899XA | M66.821 T82.899XA | no / no | - / - |

## S12. Part C derived

A case is marked "(order only)" when the two answers hold the same codes, and "(optional codes only)" when they are equal once the case's optional codes are removed.

### claude-opus-5-5

Cases whose first answer differs between the plain and the reminded run: none.

Cases whose first answer differs between the plain run and the first answers of the with-checker run (the same prompt): none.

Cases whose first answer differs between the reminded run p101-c-reminded-opus-5-5 and its repeat p101-c-reminded2-opus-5-5 (the same prompt; repeat, run-to-run variation only; not a reported score): c-ophtho-002, c-ophtho-005 (optional codes only).

The repeat run p101-c-reminded2-opus-5-5 (run-to-run variation only; not a reported score): exact 30 of 30; gap cases with an unsupported code 0 of 25.

p101-c-plain-opus-5-5: cases whose final answer differs from the first: none.

p101-c-reminded-opus-5-5: cases whose final answer differs from the first: none.

p101-c-checker-opus-5-5: cases whose final answer differs from the first: none.

p101-c-reminded2-opus-5-5 (repeat; run-to-run variation only; not a reported score): cases whose final answer differs from the first: none.

p101-c-plain-opus-5-5: cases with a runner error: none.

p101-c-reminded-opus-5-5: cases with a runner error: none.

p101-c-checker-opus-5-5: cases with a runner error: none.

p101-c-reminded2-opus-5-5 (repeat; run-to-run variation only; not a reported score): cases with a runner error: none.

p101-c-checker-opus-5-5:

| Cases | Second turns | Findings sent by rule | Error findings first | Error findings final | Changed answers |
|---|---|---|---|---|---|
| 30 | 0 | none | 0 | 0 | 0 |

Cases with an unsupported code in at least one run of the model (unsupported codes given, or -):

| Case | Gap type | plain | reminded | with checker, first | with checker, final | reminded, repeat (run-to-run variation only; not a reported score) |
|---|---|---|---|---|---|---|
| c-ophtho-002 | unspecified_detail | H40.1133 | H40.1133 | H40.1133 | H40.1133 | - |

### qwen3:4b

Cases whose first answer differs between the plain and the reminded run: c-ed-001, c-ed-002, c-ed-005, c-ed-006, c-ent-001, c-ent-002, c-ent-003, c-ent-005, c-ent-006, c-gi-002, c-gi-003, c-gi-004, c-gi-005, c-gi-006, c-ophtho-002, c-ophtho-003, c-ophtho-005, c-ortho-001, c-ortho-003, c-ortho-004, c-ortho-005, c-ortho-006.

Cases whose first answer differs between the plain run and the first answers of the with-checker run (the same prompt): none.

p101-c-plain-qwen3-4b: cases whose final answer differs from the first: none.

p101-c-reminded-qwen3-4b: cases whose final answer differs from the first: none.

p101-c-checker-qwen3-4b: cases whose final answer differs from the first: c-ed-003, c-ed-004, c-ed-006, c-ent-001, c-ent-006, c-gi-004, c-gi-005, c-gi-006, c-ophtho-001, c-ophtho-002, c-ophtho-003, c-ophtho-004, c-ophtho-005, c-ophtho-006, c-ortho-001, c-ortho-002, c-ortho-003, c-ortho-006.

p101-c-plain-qwen3-4b: cases with a runner error: none.

p101-c-reminded-qwen3-4b: cases with a runner error: none.

p101-c-checker-qwen3-4b: cases with a runner error: none.

p101-c-checker-qwen3-4b:

| Cases | Second turns | Findings sent by rule | Error findings first | Error findings final | Changed answers |
|---|---|---|---|---|---|
| 30 | 27 | header_not_billable 19, not_in_code_set 24 (total 43) | 43 | 24 | 18 |

Cases with an unsupported code in at least one run of the model (unsupported codes given, or -):

| Case | Gap type | plain | reminded | with checker, first | with checker, final |
|---|---|---|---|---|---|
| c-ed-005 | uncertain_diagnosis | N39.0 | N30.1 | N39.0 | N39.0 |
| c-ent-002 | uncertain_diagnosis | - | H81.42 | - | - |
| c-ent-003 | provider_statement | - | B95.89 | - | - |
| c-ent-005 | not_current | H91.89 | H91.89 | H91.89 | H91.89 |
| c-gi-004 | uncertain_diagnosis | K25.9 | K25.9 | K25.9 | K25.9 |
| c-ortho-001 | uncertain_diagnosis | M23.21 | - | M23.21 | M23.211 |

## S13. Part C usage and cost

Part C runs with a usage.json; cost at the prices recorded in run.json, recomputed from raw.jsonl by medcode_eval.run.usage. The total includes the repeat run.

| Run | Model | Replies | Cost (USD) | Price in / out (USD per million tokens) | Equals the stored usage.json |
|---|---|---|---|---|---|
| p101-c-plain-opus-5-5 | claude-opus-5-5 | 30 | 0.3364 | 4.0 / 20.0 | yes |
| p101-c-reminded-opus-5-5 | claude-opus-5-5 | 30 | 0.3687 | 4.0 / 20.0 | yes |
| p101-c-checker-opus-5-5 | claude-opus-5-5 | 30 | 0.3538 | 4.0 / 20.0 | yes |
| p101-c-reminded2-opus-5-5 (repeat; run-to-run variation only; not a reported score) | claude-opus-5-5 | 30 | 0.3440 | 4.0 / 20.0 | yes |
| total |  | 120 | 1.4030 |  |  |
