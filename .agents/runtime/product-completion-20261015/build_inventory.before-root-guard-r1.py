"""Read original completion obligations; emit one source-bound remaining inventory.

This script imports no CETA code, runs no product tests and publishes no status.
"""
from __future__ import annotations

import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

F = Path('T:/00-Active/Project-AI-CETA')
R = F / '.agents/runtime/product-completion-20261015'
A = F / '.agents/cp1-20261014/independent-recovery/working-tree'
R6 = F / '.agents/runtime/authoritative-inputs-20261014/CETA-UNIFIED-CODE-IMPLEMENTATION-PLAN-r6.txt'
SOURCE_PINS = {}
SOURCES = {}
OBSERVATIONS = []
ERRORS = []
START = datetime.now(timezone.utc).isoformat()
ORIGINAL_IDS = re.compile(r'\b(?:REQ-\d{2}-\d{2}|CETA-IMPL-\d{3}|WP-\d{2}|CMP-\d{2}|B\d{3}|POL-\d{2}|ADR-\d{3}|SRC-\d{3}|AT-CETA-\d{2}\.\d{2}\.\d{2}-\d{2}|CETA-\d{2}\.\d{2}\.\d{2}|G-[A-H]|E2E-\d{2}[A-Z0-9-]*|CR-[0-9a-f]{16}|RE-T\d{2}|RE-\d{2}|[ACDFSV]\d{2})\b')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def relative(path):
    return Path(path).relative_to(F).as_posix()


def read(path, *, stable=True):
    path = Path(path)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_file_attributes & 0x400:
        raise ValueError(f'Nonordinary input: {path}')
    raw = path.read_bytes()
    after = path.lstat()
    fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns')
    if stable and any(getattr(before, k) != getattr(after, k) for k in fields):
        raise ValueError(f'Changed during input read: {path}')
    key = relative(path)
    fact = dict(path=str(path), bytes=len(raw), sha256=sha(raw),
                observed_at=datetime.now(timezone.utc).isoformat(),
                ordinary=True, python_lstat={k: getattr(after, k) for k in fields},
                handle_held=False)
    if stable:
        SOURCE_PINS.setdefault(key, fact)
    SOURCES[key] = fact
    return raw


def text(path, *, stable=True):
    return read(path, stable=stable).decode('utf-8-sig')


def load(path, *, stable=True):
    return json.loads(text(path, stable=stable))


def ref(path, start=None, end=None):
    row = dict(SOURCES[relative(path)])
    if start is not None:
        row['line_start'] = start
        row['line_end'] = start if end is None else end
    return row


def source_sections(path):
    """Preserve every nonblank line, section and table row without semantic merging."""
    raw_text = text(path)
    lines = raw_text.splitlines()
    groups = []
    start = 0
    heading = None
    for n, line in enumerate(lines):
        if line.startswith('#'):
            if n > start:
                groups.append((start, n, heading))
            start, heading = n, line
    groups.append((start, len(lines), heading))
    result = []
    for lo, hi, heading in groups:
        content = '\n'.join(lines[lo:hi]).strip()
        if not content:
            continue
        statements = [dict(line_number=n+1, text=lines[n],
                           original_identifiers=sorted(set(ORIGINAL_IDS.findall(lines[n]))),
                           acceptance_status='UNVERIFIED_AT_THIS_GRANULARITY')
                      for n in range(lo, hi) if lines[n].strip()]
        result.append(dict(heading=heading, source_lines=[lo+1, hi],
                           content=content, statements=statements,
                           acceptance_status='OPEN_NO_FULL_SOURCE_CLAUSE_PROOF',
                           unsplit_conjuncts='Semantic conjunct-to-code-and-oracle reconciliation remains required.'))
    return dict(source=ref(path), sections=result,
                nonblank_lines=sum(bool(s.strip()) for s in lines),
                coverage='EVERY_NONBLANK_SOURCE_LINE_RETAINED; semantic acceptance not inferred')


def blocks(lines):
    result = []
    lo = None
    section = 'PREAMBLE'
    for n, line in enumerate(lines + ['']):
        if re.match(r'^[A-W](?:2)?\. ', line):
            section = line
        if line.strip() and lo is None:
            lo = n
        if not line.strip() and lo is not None:
            selected = lines[lo:n]
            result.append(dict(locator=f'{relative(R6)}#L{lo+1}-L{n}',
                               line_start=lo+1, line_end=n, section=section,
                               original_identifiers=sorted(set(ORIGINAL_IDS.findall('\n'.join(selected)))),
                               text='\n'.join(selected),
                               semantic_status='RETAINED_SOURCE_OBLIGATION_OR_CONTEXT; NOT_INDIVIDUALLY_ACCEPTED'))
            lo = None
    return result


