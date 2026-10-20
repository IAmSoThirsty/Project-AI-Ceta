"""Correct source-metadata inflation/attribution; preserve the frozen r2 cut."""
from pathlib import Path
from datetime import datetime,timezone
import ast
import copy
import hashlib
import importlib.util
import json
import re

F=Path('T:/00-Active/Project-AI-CETA')
R=F/'.agents/runtime/product-completion-20261015'
D=R/'qualified-r3'
P=R/'qualified-r2/COMPLETION-INVENTORY.json'
def sha(raw):return hashlib.sha256(raw).hexdigest()
assert sha(P.read_bytes())=='746a3438b1d8cf2ff4a0d90e924a43a89dbc19715a032751cd32fb53e6900f0d'
x=json.loads(P.read_text(encoding='utf-8'))
REMOVED=['status','acceptance_status','implementation_evidence','missing_evidence','actual_blocker',
         'next_executable_closure','governing_obligation','unsplit_conjuncts']

def classification(line,heading,previous='',following='',fenced=False):
 s=line.strip(); h=(heading or '').lower()
 if s.startswith('#'):return 'HEADING_PROVENANCE'
 if re.match(r'^\*\*(?:Document ID|Package edition|Document state|Implementation and runtime evidence|Status|Source|Version|Date|Author|Revision|Runtime state)\s*:',s,re.I):return 'DOCUMENT_METADATA_PROVENANCE'
 if re.match(r'^(?:Document ID|Package edition|Document state|Prepared:|Status:|Version:|Source:|Input .*SHA|Gate ID:|Initial runtime state:)',s,re.I):return 'DOCUMENT_METADATA_PROVENANCE'
 if re.match(r'^[-=_*]{3,}$',s):return 'FORMAT_PROVENANCE'
 if re.match(r'^\|[\s:|\-]+\|$',s):return 'TABLE_FORMAT_PROVENANCE'
 if s.startswith('|') and re.match(r'^\|[\s:|\-]+\|$',following.strip()):return 'TABLE_HEADER_PROVENANCE'
 if s.startswith('```'):return 'CODE_BLOCK_DELIMITER_PROVENANCE'
 if fenced:return 'CODE_OR_DATA_BLOCK_CONTEXT_NOT_AUTOMATIC_WORK'
 if re.search(r'\b(example|illustrative|example-only|illustration|sample)\b',h):return 'EXAMPLE_CONTEXT_NOT_AUTOMATIC_WORK'
 if re.match(r'^(?:For example|For illustration|e\.g\.)\b',s,re.I):return 'EXAMPLE_CONTEXT_NOT_AUTOMATIC_WORK'
 if re.search(r'\bAT-CETA-\d{2}\.\d{2}\.\d{2}-\d{2}\b',s):return 'ORIGINAL_ACCEPTANCE_PREDICATE_REFERENCE'
 if s.startswith('|'):return 'DECLARED_TABLE_CONTENT_REQUIRES_CONTEXTUAL_SEMANTIC_MAPPING'
 if re.search(r'\b(must|shall|required|requirement|never|prohibit|mandatory|acceptance|invariant|success|reject|deny|fail.closed|not.applicable)\b',s,re.I):return 'NORMATIVE_OR_APPLICABILITY_TEXT_REQUIRES_SEMANTIC_MAPPING'
 return 'SOURCE_CONTEXT_REQUIRES_CLASSIFICATION_NOT_AUTOMATIC_WORK'

