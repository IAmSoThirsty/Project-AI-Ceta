"""Additional independent defect regressions from the October 18 audit.

These are deterministic and do NOT demonstrate resistance to an attacker who
holds the signing key, controls the host, or can replace the entire database.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from truth_accountability import (AuthenticatedActor, GovernedModelBridge,
    GovernedTruthCore, SocietalGatedPipeline, VerificationRegistry, VerifierSpec,
    arithmetic_only_policy, bounded_arithmetic)


class Model:
    def __init__(self, candidate):
        self.candidate=candidate
    def generate_proposal(self,*args,**kwargs):
        return json.dumps(self.candidate)


class AuditRepairTests(unittest.TestCase):
    def setUp(self):
        self.registry=VerificationRegistry()
        self.registry.register(VerifierSpec('arithmetic', 'group-1', bounded_arithmetic))
        self.core=GovernedTruthCore(registry=self.registry)

    def tearDown(self):
        self.core.close()

    def assertTamperHeld(self, query):
        self.assertFalse(self.core.integrity_report()['ok'])
        with self.assertRaisesRegex(RuntimeError, 'integrity'):
            self.core.decision(query)
        with self.assertRaisesRegex(RuntimeError, 'integrity'):
            self.core.render(query)

    def test_refuting_evidence_verdict_tampered_into_support(self):
        claim=self.core.propose('fact','2 + 2 = 5')
        self.core.check(claim,'arithmetic')
        self.assertEqual(self.core.decision(claim).status,'REFUTED_BY_CHECK')
        self.core.db.execute("UPDATE checks_v2 SET verdict='supports' WHERE claim_id=?",(claim,))
        self.core.db.commit()
        self.assertTamperHeld(claim)

    def test_mutation_of_evidence_prevents_new_writes(self):
        claim=self.core.propose('fact','2 + 2 = 4')
        self.core.check(claim,'arithmetic')
        self.core.db.execute("UPDATE checks_v2 SET evidence_sha256='bogus' WHERE claim_id=?",(claim,))
        self.core.db.commit()
        with self.assertRaisesRegex(RuntimeError,'integrity'):
            self.core.preserve('new-speaker','New text')
        with self.assertRaisesRegex(RuntimeError,'integrity'):
            self.core.research_queue()

    def test_correction_acknowledgement_refuses_tampered_correction(self):
        source_text='I might attend.'
        source=self.core.preserve('alice',source_text)
        claim=self.core.propose('paraphrase',source_text,source_id=source,span=(0,len(source_text)))
        speaker=AuthenticatedActor('alice',frozenset({'authenticated_speaker'}))
        self.core.clarify_attribution(claim,speaker,'I did not attend.')
        self.core.db.execute("UPDATE corrections_v2 SET correction_text='I certainly attended' WHERE claim_id=?",(claim,))
        self.core.db.commit()
        with self.assertRaisesRegex(RuntimeError,'integrity'):
            self.core.acknowledgement(claim)

    def test_evidence_policy_tamper_cannot_lower_threshold(self):
        claim=self.core.propose('fact','2 + 2 = 4',policy='high_stakes')
        self.core.check(claim,'arithmetic')
        self.assertEqual(self.core.decision(claim).status,'INSUFFICIENT_EVIDENCE')
        self.core.db.execute("UPDATE proposals_v2 SET evidence_policy='standard' WHERE id=?",(claim,))
        self.core.db.commit()
        self.assertTamperHeld(claim)

    def test_deleted_correction_cannot_resurrect_withdrawn_attribution(self):
        statement='I might attend the event.'
        source=self.core.preserve('alice',statement)
        claim=self.core.propose('paraphrase',statement,source_id=source,span=(0,len(statement)))
        speaker=AuthenticatedActor('alice',frozenset({'authenticated_speaker'}))
        self.core.review_meaning(claim,speaker,'aligned','exact confirmation')
        self.assertEqual(self.core.decision(claim).status,'MEANING_REVIEWED')
        self.core.clarify_attribution(claim,speaker,'My prior statement is withdrawn.')
        self.assertEqual(self.core.decision(claim).status,'WITHDRAWN')
        self.core.db.execute('DELETE FROM corrections_v2 WHERE claim_id=?',(claim,))
        self.core.db.commit()
        self.assertTamperHeld(claim)

    def test_rogue_fact_check_without_event_fails_closed(self):
        claim=self.core.propose('fact','2 + 2 = 4')
        check=self.core.check(claim,'arithmetic')
        self.assertTrue(self.core.integrity_report()['ok'])
        original=self.core.db.execute('SELECT * FROM checks_v2 WHERE id=?',(check,)).fetchone()
        vals=list(original)
        vals[0]='f'*32
        self.core.db.execute('INSERT INTO checks_v2 VALUES (?,?,?,?,?,?,?,?,?,?,?)',vals)
        self.core.db.commit()
        self.assertTamperHeld(claim)

    def test_removing_entire_terminal_event_is_detected_by_external_anchor(self):
        ref=self.core.preserve('alice','first')
        anchor=self.core.audit_anchor()
        self.core.preserve('alice','second')
        self.assertFalse(self.core.integrity_report(expected_anchor=anchor)['ok'])
        self.assertTrue(self.core.integrity_report()['ok'])

    def test_full_deletion_needs_external_anchor_for_detection(self):
        self.core.preserve('alice','source')
        anchor=self.core.audit_anchor()
        self.core.db.execute('DELETE FROM sources_v2')
        self.core.db.execute('DELETE FROM audit_events_v2')
        self.core.db.commit()
        # The internal chain alone cannot detect a complete rollback/reset.
        self.assertTrue(self.core.integrity_report()['ok'])
        self.assertFalse(self.core.integrity_report(expected_anchor=anchor)['ok'])

    def test_host_held_hmac_key_authenticates_chain(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'sealed.db'
            key=b'secret-key-from-the-host-not-the-database'*2
            secured=GovernedTruthCore(path,audit_key=key)
            try:
                claim=secured.propose('fact','2 + 2 = 4')
                before=secured.audit_anchor()
                self.assertTrue(secured.integrity_report()['ok'])
                secured.db.execute("UPDATE proposals_v2 SET evidence_policy='high_stakes' WHERE id=?",(claim,))
                secured.db.commit()
                self.assertFalse(secured.integrity_report()['ok'])
                with self.assertRaises(RuntimeError):secured.decision(claim)
            finally:secured.close()
            reopened=GovernedTruthCore(path,audit_key=key)
            try:
                self.assertFalse(reopened.integrity_report(expected_anchor=before)['ok'])
            finally:reopened.close()
            # Opening keyed data without supplying the key is NOT a verified state.
            wrong=GovernedTruthCore(path)
            try:self.assertFalse(wrong.integrity_report()['ok'])
            finally:wrong.close()

    def test_broken_hmac_key_cannot_verify_existing_events(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'events.db'
            key=b'a'*32
            system=GovernedTruthCore(path,audit_key=key)
            system.preserve('alice','one')
            system.close()
            bad=GovernedTruthCore(path,audit_key=b'b'*32)
            try:
                self.assertFalse(bad.integrity_report()['ok'])
            finally:bad.close()

    def test_malformed_event_returns_false_not_exception(self):
        self.core.preserve('alice','one')
        self.core.db.execute('UPDATE audit_events_v2 SET payload_json=? WHERE seq=1',('false',))
        self.core.db.commit()
        self.assertFalse(self.core.integrity_report()['ok'])

    def test_model_hypothesis_cannot_claim_person_intention_by_default(self):
        pipeline=SocietalGatedPipeline(self.core,GovernedModelBridge(self.core,arithmetic_only_policy))
        answer=pipeline.execute(speaker_id='alice',exact_text='A colleague made a suggestion.',
            proposer=Model({'kind':'hypothesis','text':'The colleague plans to deceive everyone.'}))
        self.assertEqual(answer.decision,'HYPOTHESIS_HELD_FOR_REVIEW')
        self.assertNotIn('plans to deceive',answer.response)

    def test_novel_person_motive_words_do_not_bypass_host_hypothesis_hold(self):
        runner=SocietalGatedPipeline(self.core,GovernedModelBridge(self.core,arithmetic_only_policy))
        for interpretation in ('My boss is plotting sabotage.',
                               'The visitor harbors malice.',
                               'This colleague fantasizes about hurting everyone.'):
            res=runner.execute(speaker_id='alice',exact_text='A visitor arrived.',
                proposer=Model({'kind':'hypothesis','text':interpretation}))
            self.assertNotIn(interpretation,res.response)
            self.assertIn(res.decision,{'HYPOTHESIS_HELD_FOR_REVIEW','NEEDS_PERSON_EVIDENCE'})


if __name__=='__main__':unittest.main()
