from os import path
import pytest
from client import client_output
from tools.paths import CONTRACT_PATH, ACCOUNT_PATH

BAKE_ARGS = ['--max-priority', '512', '--minimal-timestamp']
TRANSFER_ARGS = ['--burn-cap', '0.257']


@pytest.mark.incremental
class TestRawContext:

    def test_delegates(self, client):
        path = '/chains/main/blocks/head/context/raw/bytes/delegates/?depth=3'
        res = client.rpc('get', path)
        expected = {
            "ed25519": {
                "02": {"29": None},
                "a9": {"ce": None},
                "c5": {"5c": None},
                "da": {"c9": None},
                "e7": {"67": None}
            }
        }
        assert res == expected

    def test_no_service_1(self, client):
        path = '/chains/main/blocks/head/context/raw/bytes/non-existent'
        with pytest.raises(client_output.InvalidClientOutput) as exc:
            client.rpc('get', path)
        assert exc.value.client_output == 'No service found at this URL\n\n'

    def test_no_service_2(self, client):
        path = ('/chains/main/blocks/head/context/raw/bytes/'
                'non-existent?depth=-1')
        with pytest.raises(client_output.InvalidClientOutput) as exc:
            client.rpc('get', path)
        expected = 'Command failed : Extraction depth -1 is invalid\n\n'
        assert exc.value.client_output == expected

    def test_no_service_3(self, client):
        path = ('/chains/main/blocks/head/context/raw/bytes/'
                'non-existent?depth=0')
        with pytest.raises(client_output.InvalidClientOutput) as exc:
            client.rpc('get', path)
        assert exc.value.client_output == 'No service found at this URL\n\n'

    def test_bake(self, client):
        client.bake('bootstrap4', BAKE_ARGS)

    def test_gen_keys(self, client, session):
        session['keys'] = ['foo', 'bar', 'boo']
        sig = [None, 'secp256k1', 'ed25519']
        for key, sig in zip(session['keys'], sig):
            args = [] if sig is None else ['--sig', sig]
            client.gen_key(key, args)

    def test_transfers(self, client, session):
        client.transfer(1000, 'bootstrap1',
                        session['keys'][0],
                        TRANSFER_ARGS)
        client.bake('bootstrap1', BAKE_ARGS)
        client.transfer(2000, 'bootstrap1',
                        session['keys'][1],
                        TRANSFER_ARGS)
        client.bake('bootstrap1', BAKE_ARGS)
        client.transfer(3000, 'bootstrap1',
                        session['keys'][2],
                        TRANSFER_ARGS)
        client.bake('bootstrap1', BAKE_ARGS)

    def test_balances(self, client, session):
        assert client.get_balance(session['keys'][0]) == 1000
        assert client.get_balance(session['keys'][1]) == 2000
        assert client.get_balance(session['keys'][2]) == 3000

    def test_transfer_bar_foo(self, client, session):
        client.transfer(1000, session['keys'][1], session['keys'][0],
                        ['--fee', '0', '--force-low-fee'])
        client.bake('bootstrap1', BAKE_ARGS +
                    ['--minimal-fees', '0', '--minimal-nanotez-per-byte',
                     '0', '--minimal-nanotez-per-gas-unit', '0'])

    def test_balances_bar_foo(self, client, session):
        assert client.get_balance(session['keys'][0]) == 2000
        assert client.get_balance(session['keys'][1]) == 1000

    def test_transfer_foo_bar(self, client, session):
        client.transfer(1000, session['keys'][0],
                        session['keys'][1],
                        ['--fee', '0.05'])
        client.bake('bootstrap1', BAKE_ARGS)

    def test_balances_foo_bar(self, client, session):
        assert client.get_balance(session['keys'][0]) == 999.95
        assert client.get_balance(session['keys'][1]) == 2000

    def test_transfer_failure(self, client, session):
        with pytest.raises(Exception):
            client.transfer(999.95, session['keys'][0], session['keys'][1])

    def test_originate_contract_noop(self, client):
        contract = path.join(CONTRACT_PATH, 'opcodes', 'noop.tz')
        client.remember('noop', contract)
        client.typecheck(contract)
        client.originate('noop',
                         1000, 'bootstrap1', contract,
                         ['--burn-cap', '0.295'])
        client.bake('bootstrap1', BAKE_ARGS)

    def test_transfer_to_noop(self, client):
        client.transfer(10, 'bootstrap1', 'noop',
                        ['--arg', 'Unit'])
        client.bake('bootstrap1', BAKE_ARGS)

    def test_contract_hardlimit(self, client):
        contract = path.join(CONTRACT_PATH, 'mini_scenarios', 'hardlimit.tz')
        client.originate('hardlimit',
                         1000, 'bootstrap1',
                         contract,
                         ['--init', '3',
                          '--burn-cap', '0.341'])
        client.bake('bootstrap1', BAKE_ARGS)
        client.transfer(10, 'bootstrap1',
                        'hardlimit',
                        ['--arg', 'Unit'])
        client.bake('bootstrap1', BAKE_ARGS)
        client.transfer(10, 'bootstrap1',
                        'hardlimit',
                        ['--arg', 'Unit'])
        client.bake('bootstrap1', BAKE_ARGS)

    def test_transfers_bootstraps5_bootstrap1(self, client):
        assert client.get_balance('bootstrap5') == 4000000
        client.transfer(400000, 'bootstrap5',
                        'bootstrap1',
                        ['--fee', '0',
                         '--force-low-fee'])
        client.bake('bootstrap1', BAKE_ARGS)
        client.transfer(400000, 'bootstrap1',
                        'bootstrap5',
                        ['--fee', '0',
                         '--force-low-fee'])
        client.bake('bootstrap1', BAKE_ARGS)
        assert client.get_balance('bootstrap5') == 4000000

    def test_activate_accounts(self, client, session):
        account = f"{ACCOUNT_PATH}/king_commitment.json"
        session['keys'] += ['king', 'queen']
        client.activate_account(session['keys'][3], account)
        client.bake('bootstrap1', BAKE_ARGS)
        account = f"{ACCOUNT_PATH}/queen_commitment.json"
        client.activate_account(session['keys'][4], account)
        client.bake('bootstrap1', BAKE_ARGS)
        assert client.get_balance(session['keys'][3]) == 23932454.669343
        assert client.get_balance(session['keys'][4]) == 72954577.464032

    def test_transfer_king_queen(self, client, session):
        keys = session['keys']
        client.transfer(10, keys[3], keys[4], TRANSFER_ARGS)
        client.bake('bootstrap1', BAKE_ARGS)
