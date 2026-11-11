"""The tabular survey against the real ICD-10-CM FY2027 refdata files.

Counts frozen from task P4.1 step 7 (ICD-10-CM FY2027, October 1, 2026
release), plus cross-checks computed here independently of the survey
where that is cheap. No network.
"""

import unittest
from collections import Counter

from medcode_eval import orderfile, tabular, tabular_survey
from medcode_eval.part_a.generate import DEFAULT_PATHS, REPO_ROOT

# element: (count, {parent: count})
CENSUS = {'ICD10CM.tabular': (1, {}),
 'chapter': (22, {'ICD10CM.tabular': 22}),
 'codeAlso': (333, {'diag': 327, 'section': 6}),
 'codeFirst': (364, {'diag': 361, 'section': 3}),
 'desc': (47344, {'chapter': 22, 'diag': 47025, 'section': 297}),
 'diag': (47025, {'diag': 45104, 'section': 1921}),
 'excludes1': (2648, {'chapter': 2, 'diag': 2581, 'section': 65}),
 'excludes2': (1172, {'chapter': 17, 'diag': 1092, 'section': 63}),
 'extension': (1790, {'sevenChrDef': 1790}),
 'heading': (4, {'visCategory': 1, 'visMax': 1, 'visMin': 1, 'visRange': 1}),
 'includes': (414, {'chapter': 3, 'diag': 378, 'section': 33}),
 'inclusionTerm': (6842, {'diag': 6838, 'section': 4}),
 'instruction': (7, {'introSection': 7}),
 'introSection': (9, {'introduction': 9}),
 'introduction': (1, {'ICD10CM.tabular': 1}),
 'name': (47047, {'chapter': 22, 'diag': 47025}),
 'note': (25287,
          {'codeAlso': 690,
           'codeFirst': 810,
           'excludes1': 5411,
           'excludes2': 2529,
           'includes': 1023,
           'inclusionTerm': 12629,
           'instruction': 8,
           'notes': 180,
           'sevenChrDef': 8,
           'sevenChrNote': 508,
           'useAdditionalCode': 1491}),
 'notes': (86, {'chapter': 14, 'diag': 57, 'section': 15}),
 'section': (297, {'chapter': 297}),
 'sectionIndex': (22, {'chapter': 22}),
 'sectionRef': (289, {'sectionIndex': 289}),
 'sevenChrDef': (508, {'diag': 508}),
 'sevenChrNote': (508, {'diag': 508}),
 'title': (9, {'introSection': 9}),
 'useAdditionalCode': (847, {'chapter': 4, 'diag': 829, 'section': 14}),
 'value': (30, {'visCategory': 6, 'visMax': 14, 'visMin': 10}),
 'version': (1, {'ICD10CM.tabular': 1}),
 'visCategory': (7, {'visualImpairment': 7}),
 'visMax': (15, {'visRange': 15}),
 'visMin': (11, {'visRange': 11}),
 'visRange': (15, {'visCategory': 15}),
 'visualImpairment': (1, {'diag': 1})}

NOTES = {'codeAlso': (333,
              690,
              {'category': 179, 'code': 359, 'section': 11, 'subcategory': 141},
              [495, 0, 0, 195],
              541,
              541),
 'codeFirst': (364,
               810,
               {'category': 343, 'code': 290, 'section': 9, 'subcategory': 168},
               [596, 4, 0, 210],
               741,
               737),
 'excludes1': (2648,
               5411,
               {'category': 2219,
                'chapter': 2,
                'code': 1644,
                'section': 150,
                'subcategory': 1396},
               [5284, 0, 0, 127],
               5714,
               5714),
 'excludes2': (1172,
               2529,
               {'category': 1066,
                'chapter': 113,
                'code': 517,
                'section': 229,
                'subcategory': 604},
               [2492, 1, 0, 36],
               2803,
               2802),
 'includes': (414,
              1023,
              {'category': 827,
               'chapter': 3,
               'code': 6,
               'section': 103,
               'subcategory': 84},
              [38, 0, 1, 984],
              90,
              89),
 'inclusionTerm': (6842,
                   12629,
                   {'category': 357, 'code': 8338, 'section': 5, 'subcategory': 3929},
                   [169, 1, 10, 12449],
                   230,
                   219),
 'instruction': (7, 8, {'introduction': 8}, [0, 0, 0, 8], 0, 0),
 'notes': (86,
           180,
           {'category': 84, 'chapter': 36, 'code': 6, 'section': 43, 'subcategory': 11},
           [55, 1, 0, 124],
           76,
           75),
 'sevenChrDef': (508, 8, {'category': 4, 'subcategory': 4}, [0, 0, 0, 8], 0, 0),
 'sevenChrNote': (508,
                  508,
                  {'category': 421, 'subcategory': 87},
                  [508, 0, 0, 0],
                  545,
                  545),
 'useAdditionalCode': (847,
                       1491,
                       {'category': 566,
                        'chapter': 10,
                        'code': 500,
                        'section': 35,
                        'subcategory': 380},
                       [1174, 0, 0, 317],
                       1439,
                       1439)}

