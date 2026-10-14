"""ROM-free tests of the pure helpers of tools/verify_animation_machine_frame_driver.py (synthetic values only)."""
import struct
import unittest

from tools import verify_animation_machine_frame_driver as v


def response(ok_fields, ram=None, pvc=None, head=(), node=(), waits=(), remaining=()):
    pc, carry, bank, head_pc, ctrl, stop, hr, nr, regs = ok_fields
    out = struct.pack('>13I', 1, pc, carry, bank, head_pc, ctrl, stop, hr, nr, len(head), len(node), len(waits), len(remaining))
    out += struct.pack('>16I', *regs)
    out += (ram or bytes(65536)) + (pvc or bytes(8192))
    for e in list(head) + list(node):
        out += struct.pack('>III', *e)
    for w in waits:
        out += struct.pack('>6I', *w)
    for e in remaining:
        out += struct.pack('>III', *e)
    return out


def expectation(**kw):
    e = dict(ram=bytes(65536), regs={k: 0 for k in v.KEYS}, pc=0xe74, bank_base=0x200000, pvc=bytes(8192), head_pc=0xe74, controller_pc=0xc52a,
             pass_stop_pc=0xe74, head_reads=7, node_reads=0, head_ports=[], node_ports=[], waits=[])
    e.update(kw)
    return e


