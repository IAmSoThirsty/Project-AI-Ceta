"""Pure-data V2 symbol derivation; never import a native loader module."""
from pathlib import Path, PurePosixPath
import argparse
import ast
import hashlib
import json
import re
import stat
import struct

F=Path('T:/00-Active/Project-AI-CETA')
R=F/'.agents/runtime/operational-resume-20261020'
W=Path(__file__).resolve().parent
S1=R/'loader-symbol-inputs-r1/work'
L3=R/'loader-capture-r3'
L5=R/'loader-capture-r5'
S1_FREEZE='d8e5dfe69680150d7b7a7ca60d7764e170896c879433e12ce414660b35aab392'
V1_PIN='4ff2ef0171010a72eea91c3dd943c3a86636db9209fee8f2eeea91e1480579b1'
L3_FREEZE='0e3d1e4b0d17cc9910028cefebedead4c1a75de0bc3f32fd1225291b1480a569'
L3_CODE='c9b7f00825bffcfaee0f34ae728affa1120a03506d2c3d549a9d16bdd39a050e'
PARSER_NAMES=('pe_codeview','pdb_codeview','match_codeview')

class DataError(ValueError):pass

def require(value,message):
    if not value:raise DataError(message)

def sha(raw):return hashlib.sha256(raw).hexdigest()

def read(path):
    path=Path(path)
    require(path.is_absolute(),'ABSOLUTE_INPUT_REQUIRED')
    for part in (path,*path.parents):
        info=part.lstat()
        require(not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&1024,'REPARSE_INPUT_REFUSED')
    before=path.stat();require(stat.S_ISREG(before.st_mode),'REGULAR_INPUT_REQUIRED')
    raw=path.read_bytes();after=path.stat()
    identity=lambda item:(item.st_dev,item.st_ino,item.st_size,item.st_mtime_ns)
    require(identity(before)==identity(after) and len(raw)==after.st_size,'INPUT_CHANGED_DURING_READ')
    return raw,dict(path=str(path),bytes=len(raw),sha256=sha(raw),device=after.st_dev,inode=after.st_ino,mtime_ns=after.st_mtime_ns)

def safe_relative(text):
    require(type(text) is str and text and not any(c in text for c in '\\:\x00\r\n'),'UNSAFE_RELATIVE_PATH')
    path=PurePosixPath(text)
    require(not path.is_absolute() and path.as_posix()==text and all(p not in ('.','..') for p in path.parts),'UNSAFE_RELATIVE_PATH')
    return path

def parse(raw):
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result,'DUPLICATE_JSON_KEY');result[key]=value
        return result
    def nonfinite(value):raise DataError('NONFINITE_JSON_REFUSED')
    return json.loads(raw.decode('utf-8-sig'),object_pairs_hook=pairs,parse_constant=nonfinite)

def pinned_json(path,digest):
    raw,pin=read(path);require(pin['sha256']==digest,'JSON_PIN_CHANGED')
    return parse(raw)

def reference(path):
    path=Path(path);require(path.resolve().is_relative_to(F.resolve()),'REFERENCE_OUTSIDE_PROJECT')
    return dict(repository_relative_path=path.relative_to(F).as_posix(),sha256=read(path)[1]['sha256'])

def verify_freeze(root,name,digest):
    manifest=pinned_json(root/name,digest);files=manifest['files']
    require(type(files) is dict and files,'EMPTY_FREEZE')
    for relative,expected in files.items():
        safe_relative(relative);raw,_=read(root/relative)
        if type(expected) is dict:
            require(set(expected)=={'bytes','sha256'} and len(raw)==expected['bytes'],'FROZEN_SIZE_CHANGED')
            expected=expected['sha256']
        require(type(expected) is str and sha(raw)==expected,'FROZEN_FILE_CHANGED:'+relative)
    return len(files)

