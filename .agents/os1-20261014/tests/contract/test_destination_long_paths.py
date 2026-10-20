"""Real Windows transport at the frozen candidate's long destination path.

KernelFixture's positive seed authority is synthetic. This regression observes
the actual owned service, native client, named pipe and private spool I/O while
the child authority remains CLOSED and the canonical store remains unchanged.
"""
from pathlib import Path
import hashlib
import sys
import unittest

import test_kernel_authority as authority_cases
from test_owned_service import _ServiceTestCase


class DestinationLongPathTests(_ServiceTestCase):
    seeded_consumption = authority_cases.NativeAuthorityResolutionTests.seeded_consumption

    def test_actual_long_request_and_response_paths_return_exact_evidence_and_settle_owned_children(self):
        fixture, consumed, keys, before = self.seeded_consumption()
        service = self.fixture_service(fixture)
        # Only this owned, not-yet-started fixture gains an extra spool directory.
        # Force the same failure boundary even if the candidate is later rehomed.
        baseline = service._spool / ("0" * 32 + ".response.json")
        component = "long-destination-" + "x" * max(1, 280 - len(str(baseline)))
        service._spool = service._spool / component
        Path("\\\\?\\" + str(service._spool)).mkdir(exist_ok=False)
        self.ready(service)
        attempt, response = self.call(service, consumed.record_wire, "kernel.resolve_consumption")
        request = service._spool / (attempt + ".request.json")
        result = service._spool / (attempt + ".response.json")
        self.assertGreater(len(str(request)), 260, "fixture must reproduce the current long destination")
        self.assertGreater(len(str(result)), 260, "both native callers must cross the original failure boundary")
        self.assertEqual(response.kind, "EVIDENCE")
        self.assertEqual(response.record_wire, consumed.record_wire)
        self.assertEqual(response.event_wire, consumed.event_wire)
        self.assertEqual(response.prior_position, consumed.prior_position)
        self.assertEqual(service.snapshot()["authority"], "CLOSED")
        for path in (request, result):
            self.assertTrue(path.is_relative_to(service._spool))
            physical = Path("\\\\?\\" + str(path)) if sys.platform == "win32" else path
            self.assertFalse(physical.is_symlink())
            self.assertFalse(physical.is_junction())
            self.assertGreater(len(physical.read_bytes()), 0)
        original = (Path("\\\\?\\" + str(result))).read_bytes()
        digest = hashlib.sha256(original).hexdigest()
        with self.assertRaises(FileExistsError):
            (Path("\\\\?\\" + str(result))).open("xb")
        self.assertEqual(hashlib.sha256((Path("\\\\?\\" + str(result))).read_bytes()).hexdigest(), digest)
        self.stop(service)
        self.reopen_unchanged(fixture, before, keys)


if __name__ == "__main__":
    unittest.main()
