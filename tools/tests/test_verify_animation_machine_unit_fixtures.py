"""ROM-free tests of the pure helpers of tools/verify_animation_machine_unit_fixtures.py (synthetic values only)."""
import struct
import unittest

from tools import verify_animation_machine_unit_fixtures as u


def state(pc=0x1000, bank=(0x200000, 0xa0, 0x1000)):
    return u.make_state(bytes(65536), {k: i for i, k in enumerate(u.KEYS)}, pc, bank)


def success(pc=1, ports=(), remaining=(), waits=(), ram=None, carry=0):
    out = struct.pack('>9I', 1, 0, pc, carry, 0x200000, 3, len(ports), len(remaining), len(waits))
    out += struct.pack('>16I', *range(16)) + (ram or bytes(65536)) + u.bank_page((0x200000, 0xa0, 0x1000))
    for e in list(ports) + list(remaining):
        out += struct.pack('>III', *e)
    for w in waits:
        out += struct.pack('>5I', *w)
    return out


class Helpers(unittest.TestCase):
    def test_bank_page_rejects_disagreeing_page(self):
        page = bytearray(8192)
        with self.assertRaises(RuntimeError):
            u.bank_page((0x200000, 0xa0, 0x1000), bytes(page))
        self.assertEqual(u.bank_page((0x200000, 0xa0, 0x1000))[0x1ff0:0x1ff4], struct.pack('>HH', 0xa0, 0x1000))

    def test_make_state_validation(self):
        with self.assertRaises(RuntimeError):
            u.make_state(bytes(10), {}, 0, (0x200000, 0, 0))
        with self.assertRaises(RuntimeError):
            state(bank=(0x1000, 0, 0))

    def test_host_writes_and_overrides(self):
        s = u.with_host_writes(state(), [(0x10fff0, 4, 0x01020304), (0x100001, 1, 9)], regs={'d3': 0x1ffffffff}, pc=0x2000)
        self.assertEqual(s['ram'][0xfff0:0xfff4], bytes([1, 2, 3, 4]))
        self.assertEqual(s['ram'][1], 9)
        self.assertEqual(s['regs']['d3'], 0xffffffff)
        self.assertEqual(s['pc'], 0x2000)
        with self.assertRaises(RuntimeError):
            u.with_host_writes(state(), [(0, 1, 256)])
        with self.assertRaises(RuntimeError):
            u.with_host_writes(state(), regs={'x9': 1})

    def test_flip_ram(self):
        s = u.flip_ram(state(), 0x10ff00, 0x80)
        self.assertEqual(s['ram'][0xff00], 0x80)
        self.assertEqual(sum(s['ram']), 0x80)

    def test_fixture_validation_and_digest(self):
        with self.assertRaises(RuntimeError):
            u.Fixture('x', state())
        with self.assertRaises(RuntimeError):
            u.Fixture('x', state(), stop=1, expect='maybe')
        with self.assertRaises(RuntimeError):
            u.Fixture('x', state(), stop=1, releases=('nope',))
        a = u.Fixture('x', state(), [(0x300000, 1, 5)], 0xc52a)
        b = u.Fixture('x', state(), [(0x300000, 1, 6)], 0xc52a)
        self.assertNotEqual(a.digest(), b.digest())
        self.assertEqual(a.digest(), u.Fixture('x', state(), [(0x300000, 1, 5)], 0xc52a).digest())

    def test_release_mask(self):
        self.assertEqual(u.release_mask(('ef2', 'card'), 0x80), 1 | 32 | 0x8000)
        self.assertEqual(u.release_mask((), 0), 0)

    def test_request_layout(self):
        req = u.encode_request(state(), [(0x300000, 1, 7)], 0xc52a, ('ef2',), 16, 3, 0x80)
        self.assertEqual(len(req), 96 + 65536 + 8192 + 12)
        v = struct.unpack_from('>24I', req)
        self.assertEqual(v[:8], (0x1000, 0, 0x200000, 0xc52a, 1 | 0x8000, 16, 3, 1))
        self.assertEqual(v[8:24], tuple(range(16)))