SEVENTH = {'defs': 508,
 'defs_with_def_on_ancestor': 24,
 'defs_differing_from_def_above': 24,
 'billable_7_unexplained_but_farther_def_lists_char': 0,
 'extensions': 1790,
 'char_sets_distinct': 12,
 'billable_7': 51587,
 'billable_7_explained': 51378,
 'billable_7_unexplained_count': 209,
 'billable_7_unexplained_by_reason': {'tabular_diag_no_definition': 209},
 'billable_7_explained_base_forms': {'first 6 characters are a tabular diag': 40225,
                                     'tabular diag padded with X to 6 characters': 11153},
 'billable_under_def_shorter_than_7': 0,
 'x6_codes': 11153,
 'x6_billable': 11153,
 'x6_explained': 11153,
 'x_in_positions_4_to_6': {'X is in a tabular diag name (billable)': 3443,
                           'X is in a tabular diag name (header)': 1323,
                           'X pads a tabular diag to 6 characters before a 7th character (billable)': 11153},
 'placeholder_true': 245,
 'placeholder_true_by_name_length': {'4': 2, '5': 243},
 'placeholder_true_with_def_in_scope': 207,
 'xml_diags_ending_in_x': 245}

ORDER_VS_XML = {'xml_codes': 47025,
 'order_codes': 98403,
 'xml_only_count': 0,
 'order_only_count': 51378,
 'order_only_by_reason': {'7th character from a definition': 51378},
 'shared_by_flag_shape': {'billable | leaf | no 7th character in scope': 23501,
                          'header | has children | 7th character in scope': 4038,
                          'header | has children | no 7th character in scope': 6538,
                          'header | leaf | 7th character in scope': 12948}}

COVERAGE = {'codeAlso': (15779, 10574),
 'codeFirst': (8792, 8287),
 'excludes1': (48142, 47634),
 'excludes2': (66825, 66825),
 'useAdditionalCode': (50149, 49728)}


class RealTabularSurveyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path, cls.stored, cls.billable = tabular_survey.load_real()
        cls.s = tabular_survey.survey(cls.path, cls.stored, cls.billable)
        cls.tree = tabular.load_tree(cls.path)

    def test_code_set(self):
        self.assertEqual(self.s["code_set"], "ICD-10-CM FY2027 (October 1, 2026 release)")
        self.assertEqual(self.s["tabular_version"], "2027")

    def test_census(self):
        got = {k: (v["count"], v["parents"]) for k, v in self.s["census"].items()}
        self.assertEqual(got, CENSUS)

    def test_notes(self):
        got = {k: (v["elements"], v["notes"], v["notes_by_level"],
                   [v["classes"][c] for c in tabular_survey.CLASSES],
                   v["references"], v["references_resolved"])
               for k, v in self.s["notes"].items()}
        self.assertEqual(got, NOTES)

    def test_seventh(self):
        self.assertEqual({k: self.s["seventh"][k] for k in SEVENTH}, SEVENTH)

    def test_order_vs_xml(self):
        o = self.s["order_vs_xml"]
        got = {k: o[k] for k in ORDER_VS_XML if k != "shared_by_flag_shape"}
        got["shared_by_flag_shape"] = {" | ".join(r[:3]): r[3]
                                       for r in o["shared_by_flag_shape"]}
        self.assertEqual(got, ORDER_VS_XML)

    def test_coverage(self):
        got = {k: (v["any_note"], v["resolvable_note"])
               for k, v in self.s["coverage"]["by_kind"].items()}
        self.assertEqual(got, COVERAGE)
        self.assertEqual(self.s["coverage"]["billable_without_tabular_diag"], 0)

    # cross-checks, computed here -------------------------------------------
    def test_cross_check_order_file(self):
        recs = orderfile.load(REPO_ROOT / DEFAULT_PATHS["order"])
        self.assertEqual(len(recs), ORDER_VS_XML["order_codes"])
        seven = [r.code for r in recs if r.billable and len(r.code) == 7]
        self.assertEqual(len(seven), SEVENTH["billable_7"])
        self.assertEqual(sum(c[5] == "X" for c in seven), SEVENTH["x6_codes"])

    def test_cross_check_tree(self):
        self.assertEqual(len(self.tree.diags), CENSUS["diag"][0])
        self.assertEqual(len(self.tree.notes), CENSUS["note"][0])
        self.assertEqual(sum(d.seven_chr is not None for d in self.tree.diags.values()),
                         CENSUS["sevenChrDef"][0])
        self.assertEqual(sum(len(d.seven_chr or ()) for d in self.tree.diags.values()),
                         CENSUS["extension"][0])
        self.assertEqual(sum(d.placeholder for d in self.tree.diags.values()),
                         self.s["census"]["diag"]["attributes"]["placeholder"])
        self.assertEqual(Counter(n.kind for n in self.tree.notes)["excludes1"],
                         NOTES["excludes1"][1])

    def test_cross_check_partition(self):
        # every stored code is a tabular diag or a 7th-character expansion
        self.assertEqual(ORDER_VS_XML["xml_codes"] + ORDER_VS_XML["order_only_count"],
                         ORDER_VS_XML["order_codes"])
        # every billable code is a tabular leaf with no 7th character in
        # scope, or an expansion explained by a definition
        self.assertEqual(ORDER_VS_XML["shared_by_flag_shape"]
                         ["billable | leaf | no 7th character in scope"]
                         + SEVENTH["billable_7_explained"], len(self.billable))
        for k, v in self.s["notes"].items():
            self.assertEqual(sum(v["classes"].values()), v["notes"], k)


if __name__ == "__main__":
    unittest.main()
