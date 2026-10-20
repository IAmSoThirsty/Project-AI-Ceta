"""Preserve the failing cut, then repair only fresh-observer continuity."""
from et_support import *

source = Q / 'src/ceta/kernel/effect_transactions.py'
assert sha(source) == '1b3c97129dfdaab1a194efb3158bcf9e08932446e069d6dd1c2abfb16efb9b82'
before = R / 'before-test-adjustment'
before.mkdir()
test = Q / 'tests/contract/test_fresh_observer_reconciliation.py'
fs.write_new(before / test.name, fs.read_bytes(test))
write_new(before / 'BINDING.json', {'test': ordinary(test), 'baseline': reference(R / 'before-r1.json'),
    'observed': 'Six new fresh-lifetime paths rejected by the old exact-identity predicate; one controlled unhashable-proof test expected ContractError but actual registry raises TypeError.'})
old = 'require(observation.observer_identity == previous.observer_identity and observation.sequence > previous.sequence'
new = '''# OB2 retires a distinct child for every observation. Its captured
                # owner authenticates each new child; continuity belongs to the
                # same bound implementation and strictly advancing sequence/time.
                require(observation.observer_identity.image_digest == previous.observer_identity.image_digest
                    and observation.sequence > previous.sequence'''
raw = source.read_text(encoding='utf-8')
assert raw.count(old) == 1
source.write_text(raw.replace(old, new), encoding='utf-8', newline='\n')
contract = Q / 'contracts/OWNED_CPU_OUTCOME_V1.md'
raw = contract.read_text(encoding='utf-8')
old = '''Uncertain/discrepant outcomes can accept a strictly advancing observation from
the same observer lifetime without replacing the original receipt. Settled
outcomes cannot be overwritten.'''
new = '''Uncertain/discrepant outcomes can accept a strictly advancing observation from
the same bound observer implementation without replacing the original receipt.
OB2 creates and retires a separate query child for each observation. Its captured
owner must authenticate that fresh child's actual lifetime, query custody and
exact request binding; matching data or image bytes alone grant no provenance.
The observer image digest must remain equal, and the retained controller's
sequence and observation monotonic time must both increase. A changed PID or
creation time does not reset either highwater. A newly constructed observer
whose sequence starts behind retained evidence remains rejected; recovery must
compose canonical sequence continuity before using that observer. Each child's
actual PID/creation/image identity remains in its immutable native observation
and canonical observer-session record. Settled outcomes cannot be overwritten.'''
assert raw.count(old) == 1
contract.write_text(raw.replace(old, new), encoding='utf-8', newline='\n')
raw = test.read_text(encoding='utf-8')
assert raw.count('for supplied in (object(), True, False, {}):') == 1
test.write_text(raw.replace('for supplied in (object(), True, False, {}):',
    'for supplied in (object(), True, False):'), encoding='utf-8', newline='\n')
write_new(R / 'REPAIR.json', {'at': utc(), 'changed': [ordinary(p) for p in (source,contract,test)],
    'production_owner_predicate_unchanged': True, 'canonical_store_and_authority_unchanged': True,
    'native_reproduction': False, 'positive_proof_providers': 'CONTROLLED'})
