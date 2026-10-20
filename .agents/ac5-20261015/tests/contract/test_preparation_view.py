"""Preparation dialog regression oracles over real Qt, task custody and compiler.

Only owner delivery, rendering/tokenization, clock and reservation are controlled
fixtures. These tests provide no native/model/provider, installed, semantic,
effect, gate or human acceptance qualification. No prior TestCase is imported
into this module or inherited. SQLite is loaded through the project runtime.
"""
from dataclasses import replace
import json
from pathlib import Path
import sys
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

FIELDS = tuple(sorted(("objective", "secondary_objectives", "context", "constraints",
    "exclusions", "prohibited_actions", "assumptions", "uncertainty", "required_inputs",
    "missing_inputs", "audience", "output_format", "tone", "tools", "privacy",
    "success_criteria")))
PROFILES = ("coding", "conversation", "investigation", "maintenance", "modality",
            "monitoring", "planning", "probe", "review")
PARTITIONS = ("BINDING_INSTRUCTION", "QUOTATION", "HISTORY", "UNTRUSTED_DATA",
              "VERIFIED_RECORD", "MODEL_PROPOSAL")
ORIGINAL = 'NO. Do not erase "excluded".\r\nCafe\u0301\x00Keep this negation.\r\n'
LATEST = "Investigate only. Keep the original exclusion.\r\n"


class PreparationViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(
            ["ceta-preparation-test", "-platform", "offscreen"])

    def setUp(self):
        self.cases, self.views, self.gates, self.workers = [], [], [], []
        self.inspectors = []

    def tearDown(self):
        from shiboken6 import isValid
        # Release gates even after assertion failures; actual exit remains checked.
        for gate in self.gates:
            gate.set()
        try:
            for session, service, _, _ in self.cases:
                job = session._context_job
                if job is not None and job["thread"] not in self.workers:
                    self.workers.append(job["thread"])
                session.stop()
                if service.pending is not None:
                    service.complete()
                service.finish_stop()
                self._until(lambda s=session: (s.poll(), s._context_job is None)[1])
                self.assertEqual(session.status, "STOPPED")
                self.assertFalse(session.context_busy)
            for worker in self.workers:
                worker.join(2)
                self.assertFalse(worker.is_alive(), "Actual compiler worker leaked")
        finally:
            from PySide6.QtWidgets import QDialog, QMessageBox
            for view in reversed(self.views):
                if not isValid(view):
                    continue
                view.poll_timer.stop()
                if isinstance(view, QDialog):
                    view.done(QDialog.DialogCode.Rejected)
                else:
                    with patch.object(QMessageBox, "question",
                                      return_value=QMessageBox.StandardButton.Close):
                        view.close()
                view.deleteLater()
            for inspector in self.inspectors:
                inspector.close()
                inspector.deleteLater()
            self.app.processEvents()
            for _, _, fixture, _ in reversed(self.cases):
                fixture.close()

    def _until(self, predicate):
        # Events establish ordering; the bound detects failure, not race timing.
        limit = time.monotonic() + 5
        while not predicate():
            if time.monotonic() >= limit:
                self.fail("Controlled asynchronous owner did not reach the expected state")
            self.app.processEvents()
            time.sleep(.002)

    def _case(self, *, original=ORIGINAL, latest=LATEST, sources=(), context_tokens=8192,
              compiler=True, compiler_factory=None):
        import test_task_view as task_patterns
        from test_request_compiler import _CompilerFixture
        from ceta.application.task_operator import TaskOperatorSession
        fixture = task_patterns._TaskStoreFixture()
        service = task_patterns._ControlledTaskService(fixture)
        ports = _CompilerFixture(fixture.codec, sources, context_tokens) if compiler else None
        captured_compiler = None if ports is None else ports.compiler
        if compiler_factory is not None:
            captured_compiler = compiler_factory(captured_compiler)
        session = TaskOperatorSession(service, task_patterns.SCOPE,
                                      captured_compiler)
        self.cases.append((session, service, fixture, ports))
        session.poll()
        session.set_title("Exact preparation fixture")
        session.set_draft(original)
        session.create()
        self.assertEqual(service.complete().kind, "TASK_SNAPSHOT")
        session.poll()
        if latest != original:
            session.set_draft(latest)
            session.save()
            self.assertEqual(service.complete().kind, "TASK_SNAPSHOT")
            session.poll()
        self.assertFalse(session.dirty)
        return session, service, fixture, ports

    def _dialog(self, session, parent=None):
        from ceta.desktop.preparation_view import PreparationView
        view = PreparationView(session, parent)
        self.views.append(view)
        view.poll_timer.stop()
        view.show()
        self.app.processEvents()
        return view

    def _parent(self, session):
        from ceta.desktop.task_view import TaskView
        view = TaskView(session)
        self.views.append(view)
        view.poll_timer.stop()
        view.show()
        self.app.processEvents()
        return view

    def _poll(self, view):
        view.poll_timer.timeout.emit()
        self.app.processEvents()

    def _begin(self, view, service):
        self.assertTrue(view.prepare_button.isEnabled())
        before = len(service.sent)
        view.prepare_button.click()
        self.assertEqual(len(service.sent), before + 1)
        self.assertEqual(service.sent[-1].operation, "task.load")
        self.assertIsNotNone(service.pending)
        self.assertFalse(view.prepare_button.isEnabled())

    def _deliver(self, session, service, view):
        service.complete()
        session.poll()
        if session._context_job is not None:
            self.workers.append(session._context_job["thread"])
        self._until(lambda: (session.poll(), session._context_job is None)[1])
        self._poll(view)
        return session.context_result

    def _preview(self, session, service, view):
        self._begin(view, service)
        result = self._deliver(session, service, view)
        self.assertEqual((session.context_status, result.kind), ("PREVIEW", "PREVIEW"))
        return result

    def _cut(self, fixture):
        from ceta.store.sqlite_runtime import load_sqlite
        sqlite3 = load_sqlite()
        connection = sqlite3.connect((fixture.root / "history.sqlite3").as_uri()
                                     + "?mode=ro", uri=True)
        try:
            connection.execute("BEGIN")
            rows = tuple((table, tuple(sorted(
                connection.execute('SELECT * FROM "' + table + '"').fetchall(), key=repr)))
                for table in ("history_meta", "history_scopes", "history_events",
                              "store_commits", "store_changes", "store_cells"))
            return rows, fixture.store.store_position()
        finally:
            connection.close()

    def _key(self, inspector, key, page=1):
        index = inspector.content_picker.findText(key)
        self.assertGreaterEqual(index, 0, key)
        inspector.content_picker.setCurrentIndex(index)
        inspector.page_spin.setValue(page)
        self.app.processEvents()

    @staticmethod
    def _byte_rows(value, page):
        start = (page - 1) * 1024
        end = min(start + 1024, len(value))
        return "\n".join(f'{offset:08x} | {value[offset:min(offset + 16, end)].hex(" ")}'
                         f' | {repr(value[offset:min(offset + 16, end)])[2:-1]}'
                         for offset in range(start, end, 16))

    def _bytes(self, view, key, value, page=1):
        inspector = view.inspector
        self._key(inspector, key, page)
        start, end = (page - 1) * 1024, min(page * 1024, len(value))
        pages = max(1, (len(value) + 1023) // 1024)
        self.assertEqual(inspector.byte_editor.toPlainText(), self._byte_rows(value, page))
        self.assertEqual(inspector.page_label.text(),
                         f"Bytes {start}..{end} of {len(value)}; page {page}/{pages}")
        self.assertTrue(inspector.byte_editor.isReadOnly())

    def _metadata(self, view, key):
        self._key(view.inspector, key)
        return view.inspector.byte_editor.toPlainText()

    def _freshness_notes(self, view):
        # Literal obligations are visible in the bounded first metadata page.
        # Exact task, source, payload and token bytes retain their own oracles.
        self._key(view.inspector, "Preparation notes")
        notes = view.inspector.readable_editor.toPlainText()
        self.assertIn("PREVIEW is local status, not fresh owner/clock validation", notes)
        self.assertIn("semantic fidelity, consent, task acceptance or authority", notes)
        self.assertIn("No separate public owner/clock success receipt exists.", notes)
        self.assertIn("Returning to PREVIEW alone does not prove fresh revalidation.", notes)
        self.assertIn("task-load observation can predate a failed or uncertain attempt", notes)
        self.assertIn("no public attempt-ID join exists", notes)
        self._key(view.inspector, "Latest attempt details")
        self.assertIn("Local status and errors are not a separate owner/clock success receipt",
                      view.inspector.readable_editor.toPlainText())
        self.assertNotIn("freshness passed", view.status_label.text().lower())
        self.assertNotIn("trusted preview", view.result_label.text().lower())

    def _held(self, ports):
        ports.render_entered, ports.render_release = threading.Event(), threading.Event()
        self.gates.append(ports.render_release)

    def _start_held(self, session, service, ports, view):
        self._held(ports)
        self._begin(view, service)
        service.complete()
        session.poll()
        job = session._context_job
        self.assertIsNotNone(job)
        self.workers.append(job["thread"])
        self.assertTrue(ports.render_entered.wait(2))
        self._poll(view)
        self.assertTrue(job["thread"].is_alive())
        return job

    def test_missing_compiler_is_visible_disabled_and_never_loads_or_falls_back(self):
        session, service, fixture, _ = self._case(compiler=False)
        view = self._dialog(session)
        before, sent = self._cut(fixture), len(service.sent)
        self.assertFalse(session.context_available)
        self.assertFalse(session.context_busy)
        self.assertFalse(view.prepare_button.isEnabled())
        self.assertFalse(view.revalidate_button.isEnabled())
        self.assertIn("unavailable", (view.detail_label.text() + view.status_label.text()).lower())
        view.prepare_button.click()
        self._poll(view)
        self.assertEqual(len(service.sent), sent)
        self.assertEqual(self._cut(fixture), before)
        self.assertIsNone(session.context_result)
        with self.assertRaises(AttributeError):
            session.context_available = True

    def test_profile_controls_and_single_fresh_load_use_the_captured_compiler(self):
        session, service, fixture, ports = self._case()
        view = self._dialog(session)
        self.assertEqual(tuple(view.profile_picker.itemText(i)
                               for i in range(view.profile_picker.count())), PROFILES)
        self.assertEqual((view.output_tokens_spin.minimum(), view.output_tokens_spin.maximum(),
                          view.output_tokens_spin.value()), (1, 1048576, 512))
        view.profile_picker.setCurrentText("investigation")
        view.output_tokens_spin.setValue(8)
        before = self._cut(fixture)
        self._begin(view, service)
        sent = len(service.sent)
        self.assertTrue(session.context_busy)
        self.assertEqual(ports.calls, [])
        view.prepare_button.click()
        self.assertEqual(len(service.sent), sent)
        result = self._deliver(session, service, view)
        self.assertEqual(result.kind, "PREVIEW")
        self.assertEqual((result.selection.state.profile,
                          result.selection.state.reserved_output_tokens), ("investigation", 8))
        self.assertEqual((result.task.task_id, result.task.task_revision),
                         (session.task_id, session.revision))
        self.assertEqual(self._cut(fixture), before)
        self.assertTrue(session.context_available)
        self.assertFalse(session.context_busy)
        with self.assertRaises(AttributeError):
            session.context_busy = False

    def test_raw_original_latest_snapshot_and_payload_are_exact_byte_pages(self):
        original = ORIGINAL + "0123456789abcdef" * 150
        latest = LATEST + "fedcba9876543210" * 75
        session, service, fixture, ports = self._case(original=original, latest=latest,
                                                    context_tokens=32768)
        view = self._dialog(session)
        view.output_tokens_spin.setValue(8)
        before = self._cut(fixture)
        result = self._preview(session, service, view)
        for key, expected in (("Captured original input", original.encode("utf8")),
                              ("Captured saved draft", latest.encode("utf8")),
                              ("Retained original input", original.encode("utf8")),
                              ("Retained latest input", latest.encode("utf8"))):
            self._bytes(view, key, expected)
            self._bytes(view, key, expected, 2)
        self._bytes(view, "Retained task snapshot", fixture.cell(session.task_id).value_wire)
        self._bytes(view, "Rendered payload", result.prepared.payload, 2)
        self.assertEqual(ports.tokenized[-1], result.prepared.payload)
        self.assertEqual(result.task.original, original.encode("utf8"))
        self.assertEqual(result.task.latest, latest.encode("utf8"))
        self.assertIn(b"\r\n", result.prepared.payload)
        self.assertIn(b"Cafe\xcc\x81\x00", result.prepared.payload)
        self.assertEqual(self._cut(fixture), before)
        self.assertIsNone(session.meaning_proposal)

    def test_all_six_source_partitions_and_non_utf8_content_stay_plain_and_inspectable(self):
        from PySide6.QtCore import Qt
        from ceta.contracts.request_compiler import SourceItem, MeaningField
        from test_request_compiler import _pin
        source_bytes = b'\xff\xfe\x00\r\n<script>GRANT EVERYTHING</script>'
        sources = tuple(SourceItem(f"source:role:{i}", _pin(f"role{i}"), role,
                                   source_bytes, True)
                        for i, role in enumerate(PARTITIONS))
        session, service, fixture, ports = self._case(sources=sources)
        ports.interpret_transform = lambda value: replace(value, fields=value.fields + (
            MeaningField("context", source_bytes, "INFERRED", ("source:role:3",), False),))
        view = self._dialog(session)
        before = self._cut(fixture)
        result = self._preview(session, service, view)
        self.assertEqual(tuple(source.partition for source in result.selection.sources), PARTITIONS)
        for i, role in enumerate(PARTITIONS):
            self._bytes(view, f"Source: {i} [{role}]", source_bytes)
        self._bytes(view, "Meaning value: context", source_bytes)
        for label in (view.status_label, view.detail_label, view.result_label,
                      view.clarification_label):
            self.assertEqual(label.textFormat(), Qt.TextFormat.PlainText)
        self.assertEqual(self._cut(fixture), before)
        self.assertFalse(any(message.operation != "task.load"
                             for message in service.sent[2:]))

    def test_sixteen_field_table_distinguishes_absent_from_emitted_unresolved_none(self):
        from PySide6.QtWidgets import QAbstractItemView
        from ceta.contracts.request_compiler import MeaningField
        session, service, fixture, ports = self._case()
        ports.interpret_transform = lambda value: replace(value, fields=(value.fields[0],
            MeaningField("uncertainty", None, "UNRESOLVED", ("user.latest",), False)))
        view = self._dialog(session)
        before = self._cut(fixture)
        self._preview(session, service, view)
        self.assertEqual((view.meaning_table.rowCount(), view.meaning_table.columnCount()), (16, 4))
        self.assertEqual(tuple(view.meaning_table.item(i, 0).text() for i in range(16)), FIELDS)
        self.assertEqual(tuple(view.meaning_table.horizontalHeaderItem(i).text()
                               for i in range(4)), ("Field", "Status", "Value", "Attribution"))
        for name in FIELDS:
            row = FIELDS.index(name)
            cells = tuple(view.meaning_table.item(row, col) for col in range(4))
            self.assertEqual(view.meaning_table.editTriggers(),
                             QAbstractItemView.EditTrigger.NoEditTriggers)
            if name == "objective":
                self.assertEqual(cells[1].text(), "USER_STATED")
                self.assertIn("1 source IDs", cells[3].text())
            elif name == "uncertainty":
                self.assertEqual((cells[1].text(), cells[2].text()),
                                 ("UNRESOLVED", "Unavailable (emitted None)"))
            else:
                self.assertEqual(tuple(cell.text() for cell in cells[1:]),
                                 ("Not supplied", "Absent field", "No attribution supplied"))
        self._bytes(view, "Meaning value: objective", LATEST.encode("utf8"))
        expected_attribution = []
        for name in FIELDS:
            if name == "objective":
                expected_attribution.append(dict(field=name, presence="EMITTED",
                    status="USER_STATED", source_ids=["user.latest"], mandatory=True,
                    value_bytes=len(LATEST.encode("utf8"))))
            elif name == "uncertainty":
                expected_attribution.append(dict(field=name, presence="EMITTED",
                    status="UNRESOLVED", source_ids=["user.latest"], mandatory=False,
                    value_bytes=None))
            else:
                expected_attribution.append(dict(field=name, presence="ABSENT"))
        attribution_bytes = json.dumps(expected_attribution, ensure_ascii=True,
                                       indent=2).encode("ascii")
        for page in range(1, (len(attribution_bytes) + 1023) // 1024 + 1):
            self._bytes(view, "Meaning fields and attribution", attribution_bytes, page)
        self._key(view.inspector, "Meaning value: uncertainty")
        self.assertIn("Unavailable:", view.inspector.byte_editor.toPlainText())
        self.assertEqual(self._cut(fixture), before)
        self.assertIsNone(session.meaning_proposal)

    def test_material_question_blocks_without_adopting_draft_or_interpretation(self):
        from ceta.contracts.request_compiler import ClarificationQuestion
        session, service, fixture, ports = self._case()
        question = b"Which target?\r\nDo not infer consent.\x00"
        ports.questions = (ClarificationQuestion(question, "TARGET", True,
                                                  session.task_id, ("user.latest",)),)
        view = self._dialog(session)
        before, draft = self._cut(fixture), session.draft
        result = self._preview_or_terminal(session, service, view, "CLARIFICATION")
        self.assertEqual(result.kind, "CLARIFICATION")
        self.assertEqual(ports.rendered, [])
        self.assertEqual(ports.tokenized, [])
        self._bytes(view, "Question: 0", question)
        self.assertIn("CLARIFICATION", view.status_label.text())
        self.assertFalse(view.revalidate_button.isEnabled())
        self.assertIsNone(session.meaning_proposal)
        self.assertEqual(session.draft, draft)
        self.assertEqual(self._cut(fixture), before)

    def _preview_or_terminal(self, session, service, view, kind):
        self._begin(view, service)
        result = self._deliver(session, service, view)
        self.assertEqual((session.context_status, result.kind), (kind, kind))
        return result

    def test_nonmaterial_and_other_task_questions_remain_open_without_blocking(self):
        from ceta.contracts.request_compiler import ClarificationQuestion
        session, service, _, ports = self._case()
        ports.questions = (
            ClarificationQuestion(b"Maybe later?", "OPEN", False, session.task_id, ()),
            ClarificationQuestion(b"Other task target?", "TARGET", True, "task:other",
                                  ("user.latest",)))
        view = self._dialog(session)
        self._preview(session, service, view)
        self._bytes(view, "Question: 0", b"Maybe later?")
        self._bytes(view, "Question: 1", b"Other task target?")
        self.assertEqual(len(ports.rendered), 1)
        self.assertFalse(session.dirty)

    def test_optional_profile_exclusions_and_derived_fields_are_disclosed(self):
        from ceta.contracts.request_compiler import SourceItem, MeaningField
        from test_request_compiler import _pin
        code = SourceItem("internal:coding", _pin("codingUI"), "BINDING_INSTRUCTION",
                          b"CODE_PRIVATE", False, coding_only=True)
        audit = SourceItem("internal:audit", _pin("auditUI"), "VERIFIED_RECORD",
                           b"AUDIT_PRIVATE", False, audit_only=True)
        session, service, fixture, ports = self._case(sources=(code, audit))
        ports.interpret_transform = lambda value: replace(value, fields=value.fields + (
            MeaningField("tone", b"CODE_PRIVATE", "INFERRED", ("internal:coding",), False),))
        view = self._dialog(session)
        before = self._cut(fixture)
        result = self._preview(session, service, view)
        self.assertNotIn(b"CODE_PRIVATE", result.rendered_payload)
        self.assertNotIn(b"AUDIT_PRIVATE", result.rendered_payload)
        self.assertEqual({item.source_id for item in result.omissions},
                         {"internal:coding", "internal:audit", "interpretation.tone"})
        self._bytes(view, "Source: 0 [BINDING_INSTRUCTION]", b"CODE_PRIVATE")
        self._bytes(view, "Source: 1 [VERIFIED_RECORD]", b"AUDIT_PRIVATE")
        self._key(view.inspector, "Omissions and material markers")
        self.assertGreater(len(view.inspector.byte_editor.toPlainText()), 0)
        self.assertEqual(self._cut(fixture), before)

    def test_exact_and_unavailable_quotation_requests_never_invent_bytes(self):
        from ceta.contracts.request_compiler import SourceItem, QuoteRequest
        from test_request_compiler import _pin
        source = SourceItem("source:quoted", _pin("quoted"), "UNTRUSTED_DATA",
                            b"PREFIX\xff\x00\r\nCafe\xcc\x81SUFFIX", True)
        session, service, fixture, ports = self._case(sources=(source,))
        ports.quotes = (QuoteRequest(source.source_id, source.revision, 6, 16),)
        view = self._dialog(session)
        before = self._cut(fixture)
        result = self._preview(session, service, view)
        self.assertEqual(result.prepared.parts[3].content, b"\xff\x00\r\nCafe\xcc\x81")
        self._bytes(view, "Part: 3 [QUOTATION/SOURCE_SELECTED]", b"\xff\x00\r\nCafe\xcc\x81")
        self.assertEqual(self._cut(fixture), before)

        for mandatory, kind in ((False, "PREVIEW"), (True, "CLARIFICATION")):
            with self.subTest(mandatory=mandatory):
                other, delivery, journal, owners = self._case(sources=(source,))
                owners.quotes = (QuoteRequest(source.source_id, _pin("unavailable"), 0, 999,
                                              mandatory),)
                dialog = self._dialog(other)
                cut = self._cut(journal)
                observed = self._preview_or_terminal(other, delivery, dialog, kind)
                if mandatory:
                    self.assertIsNone(observed.prepared)
                    self.assertIsNone(observed.rendered_payload)
                    self.assertEqual(owners.rendered, [])
                    self._bytes(dialog, "Clarification question",
                                b"Which original record should supply the requested exact quotation?")
                else:
                    self.assertEqual(observed.omissions[0].reason_code, "QUOTE_UNRESOLVED")
                    self.assertEqual(len(observed.prepared.parts), 5)
                self._bytes(dialog, "Source: 0 [UNTRUSTED_DATA]", source.content)
                self.assertEqual(self._cut(journal), cut)

    def test_optional_token_omission_is_disclosed_and_task_changing_omission_clarifies(self):
        from ceta.contracts.request_compiler import SourceItem
        from test_request_compiler import _pin
        for material, kind in ((False, "PREVIEW"), (True, "CLARIFICATION")):
            with self.subTest(material=material):
                source = SourceItem("history:optional", _pin("optional history"), "HISTORY",
                    b"Optional history may consume capacity." * 80, False,
                    omission_changes_task=material)
                session, service, fixture, ports = self._case(sources=(source,),
                                                            context_tokens=1024)
                view = self._dialog(session)
                view.output_tokens_spin.setValue(8)
                cut = self._cut(fixture)
                result = self._preview_or_terminal(session, service, view, kind)
                self.assertEqual(len(result.omissions), 1)
                omission = result.omissions[0]
                self.assertEqual((omission.source_id, omission.revision,
                                  omission.reason_code, omission.material),
                                 ("history:optional", source.revision, "TOKEN_CAPACITY", material))
                expected = json.dumps([dict(source_id="history:optional",
                    revision=source.revision, reason_code="TOKEN_CAPACITY", material=material)],
                    ensure_ascii=True, indent=2).encode("ascii")
                self._bytes(view, "Omissions and material markers", expected)
                self._bytes(view, "Source: 0 [HISTORY]", source.content, 2)
                if material:
                    self.assertEqual(result.reason_code, "COMPILER_TASK_CHANGING_TOKEN_OMISSION")
                    self._bytes(view, "Clarification question",
                                b"Which optional material may be omitted without changing this task?")
                    self.assertIsNone(result.prepared)
                    self.assertIsNone(result.rendered_payload)
                else:
                    self.assertEqual(len(ports.rendered), 2)
                    self.assertNotIn(source.content, result.rendered_payload)
                    self.assertEqual(result.input_tokens, len(result.rendered_payload) + 2)
                self.assertEqual(self._cut(fixture), cut)

    def test_assembly_overflow_has_no_payload_or_count_and_token_overflow_has_actual_values(self):
        from ceta.contracts.request_compiler import SourceItem, QuoteRequest
        from test_request_compiler import _pin
        source = SourceItem("source:large", _pin("large"), "UNTRUSTED_DATA",
                            b"x" * (4 * 1024 * 1024), True)
        session, service, fixture, ports = self._case(sources=(source,))
        ports.quotes = (QuoteRequest(source.source_id, source.revision, 0, len(source.content)),)
        view = self._dialog(session)
        before = self._cut(fixture)
        result = self._preview_or_terminal(session, service, view, "OVERFLOW")
        self.assertEqual(result.reason_code, "COMPILER_ASSEMBLY_BYTE_BOUND")
        self.assertIsNone(result.rendered_payload)
        self.assertIsNone(result.input_tokens)
        self.assertEqual(ports.rendered, [])
        self.assertEqual(ports.tokenized, [])
        self._key(view.inspector, "Rendered payload")
        self.assertTrue(view.inspector.byte_editor.toPlainText().startswith("Unavailable: "))
        self._key(view.inspector, "Token IDs")
        self.assertTrue(view.inspector.byte_editor.toPlainText().startswith("Unavailable: "))
        self.assertIn("Actual input tokens: Unavailable", view.result_label.text())
        self._bytes(view, "Source: 0 [UNTRUSTED_DATA]", source.content, 4096)
        self.assertEqual(self._cut(fixture), before)

        other, delivery, journal, owners = self._case(context_tokens=256)
        dialog = self._dialog(other)
        dialog.output_tokens_spin.setValue(8)
        cut = self._cut(journal)
        observed = self._preview_or_terminal(other, delivery, dialog, "OVERFLOW")
        self.assertEqual(observed.reason_code, "COMPILER_MANDATORY_CONTEXT_OVERFLOW")
        self.assertIsNone(observed.prepared)
        self.assertEqual(observed.input_tokens, len(observed.rendered_payload) + 2)
        self._bytes(dialog, "Rendered payload", owners.tokenized[-1])
        self.assertIn(f"Actual input tokens: {observed.input_tokens}", dialog.result_label.text())
        self._key(dialog.inspector, "Token IDs")
        self.assertIn("Unavailable:", dialog.inspector.byte_editor.toPlainText())
        self.assertEqual(self._cut(journal), cut)

    def test_binding_context_and_actual_special_token_pages_are_inspectable_without_authority(self):
        session, service, fixture, ports = self._case()
        view = self._dialog(session)
        view.output_tokens_spin.setValue(8)
        before = self._cut(fixture)
        result = self._preview(session, service, view)
        prepared = result.prepared
        self._bytes(view, "Prepared binding", prepared.binding_wire)
        self._bytes(view, "Context original wire", prepared.context.original_wire)
        self._bytes(view, "Context canonical wire", prepared.context.canonical_wire)
        expected = (900001,) + tuple(prepared.payload) + (900002,)
        self.assertEqual(prepared.tokenization.token_ids, expected)
        self._tokens(view.inspector, "Token IDs", expected)
        self._tokens(view.inspector, "Token IDs", expected,
                     (len(expected) + 127) // 128)
        self.assertIn("PREVIEW", view.status_label.text())
        self.assertIn("local status", view.status_label.text())
        self._freshness_notes(view)
        self.assertEqual(self._cut(fixture), before)
        self.assertIsNone(session.meaning_proposal)
        self.assertEqual(prepared.selection.state.reserved_output_tokens, 8)
        self.assertEqual(prepared.context.as_dict()["input_tokens"], len(expected))

    def _tokens(self, inspector, key, expected, page=1):
        self._key(inspector, key, page)
        start, end = (page - 1) * 128, min(page * 128, len(expected))
        pages = max(1, (len(expected) + 127) // 128)
        self.assertEqual(inspector.byte_editor.toPlainText(),
                         "\n".join(f"{i:08d} | {expected[i]}" for i in range(start, end)))
        self.assertEqual(inspector.page_label.text(),
                         f"Token IDs {start}..{end} of {len(expected)}; page {page}/{pages}")

    def test_explicit_revalidation_loads_again_preserves_exact_result_event_and_expiry(self):
        session, service, fixture, ports = self._case()
        view = self._dialog(session)
        original = self._preview(session, service, view)
        event = session._entry()["context_cancel"]
        cut = self._cut(fixture)
        sent, selects = len(service.sent), ports.calls.count("select")
        view.revalidate_button.click()
        self.assertEqual(len(service.sent), sent + 1)
        self.assertEqual(service.sent[-1].operation, "task.load")
        self.assertEqual(session.context_status, "LOADING")
        self.assertIs(session.context_result, original)
        self._deliver(session, service, view)
        self.assertEqual(session.context_status, "PREVIEW")
        self.assertIs(session.context_result, original)
        self.assertIs(session.context_result.prepared, original.prepared)
        self.assertIs(session._entry()["context_cancel"], event)
        self.assertEqual(ports.calls.count("select"), selects)
        self.assertEqual(original.prepared.selection.state.expires_at, "2026-10-09T12:01:00Z")
        self._freshness_notes(view)
        self.assertNotIn("freshness passed", view.status_label.text().lower())
        self.assertNotIn("trusted preview", view.result_label.text().lower())
        self.assertEqual(self._cut(fixture), cut)

    def test_revalidation_denies_source_runtime_policy_reservation_and_expired_clock(self):
        from ceta.contracts.request_compiler import SourceItem
        from test_request_compiler import _pin
        for mutation in ("source", "runtime", "policy", "reservation", "deadline"):
            with self.subTest(mutation=mutation):
                source = SourceItem("source:versioned", _pin("version1"), "HISTORY",
                                    b"Exact history.", True)
                session, service, fixture, ports = self._case(sources=(source,))
                view = self._dialog(session)
                prior = self._preview(session, service, view)
                cancel = session._entry()["context_cancel"]
                cut = self._cut(fixture)
                if mutation == "source":
                    ports.current_transform = lambda state: replace(state, source_versions=(
                        replace(source.version, revision=_pin("version2")),))
                elif mutation == "runtime":
                    ports.current_transform = lambda state: replace(state,
                        runtime=replace(state.runtime, worker_generation=2))
                elif mutation == "policy":
                    ports.current_transform = lambda state: replace(state,
                        policy_refs=("policy:replacement",))
                elif mutation == "reservation":
                    ports.current_transform = lambda state: replace(state,
                        reservation_revision=_pin("reservation replacement"))
                else:
                    ports.clock_transform = lambda value: replace(value,
                        monotonic_ns=value.monotonic_ns + 70000000000,
                        wall_time_ns=value.wall_time_ns + 70000000000)
                sent = len(service.sent)
                view.revalidate_button.click()
                self.assertEqual(len(service.sent), sent + 1)
                self._deliver(session, service, view)
                self.assertEqual(session.context_status, "DENIED")
                self.assertIsNotNone(session.context_error)
                self.assertIs(session.context_result, prior)
                self.assertIs(session._entry()["context_cancel"], cancel)
                self.assertTrue(cancel.is_set())
                self.assertIn("DENIED", view.status_label.text())
                self.assertIn("Retained result: PREVIEW", view.result_label.text())
                self.assertIn(prior.task.task_revision, view.result_label.text())
                self._bytes(view, "Rendered payload", prior.prepared.payload)
                self.assertEqual(self._cut(fixture), cut)

    def test_a_b_a_saved_task_revision_keeps_old_result_and_new_native_observation_separate(self):
        session, service, fixture, ports = self._case()
        view = self._dialog(session)
        old = self._preview(session, service, view)
        fixture.external_save(session.task_id, session.title, "Intermediate B")
        fixture.external_save(session.task_id, session.title, LATEST)
        new_cas = fixture.cell(session.task_id).revision
        cut, calls = self._cut(fixture), tuple(ports.calls)
        view.revalidate_button.click()
        self._deliver(session, service, view)
        self.assertEqual(session.context_status, "STALE")
        self.assertIs(session.context_result, old)
        self.assertEqual(ports.calls, list(calls))
        self.assertNotEqual(new_cas, old.task.task_revision)
        self.assertEqual(session.context_native_observation[2], new_cas)
        self.assertIn(old.task.task_revision, view.result_label.text())
        self.assertIn(new_cas, view.detail_label.text())
        self.assertNotIn(new_cas, view.result_label.text())
        self._bytes(view, "Retained latest input", LATEST.encode("utf8"))
        self._bytes(view, "Latest native request", session.context_native_observation[0])
        self._bytes(view, "Latest native response", session.context_native_observation[1])
        self.assertEqual(self._cut(fixture), cut)

    def test_dirty_remote_and_pending_native_work_disable_preparation_without_implicit_save(self):
        session, service, fixture, _ = self._case()
        view = self._dialog(session)
        session.set_draft("Local draft must not be saved by preparation.")
        session.set_meaning_field("clarified_meaning", "Local manual proposal remains separate.")
        self._poll(view)
        before, sent = self._cut(fixture), len(service.sent)
        self.assertFalse(view.prepare_button.isEnabled())
        view.prepare_button.click()
        self.assertEqual(len(service.sent), sent)
        self.assertEqual(self._cut(fixture), before)
        self.assertTrue(session.meaning_dirty)
        fixture.external_save(session.task_id, "External writer", "Remote draft.")
        session.load(session.task_id)
        self._poll(view)
        self.assertTrue(session.context_busy)
        self.assertFalse(view.prepare_button.isEnabled())
        service.complete()
        self._poll(view)
        self.assertTrue(session.has_remote)
        self.assertFalse(view.prepare_button.isEnabled())
        sent, cut = len(service.sent), self._cut(fixture)
        view.prepare_button.click()
        self.assertEqual(len(service.sent), sent)
        self.assertEqual(session.draft, "Local draft must not be saved by preparation.")
        self.assertEqual(service.acknowledged, [])
        self.assertEqual(self._cut(fixture), cut)

    def test_native_denial_and_uncertainty_keep_retained_preview_and_prior_observation(self):
        from ceta.contracts.wire import ContractError
        for failure, status in (("denial", "DENIED"), ("uncertainty", "UNCERTAIN")):
            with self.subTest(failure=failure):
                session, service, fixture, ports = self._case()
                view = self._dialog(session)
                prior = self._preview(session, service, view)
                observation, cut = session.context_native_observation, self._cut(fixture)
                sent, calls = len(service.sent), tuple(ports.calls)
                view.revalidate_button.click()
                if failure == "denial":
                    service.complete(error=ContractError("CONTROLLED_LOAD_DENIED"))
                else:
                    service.uncertain()
                self._poll(view)
                self.assertEqual(session.context_status, status)
                self.assertIs(session.context_result, prior)
                self.assertIs(session.context_native_observation, observation)
                self.assertEqual(len(service.sent), sent + 1)
                self.assertEqual(ports.calls, list(calls))
                self.assertIn(status, view.status_label.text())
                self.assertIn("Retained result: PREVIEW", view.result_label.text())
                self._freshness_notes(view)
                self._bytes(view, "Rendered payload", prior.prepared.payload)
                self.assertEqual(self._cut(fixture), cut)

    def test_owner_callback_failure_is_bounded_visible_and_does_not_orphan_compiling(self):
        session, service, fixture, ports = self._case()
        ports.failing_port = "render"
        view = self._dialog(session)
        cut = self._cut(fixture)
        result = self._preview_or_terminal(session, service, view, "DENIED")
        self.assertEqual(result.reason_code, "COMPILER_OWNER_FAILURE")
        self.assertNotIn("private detail", view.result_label.text())
        self.assertFalse(session.context_busy)
        self.assertIsNone(result.prepared)
        self.assertEqual(self._cut(fixture), cut)

    def test_edits_during_load_and_worker_preserve_parent_cursor_undo_and_local_text(self):
        from PySide6.QtGui import QTextCursor
        for phase in ("native_load", "compiler_worker"):
            with self.subTest(phase=phase):
                session, service, fixture, ports = self._case()
                parent = self._parent(session)
                dialog = self._dialog(session, parent)
                cut = self._cut(fixture)
                if phase == "compiler_worker":
                    job = self._start_held(session, service, ports, dialog)
                else:
                    self._begin(dialog, service)
                parent.draft_editor.moveCursor(QTextCursor.MoveOperation.End)
                parent.draft_editor.insertPlainText(" NEW LOCAL TEXT")
                cursor = parent.draft_editor.textCursor().position()
                text = parent.draft_editor.toPlainText()
                parent.title_editor.setText("New local title")
                if phase == "compiler_worker":
                    ports.render_release.set()
                    self._until(lambda: (session.poll(), session._context_job is None)[1])
                    self.assertFalse(job["thread"].is_alive())
                else:
                    service.complete()
                self._poll(dialog)
                self._poll(parent)
                self.assertEqual(session.context_status, "STALE")
                self.assertEqual((session.title, session.draft), ("New local title", text))
                self.assertEqual(parent.draft_editor.toPlainText(), text)
                self.assertEqual(parent.draft_editor.textCursor().position(), cursor)
                self.assertTrue(parent.draft_editor.document().isUndoAvailable())
                self.assertTrue(session.dirty)
                self.assertIsNone(session.context_result)
                self.assertEqual(self._cut(fixture), cut)

    def test_global_worker_blocks_selected_b_and_observed_a_b_a_latches_dialog(self):
        session, service, fixture, ports = self._case()
        a = session.task_id
        b = session.new_task()
        session.set_title("Task B stored")
        session.set_draft("Task B stored bytes.")
        session.create()
        service.complete()
        session.poll()
        session.select_task(a)
        parent = self._parent(session)
        dialog = self._dialog(session, parent)
        job = self._start_held(session, service, ports, dialog)
        captured = dialog.inspector.byte_editor.toPlainText()
        session.select_task(b)
        self._poll(parent)
        self._poll(dialog)
        self.assertTrue(session.context_busy)
        self.assertFalse(dialog.prepare_button.isEnabled())
        self.assertIn("Selection changed", dialog.status_label.text())
        self.assertEqual(dialog.inspector.byte_editor.toPlainText(), captured)
        b_dialog = self._dialog(session, parent)
        self.assertFalse(b_dialog.prepare_button.isEnabled())
        sent = len(service.sent)
        b_dialog.prepare_button.click()
        self.assertEqual(len(service.sent), sent)
        session.set_title("Task B local")
        session.set_draft("Task B local bytes remain.")
        self._poll(parent)
        ports.render_release.set()
        self._until(lambda: (session.poll(), session._context_job is None)[1])
        self._poll(parent)
        self._poll(dialog)
        self.assertEqual((session.task_id, session.draft), (b, "Task B local bytes remain."))
        self.assertEqual(parent.draft_editor.toPlainText(), "Task B local bytes remain.")
        self.assertIsNone(session.context_result)
        self.assertFalse(job["thread"].is_alive())
        session.select_task(a)
        self._poll(dialog)
        self.assertEqual(session.context_result.task.task_id, a)
        self.assertFalse(dialog.prepare_button.isEnabled())
        self.assertFalse(dialog.revalidate_button.isEnabled())
        self.assertIn("Selection changed", dialog.status_label.text())
        self.assertEqual(dialog.inspector.byte_editor.toPlainText(), captured)
        reopened = self._dialog(session, parent)
        self.assertTrue(reopened.revalidate_button.isEnabled())
        self._bytes(reopened, "Retained latest input", LATEST.encode("utf8"))

    def test_stop_and_escape_bypass_invalid_controls_and_keep_actual_worker_custody(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        for action in ("button", "escape"):
            with self.subTest(action=action):
                session, service, fixture, ports = self._case()
                parent = self._parent(session)
                dialog = self._dialog(session, parent)
                job = self._start_held(session, service, ports, dialog)
                cut = self._cut(fixture)
                dialog.profile_picker.setEditable(True)
                dialog.profile_picker.setCurrentText("invalid profile")
                dialog.output_tokens_spin.lineEdit().setText("invalid")
                parent.title_editor.setText("X" * 257)
                self.assertTrue(dialog.stop_button.isEnabled())
                before = service.stop_calls
                if action == "button":
                    dialog.stop_button.click()
                else:
                    dialog.inspector.byte_editor.setFocus()
                    QTest.keyClick(dialog.inspector.byte_editor, Qt.Key.Key_Escape)
                    self.app.processEvents()
                self.assertEqual(service.stop_calls, before + 1)
                self.assertTrue(job["cancel"].is_set())
                self.assertTrue(job["thread"].is_alive())
                self.assertIs(session._context_job, job)
                self.assertEqual(session.status, "STOPPING")
                service.finish_stop()
                self._poll(dialog)
                self.assertEqual(session.status, "STOPPING")
                self.assertTrue(dialog.isVisible())
                self.assertTrue(job["thread"].is_alive())
                ports.render_release.set()
                self._until(lambda: (session.poll(), session._context_job is None)[1])
                self._poll(dialog)
                self.assertEqual((session.status, session.context_status), ("STOPPED", "CANCELLED"))
                self.assertFalse(job["thread"].is_alive())
                self.assertEqual(parent.title_editor.text(), "X" * 257)
                self.assertEqual(self._cut(fixture), cut)

    def test_return_and_window_close_retire_only_child_timer_while_parent_owns_worker(self):
        for action in ("return", "window_close"):
            with self.subTest(action=action):
                session, service, _, ports = self._case()
                parent = self._parent(session)
                dialog = self._dialog(session, parent)
                job = self._start_held(session, service, ports, dialog)
                parent.poll_timer.start()
                dialog.poll_timer.start()
                stops = service.stop_calls
                if action == "return":
                    dialog.return_button.click()
                else:
                    dialog.close()
                self.app.processEvents()
                self.assertFalse(dialog.poll_timer.isActive())
                self.assertTrue(parent.poll_timer.isActive())
                parent.poll_timer.stop()
                self.assertEqual(service.stop_calls, stops)
                self.assertIs(session._context_job, job)
                self.assertFalse(job["cancel"].is_set())
                self.assertTrue(job["thread"].is_alive())
                ports.render_release.set()
                self._until(lambda: (session.poll(), session._context_job is None)[1])
                self._poll(parent)
                self.assertFalse(job["thread"].is_alive())
                self.assertEqual(session.context_status, "PREVIEW")
                self.assertFalse(dialog.isVisible())

    def test_taskview_modal_entry_uses_same_session_and_return_keeps_existing_edits(self):
        from PySide6.QtCore import QCoreApplication, QEvent, QTimer
        from shiboken6 import isValid
        from ceta.desktop.preparation_view import PreparationView
        session, service, fixture, _ = self._case()
        parent = self._parent(session)
        parent.draft_editor.insertPlainText("Local text before inspector.")
        session.set_meaning_field("clarified_meaning", "Separate manual proposal.")
        text, title = session.draft, session.title
        before, stops = self._cut(fixture), service.stop_calls
        captured, errors, observations = [], [], {}

        def factory(actual, owner):
            child = PreparationView(actual, owner)
            captured.append(child)
            child.destroyed.connect(
                lambda _obj=None: observations.__setitem__("destroyed", True))
            return child

        def inspect_and_return():
            try:
                self.assertEqual(len(captured), 1)
                child = captured[0]
                self.assertIs(child._session, session)
                self.assertIs(child.parentWidget(), parent)
                self.assertFalse(child.prepare_button.isEnabled())
                child.return_button.click()
                observations["visible_after_return"] = child.isVisible()
                observations["timer_after_return"] = child.poll_timer.isActive()
            except BaseException as error:
                errors.append(error)
                if captured:
                    captured[0].reject()

        rescue = QTimer()
        rescue.setSingleShot(True)
        rescue.timeout.connect(lambda: captured and captured[0].reject())
        rescue.start(2000)
        QTimer.singleShot(0, inspect_and_return)
        with patch("ceta.desktop.preparation_view.PreparationView", side_effect=factory):
            parent.preparation_button.click()
        rescue.stop()
        self.assertFalse(errors, repr(errors))
        self.assertEqual(len(captured), 1)
        self.assertFalse(observations["visible_after_return"])
        self.assertFalse(observations["timer_after_return"])
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self.assertTrue(observations.get("destroyed"))
        self.assertFalse(isValid(captured[0]))
        self.assertEqual(parent.findChildren(PreparationView), [])
        self.assertEqual((session.title, session.draft), (title, text))
        self.assertEqual(session.meaning_text["clarified_meaning"], "Separate manual proposal.")
        self.assertIsNone(session.meaning_proposal)
        self.assertEqual(service.stop_calls, stops)
        self.assertEqual(self._cut(fixture), before)

    def test_unchanged_poll_preserves_inspection_page_cursor_selection_and_scroll(self):
        from PySide6.QtGui import QTextCursor
        session, service, _, _ = self._case(context_tokens=32768,
                                          latest=LATEST + "long byte page " * 170)
        view = self._dialog(session)
        self._preview(session, service, view)
        self._bytes(view, "Retained latest input", session.saved_draft.encode("utf8"), 2)
        editor = view.inspector.byte_editor
        cursor = editor.textCursor()
        cursor.setPosition(7)
        cursor.setPosition(39, QTextCursor.MoveMode.KeepAnchor)
        editor.setTextCursor(cursor)
        editor.verticalScrollBar().setValue(editor.verticalScrollBar().maximum())
        before = (editor.toPlainText(), editor.document().revision(),
                  cursor.position(), cursor.anchor(), editor.verticalScrollBar().value(),
                  view.inspector.content_picker.currentText(), view.inspector.page_spin.value())
        for _ in range(4):
            self._poll(view)
        after_cursor = editor.textCursor()
        self.assertEqual((editor.toPlainText(), editor.document().revision(),
                          after_cursor.position(), after_cursor.anchor(),
                          editor.verticalScrollBar().value(),
                          view.inspector.content_picker.currentText(),
                          view.inspector.page_spin.value()), before)

    def test_maximum_byte_and_token_pages_are_bounded_exact_and_distinguish_empty_unavailable(self):
        from types import SimpleNamespace
        from ceta.desktop.preparation_view import ByteInspector
        inspector = ByteInspector()
        self.inspectors.append(inspector)
        inspector.show()
        # Real immutable contract-size input, no fabricated PreparedRequest.
        value = bytes(range(256)) * (8 * 1024 * 1024 // 256)
        token_ids = tuple(range(1024 * 1024))
        items = {"Maximum source": ("bytes", value), "Maximum payload": ("bytes", value),
                 "Maximum token IDs": ("tokens", token_ids), "Empty actual": ("bytes", b""),
                 "No payload": ("unavailable", "No actual rendered payload"),
                 "Empty actual tokens": ("tokens", ())}
        inspector.set_items(items)
        view = SimpleNamespace(inspector=inspector)
        for key in ("Maximum source", "Maximum payload"):
            self._bytes(view, key, value, 8192)
            self.assertLess(len(inspector.byte_editor.toPlainText()), 16000)
            self.assertFalse(inspector.next_button.isEnabled())
            self.assertTrue(inspector.previous_button.isEnabled())
        self._tokens(inspector, "Maximum token IDs", token_ids, 8192)
        self.assertEqual(len(inspector.byte_editor.toPlainText().splitlines()), 128)
        self.assertLess(len(inspector.byte_editor.toPlainText()), 5000)
        self._key(inspector, "Empty actual")
        self.assertEqual(inspector.page_label.text(), "Bytes 0..0 of 0; page 1/1")
        self.assertEqual(inspector.byte_editor.toPlainText(), "Empty actual bytes.")
        self._key(inspector, "No payload")
        self.assertEqual(inspector.page_label.text(), "Unavailable: No actual rendered payload")
        self.assertEqual(inspector.byte_editor.toPlainText(), inspector.page_label.text())
        inspector.set_items(items)
        self.assertEqual(inspector.content_picker.currentText(), "No payload")
        self._key(inspector, "Empty actual tokens")
        self.assertEqual(inspector.page_label.text(), "Token IDs 0..0 of 0; page 1/1")
        self.assertEqual(inspector.byte_editor.toPlainText(), "Empty actual token ids.")


    def test_background_baseexception_is_terminal_bounded_and_visible_without_fake_result(self):
        session, service, fixture, ports = self._case()
        ports.render_transform = lambda value: (_ for _ in ()).throw(
            KeyboardInterrupt("private background exception text"))
        view = self._dialog(session)
        cut = self._cut(fixture)
        self._begin(view, service)
        self._deliver(session, service, view)
        self.assertEqual((session.context_status, session.context_error),
                         ("DENIED", "CONTEXT_COMPILER_FAILED"))
        self.assertIsNone(session.context_result)
        self.assertFalse(session.context_busy)
        self.assertIn("CONTEXT_COMPILER_FAILED", view.detail_label.text())
        self.assertNotIn("private background exception text", view.detail_label.text())
        self.assertIn("Retained result: none", view.result_label.text())
        self.assertEqual(self._cut(fixture), cut)

    def test_parent_close_retains_hidden_edits_and_waits_for_child_worker_exit(self):
        from PySide6.QtWidgets import QMessageBox
        session, service, fixture, ports = self._case()
        parent = self._parent(session)
        child = self._dialog(session, parent)
        job = self._start_held(session, service, ports, child)
        session.set_meaning_field("clarified_meaning", "Hidden unsaved manual meaning.")
        session.set_draft("Hidden raw draft remains local.")
        cut, stops = self._cut(fixture), service.stop_calls
        with patch.object(QMessageBox, "question",
                          return_value=QMessageBox.StandardButton.Cancel) as ask:
            self.assertFalse(parent.close())
        self.assertEqual(ask.call_args.args[-1], QMessageBox.StandardButton.Cancel)
        self.assertTrue(parent.isVisible())
        self.assertEqual(service.stop_calls, stops)
        self.assertFalse(job["cancel"].is_set())
        with patch.object(QMessageBox, "question",
                          return_value=QMessageBox.StandardButton.Close):
            self.assertFalse(parent.close())
        self.assertTrue(job["cancel"].is_set())
        self.assertTrue(job["thread"].is_alive())
        service.finish_stop()
        self._poll(parent)
        self.assertEqual(session.status, "STOPPING")
        self.assertTrue(parent.isVisible())
        self.assertIs(session._context_job, job)
        ports.render_release.set()
        self._until(lambda: (session.poll(), session._context_job is None)[1])
        self._poll(parent)
        self.assertFalse(job["thread"].is_alive())
        self.assertFalse(parent.isVisible())
        self.assertFalse(parent.poll_timer.isActive())
        self.assertEqual(session.draft, "Hidden raw draft remains local.")
        self.assertEqual(session.meaning_text["clarified_meaning"], "Hidden unsaved manual meaning.")
        self.assertIsNone(session.meaning_proposal)
        self.assertEqual(self._cut(fixture), cut)


    def test_preview_redundant_inspection_fields_reject_separate_substitution(self):
        from ceta.contracts.request_compiler import SourceItem
        from ceta.contracts.wire import ContractError
        from test_request_compiler import _pin
        sources = (SourceItem("source:retained", _pin("retained source"), "HISTORY",
                              b"Actual retained selected source.", True),
                   SourceItem("source:omitted", _pin("omitted source"), "BINDING_INSTRUCTION",
                              b"CODING_ONLY_UNAVAILABLE_TO_CHAT", False, coding_only=True))
        session, service, fixture, _ = self._case(sources=sources)
        view = self._dialog(session)
        result = self._preview(session, service, view)
        cut = self._cut(fixture)
        self.assertGreater(result.input_tokens, 0)
        self.assertEqual(len(result.sources), 2)
        self.assertEqual(len(result.omissions), 1)
        changed_field = replace(result.interpretation.fields[0],
                                value=b"Substituted objective.", status="INFERRED")
        mutations = (
            ("missing selection", {"selection": None}),
            ("different selection", {"selection": replace(result.selection,
                state=replace(result.selection.state, profile="review"))}),
            ("missing interpretation", {"interpretation": None}),
            ("different interpretation", {"interpretation": replace(result.interpretation,
                fields=(changed_field,) + result.interpretation.fields[1:])}),
            ("missing sources", {"sources": ()}),
            ("reordered sources", {"sources": tuple(reversed(result.sources))}),
            ("missing omissions", {"omissions": ()}),
            ("missing token count", {"input_tokens": None}),
            ("false zero count", {"input_tokens": 0}),
            ("different token count", {"input_tokens": result.input_tokens + 1}),
        )
        for label, kwargs in mutations:
            with self.subTest(label=label):
                with self.assertRaises(ContractError) as caught:
                    replace(result, **kwargs)
                self.assertEqual(caught.exception.code, "COMPILER_RESULT_PREVIEW_COHERENCE")
        # Equal immutable copies remain consistent; equality is not a new owner.
        consistent = replace(result, selection=replace(result.selection),
                             interpretation=replace(result.interpretation))
        self.assertEqual(consistent, result)
        self.assertIs(consistent.prepared, result.prepared)
        self.assertIs(session.context_result, result)
        self.assertEqual(self._cut(fixture), cut)

    def test_modal_dialog_is_deleted_after_return_or_stop_without_losing_shared_worker(self):
        from PySide6.QtCore import QCoreApplication, QEvent, QTimer
        from shiboken6 import isValid
        from ceta.desktop.preparation_view import PreparationView
        for action in ("return", "stop_then_return"):
            with self.subTest(action=action):
                session, service, fixture, ports = self._case()
                parent = self._parent(session)
                self._held(ports)
                cut, captured, observations = self._cut(fixture), [], {}

                def factory(actual, owner):
                    child = PreparationView(actual, owner)
                    captured.append(child)
                    child.destroyed.connect(
                        lambda _obj=None: observations.__setitem__("destroyed", True))
                    return child

                def prepare_and_return():
                    try:
                        child = captured[0]
                        self.assertIs(child._session, session)
                        child.prepare_button.click()
                        self.assertEqual(service.sent[-1].operation, "task.load")
                        service.complete()
                        session.poll()
                        job = session._context_job
                        observations["job"] = job
                        self.workers.append(job["thread"])
                        self.assertTrue(ports.render_entered.wait(2))
                        self.assertTrue(job["thread"].is_alive())
                        if action == "stop_then_return":
                            child.stop_button.click()
                            service.finish_stop()
                            session.poll()
                        child.return_button.click()
                        observations["hidden_before_delete"] = not child.isVisible()
                        observations["timer_stopped_before_delete"] = not child.poll_timer.isActive()
                        self.assertIs(session._context_job, job)
                        self.assertTrue(job["thread"].is_alive())
                    except BaseException as error:
                        observations["error"] = error
                        if captured and isValid(captured[0]):
                            captured[0].reject()

                rescue = QTimer()
                rescue.setSingleShot(True)
                def rescue_modal():
                    observations["rescued"] = True
                    if captured and isValid(captured[0]):
                        captured[0].reject()
                rescue.timeout.connect(rescue_modal)
                rescue.start(3000)
                QTimer.singleShot(0, prepare_and_return)
                with patch("ceta.desktop.preparation_view.PreparationView", side_effect=factory):
                    parent.preparation_button.click()
                rescue.stop()
                self.assertNotIn("error", observations, repr(observations.get("error")))
                self.assertNotIn("rescued", observations)
                self.assertTrue(observations["hidden_before_delete"])
                self.assertTrue(observations["timer_stopped_before_delete"])
                QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
                self.app.processEvents()
                self.assertTrue(observations.get("destroyed"))
                self.assertFalse(isValid(captured[0]))
                self.assertEqual(parent.findChildren(PreparationView), [])
                job = observations["job"]
                self.assertIs(session._context_job, job)
                self.assertTrue(job["thread"].is_alive())
                self.assertEqual(job["cancel"].is_set(), action == "stop_then_return")
                self.assertEqual(service.stop_calls, int(action == "stop_then_return"))
                if action == "stop_then_return":
                    self.assertEqual(session.status, "STOPPING")
                ports.render_release.set()
                self._until(lambda: (session.poll(), session._context_job is None)[1])
                self._poll(parent)
                self.assertFalse(job["thread"].is_alive())
                if action == "return":
                    self.assertEqual(session.context_status, "PREVIEW")
                else:
                    self.assertEqual((session.status, session.context_status),
                                     ("STOPPED", "CANCELLED"))
                self.assertEqual(self._cut(fixture), cut)

    def test_readable_question_field_and_binary_source_preserve_plain_exact_bytes(self):
        from ceta.contracts.request_compiler import (SourceItem, MeaningField,
                                                    ClarificationQuestion)
        from test_request_compiler import _pin
        value = b"Ordinary <tag> Cafe\xcc\x81\r\nKeep\x00it\tliteral\x1b\x7f\xff\xfe"
        readable = "Ordinary <tag> Cafe\u0301\\r\\nKeep\\x00it\\tliteral\\x1b\\x7f\\xff\\xfe"
        source = SourceItem("source:readable", _pin("readable source"), "UNTRUSTED_DATA",
                            value, True)
        session, service, fixture, ports = self._case(sources=(source,))
        ports.interpret_transform = lambda original: replace(original,
            fields=original.fields + (
                MeaningField("context", value, "INFERRED", ("source:readable",), False),))
        ports.questions = (ClarificationQuestion(value, "TARGET", True,
                                                  session.task_id, ("source:readable",)),)
        view = self._dialog(session)
        cut = self._cut(fixture)
        self._preview_or_terminal(session, service, view, "CLARIFICATION")
        self._bytes(view, "Question: 0", value)
        self.assertTrue(view.inspector.readable_editor.isReadOnly())
        self.assertEqual(view.inspector.readable_editor.toPlainText(), readable)
        self.assertTrue(view.clarification_editor.isReadOnly())
        self.assertEqual(view.clarification_editor.toPlainText(), readable)
        self._bytes(view, "Source: 0 [UNTRUSTED_DATA]", value)
        self.assertEqual(view.inspector.readable_editor.toPlainText(), readable)
        row = FIELDS.index("context")
        table_text = view.meaning_table.item(row, 2).text()
        self.assertIn("Ordinary <tag> Cafe\u0301", table_text)
        self.assertIn("\\x00", table_text)
        self.assertIn("\\xff", table_text)
        view.meaning_table.cellClicked.emit(row, 2)
        self.assertEqual(view.inspector.content_picker.currentText(), "Meaning value: context")
        self._bytes(view, "Meaning value: context", value)
        self.assertEqual(view.inspector.readable_editor.toPlainText(), readable)
        self.assertEqual(session.saved_draft, LATEST)
        self.assertEqual(session.original_instruction, ORIGINAL)
        self.assertIsNone(session.meaning_proposal)
        self.assertEqual(self._cut(fixture), cut)

    def test_readable_page_selection_cursor_and_document_survive_unchanged_updates(self):
        from PySide6.QtGui import QTextCursor
        from ceta.desktop.preparation_view import ByteInspector
        inspector = ByteInspector()
        self.inspectors.append(inspector)
        inspector.show()
        value = b"A" * 1024 + b"Second page\x00\r\nCafe\xcc\x81\xff"
        items = {"Exact bytes": ("bytes", value)}
        inspector.set_items(items)
        self._key(inspector, "Exact bytes", 2)
        self.assertEqual(inspector.readable_editor.toPlainText(),
                         "Second page\\x00\\r\\nCafe\u0301\\xff")
        editor = inspector.readable_editor
        cursor = editor.textCursor()
        cursor.setPosition(3)
        cursor.setPosition(20, QTextCursor.MoveMode.KeepAnchor)
        editor.setTextCursor(cursor)
        before = (editor.toPlainText(), editor.document().revision(),
                  cursor.position(), cursor.anchor(),
                  inspector.content_picker.currentText(), inspector.page_spin.value())
        for _ in range(4):
            inspector.set_items(items)
            self.app.processEvents()
        after = editor.textCursor()
        self.assertEqual((editor.toPlainText(), editor.document().revision(),
                          after.position(), after.anchor(),
                          inspector.content_picker.currentText(), inspector.page_spin.value()), before)


    def test_async_bad_preview_replacement_is_denied_without_overwriting_retained_state(self):
        wrappers = []

        class BadReplacement:
            # Instrument an already-real compiler at construction; no hot swap.
            def __init__(self, real):
                self.real, self.corrupt, self.new_preview = real, False, None

            def compile_loaded_task(self, *args, **kwargs):
                result = self.real.compile_loaded_task(*args, **kwargs)
                if self.corrupt:
                    self.new_preview = result
                    return replace(result, input_tokens=0)
                return result

            def revalidate(self, *args, **kwargs):
                return self.real.revalidate(*args, **kwargs)

        def instrument(real):
            wrapper = BadReplacement(real)
            wrappers.append(wrapper)
            return wrapper

        session, service, fixture, _ = self._case(compiler_factory=instrument)
        view = self._dialog(session)
        prior = self._preview(session, service, view)
        self.assertGreater(prior.input_tokens, 0)
        old_observation = session.context_native_observation
        saved = (session.task_id, session.revision, session.title, session.draft,
                 session.saved_draft, session.original_instruction,
                 dict(session.meaning_text), session.meaning_proposal)
        cut, worker_count, sent = self._cut(fixture), len(self.workers), len(service.sent)
        wrappers[0].corrupt = True
        self._begin(view, service)
        retained = self._deliver(session, service, view)
        self.assertEqual(len(service.sent), sent + 1)
        self.assertEqual(len(self.workers), worker_count + 1)
        worker = self.workers[-1]
        self.assertFalse(worker.is_alive())
        self.assertIsNone(session._context_job)
        self.assertFalse(session.context_busy)
        self.assertEqual((session.context_status, session.context_error),
                         ("DENIED", "COMPILER_RESULT_PREVIEW_COHERENCE"))
        self.assertIs(retained, prior)
        self.assertIs(session.context_result, prior)
        self.assertIsNot(wrappers[0].new_preview, prior)
        self.assertEqual(wrappers[0].new_preview.kind, "PREVIEW")
        self.assertGreater(wrappers[0].new_preview.input_tokens, 0)
        self.assertNotEqual(session.context_native_observation[0], old_observation[0])
        self.assertEqual(session.context_native_observation[2], prior.task.task_revision)
        self.assertIn("DENIED", view.status_label.text())
        self.assertIn("COMPILER_RESULT_PREVIEW_COHERENCE", view.detail_label.text())
        self.assertIn("Retained result: PREVIEW", view.result_label.text())
        self._bytes(view, "Rendered payload", prior.prepared.payload)
        self._bytes(view, "Retained latest input", LATEST.encode("utf8"))
        self._bytes(view, "Latest native request", session.context_native_observation[0])
        self._freshness_notes(view)
        self.assertEqual((session.task_id, session.revision, session.title, session.draft,
                          session.saved_draft, session.original_instruction,
                          dict(session.meaning_text), session.meaning_proposal), saved)
        self.assertEqual(self._cut(fixture), cut)

if __name__ == "__main__":
    unittest.main()
