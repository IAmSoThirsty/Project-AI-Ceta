from ac3_support import *
import atexit
R=D=Path(os.environ['CETA_AC3_ADVERSE_ROOT']).resolve(strict=True)
assert R.is_relative_to(F/'.agents/runtime/ac3-20261014')
sys.path.insert(0,str(Q/'src'))
from ceta.supervisor import isolated_worker as _module
_real_init=_module._IsolationAPI.__init__
_forbidden=[];_api_count=[]
def _guarded_init(api,*args,**kwargs):
    _real_init(api,*args,**kwargs);_api_count.append(1)
    def denied(*args):
        _forbidden.append('restricted_CreateProcessW');raise AssertionError('AC3_NO_RESTRICTED_CREATE_AUTHORITY')
    api.CreateProcessW=denied
    for name in ('CreateAppContainerProfile','DeleteAppContainerProfile'):
        def prohibited(*args,_name=name):
            _forbidden.append(_name);raise AssertionError('AC3_NO_PROFILE_MUTATION_AUTHORITY')
        setattr(api.userenv,name,prohibited)
_module._IsolationAPI.__init__=_guarded_init
def candidate_cut():
    inputs=json.loads((F/'.agents/runtime/ac3-20261014/SOURCE-INPUTS.json').read_text())
    return {name:ordinary(Q/name) for name in sorted(inputs['selected_dependencies'])}
def source_cut():
    inputs=json.loads((F/'.agents/runtime/ac3-20261014/SOURCE-INPUTS.json').read_text())
    return {name:ordinary(F/name) for name in inputs['Source_payloads']}
def _guard_record():
    write_new(D/'NO-PROFILE-GUARD.json',{'recorded_at':utc(),'guarded_API_constructions':len(_api_count),'forbidden_calls':_forbidden})
atexit.register(_guard_record)
