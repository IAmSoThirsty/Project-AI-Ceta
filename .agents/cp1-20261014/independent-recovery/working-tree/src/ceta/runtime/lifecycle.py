# Subsystem 00 runtime lifecycle core (CETA-00.03). Standard library only, per D-001.
import hashlib
import hmac
import secrets
import time
from collections import namedtuple
from enum import Enum


class State(Enum):
    CREATED = 'created'
    BOOTING = 'booting'
    MAINTENANCE = 'maintenance'
    RUNNING = 'running'
    STOPPING = 'stopping'
    STOPPED = 'stopped'
    FAILED = 'failed'


LEGAL = {
    State.CREATED: {State.BOOTING},
    State.BOOTING: {State.RUNNING, State.MAINTENANCE, State.FAILED},
    State.MAINTENANCE: {State.BOOTING, State.STOPPING},
    State.RUNNING: {State.STOPPING},
    State.STOPPING: {State.STOPPED, State.FAILED},
    State.STOPPED: {State.BOOTING},
    State.FAILED: {State.BOOTING, State.STOPPING},
}


BootResult = namedtuple('BootResult', 'state lifecycle_generation started diagnostics')
ShutdownResult = namedtuple('ShutdownResult', 'state stop_order outcomes deadline_exceeded diagnostics')


class IllegalTransition(Exception):
    pass


class Refused(Exception):
    def __init__(self, code, detail):
        super().__init__(code + ': ' + detail)
        self.code = code
        self.detail = detail


class ManualClock:
    def __init__(self, start=0.0):
        if start < 0:
            raise ValueError('clock start must be non-negative')
        self._t = float(start)

    def now(self):
        return self._t

    def advance(self, seconds):
        if seconds < 0:
            raise ValueError('clock cannot move backwards')
        self._t += float(seconds)


class MonotonicClock:
    def now(self):
        return time.monotonic()


class Token:
    # Readiness token issued by Runtime.token(). MAC keyed by the issuing runtime private secret.
    __slots__ = ('name', 'generation', 'mac')

    def __init__(self, name, generation, mac):
        self.name = name
        self.generation = generation
        self.mac = mac

    def __repr__(self):
        return 'Token({!r}, {!r})'.format(self.name, self.generation)


class Component:
    def __init__(self, name, depends=(), start=None, stop=None, drain=None):
        if not isinstance(name, str) or not name:
            raise ValueError('component name must be non-empty text')
        if isinstance(depends, str):
            raise TypeError('depends must be a collection of names, not text')
        deps = tuple(depends)
        for d in deps:
            if not isinstance(d, str):
                raise TypeError('dependency names must be text')
            if not d:
                raise ValueError('dependency names must be non-empty text')
        if name in deps:
            raise Refused('dependency_cycle', name + ' depends on itself')
        for hook in (start, stop, drain):
            if hook is not None and not callable(hook):
                raise TypeError('lifecycle hooks must be callable or None')
        self.name = name
        self.depends = deps
        self.start_hook = start
        self.stop_hook = stop
        self.drain_hook = drain
        self.ready = False
        self.failed = False
        self.generation = 0
        self.pending = {}