def classify_doc(doc):
 # Source statements remain source records, never independently minted work IDs.
 for section in doc['sections']:
  for k in REMOVED:section.pop(k,None)
  section['record_kind']='SOURCE_SECTION_PROVENANCE'
  section['completion_work_item']=False
  section['semantic_mapping']='Normative predicates must be resolved under their actual original obligation; this section/location count creates no additional task.'
  rows=section['statements'];fenced=False
  defining=None
  match=re.search(r'\bREQ-\d{2}-\d{2}\b',section.get('heading') or '')
  if match:defining=match.group()
  for i,row in enumerate(rows):
   line=row['text'];kind=classification(line,section.get('heading'),rows[i-1]['text'] if i else '',rows[i+1]['text'] if i+1<len(rows) else '',fenced)
   for k in REMOVED:row.pop(k,None)
   row['record_kind']=kind;row['completion_work_item']=False
   row['actual_requirement_section_id']=defining
   row['semantic_status']=('NO_EXECUTABLE_TASK_FOR_PROVENANCE' if kind.endswith('PROVENANCE') or 'EXAMPLE' in kind else 'CONTEXTUAL_MAPPING_UNVERIFIED; NOT_AN_ADDITIVE_WORK_ITEM')
   if line.strip().startswith('```'):fenced=not fenced
 return doc

def walk_docs(obj,seen):
 if isinstance(obj,dict):
  if 'source' in obj and isinstance(obj.get('sections'),list) and obj.get('coverage'):
   if id(obj) not in seen:classify_doc(obj);seen.add(id(obj))
  for value in list(obj.values()):walk_docs(value,seen)
 elif isinstance(obj,list):
  for value in obj:walk_docs(value,seen)

walk_docs(x,set())
# Keep each original SPEC document once for context. A REQ row includes only its own section.
documents={}
components={c['original']['id']:c for c in x['canonical_components']}
for row in x['requirements']:
 ident=row['original']['id'];doc=row['detailed_specification'];path=doc['source']['path']
 documents.setdefault(path,copy.deepcopy(doc))
 selected=[s for s in doc['sections'] if re.search(r'(?<![A-Z0-9-])'+re.escape(ident)+r'(?![A-Z0-9-])',s.get('heading') or '')]
 if len(selected)!=1:raise ValueError(f'Exact defining source section is ambiguous for {ident}: {len(selected)}')
 row['detailed_specification']={'source':doc['source'],'sections':selected,
    'context_document_reference':path,'coverage':'EXACT_OWN_REQUIREMENT_SECTION_ONLY; full source preserved once in original_specification_documents'}
 row['actual_source_section_id']=ident
 row['containing_document_is_not_per_requirement_evidence']=True
 direct=[c for c in x['canonical_components'] if row['original']['section'] in c['original'].get('section_ids',[])]
 row['related_work_package_source_paths']=row['implemented_source_paths']
 ownpaths=sorted({p['source']['path'] for c in direct for p in c['actual_implementation']})
 row['implemented_source_paths']=ownpaths
 row['implementation_binding']='DIRECT_REGISTERED_SPEC_TO_COMPONENT_PATH_ONLY; source presence does not establish this requirement behavior'
 row['direct_canonical_component_ids']=[c['original']['id'] for c in direct]
 absent=[c['original']['path'] for c in direct if not c['actual_implementation']]
 present=[c['original']['path'] for c in direct if c['actual_implementation']]
 row['implementation_assessment']={
   'evidence_kind':'OBSERVED_SOURCE_PRESENCE_OR_ABSENCE; REQUIREMENT_SEMANTICS_NOT_FULLY_ASSESSED',
   'registered_component_paths_with_code':present,'registered_component_paths_without_code':absent,
   'semantic_implementation_state':'UNVERIFIED_NOT_AUTOMATICALLY_MISSING',
   'scope':'Exact recorded Source290 observation; private candidate deltas are separate.'}
 row['implementation_evidence']={'direct_source_paths':ownpaths,
   'source_index_reference':'current_source_code_index','candidate_catalog_reference':'candidate_catalog',
   'accepted_source_reference':'accepted_source','qualification_limit':'These sources are observed; full requirement-specific behavior and oracle evidence were not completely assessed.'}
 row['missing_evidence']='EVIDENCE_NOT_FULLY_INSPECTED_OR_JOINED: no complete exact requirement-conjunct to source/candidate/oracle/independent acceptance decision was established by this inventory.'
 row['actual_blocker']={'kind':'SEMANTIC_ASSESSMENT_AND_ACCEPTANCE_JOIN_UNRESOLVED',
   'known_local_absence':absent,'known_local_absence_limit':'No executable code in these direct registered directories at the source observation; alternate or candidate fulfillment is not inferred absent.',
   'required_original_outcome':row['original']['requirement_text'],
   'required_original_cases':row['original'].get('acceptance_ids',[]),
   'uninspected_is_not_missing_implementation':True}
 row['backlog_role']='ORIGINAL_PARENT_OBLIGATION; NOT_A_CLAIM_OF_COMPLETE_ATOMIC_DECOMPOSITION'
 for sentence in row['requirement_sentences']:
  for k in REMOVED:sentence.pop(k,None)
  sentence.update(record_kind='SOURCE_SENTENCE_WITHIN_ORIGINAL_REQUIREMENT',
    actual_requirement_section_id=ident,completion_work_item=False,
    semantic_status='Conjunct decomposition unverified; this sentence is neither an invented requirement ID nor an additional accepted work item.')