def finishable_code(path):
    if not path.exists():
        return dict(path=str(path), present=False, status='ABSENT_AT_OBSERVATION')
    body = text(path)
    row = dict(source=ref(path), present=True, semantics='PRESENCE_IS_NOT_REQUIREMENT_ACCEPTANCE')
    if path.suffix == '.py':
        try:
            tree = ast.parse(body)
            row['top_level_classes'] = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
            row['declared_functions'] = [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            row['declared_functions_count'] = len(row['declared_functions'])
            row['closed_or_unavailable_lines'] = [dict(line=i+1, text=line.strip()) for i, line in enumerate(body.splitlines())
                                                if re.search(r'UNAVAILABLE|NOT_QUALIFIED|AUTHORITY_CLOSED|runtime admission is not', line)][:40]
        except (SyntaxError, ValueError) as exc:
            row['syntax_error'] = type(exc).__name__
    row['native_unit_mentions'] = sorted(set(re.findall(r'\bCETA-\d{2}\.\d{2}\.\d{2}\b', body)))
    return row


def receipts_for(runtime, run_id):
    state_path = runtime / run_id / 'state.json'
    if not state_path.exists():
        return dict(status='LIFECYCLE_NOT_FOUND_AT_CONVENTIONAL_RUN_PATH', fully_authenticated=False)
    state = load(state_path, stable=False)
    claims_path = runtime / run_id / 'claims.json'
    claims = load(claims_path, stable=False) if claims_path.exists() else None
    rows = {}
    for node_id, node in state.get('nodes', {}).items():
        row = {k: node.get(k) for k in ('state', 'decision', 'executor_id', 'workspace', 'receipt_hash', 'artifact_hash', 'completed_at')}
        stored = runtime / run_id / node.get('receipt_ref', f'receipts/{node_id}.json')
        if stored.exists():
            try:
                persisted = load(stored, stable=False)
                expected = persisted.get('receipt_hash')
                actual = sha(json.dumps({k: v for k, v in persisted.items() if k != 'receipt_hash'},
                                        ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())
                row['persisted_receipt'] = ref(stored)
                row['computed_augmented_fingerprint'] = actual
                row['fingerprint_matches'] = expected == actual == node.get('receipt_hash')
            except Exception as exc:
                row['receipt_check_error'] = type(exc).__name__
        rows[node_id] = row
    return dict(state_source=ref(state_path), sequence=state.get('sequence'), nodes=rows,
                claims=claims, observation_only=True,
                limits='Persisted fingerprint/state observed; graph, result envelope and artifact are not fully requalified here. A node label is not product acceptance.')


def candidate_catalog():
    result = []
    for q in sorted((F / '.agents').iterdir()):
        if not q.is_dir() or q.is_symlink():
            continue
        f = q / 'TRANSFER-MANIFEST.json'
        if not f.exists():
            continue
        try:
            m = load(f)
            runtime = F / '.agents/runtime' / q.name
            paths = m.get('eligible_application_paths') or m.get('application_paths') or m.get('selected_paths') or []
            if not paths:
                for kind in ('EXTEND', 'CREATE'):
                    value = m.get(kind, [])
                    paths += list(value) if isinstance(value, (list, dict)) else []
            hashes = m.get('expected_payload_hashes', {})
            if not hashes and isinstance(m.get('payloads'), dict):
                for rel, row in m['payloads'].items():
                    if isinstance(row, str): hashes[rel] = row
                    elif isinstance(row, dict):
                        candidate = row.get('candidate', row)
                        if isinstance(candidate, dict) and candidate.get('sha256'): hashes[rel] = candidate['sha256']
            normalized_paths = [str(z) for z in paths if isinstance(z, (str, Path))]
            result.append(dict(run_id=m.get('run_id', q.name), candidate_root=str(q),
                manifest=ref(f), recorded_at=m.get('recorded_at', m.get('at')),
                author=m.get('author'), declared_scope=m.get('scope'),
                application_paths=normalized_paths, declared_payload_count=len(hashes) or m.get('payload_count'),
                selected_hashes={s: hashes.get(s) for s in normalized_paths},
                source_publication_declaration=m.get('Source_publication', m.get('source_publication')),
                full_gate_complete_declaration=m.get('full_gate_complete'),
                activation_ready_declaration=m.get('activation_ready'),
                lifecycle=receipts_for(runtime, str(m.get('run_id', q.name))),
                acceptance_status='CANDIDATE_OR_HISTORICAL_CUT; NOT_ACTIVE_SOURCE_BY_EXISTENCE',
                limits=m.get('limits', m.get('limitations', []))))
        except Exception as exc:
            ERRORS.append(dict(path=str(f), error=type(exc).__name__, message=str(exc)[:240], classification='INVENTORY_INPUT_SCHEMA_OR_READ_FOLLOW_UP'))
    return result


def make_inventory():
    git = {}
    for name, args in [('root', ['rev-parse', '--show-toplevel']), ('head', ['rev-parse', 'HEAD']),
                       ('branch', ['branch', '--show-current']), ('status', ['status', '--short', '-uno'])]:
        c = subprocess.run(['git', '-C', str(F), '-c', 'core.optionalLocks=false', *args],
                           capture_output=True, text=True, check=False)
        git[name] = dict(argv=c.args, exit_status=c.returncode, stdout=c.stdout, stderr=c.stderr)
    r6_text = text(R6)
    assert sha(R6.read_bytes()) == 'e22b88a57c608a9b5711ee956a1e8909ea6efc002b39a578ea88692ddd0edf73'
    r6_lines = r6_text.splitlines()
    r6_blocks = blocks(r6_lines)
    registry_paths = dict(requirements='requirements/requirements.json', atomic_tickets='requirements/atomic_tickets.json',
        work_packages='build/work_packages.json', gates='build/gates.json', scenarios='acceptance/scenarios.json',
        components='architecture/components.json', lifecycle='standards/lifecycle_coverage.json',
        decisions='decisions/decision_register.json', policies='policies/policy_registry.json', volumes='standards/volume_register.json')
    registries = {k: load(F/v) for k,v in registry_paths.items()}
    requirement_rows = registries['requirements']['requirements']
    wp = registries['work_packages']['packages']
    components = registries['components']['components']
    compmap = {r['id']: r for r in components}
    acceptance_plan_path = F / '.local-build-cache/increment-31-verification-forward-plan-20261011-01/acceptance-code-plan.json'
    acceptance_plan = load(acceptance_plan_path)
    b_cards = {v['id']: v for v in acceptance_plan['case_cards']}
    scope = load(F/'.local-build-cache/full-product-plan-20261013/scope-index.json')
    baseline_path = F/'.agents/runtime/ct4-20261014/ACCEPTED-SOURCE-BASELINE.json'
    baseline = load(baseline_path)
    current = {}
    for rel, expected in baseline['source_hashes'].items():
        f = F / rel
        if f.exists():
            read(f)
            current[rel] = dict(expected_sha256=expected, observed=ref(f), matches=sha(f.read_bytes()) == expected)
        else:
            current[rel] = dict(expected_sha256=expected, matches=False, missing=True)
    code = []
    for f in sorted((F/'src/ceta').rglob('*')):
        if f.is_file() and not f.is_symlink() and f.suffix in ('.py', '.rs'):
            code.append(finishable_code(f))
    code_by_component = {}
    for c in components:
        prefix = c['path'].rstrip('/')+'/'
        code_by_component[c['id']] = [z for z in code if relative(Path(z['source']['path'])).startswith(prefix)]
    candidates = candidate_catalog()
    candidate_by_path = defaultdict(list)
    for c in candidates:
        for rel in c['application_paths']:
            if rel.startswith(('src/', 'native/', 'tools/', 'contracts/')):
                candidate_by_path[rel].append(c['run_id'])
    def source_set(cmpids):
        return sorted({z['source']['path'] for cid in cmpids for z in code_by_component.get(cid, [])})
    requirements = []
    for original in requirement_rows:
        matching = [v for v in wp if original['id'] in v.get('requirement_ids', [])]
        cmpids = sorted({cid for v in matching for cid in v.get('component_owners', []) if cid in compmap}
                        | {c['id'] for c in components if original['section'] in c.get('section_ids', [])})
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', original['requirement_text'])
        requirements.append(dict(original=original,
            original_source=ref(F/'requirements/requirements.json'), detailed_specification=source_sections(F/original['specification_path']),
            text_preserved_verbatim=True, requirement_sentences=[dict(text=s, status='UNVERIFIED_CONJUNCTS_REMAIN') for s in sentences],
            semantic_conjunct_coverage='OPEN: sentence extraction is not full conjunct decomposition or implementation proof',
            work_package_ids=[v['id'] for v in matching], canonical_component_ids=cmpids,
            implemented_source_paths=source_set(cmpids), implementation_binding='COMPONENT_OWNERSHIP_ONLY; no clause-level acceptance inferred',
            candidate_paths={rel: runs for rel,runs in candidate_by_path.items() if any(rel.startswith(compmap[cid]['path']+'/') for cid in cmpids)},
            acceptance_status='OUTSTANDING_FULL_REQUIREMENT_ACCEPTANCE_UNVERIFIED',
            blockers=['No source-bound independent completion proof establishes every conjunct of this requirement group.',
                      'The exact original B-case and applicable native/codex oracles remain separately required.'],
            next_executable_closure=dict(work_packages=[v['id'] for v in matching],
                action='Bind each remaining conjunct to its canonical source method and original oracle; complete missing behavior, then execute the exact required evidence class and distinct delivered review.',
                original_case_ids=original.get('acceptance_ids', []))))
    package_rows = []
    for v in wp:
        path = F / v['path']
        package_rows.append(dict(original=v, specification=source_sections(path),
            implemented_source_paths=source_set(v.get('component_owners', [])),
            acceptance_status='OPEN_PACKAGE_EXIT_NOT_INDEPENDENTLY_ESTABLISHED',
            remaining_requirement_ids=v.get('requirement_ids', []), remaining_original_case_ids=v.get('acceptance_ids', []),
            next_executable_closure='Execute the exact exit criteria and all linked requirement, policy, case and source-clause predicates against the delivered candidate; retain blocked dependencies and evidence class.'))
    native_units = []
    referenced_native_sources = defaultdict(list)
    for z in code:
        for uid in z['native_unit_mentions']:
            referenced_native_sources[uid].append(z['source']['path'])
    for u in scope['native_units']:
        old = u['specification']['path'].replace('\\','/')
        rel = old.split('/CETA-NATIVE-ARCHITECTURE/', 1)[1]
        f = A / rel
        doc = source_sections(f)
        at_rows = []
        for section in doc['sections']:
            for s in section['statements']:
                ids = re.findall(r'\bAT-CETA-\d{2}\.\d{2}\.\d{2}-\d{2}\b', s['text'])
                for ident in ids:
                    at_rows.append(dict(original_id=ident, source_line=s['line_number'], original_text=s['text'],
                                        status='UNVERIFIED_NO_EXACT_CURRENT_ORACLE_RECEIPT_JOIN'))
        native_units.append(dict(original_id=u['unit_id'], name=u['name'], subsystem_id=u['subsystem_id'],
            component_id=u['component_id'], specification=doc,
            original_specification_sha256=u['specification']['sha256'],
            original_hash_matches=doc['source']['sha256'] == u['specification']['sha256'],
            supplemental_acceptance_ids=u['acceptance_ids'], acceptance_source_rows=at_rows,
            implementation_status='UNIT_TO_CANONICAL_METHOD_BINDING_NOT_FULLY_RATIFIED',
            implemented_source_references=referenced_native_sources[u['unit_id']],
            source_reference_limit='An exact unit-ID mention is a source reference, not complete implementation or acceptance.',
            acceptance_status='OUTSTANDING_FILE_SPEC_COMPLETION_UNVERIFIED',
            blockers=['All 14 specification sections require exact method/caller coverage, including specific positive/adverse oracle, bounds, concurrency, recovery and actual neighbor integration.',
                      'No current source-bound independent receipt covering all ten exact supplemental IDs is established by this inventory.'],
            next_executable_closure=f"Reconcile {u['unit_id']} to the existing canonical owner; implement missing specified behavior and qualify all ten original AT IDs plus affected B cases without replacing either namespace."))
    subdirs = sorted(d for d in A.iterdir() if d.is_dir() and re.fullmatch(r'\d{2}-[A-Z-]+', d.name))
    subsystem_rows = []
    for d in subdirs:
        sid = d.name[:2]
        pattern = re.compile(r'^'+re.escape(d.name)+r' \|')
        start = next(i for i,line in enumerate(r6_lines) if pattern.match(line))
        stop = next((i for i in range(start+1, len(r6_lines)) if re.match(r'^\d{2}-[A-Z-]+ \|', r6_lines[i]) or r6_lines[i].startswith('H2. ')), min(start+40,len(r6_lines)))
        cross = '\n'.join(r6_lines[start:stop])
        wpids = sorted(set(re.findall(r'\bWP-\d{2}\b', cross)))
        cmps = sorted({cid for v in wp if v['id'] in wpids for cid in v.get('component_owners', []) if cid in compmap})
        docs = {}
        for name in ['README.md','ARCHITECTURE.md','BUILD-SEQUENCE.md','DEPENDENCIES.md','INTERFACE-CONTRACTS.md','ACCEPTANCE.md','TEST-MATRIX.md','FAILURE-AND-RECOVERY.md','FILE-INDEX.md']:
            if (d/name).exists(): docs[name] = source_sections(d/name)
        subsystem_rows.append(dict(original_id=sid, original_identity=d.name, source_root=str(d),
            units=[u['original_id'] for u in native_units if u['subsystem_id']==sid],
            logical_components=[x.name for x in sorted(d.iterdir()) if x.is_dir() and re.match(r'\d{2}\.\d{2}-',x.name)],
            documents=docs, r6_crosswalk_source=ref(R6,start+1,stop), r6_crosswalk_text=cross,
            original_work_package_crosswalk=wpids, related_canonical_components=cmps,
            related_implemented_paths=source_set(cmps), binding_limit='R6 work-package allocation only; 25 native groups and 25 CMP owners are distinct namespaces, not a 1:1 owner mapping.',
            gate_id=f'GATE-SUBSYSTEM-{sid}', gate_status='UNVERIFIED_NOT_CLOSED_BY_UNIT_COUNTS',
            blockers=['All unit, component, contract and subsystem acceptance criteria need exact delivered proof; partial modules do not close the subsystem.'],
            next_executable_closure='Use the existing subsystem BUILD-SEQUENCE and original WP prerequisites; reconcile each unit to one canonical owner and exercise actual producer-consumer paths before distinct subsystem acceptance.'))
    b_cases = []
    for row in registries['scenarios']['scenarios']:
        card = b_cards[row['id']]
        b_cases.append(dict(original=row, specification=source_sections(F/row['specification_path']),
            original_case_card=card, acceptance_status='OUTSTANDING_ORIGINAL_EVIDENCE_CLASS_NOT_ESTABLISHED',
            blocking_boundary='Contract-regression success and controlled substitutes do not establish this original scenario and its declared real-resource/installed/semantic/independent oracle.',
            next_executable_closure='Implement and execute the preserved case card plus every original variant through the ordinary declared entry and actual required resource/observer, then independently bind result to candidate/source/environment.'))
    lifecycle = []
    for original in registries['lifecycle']['sections']:
        f = F/original['path']
        doc = source_sections(f)
        lifecycle.append(dict(original=original, source_document=doc,
            applicability_status='PRESERVED_RECORDED_APPLICABILITY; original NA decisions are not automatically owner-ratified',
            acceptance_status='OUTSTANDING_CLAUSE_LEVEL_CONFORMANCE_NOT_ESTABLISHED',
            next_executable_closure='Reconcile original applicability/prerequisites and every required outcome at source-line granularity; bind actual code, original B oracles and distinct required evidence. Preserve dissent and unresolved exclusions.'))
    artifacts = {}
    for category, pattern in [('interfaces', 'INTERFACE-CONTRACTS/**/*.contract.md'),
                              ('e2e', 'ACCEPTANCE-CRITERIA/END-TO-END-SCENARIOS/*.md'),
                              ('acceptance_gates', 'ACCEPTANCE-CRITERIA/*.md')]:
        artifacts[category] = [dict(original_path=str(f.relative_to(A)).replace('\\','/'),
                                    document=source_sections(f), acceptance_status='UNVERIFIED_CURRENT_SOURCE_BOUND_ACCEPTANCE',
                                    next_executable_closure='Execute every original field/invariant/positive/adverse/recovery/entry/evidence predicate through the actual canonical producer and consumer and bind independent delivered results.')
                               for f in sorted(A.glob(pattern)) if f.is_file()]
    # Component README requirements carry normative parent flow/invariant details too.
    component_docs = [source_sections(f) for d in subdirs for f in sorted(d.glob('*-*/README.md'))]
    policy_rows = [dict(original=v, specification=source_sections(F/v['path']),
                        acceptance_status='OUTSTANDING_COMPILED_ENFORCEMENT_AND_REAL_NEGATIVE_ACCEPTANCE')
                   for v in registries['policies']['policies']]
    decision_rows = [dict(original=v, specification=source_sections(F/v['path']),
                          acceptance_status='PRESERVED_SOURCE_DECISION; runtime implementation/conformance unverified')
                     for v in registries['decisions']['decisions']]
    atomics = []
    for v in registries['atomic_tickets']['tickets']:
        paths = v.get('implementation', [])
        paths = [paths] if isinstance(paths,str) else paths
        observed = []
        for s in paths if isinstance(paths,list) else []:
            f = F/s
            if f.is_file(): observed.append(finishable_code(f))
        refs = []
        for item in v.get('evidence_refs', []):
            f = F/item
            refs.append(dict(reference=item,present=f.is_file(),status='HISTORICAL_SCOPE_NOT_PARENT_COMPLETION'))
        atomics.append(dict(original=v, observed_implementation=observed, evidence_reference_presence=refs,
                           parent_status='PARENT_REQUIREMENTS_REMAIN_OPEN',
                           acceptance_status='RECORDED_INCREMENT_SCOPE_ONLY; independent current full parent proof not established'))
    gates = [dict(original=g, acceptance_status='OPEN_NOT_INDEPENDENTLY_EVALUATED_AS_COMPLETE',
                  exact_blockers=['Required work-package exits, parent clauses and original evidence classes remain outstanding.',g['acceptance']],
                  next_executable_closure='Independently evaluate the original conjunctive gate only after every declared prerequisite has exact compatible delivered evidence.')
             for g in registries['gates']['gates']]
    closure_lanes = [
      dict(name='Publish the reviewed current source cut', source_ids=['A16','C12','C09','WP-00','WP-01','G-A'],
           paths=['src/ceta/store/journal.py','src/ceta/application/lifecycle.py','src/ceta/application/task_operator.py','src/ceta/contracts/editor_recovery.py'],
           evidence_candidates=['js7-20261015'], status='CURRENT_SOURCE_ACCEPTED_CT4_290; JS7_295_PENDING',
           blocker='The private JS7 15-path cut is separate from accepted Source290. Fresh candidate full1556, guarded publication, delivered full1556, distinct166, original backups and actual baseline acceptance are required.',
           next='Root consumes distinct reviewed tooling/companions and fresh source hashes; performs the existing guarded single-attempt source sequence and exact acceptance checks.', depends_on=[]),
      dict(name='Join independently reviewed native/authority libraries', source_ids=['C01','C09','C12','RE-T16','RE-T17','RE-T18','RE-T20','RE-T27','G-B'],
           paths=['src/ceta/kernel/transactions.py','src/ceta/kernel/cpu_execution.py','src/ceta/kernel/effect_transactions.py','src/ceta/identity/owner_session.py'],
           evidence_candidates=['fn6-20261015'],status='FROZEN_PRIVATE_LIBRARY_CUT_NOT_ACTIVE_SOURCE',
           blocker='FN6 library/component evidence and missing native/full gates cannot be inherited as accepted public runtime or blindly overlaid over current Source.',
           next='Reconcile selected accepted deltas against the newly accepted source, retain untouched newer bytes, run required connected/native/full and independent delivered gates.',depends_on=['Publish the reviewed current source cut']),
      dict(name='Canonical native execution retainer and physical outcome capacity', source_ids=['RE-T16','RE-T17','RE-T18','RE-T20','RE-T27','B016','G-B'],
           paths=['src/ceta/kernel/cpu_execution.py','src/ceta/kernel/transactions.py','src/ceta/kernel/effect_transactions.py','src/ceta/identity/owner_session.py'],
           evidence_candidates=['fn6-20261015'], status='MISSING_PRODUCTION_OWNER_CAPABILITY; NE1_UNSTARTED_AND_WITHDRAWN',
           blocker='Coordinator captures retain_owned_cpu_execution and transactions capture require_owned_cpu_outcome_current. NativeCpuOwnerSession supplies approval/preparation but not those production capabilities; no qualified physical outcome-storage/queue capacity provider was identified. Logical reserved bytes/free disk/Boolean are insufficient.',
           next='Implement on the same captured owner/kernel/journal and opaque original context/thread; retain exact native target/capture and canonical generations/Stop ordering, with explicit closed capacity dependency. Qualify real physical capacity separately before public activation.',depends_on=['Join independently reviewed native/authority libraries']),
      dict(name='Genuine owner enrollment and per-effect native approval', source_ids=['RE-T04','RE-T05','RE-T06','RE-T16','WP-03','G-B'],
           paths=['src/ceta/identity/native_approval.py','src/ceta/identity/native_owner_view.py','src/ceta/identity/owner_session.py','src/ceta/kernel/owner_authority.py'],status='GENUINE_HUMAN_APPROVAL_ACCEPTANCE_UNVERIFIED',
           blocker='Data contracts, controlled positive witnesses and native identity observations do not establish a genuine current enrollment/Hello approval or authorize cap/restore. Native helper/context/code/root identity and distinct approval domains must be demonstrated.',
           next='Use the existing explicit prepare/approve/execute/inspect/reconcile profile; display the exact committed request and obtain actual authenticated human approval only at that boundary.',depends_on=['Join independently reviewed native/authority libraries']),
      dict(name='Restricted worker isolation and independent native consequence', source_ids=['C16','RE-T09','RE-T10','RE-T18','WP-04','G-B'],
           paths=['src/ceta/supervisor/isolated_worker.py','src/ceta/supervisor/windows_jobs.py','src/ceta/effects/native_cpu_binding.py','src/ceta/effects/native_observer.py'],status='POSITIVE_RESTRICTED_PUBLIC_EFFECT_UNVERIFIED',
           blocker='Successful medium fixture observation/CPU or ordinary IPC qualification does not establish the selected no-capability restricted-token bypass-negative profile. Prior one-attempt restrictive launches failed; an operator-tool approval is not product authority.',
           next='Resolve the measured native restriction failure on a separately reviewed exact cut, then execute original token/handle/ACL/network/bypass and retirement predicates with actual approved resources; qualify independent cap and separately approved restore.',depends_on=['Canonical native execution retainer and physical outcome capacity','Genuine owner enrollment and per-effect native approval']),
      dict(name='Public compiler, application/model and continuing intelligence', source_ids=['D03','C14','WP-06','WP-07','WP-08','WP-09','WP-10','WP-11','WP-12','WP-16','G-C'],
           paths=['src/ceta/desktop/launcher.py','src/ceta/context','src/ceta/memory','src/ceta/inference','src/ceta/companion','src/ceta/reflection','src/ceta/shadow','src/ceta/review','src/ceta/orchestration'],status='PARTIAL_OR_ABSENT_CANONICAL_RUNTIME_CAPABILITIES_UNVERIFIED',
           blocker='Protected positive authority must precede the normal real RequestCompiler. Actual local model/assets, useful reasoning, continuity, memory/retrieval, independent review, tools and native human workflow need semantic and recovery qualification, not only interface/regression success.',
           next='Finish each original WP exit and mapped native file specification through the canonical model-free and local-model entry paths; execute exact original semantic/model/privacy/continuity oracles.',depends_on=['Restricted worker isolation and independent native consequence']),
      dict(name='Security, interoperability, modality, training and policy obligations',source_ids=['WP-13','WP-14','WP-15','WP-20','WP-21','G-D'],
           paths=['src/ceta/custody','src/ceta/cbcc','src/ceta/integrity','src/ceta/modalities','src/ceta/evaluation'],status='FULL_MANDATORY_LANES_UNVERIFIED',
           blocker='All selected policies, object custody, integrity/assumption propagation, CBCC, modalities/additional adapters and governed training/promotion remain mandatory. WP-21 is outside WP-27 ancestry and still required.',
           next='Implement and qualify exact source-defined lanes or obtain explicit scope decisions without silently treating unavailable mandatory capability as complete.',depends_on=['Public compiler, application/model and continuing intelligence']),
      dict(name='Preservation, adoption, source clauses and migration',source_ids=['C10','C17','WP-00','WP-01','WP-17','G-A','G-E'],
           paths=['requirements/requirements.json','standards/lifecycle_coverage.json','src/ceta/migration','tools/preserve_ceta_baseline.py'],status='FULL_ADOPTION_MIGRATION_AND_HISTORY_COMPLETION_UNVERIFIED',
           blocker='Partial HP1 capture, protected held categories, relevant branch selection/integration, original source adoption and clause-level conformance remain distinct. Historical NOT_APPLICABLE labels do not ratify all source exclusions. Original data-category migration/rollback needs actual rehearsal.',
           next='Reconcile exact retained originals and all source decisions, close authorized recoverable preservation/adoption and migration proofs, retain unresolved protected decisions and do not overwrite live profile.',depends_on=['Publish the reviewed current source cut']),
      dict(name='Formal build-status writer and completion admission',source_ids=['F01','F02','F03','F04','F05','F06','F07','F08','F09','F10','F11','F12'],
           paths=['tools/statuslib/schemas.py','tools/statuslib/evidence.py','tools/statuslib/predicates.py','tools/statuslib/reader.py','tools/statuslib/transaction.py','tools/status_admission.py'],status='V2_STATUS_ADMISSION_COMPLETION_UNVERIFIED',
           blocker='Scoped continuity observations do not implement or qualify the separate sole-writer v2 schemas, current predicates, generation reader, atomic per-file recovery and final pointer publication.',
           next='Follow the existing F01-F12 module order and actual Windows writer/recovery tests; keep product ledger separate and old metadata/evidence immutable.',depends_on=['Publish the reviewed current source cut']),
      dict(name='Installed offline, performance, recovery and independent verification',source_ids=['WP-18','WP-19','WP-22','WP-23','WP-24','G-F'],
           paths=['src/ceta/evaluation','src/ceta/verification','src/ceta/delivery','src/ceta/migration'],status='NOT_ESTABLISHED_ON_EXACT_INSTALLED_CANDIDATE',
           blocker='No inventory evidence closes exact full-stack semantic/performance/install/offline/OS-isolated/migration/recovery acceptance without a source checkout. An E3 development run is a different evidence class.',
           next='Build the exact candidate and verify actual installer, dependency/assets/SBOM, clean offline install, source-free ordinary journeys, update/restore, bounded growth and independent verifier on the designated environment.',depends_on=['Public compiler, application/model and continuing intelligence','Security, interoperability, modality, training and policy obligations','Preservation, adoption, source clauses and migration']),
      dict(name='Actual endurance, external/hardware and human acceptance',source_ids=['C11','C20','WP-25','WP-26','G-G'],
           paths=['acceptance/cases','src/ceta/evaluation'],status='ACTUAL_REQUIRED_TIME_HARDWARE_EXTERNAL_HUMAN_EVIDENCE_UNVERIFIED',
           blocker='Seven real days, real independent/domain/hardware identities and user-visible acceptance cannot be substituted by accelerated clocks, same-host agent separation, mocks, case counts or generated reports.',
           next='Execute the finite approved campaign on the exact compatible installed candidate with real elapsed checkpoints, hardware/domain observers, full refusal/recovery/effect/memory paths and human observations.',depends_on=['Installed offline, performance, recovery and independent verification']),
      dict(name='Owner cutover, one live authority, signing and release',source_ids=['C20','WP-27','G-H'],
           paths=['build/gates.json','handoff/continuity.json','src/ceta/delivery'],status='RESERVED_OWNER_DECISIONS_AND_FULL_ACCEPTANCE_PENDING',
           blocker='All 28 packages including WP-21, all original B/AT/source/policy and mandatory profile gates, exact verified artifacts and recovery must be complete before the separate current owner cutover/signing/publication decisions.',
           next='Independently evaluate all conjunctive product gates, present exact artifacts and preserved rollback path for the genuine scoped owner decisions, then verify one live authority.',depends_on=['Actual endurance, external/hardware and human acceptance','Formal build-status writer and completion admission'])]
    closure_lanes.insert(8, dict(name='Preservation-tool exceptional reader custody',
       source_ids=['C06','C10','C12','WP-00','G-A'],
       paths=['.agents/pr4-20261014/preserve_ceta_complete.py'],status='SEPARATE_UNRESOLVED_FAILURE_PATH_FOLLOW_UP',
       blocker='The immutable P4 ordinary-reader handle-to-descriptor-to-stream transfer and primary/secondary cleanup defects remain open. JS7 repairs its publisher-local reader only; it does not repair or qualify all P4 failure paths. WT evidence uses exact-function controlled counterexamples, not an actual native leak claim.',
       next='Preserve pinned P4 and WT report; prepare a separately reviewed narrow successor/owned reader for its affected consumers and qualify exact custody/close uncertainty before reuse on those exceptional paths.',
       depends_on=['Publish the reviewed current source cut']))
    # This reads only finite declared native-result records. It does not repeat any native run.
    native_reports = []
    for rel in ['.agents/runtime/os5n2-20261015/ROOT-NATIVE-FINDINGS.json',
                '.agents/runtime/os5n2-20261015/ROOT-CALLER-REPLAY.json',
                '.agents/runtime/ka5-20261015/native-readiness/ROOT-NATIVE-FINDINGS.json',
                '.agents/runtime/ac5-profile-tool-20261015/PREPARED-TOOL.json',
                '.agents/runtime/js5-publication-review-20261015/REPORT.json',
                '.agents/runtime/js7-20261015/independent-review/review.json',
                '.agents/runtime/fn6-20261015/independent-review/review.json']:
        path = F/rel
        if path.is_file():
            record = load(path)
            native_reports.append(dict(source=ref(path), record=record,
                scope='EXACT_RECORDED_NATIVE_OR_ENGINEERING_SCOPE_ONLY; no production authority or whole product inference'))
    route_rows = []
    for i, line in enumerate(r6_lines):
        if re.match(r'^CR-[0-9a-f]{16} \|', line):
            row = dict(original_id=line.split(' |')[0], original_line=line, source=ref(R6,i+1,min(i+2,len(r6_lines))),
                       following_binding=r6_lines[i+1] if i+1<len(r6_lines) else '',
                       status='CANONICAL_ROUTE_QUALIFICATION_UNVERIFIED')
            path_match = re.search(r'\| (T:\\[^|]+?) :: ([^|]+?) \|', line)
            if path_match:
                old, symbol = path_match.groups()
                normalized = old.replace('\\','/')
                suffix = None
                for prefix in ['/rebuild_ios/','/CETA_Intelligence_Operating_System_Build_Package/']:
                    if prefix in normalized: suffix=normalized.split(prefix,1)[1]
                row['original_symbol'] = symbol
                if suffix:
                    row['current_repository_path'] = str(F/suffix)
                    row['path_present'] = (F/suffix).is_file()
                    row['relocation_limit'] = 'Historical path spelling translated only; symbol/caller and full route qualification not inferred.'
            route_rows.append(row)
    # Preserve all line-level requirements across native parent/interface/acceptance docs and original source sections.
    js7 = load(F/'.agents/js7-20261015/TRANSFER-MANIFEST.json')
    fn6 = load(F/'.agents/fn6-20261015/TRANSFER-MANIFEST.json')
    js7_hashes = js7['expected_payload_hashes']
    fn6_hashes = {k:v['candidate']['sha256'] for k,v in fn6['payloads'].items()}
    forward_join = dict(js7_manifest=ref(F/'.agents/js7-20261015/TRANSFER-MANIFEST.json'),
        fn6_manifest=ref(F/'.agents/fn6-20261015/TRANSFER-MANIFEST.json'),
        shared_equal=[k for k,v in js7_hashes.items() if fn6_hashes.get(k)==v],
        shared_different=[k for k,v in js7_hashes.items() if k in fn6_hashes and fn6_hashes[k]!=v],
        missing_from_fn6=[k for k in js7_hashes if k not in fn6_hashes],
        added_by_fn6=sorted(set(fn6_hashes)-set(js7_hashes)),
        js7_publication_paths_match_fn6=all(fn6_hashes.get(k)==js7_hashes[k] for k in js7['application_paths']),
        acceptance='COMPATIBLE_CANDIDATE_STAGE_ONLY; fresh accepted-source binding and all delivery gates required')
    inventory = dict(schema='ceta.remaining-completion-inventory.v1', observed_at=START,
       repository=str(F), display_identity='Project-AI: CETA', author='/root/history_preservation',
       scope='EXHAUSTIVE ORIGINAL IDENTIFIER/CLAUSE-LOCATION INVENTORY WITH EXPLICIT SEMANTIC AND ACCEPTANCE GAPS',
       authority='Current user instruction freezes new features and prioritizes source integration and this single remaining-backlog inventory. The existing r6 and approved implementation plan remain the plans.',
       current_user_direction_verbatim=[
         'Freeze the product scope. No new features, subsystems, or architectural expansions beyond what the established full-product specification requires.',
         'Produce one authoritative completion inventory. All 25 subsystems, every remaining requirement, its current implementation evidence, its acceptance status, and its actual blocker. No invented percentages.',
         'Put everything on one critical path. Repair source publication and integration first. Then finish the canonical authorization-to-effect chain, followed by the remaining application, model, and runtime requirements.',
         'Stop using test counts as progress toward completion by themselves. Every accepted change must close a specific outstanding product requirement. Defects still get repaired, but the work must demonstrably reduce the remaining backlog.',
         'Finish with the real product acceptance. Installed, offline, functioning through its intended interfaces, executing authorized operations, refusing unauthorized ones, recovering properly, and satisfying its specified endurance and human acceptance requirements.'],
       dictionary_basis=dict(provenance='Exact Merriam-Webster definitions verified by Root and supplied in the delegated instruction; used only to anchor the established full-product scope.',
          finish=dict(sense='transitive 2a',definition='to bring to completion or issue',source='https://www.merriam-webster.com/dictionary/finish'),
          operational=dict(sense='3b',definition='ready for or in condition to undertake a destined function',source='https://www.merriam-webster.com/dictionary/operational')),
       execution=dict(NE1_candidate_created=False,NE1_runtime_created=False,NE1_claim_acquired=False,
           native_tests_run=0, product_tests_run=0, Source_writes=False,status_writes=False,
           inventory_writes_only=str(R), own_live_operations_at_switch=[]),
       interpretation_limits=[
           'Coverage cardinalities count retained source records and locators. They are never a completion percentage, test-count progress or accepted-requirement count.',
           'Every nonblank r6 line and every read file-spec line is retained. A line, sentence, paragraph, source section or test label is not necessarily one atomic semantic obligation. Unsplit conjuncts and applicability/currentness reconciliation stay explicitly open.',
           'The 35 atomic tickets explicitly cover current earlier increments only. They are not the complete product backlog and do not replace the 175 requirement groups,432 unit specs,406 source sections or original cases.',
           'Presence of source methods, candidate manifests, node states or historical tests cannot establish original whole-product acceptance. This inventory executes no product tests and does not reapprove any component.',
           'Active code is the current repository. Historical S/D/architecture absolute paths in r6 are provenance. Current explicit resume and sole-repository authority supersede old A14 hold and former active-source roots; old source wording is preserved.',
           'All accepted source evidence is bound to CT4 exact290 until a later independently established acceptance supersedes it. Candidate and current publication observations are time-bound and separately recorded.',
           'Source observation uses ordinary-file lstat/read bracketing and hashes, no retained native handles or machine isolation. It is not whole Git/ignored/worktree conservation or native safety qualification.',
           'This author built several earlier candidates including JS2/KA4/JS6/JS7. Their independent acceptance must come from their recorded distinct reviewers, never this inventory.',
           'No external project content, user-private data, credentials, profiles or native processes were read or operated by this inventory.'
       ],
       git_observation=git, accepted_source=dict(record=baseline, source=ref(baseline_path),
           current_payload_comparison=current, all_expected_payloads_match=all(z['matches'] for z in current.values()),
           limit='Byte currentness only; historical accepted full regression does not close original product gates.'),
       registry_sources={k:ref(F/v) for k,v in registry_paths.items()},
       r6=dict(source=ref(R6),lines=len(r6_lines),blocks=r6_blocks,
           semantic_conjunct_status='NOT_FULLY_RATIFIED; original source lines remain outstanding until exact source/code/oracle/evidence join'),
       requirements=requirements, atomic_tickets=atomics,work_packages=package_rows,global_gates=gates,
       canonical_components=[dict(original=c,actual_implementation=code_by_component[c['id']],
           status='PARTIAL_PRESENCE_OR_ABSENCE_OBSERVED; FULL_COMPONENT_ACCEPTANCE_UNVERIFIED') for c in components],
       native_subsystems=subsystem_rows,native_units=native_units,native_component_specifications=component_docs,
       native_interfaces=artifacts['interfaces'],native_e2e_scenarios=artifacts['e2e'],native_acceptance_requirements=artifacts['acceptance_gates'],
       original_B_cases=b_cases,source_lifecycle=lifecycle,policies=policy_rows,architecture_decisions=decision_rows,
       source_volumes=registries['volumes'],canonical_routes=route_rows,
       candidate_catalog=candidates,current_source_code_index=code,native_observations=native_reports,
       candidate_integration_join=forward_join,
       remaining_critical_path=closure_lanes,
       original_work_package_dependency_layers=scope['package_dag_layers'],
       original_native_readiness_waves=source_sections(A/'DEPENDENCY-MAPS/BUILD-ORDER-GRAPH.md'),
       dependency_rule='Original WP edges govern mandatory package dependencies. Native W00-W11 are interface readiness only. Closure lanes are evidence classifications derived from existing plan, not new architecture or new WP edges.',
       inventory_errors=ERRORS,whole_product_complete=False,all_mandatory_requirements_accepted=False,
       collaborative_review=dict(state='PENDING_ROOT_AND_DISTINCT_REVIEW',changes_after_review='NEW IMMUTABLE SUCCESSOR ONLY'))
    inventory['coverage_cardinalities'] = dict(
        native_subsystems=len(subsystem_rows), canonical_components=len(components), requirement_groups=len(requirements),
        requirement_sentences_retained=sum(len(r['requirement_sentences']) for r in requirements),
        requirement_atomic_conjuncts_fully_qualified='UNVERIFIED', atomic_increment_tickets=len(atomics),
        work_packages=len(package_rows),global_gates=len(gates), original_B_cases=len(b_cases),
        original_planned_B_variants=sum(len(v.get('variant_matrix', [])) for v in b_cards.values()),
        native_units=len(native_units), native_unit_specification_hashes_matching=sum(u['original_hash_matches'] for u in native_units),
        native_file_sections=sum(len(u['specification']['sections']) for u in native_units),
        supplemental_AT_identifiers=len({a for u in native_units for a in u['supplemental_acceptance_ids']}),
        native_component_documents=len(component_docs),native_contracts=len(artifacts['interfaces']),native_E2E_scenarios=len(artifacts['e2e']),
        lifecycle_source_sections=len(lifecycle),policies=len(policy_rows),architecture_decisions=len(decision_rows),
        source_volumes=len(registries['volumes']['volumes']), canonical_routes=len(route_rows),
        r6_total_lines=len(r6_lines),r6_nonblank_lines=sum(bool(l.strip()) for l in r6_lines),
        r6_retained_nonblank_lines=sum(sum(bool(l.strip()) for l in b['text'].splitlines()) for b in r6_blocks),
        candidate_manifests_observed=len(candidates), active_source_code_files=len(code),
        source_payloads_in_accepted_baseline=len(current), original_case_acceptance_established_by_this_inventory=0)
    # Verify all indexed normative sources again. Mutable lifecycle observations are explicitly excluded.
    mismatches = []
    for rel, original in SOURCE_PINS.items():
        f = F/rel
        if not f.exists() or sha(f.read_bytes()) != original['sha256']:
            mismatches.append(rel)
    inventory['source_read_conservation'] = dict(observed_end=datetime.now(timezone.utc).isoformat(),
        ordinary_input_files=len(SOURCE_PINS),changed_inputs=mismatches,
        stable_normative_input_bytes=not mismatches,
        mutable_runtime_states='Time-bound observations; not asserted unchanged across independent authorized actions.')
    inventory['source_catalog'] = SOURCES
    return inventory


def render(x):
    """The rendering reads only the emitted JSON; no independent facts or status edits."""
    out = ['# Project-AI: CETA — remaining completion inventory', '',
           f"Observed: {x['observed_at']}", '',
           'Product completion remains unverified. The accepted source, private candidates and original acceptance obligations are recorded separately below.', '',
           'Coverage counts enumerate source records. They do not measure product completion.', '',
           '| Source scope | Retained count |', '| --- | --- |']
    for k,v in x['coverage_cardinalities'].items(): out.append(f'| {k} | {v} |')
    out += ['', '## Accepted source and active work', '',
            f"Accepted source: `{x['accepted_source']['source']['path']}`; SHA256 `{x['accepted_source']['source']['sha256']}`.",
            f"Current comparison of its expected payloads: `{x['accepted_source']['all_expected_payloads_match']}`. Whole-product acceptance: `{x['whole_product_complete']}`.", '',
            '## Concrete remaining critical path', '']
    for lane in x['remaining_critical_path']:
        out += [f"### {lane['name']}", '', f"Status: **{lane['status']}**", '',
                f"Original references: {', '.join(lane['source_ids'])}", '',
                f"Blocker: {lane['blocker']}", '', f"Next executable closure: {lane['next']}", '',
                'Paths: '+', '.join(f'`{str(F/rel)}`' for rel in lane['paths']), '',
                'Dependencies: '+(', '.join(lane['depends_on']) or 'Existing source and engineering authority'), '']
    out += ['## Original global gates', '']
    for g in x['global_gates']:
        z=g['original'];out += [f"### {z['id']} — {z['name']}", '', f"Status: {g['acceptance_status']}",
          '', 'Required work packages: '+', '.join(z['required_work_packages']), '', z['acceptance'], '',g['next_executable_closure'],'']
    out += ['## All 25 original native subsystems', '']
    for s in x['native_subsystems']:
        out += [f"### {s['original_identity']}", '', f"Gate: {s['gate_id']} — {s['gate_status']}", '',
                'Original work-package crosswalk: '+', '.join(s['original_work_package_crosswalk']), '',
                'Units: '+', '.join(s['units']), '', s['binding_limit'], '', s['next_executable_closure'], '']
    out += ['## Original 28 work packages and exact exits', '']
    for w in x['work_packages']:
        z=w['original'];out += [f"### {z['id']} — {z['title']}", '',w['acceptance_status'],'',
            'Dependencies: '+(', '.join(z['depends_on']) or 'None declared'),'',
            'Requirements: '+', '.join(w['remaining_requirement_ids']), '',
            'Original cases: '+', '.join(w['remaining_original_case_ids']), '',
            f"Exact specification: `{w['specification']['source']['path']}` SHA256 `{w['specification']['source']['sha256']}`.", '',w['next_executable_closure'],'']
    out += ['## All 175 requirement groups, preserving original wording', '']
    for r in x['requirements']:
        z=r['original'];out += [f"### {z['id']} — {z['title']}", '',z['requirement_text'],'',
            f"Status: {r['acceptance_status']}", '',r['semantic_conjunct_coverage'],'',
            'Work packages: '+', '.join(r['work_package_ids']), '',
            'Original acceptance: '+', '.join(z.get('acceptance_ids', [])), '',
            'Observed canonical source: '+(', '.join(f'`{s}`' for s in r['implemented_source_paths']) or 'No executable source found in mapped canonical owners.'), '',
            r['next_executable_closure']['action'],'']
    out += ['## All 128 original B cases', '']
    for b in x['original_B_cases']:
        z=b['original']; card=b['original_case_card']
        out += [f"### {z['id']} — {z['title']}", '', z['normative_scenario'],'',
                f"Evidence class: {z['required_evidence_class']}; status: {b['acceptance_status']}.",'',
                f"Exact specification: `{b['specification']['source']['path']}`.",'',
                'Required variants (original card, unchanged):', '',
                '```json',json.dumps(card.get('variant_matrix', []),ensure_ascii=False,indent=2),'```','',
                b['blocking_boundary'],'',b['next_executable_closure'],'']
    out += ['## All 432 native implementation units and 4,320 supplemental acceptance IDs','']
    for u in x['native_units']:
        out += [f"### {u['original_id']} — {u['name']}",'',u['acceptance_status'],'',
                f"Detailed source: `{u['specification']['source']['path']}` SHA256 `{u['specification']['source']['sha256']}`.",'',
                'Supplemental IDs: '+', '.join(u['supplemental_acceptance_ids']),'',
                'Observed exact unit references: '+(', '.join(f'`{z}`' for z in u['implemented_source_references']) or 'No exact unit-ID code binding established.'),'',
                u['next_executable_closure'],'']
        for section in u['specification']['sections']:
            out += [f"{section['heading'] or 'Source preamble'} — source lines {section['source_lines'][0]}–{section['source_lines'][1]}; acceptance unverified.",'']
    out += ['## All 406 original lifecycle sections','']
    for c in x['source_lifecycle']:
        z=c['original'];out += [f"### {z['section']} — {z['original_title']}",'',
           'Original applicability: '+str(z.get('applicability')),'',c['applicability_status'],'',
           str(z.get('original_required_outcome','')),'',c['acceptance_status'],'',
           f"Source: `{c['source_document']['source']['path']}` SHA256 `{c['source_document']['source']['sha256']}`.",'',
           c['next_executable_closure'],'']
    for field,label in [('policies','24 original policies'),('architecture_decisions','22 original architecture decisions'),('atomic_tickets','35 historical incremental tickets')]:
        out += [f'## {label}','']
        for v in x[field]:
            z=v['original'];out += [f"### {z.get('id')} — {z.get('title', z.get('obligation',''))}",'',
              v.get('acceptance_status','UNVERIFIED'),'','```json',json.dumps(z,ensure_ascii=False,indent=2),'```','']
    out += ['## Candidate versus integrated evidence','',
            '| Candidate | Recorded implement/review/integrate | Selected application paths | Source acceptance |',
            '| --- | --- | --- | --- |']
    for c in x['candidate_catalog']:
        ns=c['lifecycle'].get('nodes',{}); state='/'.join(str(ns.get(k,{}).get('state','NOT_OBSERVED')) for k in ['implement','review','integrate'])
        out.append(f"| {c['run_id']} | {state} | {len(c['application_paths'])} | {c['acceptance_status']} |")
    out += ['', '## Complete r6 source-location ledger','',
            'Every nonblank line is retained verbatim below. Original identifiers are preserved. Locators are source references, not invented normative clause IDs. Semantic conjunct closure and source-specific acceptance remain open.','']
    for b in x['r6']['blocks']:
        out += [f"### r6 lines {b['line_start']}–{b['line_end']}",'',
                'Original identifiers: '+(', '.join(b['original_identifiers']) or 'No explicit original ID; source locator only.'),'',
                '```text',b['text'],'```','']
    out += ['## Scope limits and remaining reconciliation gaps','']
    out += ['- '+s for s in x['interpretation_limits']]
    out += ['',f"Source read conservation: {json.dumps(x['source_read_conservation'],ensure_ascii=False)}",'',
            f"Collaborative review: {x['collaborative_review']['state']}",'']
    return '\n'.join(out)


def exclusive(path, raw):
    path=Path(path)
    if path.parent != R:
        raise ValueError('Output must be a direct child of the assigned inventory scope')
    with path.open('xb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())


if __name__ == '__main__':
    x=make_inventory()
    path=R/'COMPLETION-INVENTORY.json'
    exclusive(path,(json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    # Rendering is derived from exactly the persisted authoritative JSON.
    persisted=json.loads(path.read_text(encoding='utf-8'))
    exclusive(R/'COMPLETION-INVENTORY.md',render(persisted).encode('utf-8'))
    print(json.dumps(dict(json=str(path),json_sha256=sha(path.read_bytes()),
          markdown_sha256=sha((R/'COMPLETION-INVENTORY.md').read_bytes()),
          coverage=x['coverage_cardinalities'],errors=len(ERRORS),
          source_conservation=x['source_read_conservation']),indent=2))