class Packets(unittest.TestCase):
    def test_success_roundtrip(self):
        r = u.parse_response(success(pc=0xc52a, ports=[(0x3c0000, 4, 5)], remaining=[(0x300000, 1, 2)], waits=[(0x16bd0, 1, 2, 3, 4)]))
        self.assertTrue(r['ok'])
        self.assertEqual((r['pc'], r['ports'], r['remaining'], r['waits'], r['reads']), (0xc52a, [(0x3c0000, 4, 5)], [(0x300000, 1, 2)], [(0x16bd0, 1, 2, 3, 4)], 3))

    def test_failure_and_malformed(self):
        r = u.parse_response(struct.pack('>III', 0, 1, 2) + b'boom')
        self.assertEqual((r['ok'], r['preserved'], r['committed'], r['error']), (False, True, 2, 'boom'))
        with self.assertRaises(ValueError):
            u.parse_response(success()[:-1])
        with self.assertRaises(ValueError):
            u.parse_response(struct.pack('>III', 2, 0, 0) + b'bad request')
        with self.assertRaises(ValueError):
            u.parse_response(b'short')
        with self.assertRaises(ValueError):
            u.parse_response(success(carry=3))


class Compare(unittest.TestCase):
    def native(self):
        return dict(ram=bytes(65536), regs={k: i for i, k in enumerate(u.KEYS)}, pc=1, bank=(0x200000, 0xa0, 0x1000), pvc=u.bank_page((0x200000, 0xa0, 0x1000)),
                    ports=[(0x300001, 1, 1)], consumed=[(0x300000, 1, 9)], remaining=[], status_reads=0, waits=[(0x16bd0, 1, 2, 3, 4)])

    def cpp(self):
        return u.parse_response(success(ports=[(0x300001, 1, 1)], waits=[(0x16bd0, 1, 2, 3, 4)]))

    def test_equal_and_each_field(self):
        q = [(0x300000, 1, 9)]
        c, n = self.cpp(), self.native()
        c['reads'] = 1
        self.assertEqual(u.compare(c, n, q), [])
        for key, mutate in (('pc', lambda x: x.update(pc=2)), ('reg-d3', lambda x: x['regs'].update(d3=0)), ('bank', lambda x: x.update(bank_base=0x300000)),
                            ('ram', lambda x: x.update(ram=b'\1' + x['ram'][1:])), ('pvc', lambda x: x.update(pvc=bytes(8192))),
                            ('ports', lambda x: x.update(ports=[(0x300001, 1, 2)])), ('waits', lambda x: x.update(waits=[])),
                            ('external-reads', lambda x: x.update(reads=2)), ('queue-remaining', lambda x: x.update(remaining=[(0x300000, 1, 1)]))):
            bad = dict(c, regs=dict(c['regs']))
            mutate(bad)
            fields = [d['field'] for d in u.compare(bad, n, q)]
            self.assertIn(key, fields, key)
        self.assertEqual(u.compare(dict(ok=False, error='e', preserved=True, committed=0), n, q)[0]['field'], 'cpp-error')

    def test_port_long_split_rule(self):
        cpp = [(0x3c0000, 4, 0x12345678), (0x300001, 1, 1)]
        nat = [(0x3c0000, 2, 0x1234), (0x3c0002, 2, 0x5678), (0x300001, 1, 1)]
        self.assertEqual(u.compare_ports(cpp, nat), (None, 1))
        self.assertIsNotNone(u.compare_ports(cpp, [(0x3c0000, 2, 0x1234), (0x3c0002, 2, 0x5679), (0x300001, 1, 1)])[0])
        self.assertIsNotNone(u.compare_ports(nat, cpp)[0])               # the rule is one directional
        self.assertIsNotNone(u.compare_ports(cpp, nat[:2])[0])
        self.assertEqual(u.compare_ports([(0x2ffff0, 2, 0x11234)], [(0x2ffff0, 2, 0x1234)])[0], None)   # PVC WORD values are masked

    def test_reference(self):
        n = self.native()
        self.assertEqual(u.compare_reference(n, dict(pc=1, regs=n['regs'])), [])
        self.assertEqual(u.compare_reference(n, dict(pc=2))[0]['field'], 'native-vs-reference-pc')
        self.assertEqual(u.compare_reference(n, dict(ram=b'\1' + bytes(65535)))[0]['address'], 0x100000)


if __name__ == '__main__':
    unittest.main()
