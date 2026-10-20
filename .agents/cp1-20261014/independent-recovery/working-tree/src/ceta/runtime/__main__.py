import sys
from . import Refused, Runtime, ManualClock, State

SCENARIOS = ('running', 'missing-dependency', 'maintenance')


def build(api_dep='policy'):
    r = Runtime(ManualClock())
    r.register('db', start=lambda: print('  start db'), stop=lambda: print('  stop db'))
    r.register('policy', depends=('db',), start=lambda: print('  start policy'), stop=lambda: print('  stop policy'))
    r.register('api', depends=(api_dep,), start=lambda: print('  start api'), stop=lambda: print('  stop api'))
    return r


def main(argv):
    if len(argv) != 1 or argv[0] not in SCENARIOS:
        print('usage: python -m ceta.runtime running|missing-dependency|maintenance')
        return 1
    name = argv[0]
    if name == 'missing-dependency':
        r = build(api_dep='ghost')
        try:
            r.boot(lambda: True)
        except Refused as exc:
            print('REFUSED code=' + exc.code + ' state=' + r.state.value)
            return 2
        print('UNEXPECTED boot did not refuse')
        return 3
    r = build()
    trust = (name == 'running')
    print('BOOT trust_present=' + str(trust))
    res = r.boot(lambda: trust)
    print('BOOT_RESULT state=' + res.state.value + ' started=' + str(res.started) + ' dispatch_open=' + str(r.dispatch_open))
    if name == 'maintenance':
        return 3
    print('SHUTDOWN begin')
    sd = r.shutdown(10)
    print('SHUTDOWN_RESULT state=' + sd.state.value + ' stop_order=' + str(sd.stop_order))
    return 0 if sd.state is State.STOPPED else 3


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