class FrameDriverHelperTests(unittest.TestCase):
    def test_request_layout(self):
        regs = {k: i for i, k in enumerate(v.KEYS)}
        req = v.encode_request(1, bytes(65536), regs, 0xe74, 0x200000, bytes(8192), [(0x3c0006, 2, 0)], 0)
        self.assertEqual(len(req), 4 * 23 + 65536 + 8192 + 12)
        words = struct.unpack_from('>23I', req)
        self.assertEqual(words[0], 1)
        self.assertEqual(words[1:17], tuple(range(16)))
        self.assertEqual(words[17:23], (0xe74, 0, 0x200000, 0, 0x180, 1))
        off = v.encode_request(0, bytes(65536), regs, 0x2ac2, 0x200000, bytes(8192), [], 0, card_resume=False, card_answer=0)
        self.assertEqual(struct.unpack_from('>23I', off)[21], 0)

    def test_parse_roundtrip_and_errors(self):
        payload = response((0xe74, 0, 0x200000, 0xe74, 0xc52a, 0xe74, 7, 0, list(range(16))), head=[(0x300001, 1, 0)],
                           waits=[(0, 0x16bd0, 0x108d34, 2, 4, 8)], remaining=[(0x300000, 1, 0x5a)])
        got = v.parse_response(payload)
        self.assertTrue(got['ok'])
        self.assertEqual(got['head_ports'], [(0x300001, 1, 0)])
        self.assertEqual(got['waits'], [(0, 0x16bd0, 0x108d34, 2, 4, 8)])
        self.assertEqual(got['remaining'], [(0x300000, 1, 0x5a)])
        with self.assertRaises(ValueError):
            v.parse_response(payload[:-1])
        fail = v.parse_response(struct.pack('>II', 0, 1) + b'unsupported animation machine PC')
        self.assertFalse(fail['ok'])
        self.assertTrue(fail['preserved'])
        self.assertEqual(fail['error'], 'unsupported animation machine PC')

    def test_port_conversion(self):
        native = [(1, 0x2ffff0, 2, 0x00a0), (2, 0x3c0000, 2, 0x1234), (2, 0x3c0002, 2, 0x5678), (2, 0x3c0000, 4, 0x11112222)]
        cpp = [(0x2ffff0, 2, 0x00a0), (0x3c0000, 4, 0x12345678), (0x3c0000, 4, 0x11112222)]
        conv, splits = v.cpp_ports_native_form(cpp, native, [(1, 3)])
        self.assertEqual(conv, native)
        self.assertEqual(splits, 1)
        conv, splits = v.cpp_ports_native_form(cpp, native, [])          # no split range: no split
        self.assertNotEqual(conv, native)
        self.assertEqual(splits, 0)

    def test_native_waits(self):
        waits = [dict(pc=0x16bd0, kind='sprite-flush', live=4, compared=8, released=[[0x108d34, 2, 8]]),
                 dict(pc=0xc00468, kind='bios-card', live=0xc37c, compared=0x80, released=[['pc', 0xc37c], ['a7', 4], ['ram', 0x10fdc6, 1, 0x80]],
                      a7_at_stop=0x1fefe0, saved_a6=0x100b30, card_before=0)]
        self.assertEqual(v.native_wait_tuples(waits, 1), [(1, 0x16bd0, 0x108d34, 2, 4, 8), (1, 0xc00468, 0x10fdc6, 1, 0, 0x80)])

    def test_compare_detects(self):
        exp = expectation(head_ports=[(2, 0x300001, 1, 0)], waits=[(0, 0x16bd0, 0x108d34, 2, 4, 8)])
        base = (0xe74, 0, 0x200000, 0xe74, 0xc52a, 0xe74, 7, 0, [0] * 16)
        good = v.parse_response(response(base, head=[(0x300001, 1, 0)], waits=[(0, 0x16bd0, 0x108d34, 2, 4, 8)]))
        self.assertEqual(v.compare(good, exp), [])
        ram = bytearray(65536)
        ram[5] = 1
        cases = [response(base, ram=bytes(ram), head=[(0x300001, 1, 0)], waits=[(0, 0x16bd0, 0x108d34, 2, 4, 8)]),
                 response(base, head=[(0x300001, 1, 1)], waits=[(0, 0x16bd0, 0x108d34, 2, 4, 8)]),
                 response(base, head=[(0x300001, 1, 0)], waits=[(0, 0x16bd0, 0x108d34, 2, 4, 9)]),
                 response(base, head=[(0x300001, 1, 0)], waits=[(0, 0x16bd0, 0x108d34, 2, 4, 8)], remaining=[(0x300000, 1, 0)]),
                 response((0xe74, 1, 0x200000, 0xe74, 0xc52a, 0xe74, 7, 0, [0] * 16), head=[(0x300001, 1, 0)], waits=[(0, 0x16bd0, 0x108d34, 2, 4, 8)]),
                 response((0xe74, 0, 0x200000, 0xe74, 0xc52a, 0xe74, 6, 0, [0] * 16), head=[(0x300001, 1, 0)], waits=[(0, 0x16bd0, 0x108d34, 2, 4, 8)])]
        fields = [v.compare(v.parse_response(p), exp)[0]['field'] for p in cases]
        self.assertEqual(fields, ['ram', 'head_ports', 'waits', 'queue-not-consumed', 'carry', 'head_reads'])
        err = v.parse_response(struct.pack('>II', 0, 1) + b'x')
        self.assertEqual(v.compare(err, exp)[0]['field'], 'cpp-error')

    def test_expected_failure_kind(self):
        err = lambda text, preserved=1: v.parse_response(struct.pack('>II', 0, preserved) + text.encode())
        self.assertTrue(v.check_expected_failure(err('unaligned animation machine PC'), 'pass', 'odd-pc')['ok'])
        self.assertTrue(v.check_expected_failure(err('animation fade card odd JSR target'), 'pass', 'fetch-unmapped')['ok'])
        self.assertFalse(v.check_expected_failure(err('unaligned animation machine PC'), 'pass', 'fetch-unmapped')['ok'])
        self.assertFalse(v.check_expected_failure(err('unaligned animation machine PC', 0), 'pass', 'odd-pc')['ok'])
        self.assertFalse(v.check_expected_failure(err('x'), 'pass', 'step-limit')['ok'])

    def test_page_normalisation_and_digest(self):
        page = bytearray(8192)
        page[0x1ff0:0x1ff4] = b'\xff\xff\xff\xff'
        p = v.normalise_page(bytes(page), 0xa0, 0x1000)
        self.assertEqual(p[0x1ff0:0x1ff4], bytes.fromhex('00a01000'))
        regs = {k: 0 for k in v.KEYS}
        self.assertNotEqual(v.state_digest(bytes(65536), regs, 0xe74, 0x200000, p), v.state_digest(bytes(65536), regs, 0xe4a, 0x200000, p))


if __name__ == '__main__':
    unittest.main()
