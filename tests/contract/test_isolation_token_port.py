"""Current-candidate token data integration; no native constructor is invoked."""
from dataclasses import asdict, fields
import unittest
from unittest.mock import patch

from ceta.contracts.wire import ContractError
from ceta.supervisor import isolated_worker as parent
from test_isolation_token_diagnostics import _ControlledBuffers, SID
from test_isolation_qualification_oracle import oracle


class IsolationTokenPortTests(unittest.TestCase):
    def test_original_constructor_prefix_never_invents_unmeasured_fields(self):
        names = tuple(field.name for field in fields(parent.IsolationTokenFacts))
        self.assertEqual(names, ('appcontainer_sid', 'is_appcontainer', 'capability_count',
            'integrity_rid', 'restricted', 'observed_monotonic_ns', 'restricted_sid_count',
            'restriction_last_error', 'restriction_raw_result'))
        for restricted in (False, True):
            with self.subTest(restricted=restricted), self.assertRaises(ContractError):
                parent.IsolationTokenFacts(SID, True, 0, 4096, restricted, 11)

    def test_actual_parent_parser_copy_connects_to_existing_worker_oracle(self):
        for raw, count, error in ((0, 0, 0), (1, 1, 0), (-1, 1, 5), (2, 4095, 0)):
            with self.subTest(raw=raw, count=count, error=error):
                api = _ControlledBuffers(restricted=raw, restricted_count=count,
                    restriction_error_code=error)
                with patch.object(parent.time, 'monotonic_ns', return_value=11):
                    measured = parent._IsolationAPI.token_facts(api, 55, 303)
                copied = asdict(measured)
                worker = dict(schema='ceta-isolation-token-v2', appcontainer_sid=SID,
                    is_appcontainer=1, capability_count=0, integrity='S-1-16-4096',
                    restricted=bool(raw), restriction_raw_result=raw,
                    restriction_last_error=error, restricted_sid_count=count)
                oracle.assert_token_pair(copied, worker, SID)
                self.assertEqual(api.closed, [7701])
                self.assertEqual(api._pending_handles, [])
                self.assertEqual(api._pending_token_outputs, [])
                mismatch = dict(worker, restricted_sid_count=1 if count == 0 else 0)
                with self.assertRaises(oracle.QualificationError):
                    oracle.assert_token_pair(copied, mismatch, SID)


if __name__ == '__main__':
    unittest.main()
