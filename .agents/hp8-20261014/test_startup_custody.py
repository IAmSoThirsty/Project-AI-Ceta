"""Two unchanged HP7 reviewer custody oracles; reused methods count as zero new LOC."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,inspect,json,os,sys,threading,unittest,uuid
from unittest.mock import patch
F=Path(r"T:\00-Active\Project-AI-CETA")
Q=Path(__file__).resolve().parent
R=F/".agents/runtime"/Q.name
V=R/"native-review-fixtures"
V.mkdir(exist_ok=True)
sys.path.insert(0,str(Q))
import preserve_ceta_complete as tool
import legacy_cache_validation as legacy
from test_legacy_cache_validation import watch_native
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now(timezone.utc).isoformat()
FACTS=[]


class StartedPipeCustodyTests(unittest.TestCase):
    def schedule(self, primary):
        gate, entered = threading.Event(), threading.Event()
        started_threads, opened_files, state = [], [], {}
        actual_start, actual_run = threading.Thread.start, threading.Thread.run
        area = V / ("startup-" + uuid.uuid4().hex)
        area.mkdir(exist_ok=False)
        def held_run(thread):
            target = getattr(thread, "_target", None)
            if getattr(target, "__name__", "") == "send":
                state["sender"] = thread
                state["descriptor"] = inspect.getclosurevars(target).nonlocals["in_write"]
                entered.set()
                if not gate.wait(15):
                    raise AssertionError("owned synthetic sender release was not delivered")
            return actual_run(thread)
        def interrupted_start(thread):
            actual_start(thread)
            if getattr(getattr(thread, "_target", None), "__name__", "") == "send":
                started_threads.append(thread)
                if not entered.wait(3):
                    raise AssertionError("real pipe sender entry not observed")
                raise primary
        fact = {"control_exception": type(primary).__name__, "request_kind": "SYNTHETIC_EMPTY_JSON_ONLY",
                "cache_or_generator_read": False, "source_or_cache_execution": False,
                "started_at": now(), "validation_sha256": sha(Q / "legacy_cache_validation.py")}
        try:
            with watch_native(self.id()) as launched:
                with patch.object(threading.Thread, "run", held_run), patch.object(threading.Thread, "start", interrupted_start):
                    observed = None
                    try:
                        legacy._exchange(tool, b"{}")
                    except BaseException as error:
                        observed = error
                    self.assertIs(observed, primary)
                    self.assertEqual(len(started_threads), 1)
                    sender, descriptor = state["sender"], state["descriptor"]
                    fact.update(sender_ident=sender.ident, sender_alive_at_parent_exception=sender.is_alive(),
                                descriptor=descriptor, returned_thread_count=len(getattr(observed, "threads", ())),
                                returned_descriptor_count=len(getattr(observed, "pipe_descriptors", ())),
                                returned_worker_lease=getattr(observed, "worker_lease", None) is not None,
                                native_lifetimes=[dict(row) for _, row in launched])
                    try:
                        os.fstat(descriptor)
                        fact["sender_descriptor_open_at_parent_exception"] = True
                    except OSError:
                        fact["sender_descriptor_open_at_parent_exception"] = False
                    # All new files are reviewer-owned. No cache/source bytes
                    # are in this request. Observe whether the just-closed FD
                    # can become a new ordinary file before sender retirement.
                    if not fact["sender_descriptor_open_at_parent_exception"]:
                        for index in range(20):
                            path = area / (str(index) + ".synthetic")
                            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                            opened_files.append((fd, path))
                            if fd == descriptor:
                                state["reused_path"] = path
                                fact["reused_fixture_path"] = str(path)
                                fact["reused_fixture_before"] = {
                                    "native_identity": tool.file_identity(os.fstat(fd)),
                                    "bytes": path.stat().st_size,
                                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                                break
                    fact["descriptor_reused_by_own_fixture"] = "reused_path" in state
                    gate.set()
                    sender.join(5)
                    fact["sender_joined_after_explicit_review_recovery"] = not sender.is_alive()
                    if "reused_path" in state:
                        data = state["reused_path"].read_bytes()
                        fact.update(reused_fixture_bytes=len(data), reused_fixture_sha256=hashlib.sha256(data).hexdigest(),
                                    late_synthetic_write=data == b"{}")
                        fact["reused_fixture_after"] = {"native_identity": tool.file_identity(path.stat()),
                                                        "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                for _, row in launched:
                    self.assertTrue(row["closed"])
                    self.assertEqual(row["active_processes_before_close"], 0)
                    self.assertIsNotNone(row["exit_status"])
                fact["worker_exited_empty_and_closed"] = True
        finally:
            gate.set()
            for thread in started_threads:
                thread.join(5)
            for fd, path in opened_files:
                try:
                    os.close(fd)
                except OSError:
                    # A late sender may already have closed its old number,
                    # now the reviewer fixture's descriptor. No other FD is
                    # acquired or closed while this exact set is recovered.
                    pass
            fact["all_owned_senders_joined_after_recovery"] = all(not thread.is_alive() for thread in started_threads)
            retired = []
            for fd, path in opened_files:
                try:
                    os.fstat(fd)
                    retired.append(False)
                except OSError:
                    retired.append(True)
            fact["all_own_fixture_descriptors_retired"] = all(retired)
            fact["finished_at"] = now()
            FACTS.append(fact)
        self.assertFalse(fact["sender_alive_at_parent_exception"] and
                         not fact["sender_descriptor_open_at_parent_exception"] and
                         fact["returned_thread_count"] == 0,
                         "Live started pipe sender lost descriptor custody before parent control exception returned")
        self.assertFalse(fact.get("late_synthetic_write", False),
                         "Unretired sender wrote to a reviewer file that reused its closed descriptor")

    def test_keyboard_interrupt_after_real_sender_start_preserves_exact_custody(self):
        self.schedule(KeyboardInterrupt("explicit post-start interruption"))

    def test_system_exit_after_real_sender_start_preserves_exact_custody(self):
        self.schedule(SystemExit(17))