x['original_specification_documents']=documents
for block in x['r6']['blocks']:
 for k in REMOVED:block.pop(k,None)
 block['record_kind']='R6_SOURCE_LOCATION_PROVENANCE'
 block['completion_work_item']=False
 block['semantic_status']='Original normative obligations are accounted by their original registry/specification rows. This location creates no generic coding task; superseded scope, headings, metadata and examples remain context.'
for ticket in x['atomic_tickets']:
 ticket['backlog_role']='HISTORICAL_INCREMENT_RECORD; parent requirement rows govern remaining completion'
 ticket['implementation_assessment']='Recorded scope/evidence retained; current complete parent semantics were not fully assessed.'
for field in ['native_units','native_subsystems','native_interfaces','native_e2e_scenarios','native_acceptance_requirements','source_lifecycle','policies','architecture_decisions','canonical_routes','global_gates','work_packages','original_B_cases']:
 for row in x[field]:
  row['implementation_assessment']='SOURCE_AND_EVIDENCE_REFERENCES_RETAINED; exact complete semantic fulfillment/evidence not fully assessed. Not a claim every implementation is missing.'
  row['evidence_inspection_status']='FULL_ORIGINAL_ACCEPTANCE_NOT_ESTABLISHED_IN_INSPECTED_CUT; uninspected records remain unverified rather than asserted nonexistent.'
for c in x['canonical_components']:
 c['observed_implementation_state']=('EXECUTABLE_SOURCE_PRESENT_FULL_BEHAVIOR_UNVERIFIED' if c['actual_implementation'] else 'NO_EXECUTABLE_FILES_OBSERVED_IN_REGISTERED_DIRECTORY')
for lane in x['remaining_critical_path']:
 lane['assessment_kind']='EVIDENCE_OR_INTEGRATION_PENDING'
 if lane['name']=='Canonical native execution retainer and physical outcome capacity':lane['assessment_kind']='KNOWN_INSPECTED_MISSING_OWNER_CAPABILITIES_AND_UNQUALIFIED_PHYSICAL_CAPACITY_SEAM'
 elif 'Preservation-tool' in lane['name']:lane['assessment_kind']='VERIFIED_CONTROLLED_EXCEPTION_CUSTODY_DEFECT_SEPARATE_FOLLOW_UP'
 elif lane['name']=='Public compiler, application/model and continuing intelligence':lane['assessment_kind']='PARTIAL_SOURCE_AND_OBSERVED_REGISTERED_DIRECTORY_GAPS; FULL_SEMANTIC_ASSESSMENT_PENDING'

