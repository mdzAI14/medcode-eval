Code set: ICD-10-CM FY2027 (October 1, 2026 release). Gold sha256: 3ba94808da8b7970192a1c4f391aa106855125fb7e2abcede50716039abed633. Cases: 25. Answers: 25 (0 with unknown ids). Second turns: 22. Stop reasons: none recorded; cases with a reply whose stop reason is not end_turn: 0.

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

Per case:

| Case | Trap | Specialty | Gold | Optional | First | Final | Second turn | Exact first / final | Optional given first / final |
|---|---|---|---|---|---|---|---|---|---|
| b-ed-001 | seventh_character | ed | S52.501A W11.XXXA Y92.014 Y93.H9 | Y99.8 | S82.812A Y92.11 | S82.812A Y92.111 | yes | no / no | 0 / 0 |
| b-ed-002 | sequencing | ed | A41.9 N39.0 | R41.0 | B96.89 N39.2 R65.8 | B96.89 N39.2 R65.8 | yes | no / no | 0 / 0 |
| b-ed-003 | laterality | ed | L03.115 I10 | Z79.899 | B95.81 I10 | B95.81 I10 | yes | no / no | 0 / 0 |
| b-ed-004 | excludes1 | ed | N13.2 | - | N31.1 N25.2 | N31.1 N25.2 | yes | no / no | 0 / 0 |
| b-ed-005 | combination | ed | K80.00 | - | K86.10 K81.91 | K86.10 K81.91 | yes | no / no | 0 / 0 |
| b-ent-001 | sequencing | ent | A40.0 J36 | B95.0 | R21.11 R21.12 R21.13 R21.14 R21.15 R21.16 R21.17 R21.18 R21.19 R21.21 R21.22 R21.23 R21.24 R21.25 R21.26 R21.27 R21.28 R21.29 R21.31 R21.32 R21.33 R21.34 R21.35 R21.36 R21.37 R21.38 R21.39 R21.41 R21.42 R21.43 R21.44 R21.45 R21.46 R21.47 R21.48 R21.49 R21.51 R21.52 R21.53 R21.54 R21.55 R21.56 R21.57 R21.58 R21.59 R21.61 R21.62 R21.63 R21.64 R21.65 R21.66 R21.67 R21.68 R21.69 R21.71 R21.72 R21.73 R21.74 R21.75 R21.76 R21.77 R21.78 R21.79 R21.81 R21.82 R21.83 R21.84 R21.85 R21.86 R21.87 R21.88 R21.89 R21.91 R21.92 R21.93 R21.94 R21.95 R21.96 R21.97 R21.98 R21.99 | invalid | yes | no / no | 0 / 0 |
| b-ent-002 | excludes1 | ent | H66.011 | - | H66.91 H66.11 | H66.91 H66.11 | no | no / no | 0 / 0 |
| b-ent-003 | combination | ent | J35.3 | - | R05 J36.9 | R05.1 J36.9 | yes | no / no | 0 / 0 |
| b-ent-004 | seventh_character | ent | S01.411D V18.4XXD | - | Z85.811 W14..811XA | Z85.811 W14..811XA | yes | no / no | 0 / 0 |
| b-ent-005 | laterality | ent | H90.42 | - | H91.41 Z85.7 | H91.41 Z85.71 | yes | no / no | 0 / 0 |
| b-gi-001 | excludes1 | gi | K25.4 | - | K25.11 K25.21 | K25.11 K25.21 | yes | no / no | 0 / 0 |
| b-gi-002 | combination | gi | K21.00 | R13.10 | K21.9 K52.11 | K21.9 K52.11 | yes | no / no | 0 / 0 |
| b-gi-003 | sequencing | gi | E11.43 K31.84 Z79.4 | - | K56.40 E11.9 | K56.40 E11.9 | yes | no / no | 0 / 0 |
| b-gi-004 | laterality | gi | K40.90 | - | K40..9, Y42.119 | K40..9, Y42.119 | yes | no / no | 0 / 0 |
| b-gi-005 | seventh_character | gi | K25.3 T39.315A | - | K29.81 T36.3X1A | K29.81 T36.3X1A | no | no / no | 0 / 0 |
| b-ophtho-001 | combination | ophtho | E11.3511 E11.3292 Z79.4 Z79.84 | - | H40.11 H40.12 H40.119 | H40.111 H40.121 H40.119 | yes | no / no | 0 / 0 |
| b-ophtho-002 | laterality | ophtho | H25.11 Z96.1 | Z98.42 | H36.422 H36.421 | H36.422 H36.421 | yes | no / no | 0 / 0 |
| b-ophtho-003 | seventh_character | ophtho | H40.1112 | Z83.511 | H40.121 Z82.0 | H40.1212 Z82.0 | yes | no / no | 0 / 0 |
| b-ophtho-004 | sequencing | ophtho | L71.9 H10.823 | - | H02.11 H02.12 | H02.111 H02.121 | yes | no / no | 0 / 0 |
| b-ophtho-005 | excludes1 | ophtho | H10.811 | - | H11.11 H11.1 | H11.111 H11.11 | yes | no / no | 0 / 0 |
| b-ortho-001 | laterality | ortho | M17.11 | - | invalid | invalid | no | no / no | 0 / 0 |
| b-ortho-002 | seventh_character | ortho | S82.61XD W18.30XD | - | M22.51 Y92.31 | M22.51 Y92.310 | yes | no / no | 0 / 0 |
| b-ortho-003 | excludes1 | ortho | M80.051A I10 | Z79.899 W18.30XA Y92.009 Y93.01 Y99.8 | S72.219A M81.81 | S72.219A M81.81 | yes | no / no | 0 / 0 |
| b-ortho-004 | combination | ortho | M51.16 | - | M51.82 G70.13 | M51.82 G70.13 | yes | no / no | 0 / 0 |
| b-ortho-005 | sequencing | ortho | D66 M36.2 | - | H61.11 D60.1 | H61.111 D60.1 | yes | no / no | 0 / 0 |