def parsers(source,digest):
    require(type(source) is bytes and sha(source)==digest,'PARSER_SOURCE_CHANGED')
    tree=ast.parse(source);selected=[];records=[]
    for name in PARSER_NAMES:
        nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name==name]
        require(len(nodes)==1,'EXACT_PARSER_FUNCTION_REQUIRED')
        node=nodes[0]
        require(not node.decorator_list and not node.args.defaults and not any(node.args.kw_defaults),'PARSER_DEFINITION_EFFECT_REFUSED')
        require(not any(isinstance(item,(ast.Import,ast.ImportFrom,ast.Global,ast.Nonlocal)) for item in ast.walk(node)), 'PARSER_IMPORT_OR_GLOBAL_REFUSED')
        selected.append(node)
        records.append(dict(name=name,ast_sha256=sha(ast.dump(node,include_attributes=False).encode()),first_line=node.lineno,last_line=node.end_lineno))
    namespace=dict(struct=struct,re=re,require=require,CaptureError=DataError)
    # Only undecorated function definitions execute. Native module top-level
    # imports, classes, declarations and providers are absent from this AST.
    exec(compile(ast.Module(body=selected,type_ignores=[]),'<pinned-r3-pure-parser>','exec'),namespace)
    return namespace,records

def contains_exact(value,expected):
    if type(value) is dict:return any(contains_exact(item,expected) for item in value.values())
    if type(value) is list:return any(contains_exact(item,expected) for item in value)
    return type(value) is str and value==expected

def approved_loader(review_ref):
    require(type(review_ref) is dict and set(review_ref)=={'repository_relative_path','sha256'},'EXACT_REVIEW_REFERENCE_REQUIRED')
    relative=safe_relative(review_ref['repository_relative_path']);path=F/relative
    require(path.resolve().is_relative_to((L5/'review').resolve()),'CURRENT_LOADER_REVIEW_LOCATION_REQUIRED')
    report=pinned_json(path,review_ref['sha256']);require(report.get('decision')=='approved','CURRENT_LOADER_REVIEW_NOT_APPROVED')
    runtime=L5/'control/ceta-loader-capture-r5-20261020'
    state=parse(read(runtime/'state.json')[0]);node=state['nodes']['review'];author=state['nodes']['implement']
    require(node['state']=='SUCCEEDED' and node['decision']=='approved' and node['executor_id']!=author['executor_id'],'ACTUAL_DISTINCT_LOADER_REVIEW_REQUIRED')
    require(author['state']=='SUCCEEDED' and author['executor_id']=='/root/implement','CURRENT_LOADER_IMPLEMENTATION_NOT_ACCEPTED')
    receipt_relative=safe_relative(node['receipt_ref']);receipt_path=runtime/receipt_relative
    receipt=parse(read(receipt_path)[0])
    require(receipt['node_id']=='review' and receipt['executor_id']==node['executor_id'] and receipt['decision']=='approved','LOADER_REVIEW_RECEIPT_IDENTITY_CHANGED')
    require(contains_exact(receipt['result'],review_ref['sha256']),'RUNTIME_RECEIPT_DOES_NOT_BIND_REVIEW')
    require(not parse(read(runtime/'claims.json')[0]).get('review'),'LOADER_REVIEW_STILL_CLAIMED')
    source_freeze=reference(L5/'work/FROZEN.json')
    require(contains_exact(report,source_freeze['sha256']),'REVIEW_DOES_NOT_BIND_EXACT_LOADER_FREEZE')
    return dict(review=review_ref,receipt=reference(receipt_path),runtime_receipt_identity=node['receipt_hash'],reviewer=node['executor_id'],author=author['executor_id'],run_id=state['run_id'],source_freeze=source_freeze)

def dataset():
    count=verify_freeze(S1,'FREEZE-MANIFEST.json',S1_FREEZE)
    old=pinned_json(S1/'CETA_OWNED_LOADER_SYMBOL_INPUTS_V1.json',V1_PIN)
    require(old['schema_version']==1 and old['kind']=='CETA_OWNED_LOADER_SYMBOL_INPUTS_V1' and old['codeview_match'] is False and old['eligible_for_native_capture'] is False,'REJECTED_V1_STATE_CHANGED')
    require(set(old['input_pins'])=={'ntdll','pdb','dbghelp','dbgcore'},'FOUR_EXACT_INPUT_PINS_REQUIRED')
    for pin in old['input_pins'].values():require(read(pin['path'])[1]==pin,'RETAINED_FILE_IDENTITY_CHANGED')
    dep=old['dependency_acquisition'];acq=pinned_json(F/safe_relative(dep['repository_relative_path']),dep['sha256'])
    archive,pin=read(acq['archive']);require(pin['sha256']==acq['archive_sha256'],'OFFICIAL_ARCHIVE_CHANGED')
    return old,count

