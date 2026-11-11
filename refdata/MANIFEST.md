# refdata manifest

Every file under `refdata/` (except the untracked `incoming/`) is an
unmodified copy of a public CMS release, listed here with its size, sha256
and source.

## icd10cm_fy2027/

Code set: ICD-10-CM FY2027.

- Source page: https://www.cms.gov/medicare/coding-billing/icd-10-codes
- Download date: 2026-11-10

| File | Bytes | sha256 | Source ZIP | Source ZIP sha256 | Release label |
|---|---|---|---|---|---|
| icd10cm_order_2027.txt | 14724229 | 38981fb2c1226e2b92393cef7d921d2293494dd184b5ad039dde08e4b364265f | 2027-code-descriptions-tabular-order.zip (member `Code Descriptions/icd10cm_order_2027.txt`) | 91c6c9d1117764ce72375a0f3a5493b1725dafbc1ab283b55799076c9e194965 | ICD-10-CM FY2027 (October 1, 2026 release) |
| icd10cm_tabular_2027.xml | 9779494 | d778c97a5bb9da7d71645610e277f8db3bd302befa3b08d71dd5043715a74b2a | 2027-code-tables-tabular-index.zip (member `Table and Index/icd10cm_tabular_2027.xml`) | 37baa476323714be16f95c9b2c96812bf6f3623d9f15188866e584dc529b0298 | ICD-10-CM FY2027 (October 1, 2026 release) |
| icd10cm_tabular.xsd | 12170 | c862464d782fd1b46df7b0b7b85cc44a48a73b7fd2e815c34f872228a8c2499c | 2027-code-tables-tabular-index.zip (member `Table and Index/icd10cm_tabular.xsd`) | 37baa476323714be16f95c9b2c96812bf6f3623d9f15188866e584dc529b0298 | ICD-10-CM FY2027 (October 1, 2026 release) |
| icd10cm_tabular_addenda_2027.pdf | 442177 | 036d0156fcb451d442f1a3f232f3071dd8f8b017d129af595951497f5c6507a0 | 2027-icd-10-addendum.zip (member `Addendum/icd10cm_tabular_addenda_2027.pdf`) | 16986a34d1458e549217229686f1a487cf6419ee6acb1043fbc770f8fabdd026 | ICD-10-CM FY2027 (October 1, 2026 release) |
| fy-2027-icd-10-cm-coding-guidelines.pdf | 830104 | 1f0065b609b678e98f85bf047b3b012c6a88ba3222e42be2f2435889e05738ab | none: direct download, no ZIP | n/a | FY 2027 ICD-10-CM Official Guidelines for Coding and Reporting (label taken from the file name only) |
| icd10cm_order_addenda_2027.txt | 42495 | d64c57ef4534e4f90336decf27a34ba42979c31cd88f6ea923b5b5edd3da6384 | 2027-code-descriptions-tabular-order.zip (member `Code Descriptions/icd10cm_order_addenda_2027.txt`) | 91c6c9d1117764ce72375a0f3a5493b1725dafbc1ab283b55799076c9e194965 | ICD-10-CM FY2027 (October 1, 2026 release) |

Notes

- The four ZIP members were extracted byte for byte; each one's size
  matches the ZIP's listing.
- The guidelines PDF is a byte-identical copy of the downloaded file. Its
  release label comes from its file name only; the PDF has not been
  parsed. The source page and download date above cover it as well, since
  no separate source was recorded for it.
- Other members of the three ZIPs (index, external-cause index, drug and
  neoplasm tables, PDF versions of the tabular, the codes file and the
  code/order addenda text files, other addenda PDFs) are not tracked.
