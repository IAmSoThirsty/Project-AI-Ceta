"""Strict commands for an already selected, live trusted manual CPU session.

The host supplies the concrete session on the authenticated receiver's original
thread. Standalone invocation has no installed selected host and fails closed.
No CLI flag imports configuration, credentials, proof or a deployment factory.
"""
import argparse
import sys

from ceta.contracts.real_effect import REAL_EFFECT_PROFILE
from ceta.contracts.wire import ContractError, canonical_bytes


def parser():
    result = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = result.add_subparsers(dest='command', required=True)
    start = commands.add_parser('start', allow_abbrev=False)
    start.add_argument('--profile', choices=(REAL_EFFECT_PROFILE,), required=True)
    for name in ('run', 'restore', 'enroll', 'prepare', 'prepare-restore', 'inspect', 'approve', 'execute', 'reconcile', 'stop'):
        command = commands.add_parser(name, allow_abbrev=False)
        command.add_argument('--run-id', required=True)
        if name in ('prepare', 'run'):
            if name == 'prepare':
                command.add_argument('--operation', choices=('owned-worker.cpu-cap',), required=True)
            command.add_argument('--cpu-rate', type=int, required=True)
        if name in ('restore', 'approve', 'execute', 'reconcile'):
            command.add_argument('--request-id', required=True)
        if name == 'stop':
            command.add_argument('--reason-ref', default='reason:manual-owner-stop')
    return result


def dispatch(arguments, session):
    from ceta.composition.real_effect_service import ManualRealEffectSession
    if type(session) is not ManualRealEffectSession:
        raise ContractError('MANUAL_PROFILE_SELECTED_AUTHENTICATED_HOST_UNAVAILABLE')
    # The selected owner verifies the actual opaque context; run IDs do not.
    session._selected(getattr(arguments, 'run_id', None),
        bookkeeping=arguments.command in ('inspect', 'reconcile', 'stop'))
    if arguments.command == 'start':
        return session.inspect()
    if arguments.command == 'enroll':
        return session.enroll()
    if arguments.command == 'prepare':
        return session.prepare(cpu_rate=arguments.cpu_rate)
    if arguments.command == 'prepare-restore':
        return session.prepare(restoration=True)
    if arguments.command == 'approve':
        return session.approve(arguments.request_id)
    if arguments.command == 'execute':
        return session.execute(arguments.request_id)
    if arguments.command == 'reconcile':
        return session.reconcile(arguments.request_id)
    if arguments.command == 'stop':
        return session.stop(arguments.reason_ref)
    if arguments.command == 'inspect':
        return session.inspect()
    raise ContractError('MANUAL_PROFILE_COMMAND_UNAVAILABLE')


def dispatch_client(arguments, client):
    from ceta.composition.real_effect_client import ManualEffectClient
    if type(client) is not ManualEffectClient:
        raise ContractError('MANUAL_PROFILE_SELECTED_AUTHENTICATED_HOST_UNAVAILABLE')
    if getattr(arguments, 'run_id', None) != client.run_id:
        raise ContractError('MANUAL_PROFILE_RUN_ID_MISMATCH')
    kinds = {'run': 'RUN', 'restore': 'RESTORE', 'inspect': 'INSPECT',
        'reconcile': 'RECONCILE', 'stop': 'STOP'}
    if arguments.command not in kinds:
        raise ContractError('MANUAL_PROFILE_ONE_AUTHENTICATED_OPERATION_REQUIRED')
    return client.call(kinds[arguments.command], cpu_rate=getattr(arguments, 'cpu_rate', None),
        request_id=getattr(arguments, 'request_id', None), reason_ref=getattr(arguments, 'reason_ref', None))


def main(argv=None, *, session=None, client=None, output=None):
    arguments = parser().parse_args(argv)
    destination = sys.stdout.buffer if output is None else output
    try:
        if session is not None and client is not None:
            raise ContractError('MANUAL_PROFILE_AMBIGUOUS_COMPOSITION')
        result = dispatch_client(arguments, client) if client is not None else dispatch(arguments, session)
        wire = canonical_bytes(result)
        if len(wire) > 262144:
            raise ContractError('MANUAL_PROFILE_RESPONSE_BOUND')
        destination.write(wire + b'\n')
        destination.flush()
        return 2 if result.get('kind') == 'DENIED_RECONCILE' else 0
    except ContractError as error:
        # A denial can follow COMMIT or effect. It is never a no-effect receipt.
        wire = canonical_bytes(dict(profile=REAL_EFFECT_PROFILE, kind='DENIED',
            code=error.code, transition_or_effect='UNESTABLISHED_BY_RESPONSE'))
        destination.write(wire + b'\n')
        destination.flush()
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
