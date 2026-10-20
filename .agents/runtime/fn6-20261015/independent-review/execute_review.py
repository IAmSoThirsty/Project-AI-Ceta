"""Run unchanged frozen recipes with only reviewer output and resource observations."""
from review_support import *
import runpy,threading
kind=sys.argv[1]
recipes={'controlled':('run_controlled.py',['controlled-r1','all']),
    'preparation':('run_preparation.py',['preparation-r1','connected']),
    'consumers':('run_consumers.py',['consumers-r1']),
    'joined':('run_joined_controls.py',['joined-r1','joined']),
    'outcomes':('run_outcomes.py',['outcomes-r1']),
    'initializer':('run_initializer.py',['initializer-r1']),
    'leaf':('run_leaf.py',[])}
script,args=recipes[kind];before=preflight();threads=set(threading.enumerate())
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
from ceta.store.sqlite_runtime import load_sqlite
sqlite=load_sqlite()
from resource_observer import Observer
observer=None if kind=='initializer' else Observer(sqlite)
primary=None;status=None
if observer:observer.install()
try:
    sys.argv=[str(V/script),*args]
    runpy.run_path(str(V/script),run_name='__main__')
    status=0
except SystemExit as error:
    status=error.code if type(error.code) is int else (0 if error.code is None else 1)
    if status:primary=error
except BaseException as error:
    primary=error;status=1
finally:
    if observer:observer.uninstall()
resources=observer.finish() if observer else read(V/'initializer-r1/RESULT.json')['physical_resources']
remaining=[dict(name=t.name,native_id=t.native_id) for t in set(threading.enumerate())-threads if t.is_alive()]
physical=(resources['owned_resources_closed'] is True and resources['remaining_resources']==[]
    and all(r['physical_closed_probe'] for r in resources['sqlite'])
    and all(r['closed'] and r['fileno_denied'] for r in resources['streams'])
    and all(r['closed'] for r in resources['os_descriptors']))
preflight()
write_new(V/('PHYSICAL-'+kind+'.json'),dict(at=utc(),kind=kind,runner_exit_status=status,
    primary=None if primary is None else {'type':type(primary).__name__},physical_resources=resources,
    all_physical_captured_resources_closed=physical,remaining_threads=remaining,
    fixture_only=True,native_product_workers=0,profile_Hello_CPU_Set=False,Source_publication=False,
    exit_status=0 if status==0 and physical and not remaining else 1))
assert physical and not remaining,('physical custody incomplete',kind,resources['remaining_resources'],remaining)
if primary is not None:raise primary
sys.exit(status)