# Exact finite static proof of the specifically inspected missing capability, not a Boolean/default provider.
q=F/'.agents/fn6-20261015'
facts=[]
for rel in ['src/ceta/kernel/cpu_execution.py','src/ceta/kernel/transactions.py','src/ceta/identity/owner_session.py','contracts/OWNED_CPU_EXECUTION_V1.md']:
 f=q/rel;raw=f.read_bytes();body=raw.decode('utf-8-sig');lines=body.splitlines()
 facts.append({'path':str(f),'sha256':sha(raw),'bytes':len(raw),
  'capability_callsite_lines':[{'line':i+1,'text':s.strip()} for i,s in enumerate(lines) if 'retain_owned_cpu_execution' in s or 'require_owned_cpu_outcome_current' in s],
  'owner_class_declared_methods':{n.name:[s.name for s in n.body if isinstance(s,(ast.FunctionDef,ast.AsyncFunctionDef))] for n in ast.parse(body).body if isinstance(n,ast.ClassDef) and n.name in ['NativeOwnerSession','NativeCpuOwnerSession']} if f.suffix=='.py' else {},
  'observation':'STATIC_EXACT_CANDIDATE_BYTES; no import or native/product execution'})
x['known_native_owner_interface_gap']={'assessment':'KNOWN_MISSING_IN_INSPECTED_PRODUCTION_OWNER',
 'required_capabilities':['retain_owned_cpu_execution','require_owned_cpu_outcome_current'],
 'facts':facts,'physical_capacity_assessment':'NO_QUALIFIED_PRODUCTION_PHYSICAL_OUTCOME_CAPACITY_PROVIDER_IDENTIFIED_IN_INSPECTED_SESSION/COORDINATOR_CONTRACT; logical reserves are not sufficient',
 'next_executable_closure':'Implement the same-owner retainer/currentness domain integration against canonical kernel/store and original context, retaining an explicit closed dependency until the physical/native/genuine-approval capacity profile is actually qualified.'}
x['inventory_revision']={'prepared_at':datetime.now(timezone.utc).isoformat(),
 'reason':['Root/PW F01: headings/metadata/examples must remain provenance, not invented work.',
           'PW F02: a REQ may not inherit the entire containing SPEC document as its own obligation/evidence.',
           'Distinguish exact observed missing interface/path from semantics/evidence not yet inspected.'],
 'predecessor':{'path':str(P),'sha256':sha(P.read_bytes())},
 'remaining_limit':'This is a concrete original-obligation/backlog inventory with explicit semantic-assessment gaps. It is not a claim that the requested complete semantic source-to-code mapping is finished.'}
x['authoritative_inventory_path']=str(D/'COMPLETION-INVENTORY.json')
x['scope']='ORIGINAL COMPLETION OBLIGATIONS AND CONCRETE REMAINING CLOSURE LANES; SOURCE LOCATORS ARE PROVENANCE, NOT EXTRA WORK'
x['collaborative_review']['state']='PENDING_ROOT_AND_DISTINCT_REVIEW_OF_R3'
D.mkdir(exist_ok=False)
with (D/'COMPLETION-INVENTORY.json').open('x',encoding='utf-8') as s:json.dump(x,s,ensure_ascii=False,indent=2);s.write('\n')
# Existing rendering algorithm remains derived from the authoritative JSON; clarify source-location appendix role.
spec=importlib.util.spec_from_file_location('inventory_render_only',R/'build_inventory.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
render=m.render(x)
render=render.replace('## Complete r6 source-location ledger','## r6 provenance appendix — no additional work items')
render=render.replace('Every nonblank line is retained verbatim below. Original identifiers are preserved. Locators are source references, not invented normative clause IDs. Semantic conjunct closure and source-specific acceptance remain open.',
 'Every nonblank line is retained verbatim as provenance. Headings, metadata, table structure, examples and context are not implementation tasks. Actual remaining obligations use their original registry/specification rows. Source/code/oracle semantic assessment remains explicitly unresolved where recorded.')
with (D/'COMPLETION-INVENTORY.md').open('x',encoding='utf-8') as s:s.write(render)
print(json.dumps({'json':str(D/'COMPLETION-INVENTORY.json'),'json_sha256':sha((D/'COMPLETION-INVENTORY.json').read_bytes()),
 'markdown_sha256':sha((D/'COMPLETION-INVENTORY.md').read_bytes()),'defining_REQ_sections':len(x['requirements']),
 'source_documents_deduplicated':len(documents),'critical_path_entries':len(x['remaining_critical_path'])},indent=2))
