Code set: ICD-10-CM FY2027 (October 1, 2026 release). Gold sha256: 3ba94808da8b7970192a1c4f391aa106855125fb7e2abcede50716039abed633. Cases: 25. Answers: 25 (0 with unknown ids). Second turns: 2. Stop reasons: end_turn 27; cases with a reply whose stop reason is not end_turn: 0.

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

Per case:

| Case | Trap | Specialty | Gold | Optional | First | Final | Second turn | Exact first / final | Optional given first / final |
|---|---|---|---|---|---|---|---|---|---|
| b-ed-001 | seventh_character | ed | S52.501A W11.XXXA Y92.014 Y93.H9 | Y99.8 | S52.501A W11.XXXA Y92.014 Y93.H9 Y99.8 | S52.501A W11.XXXA Y92.014 Y93.H9 Y99.8 | no | yes / yes | 1 / 1 |
| b-ed-002 | sequencing | ed | A41.9 N39.0 | R41.0 | A41.9 N39.0 | A41.9 N39.0 | no | yes / yes | 0 / 0 |
| b-ed-003 | laterality | ed | L03.115 I10 | Z79.899 | L03.115 I10 | L03.115 I10 | no | yes / yes | 0 / 0 |
| b-ed-004 | excludes1 | ed | N13.2 | - | N13.2 | N13.2 | no | yes / yes | 0 / 0 |
| b-ed-005 | combination | ed | K80.00 | - | K80.00 | K80.00 | no | yes / yes | 0 / 0 |
| b-ent-001 | sequencing | ent | A40.0 J36 | B95.0 | A40.0 J36 | A40.0 J36 | no | yes / yes | 0 / 0 |
| b-ent-002 | excludes1 | ent | H66.011 | - | H66.011 | H66.011 | no | yes / yes | 0 / 0 |
| b-ent-003 | combination | ent | J35.3 | - | J35.3 | J35.3 | no | yes / yes | 0 / 0 |
| b-ent-004 | seventh_character | ent | S01.411D V18.4XXD | - | S01.411D V18.4XXD | S01.411D V18.4XXD | no | yes / yes | 0 / 0 |
| b-ent-005 | laterality | ent | H90.42 | - | H90.42 | H90.42 | no | yes / yes | 0 / 0 |
| b-gi-001 | excludes1 | gi | K25.4 | - | K25.4 K29.01 B96.81 | K25.4 K29.01 B96.81 | yes | no / no | 0 / 0 |
| b-gi-002 | combination | gi | K21.00 | R13.10 | K21.00 | K21.00 | no | yes / yes | 0 / 0 |
| b-gi-003 | sequencing | gi | E11.43 K31.84 Z79.4 | - | E11.43 K31.84 Z79.4 | E11.43 K31.84 Z79.4 | no | yes / yes | 0 / 0 |
| b-gi-004 | laterality | gi | K40.90 | - | K40.90 | K40.90 | no | yes / yes | 0 / 0 |
| b-gi-005 | seventh_character | gi | K25.3 T39.315A | - | K25.3 T39.315A | K25.3 T39.315A | no | yes / yes | 0 / 0 |
| b-ophtho-001 | combination | ophtho | E11.3511 E11.3292 Z79.4 Z79.84 | - | E11.3511 E11.3292 Z79.4 Z79.84 | E11.3511 E11.3292 Z79.4 Z79.84 | no | yes / yes | 0 / 0 |
| b-ophtho-002 | laterality | ophtho | H25.11 Z96.1 | Z98.42 | H25.11 Z96.1 Z98.42 | H25.11 Z96.1 Z98.42 | no | yes / yes | 1 / 1 |
| b-ophtho-003 | seventh_character | ophtho | H40.1112 | Z83.511 | H40.1112 Z83.511 | H40.1112 Z83.511 | no | yes / yes | 1 / 1 |
| b-ophtho-004 | sequencing | ophtho | L71.9 H10.823 | - | L71.9 H13 | L71.9 H10.403 | yes | no / no | 0 / 0 |
| b-ophtho-005 | excludes1 | ophtho | H10.811 | - | H10.811 | H10.811 | no | yes / yes | 0 / 0 |
| b-ortho-001 | laterality | ortho | M17.11 | - | M17.11 | M17.11 | no | yes / yes | 0 / 0 |
| b-ortho-002 | seventh_character | ortho | S82.61XD W18.30XD | - | S82.61XD W18.30XD | S82.61XD W18.30XD | no | yes / yes | 0 / 0 |
| b-ortho-003 | excludes1 | ortho | M80.051A I10 | Z79.899 W18.30XA Y92.009 Y93.01 Y99.8 | M80.051A I10 | M80.051A I10 | no | yes / yes | 0 / 0 |
| b-ortho-004 | combination | ortho | M51.16 | - | M51.16 | M51.16 | no | yes / yes | 0 / 0 |
| b-ortho-005 | sequencing | ortho | D66 M36.2 | - | D66 M36.2 | D66 M36.2 | no | yes / yes | 0 / 0 |