class Runtime:
    def __init__(self, clock):
        self.clock = clock
        self.state = State.CREATED
        self.lifecycle_generation = 0
        self._components = {}
        self._secret = secrets.token_bytes(32)

    def _set(self, target):
        if target not in LEGAL[self.state]:
            raise IllegalTransition(self.state.value + ' to ' + target.value + ' is not a legal transition')
        self.state = target

    @property
    def dispatch_open(self):
        return self.state is State.RUNNING

    def register(self, name, depends=(), start=None, stop=None, drain=None):
        if self.state not in (State.CREATED, State.STOPPED):
            raise Refused('registration_closed', 'state is ' + self.state.value)
        if name in self._components:
            raise Refused('duplicate_component', name)
        self._components[name] = Component(name, depends, start, stop, drain)

    def component(self, name):
        return self._components[name]

    def order(self):
        for c in self._components.values():
            for d in c.depends:
                if d not in self._components:
                    raise Refused('missing_dependency', c.name + ' requires ' + d)
        deps = {n: tuple(dict.fromkeys(c.depends)) for n, c in self._components.items()}
        indeg = {n: len(deps[n]) for n in deps}
        dependents = {n: [] for n in deps}
        for n in deps:
            for d in deps[n]:
                dependents[d].append(n)
        queue = [n for n in deps if indeg[n] == 0]
        out = []
        while queue:
            n = queue.pop(0)
            out.append(n)
            for m in dependents[n]:
                indeg[m] -= 1
                if indeg[m] == 0:
                    queue.append(m)
        if len(out) != len(deps):
            raise Refused('dependency_cycle', 'cycle among components')
        return out

    def _stop_component(self, name, diagnostics):
        c = self._components[name]
        try:
            if c.stop_hook is not None:
                c.stop_hook()
        except Exception as exc:
            c.failed = True
            c.ready = False
            diagnostics.append('stop_failed:' + name + ':' + type(exc).__name__)
            return False
        c.ready = False
        return True

    def _trust_ok(self, check, diagnostics):
        try:
            verdict = check()
        except Exception as exc:
            diagnostics.append('trust_check_error:' + type(exc).__name__)
            return False
        if verdict is True:
            return True
        diagnostics.append('trust_material_missing' if verdict is False else 'trust_material_invalid_result')
        return False

    def boot(self, trust_check):
        if not callable(trust_check):
            raise TypeError('trust_check must be callable')
        order = self.order()
        unrecovered = [n for n in order if self._components[n].failed]
        if unrecovered:
            raise Refused('component_unrecovered', ','.join(unrecovered))
        self._set(State.BOOTING)
        self.lifecycle_generation += 1
        diagnostics = []
        if not self._trust_ok(trust_check, diagnostics):
            self._set(State.MAINTENANCE)
            return BootResult(self.state, self.lifecycle_generation, (), tuple(diagnostics))
        started = []
        for n in order:
            c = self._components[n]
            c.generation += 1
            try:
                if c.start_hook is not None:
                    c.start_hook()
            except Exception as exc:
                diagnostics.append('start_failed:' + n + ':' + type(exc).__name__)
                for m in reversed(started):
                    self._stop_component(m, diagnostics)
                self._set(State.FAILED)
                return BootResult(self.state, self.lifecycle_generation, (), tuple(diagnostics))
            c.ready = True
            started.append(n)
        self._set(State.RUNNING)
        return BootResult(self.state, self.lifecycle_generation, tuple(started), tuple(diagnostics))

    def _mac(self, name, generation):
        msg = (name + chr(0) + str(generation)).encode('utf-8')
        return hmac.new(self._secret, msg, hashlib.sha256).digest()

    def token(self, name):
        c = self._components[name]
        if not c.ready:
            raise Refused('not_ready', name)
        return Token(name, c.generation, self._mac(name, c.generation))

    def submit(self, token, effect_id):
        if not isinstance(token, Token):
            raise Refused('forged_token', 'token must be issued by Runtime.token()')
        if not isinstance(token.name, str) or not isinstance(token.generation, int) or not isinstance(token.mac, bytes):
            raise Refused('forged_token', 'token fields are malformed')
        if not hmac.compare_digest(token.mac, self._mac(token.name, token.generation)):
            raise Refused('forged_token', 'token MAC does not match this runtime')
        if not isinstance(effect_id, str) or not effect_id:
            raise ValueError('effect_id must be non-empty text')
        if self.state is not State.RUNNING:
            raise Refused('dispatch_closed', self.state.value)
        c = self._components.get(token.name)
        if c is None or not c.ready or c.generation != token.generation:
            raise Refused('stale_readiness', str(token.name))
        if effect_id in c.pending:
            raise Refused('duplicate_effect', effect_id)
        c.pending[effect_id] = True

    def recover(self, name):
        if self.state not in (State.CREATED, State.STOPPED, State.FAILED, State.MAINTENANCE):
            raise Refused('recovery_closed', self.state.value)
        c = self._components[name]
        c.failed = False
        c.ready = False
        c.pending = {}

    def shutdown(self, deadline_seconds):
        if deadline_seconds < 0:
            raise ValueError('deadline_seconds must be non-negative')
        if self.state in (State.CREATED, State.STOPPED):
            return ShutdownResult(self.state, (), (), False, ())
        if self.state is State.STOPPING:
            raise IllegalTransition('shutdown already in progress')
        self._set(State.STOPPING)
        deadline = self.clock.now() + float(deadline_seconds)
        order = list(reversed(self.order()))
        outcomes = []
        diagnostics = []
        exceeded = False
        any_failed = False
        for n in order:
            c = self._components[n]
            if c.failed:
                diagnostics.append('component_unrecovered:' + n)
                any_failed = True
                continue
            if not c.ready:
                continue
            pending = list(c.pending)
            finished = set()
            if pending and c.drain_hook is not None:
                try:
                    finished = set(c.drain_hook(tuple(pending), deadline, self.clock))
                except Exception as exc:
                    diagnostics.append('drain_failed:' + n + ':' + type(exc).__name__)
                    any_failed = True
                    finished = set()
            if pending and self.clock.now() > deadline:
                exceeded = True
                diagnostics.append('deadline_exceeded:' + n)
                finished = set()
            for e in pending:
                outcomes.append((n, e, 'completed' if e in finished else 'uncertain'))
            c.pending = {}
            if not self._stop_component(n, diagnostics):
                any_failed = True
        final = State.FAILED if any_failed else State.STOPPED
        self._set(final)
        return ShutdownResult(final, tuple(order), tuple(outcomes), exceeded, tuple(diagnostics))
