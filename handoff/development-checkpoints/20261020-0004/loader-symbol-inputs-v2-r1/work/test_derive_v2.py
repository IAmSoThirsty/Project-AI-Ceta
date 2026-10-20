"""Bounded data-only regression cases for symbol provenance derivation."""
import ast
from pathlib import Path
import unittest
import derive_v2 as d

class DerivationTests(unittest.TestCase):
    def test_rejected_v1_and_all_retained_files_are_unchanged(self):
        value,count=d.dataset();self.assertGreater(count,0);self.assertIs(value['codeview_match'],False)
    def test_exact_frozen_r3_source_extracts_only_three_function_definitions(self):
        source=(d.L3/'work/loader_snaps.py').read_bytes();funcs,records=d.parsers(source,d.sha(source))
        self.assertEqual([r['name'] for r in records],list(d.PARSER_NAMES));self.assertNotIn('prepare_producer',funcs)
    def test_actual_retained_ntdll_and_pdb_match_ages_1_4_1(self):
        source=(d.L3/'work/loader_snaps.py').read_bytes();funcs,_=d.parsers(source,d.sha(source));old,_=d.dataset();pins=old['input_pins']
        image=funcs['pe_codeview'](d.read(pins['ntdll']['path'])[0]);pdb=funcs['pdb_codeview'](d.read(pins['pdb']['path'])[0]);match=funcs['match_codeview'](image,pdb)
        self.assertEqual([match[k] for k in ('image_age','info_age','dbi_age')],[1,4,1])
    def test_modified_parser_bytes_are_rejected(self):
        with self.assertRaisesRegex(d.DataError,'PARSER_SOURCE_CHANGED'):d.parsers(b'bad','0'*64)
    def test_duplicate_and_nonfinite_json_are_rejected(self):
        for raw in (b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":Infinity}'):
            with self.subTest(raw=raw),self.assertRaises(d.DataError):d.parse(raw)
    def test_traversal_absolute_noncanonical_and_windows_paths_are_rejected(self):
        for value in ('../secret','a/../b','/root','T:/file','a\\b','a//b','a\x00b'):
            with self.subTest(path=value),self.assertRaises(d.DataError):d.safe_relative(value)
    def test_pending_or_wrong_location_review_cannot_be_accepted(self):
        with self.assertRaises(d.DataError):d.approved_loader(dict(repository_relative_path='README.md',sha256='0'*64))
    def test_rejected_predecessor_review_cannot_admit_current_loader(self):
        for cut in ('loader-capture-r3','loader-capture-r4'):
            path=d.R/cut/'review/REVIEW.json'
            with self.subTest(cut=cut),self.assertRaisesRegex(d.DataError,'CURRENT_LOADER_REVIEW_LOCATION_REQUIRED'):
                d.approved_loader(d.reference(path))
    def test_effectful_parser_decorators_are_refused_without_execution(self):
        body='@danger()\ndef pe_codeview(raw):\n return {}\ndef pdb_codeview(raw):\n return {}\ndef match_codeview(image,pdb):\n return {}\n'.encode()
        with self.assertRaisesRegex(d.DataError,'PARSER_DEFINITION_EFFECT_REFUSED'):d.parsers(body,d.sha(body))
    def test_parser_imports_are_refused_without_module_execution(self):
        body='def pe_codeview(raw):\n import ctypes\n return {}\ndef pdb_codeview(raw):\n return {}\ndef match_codeview(image,pdb):\n return {}\n'.encode()
        with self.assertRaisesRegex(d.DataError,'PARSER_IMPORT_OR_GLOBAL_REFUSED'):d.parsers(body,d.sha(body))
    def test_exact_receipt_hash_binding_does_not_accept_substring(self):
        self.assertTrue(d.contains_exact({'a':[{'b':'abc'}]},'abc'));self.assertFalse(d.contains_exact({'a':'abcx'},'abc'))

if __name__=='__main__':unittest.main()