def compute(review_ref):
    approval=approved_loader(review_ref)
    r3_count=verify_freeze(L3/'work','FROZEN.json',L3_FREEZE)
    manifest=pinned_json(L3/'work/CODE-MANIFEST.json',L3_CODE)
    base_raw,base_pin=read(L3/'work/loader_snaps.py')
    require(manifest['code_hashes']['loader_snaps.py']==base_pin['sha256'],'R3_PARSER_MANIFEST_CHANGED')
    loader_count=verify_freeze(L5/'work','FROZEN.json',approval['source_freeze']['sha256'])
    loader_manifest=parse(read(L5/'work/CODE-MANIFEST.json')[0])
    raw,pin=read(L5/'work/loader_snaps.py')
    require(raw==base_raw and loader_manifest['code_hashes']['loader_snaps.py']==pin['sha256'],'APPROVED_LOADER_PARSER_CHANGED_FROM_REVIEWED_BASE')
    funcs,records=parsers(raw,pin['sha256']);old,s1_count=dataset();pins=old['input_pins']
    image=funcs['pe_codeview'](read(pins['ntdll']['path'])[0])
    pdb=funcs['pdb_codeview'](read(pins['pdb']['path'])[0]);match=funcs['match_codeview'](image,pdb)
    require((match['image_age'],match['info_age'],match['dbi_age'])==(1,4,1),'RETAINED_OBSERVATIONS_CHANGED')
    return dict(schema_version=2,kind='CETA_OWNED_LOADER_SYMBOL_INPUTS_V2',input_pins=pins,image_codeview=image,pdb_codeview=pdb,codeview_match=match,dependency_acquisition=old['dependency_acquisition'],disposition='COMPATIBLE_LOCAL_SYMBOL_DATA_REQUIRES_DISTINCT_V2_REVIEW_AND_ACTION_APPROVAL',historical_blocked_v1=reference(S1/'CETA_OWNED_LOADER_SYMBOL_INPUTS_V1.json'),historical_s1_freeze=reference(S1/'FREEZE-MANIFEST.json'),parser_base_freeze=reference(L3/'work/FROZEN.json'),parser_base_code_manifest=reference(L3/'work/CODE-MANIFEST.json'),loader_freeze=approval['source_freeze'],loader_code_manifest=reference(L5/'work/CODE-MANIFEST.json'),loader_review=approval,parser_evidence=dict(source=reference(L5/'work/loader_snaps.py'),reused_from=reference(L3/'work/loader_snaps.py'),functions=records,execution='Three pure AST function definitions only; native module never imported'),retained_evidence_files_verified=dict(s1=s1_count,parser_base=r3_count,approved_loader=loader_count),authenticode_observations=old['authenticode_statuses'],public_export_exclusions=old.get('public_export_exclusions',[]),protected_effects_authorized=False,native_qualification=False,product_acceptance=False,limitations=['This data identity match grants no native execution authority.','Actual DbgHelp type resolution and PEB layout remain unverified.','Original V1, its failed run and all raw acquisition evidence remain unchanged.','Separate V2 Collaborative Review and exact action-specific owner approval are required.','Historical signature observations retain their original time and scope; this derivation reruns no certificate or signature API.'])

def verify(path):
    value=parse(read(path)[0]);expected=compute(value['loader_review']['review'])
    require(value==expected,'V2_DERIVATION_CHANGED')
    return dict(status='PASS_PURE_DATA_V2',supplement=reference(path),ages=[value['codeview_match'][key] for key in ('image_age','info_age','dbi_age')],native_qualification=False,protected_effects_authorized=False)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=('derive','verify'));parser.add_argument('path',type=Path);parser.add_argument('--review',type=Path);parser.add_argument('--review-sha256');args=parser.parse_args()
    if args.mode=='derive':
        require(args.review is not None and args.review_sha256 is not None,'REVIEW_ARGUMENTS_REQUIRED')
        ref=reference(args.review);require(ref['sha256']==args.review_sha256,'REVIEW_ARGUMENT_PIN_CHANGED')
        value=compute(ref);require(args.path.resolve().parent==W.resolve(),'OUTPUT_OUTSIDE_OWN_WORK')
        with args.path.open('x',encoding='utf8',newline='\n') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(verify(args.path),indent=2))

if __name__=='__main__':main()
