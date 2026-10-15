"""ROM-free unit tests for the static code-coverage baseline tool."""

import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "measure_code_coverage.py"
SPEC = importlib.util.spec_from_file_location("measure_code_coverage", SCRIPT)
mcc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mcc)

RTS = bytes.fromhex("4e75")
NOP = bytes.fromhex("4e71")


def image(size=0x1000, **placements):
    data = bytearray(size)
    for key, blob in placements.items():
        data[int(key[1:], 16):int(key[1:], 16) + len(blob)] = blob
    return data


def put(data, addr, blob):
    data[addr:addr + len(blob)] = blob


def long_be(value):
    return value.to_bytes(4, "big")


class RoutedParsingTests(unittest.TestCase):
    def test_ranges_singles_and_exclusions(self):
        text = ("if ((next.pc>=0x100 && next.pc<0x110) || (next.pc>=0x200 && next.pc<=0x210"
                " && next.pc!=0x208) || next.pc==0x300 || next.pc==stop_pc)")
        atoms, expected = mcc.parse_routed_atoms(text)
        spans = [(a["start"], a["end"], a["kind"]) for a in atoms]
        self.assertEqual(spans, [(0x100, 0x110, "range"), (0x200, 0x208, "range"),
                                 (0x209, 0x211, "range"), (0x300, 0x301, "single")])
        self.assertEqual(expected, 3)
        self.assertEqual(mcc.matched_comparison_count(text), 3)

    def test_merge_adjacent_and_overlapping(self):
        merged = mcc.merge_intervals([(0x10, 0x20), (0x20, 0x30), (0x28, 0x40), (0x50, 0x51)])
        self.assertEqual(merged, [(0x10, 0x40), (0x50, 0x51)])

    def test_interval_set(self):
        s = mcc.IntervalSet([(0x10, 0x20), (0x40, 0x50)])
        self.assertTrue(s.contains(0x10))
        self.assertFalse(s.contains(0x20))
        self.assertTrue(s.contains(0x4f))
        self.assertEqual(s.overlap(0x18, 0x44), 8 + 4)
        self.assertEqual(s.total_bytes(), 0x20)

    def test_documented_ranges_filtering(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.md").write_text(
                "ROM 0x1000..0x1100 ok, RAM 0x100000..0x10ffff no, odd 0x1001..0x1100 no,"
                " tiny 0x0010..0x0020 no", encoding="utf-8")
            merged, listing = mcc.parse_documented_ranges(tmp)
        self.assertEqual(merged, [(0x1000, 0x1100)])
        self.assertEqual(listing[0]["files"], ["a.md"])


class DiscoveryTests(unittest.TestCase):
    def test_direct_flow_branches_and_calls(self):
        data = image()
        # 0x200: bsr.w 0x300; bra.s 0x20a (skips filler); 0x208: dc.w invalid; 0x20a: rts
        put(data, 0x200, bytes.fromhex("6100") + (0x300 - 0x202).to_bytes(2, "big"))
        put(data, 0x204, bytes.fromhex("6004"))  # bra.s 0x20a
        put(data, 0x206, bytes.fromhex("ffffffff"))
        put(data, 0x20a, RTS)
        put(data, 0x300, NOP + RTS)
        disc = mcc.Discovery(data)
        disc.add_root(0x200, "test", "A")
        self.assertEqual(sorted(disc.instrs), [0x200, 0x204, 0x20a, 0x300, 0x302])
        self.assertNotIn(0x206, disc.instrs)

    def test_conditional_branch_and_dbra_follow_both_paths(self):
        data = image()
        put(data, 0x200, bytes.fromhex("6602"))  # bne.s 0x204
        put(data, 0x202, NOP)
        put(data, 0x204, bytes.fromhex("51c8") + (0x20a - 0x206).to_bytes(2, "big"))  # dbra d0
        put(data, 0x208, RTS)
        put(data, 0x20a, RTS)
        disc = mcc.Discovery(data)
        disc.add_root(0x200, "test", "A")
        self.assertEqual(sorted(disc.instrs), [0x200, 0x202, 0x204, 0x208, 0x20a])

    def test_invalid_opcode_stops_and_is_recorded(self):
        data = image()
        put(data, 0x200, NOP + bytes.fromhex("ffff") + RTS)
        disc = mcc.Discovery(data)
        disc.add_root(0x200, "test", "A")
        self.assertEqual(sorted(disc.instrs), [0x200])
        self.assertEqual(disc.invalid_stops, {0x202: "invalid_opcode"})

    def test_jmp_abs_does_not_fall_through_and_jsr_does(self):
        data = image()
        put(data, 0x200, bytes.fromhex("4eb9") + long_be(0x400))  # jsr 0x400
        put(data, 0x206, bytes.fromhex("4ef9") + long_be(0x500))  # jmp 0x500
        put(data, 0x20c, NOP)
        put(data, 0x400, RTS)
        put(data, 0x500, RTS)
        disc = mcc.Discovery(data)
        disc.add_root(0x200, "test", "A")
        self.assertEqual(sorted(disc.instrs), [0x200, 0x206, 0x400, 0x500])

    def test_indirect_jump_is_unresolved(self):
        data = image()
        put(data, 0x200, bytes.fromhex("4ed0"))  # jmp (a0)
        disc = mcc.Discovery(data)
        disc.add_root(0x200, "test", "A")
        self.assertEqual(disc.unresolved, {0x200: "(An)"})
        self.assertEqual(sorted(disc.instrs), [0x200])

    def test_immediate_pointer_becomes_layer_b_root_and_implausible_is_rejected(self):
        data = image()
        # move.l #0x400,(a0); move.l #0x600,-(a7); rts
        put(data, 0x200, bytes.fromhex("20bc") + long_be(0x400))
        put(data, 0x206, bytes.fromhex("2f3c") + long_be(0x600))
        put(data, 0x20c, RTS)
        put(data, 0x400, NOP + RTS)
        # 0x600 stays zero fill: ori.b #0,d0 decodes but is rejected as fill
        disc = mcc.Discovery(data)
        disc.add_root(0x200, "test", "A")
        disc.drain("B")
        self.assertEqual(disc.instrs[0x200][1], "A")
        self.assertEqual(disc.instrs[0x400][1], "B")
        self.assertNotIn(0x600, disc.instrs)
        self.assertEqual(disc.rejected, {"move.l #imm,-(An)": 1})

    def test_lea_pea_and_data_move_to_register_are_not_confused(self):
        data = image()
        put(data, 0x200, bytes.fromhex("41f9") + long_be(0x400))  # lea 0x400,a0
        put(data, 0x206, bytes.fromhex("203c") + long_be(0x500))  # move.l #0x500,d0 (ignored)
        put(data, 0x20c, RTS)
        put(data, 0x400, RTS)
        put(data, 0x500, RTS)
        disc = mcc.Discovery(data)
        disc.add_root(0x200, "test", "A")
        disc.drain("B")
        self.assertIn(0x400, disc.instrs)
        self.assertNotIn(0x500, disc.instrs)

    def test_bra_jump_table(self):
        data = image()
        # jmp 2(pc,d0.w) ; table: bra.w 0x300, bra.s 0x400-ish via bra.w, then rts ends table
        put(data, 0x200, bytes.fromhex("4efb0002"))
        put(data, 0x204, bytes.fromhex("6000") + (0x300 - 0x206).to_bytes(2, "big"))
        put(data, 0x208, bytes.fromhex("6000") + (0x400 - 0x20a).to_bytes(2, "big"))
        put(data, 0x20c, RTS)
        put(data, 0x300, RTS)
        put(data, 0x400, RTS)
        disc = mcc.Discovery(data)
        disc.add_root(0x200, "test", "A")
        disc.drain("B")
        self.assertEqual(sorted(disc.instrs), [0x200, 0x204, 0x208, 0x300, 0x400])
        self.assertEqual(disc.instrs[0x204][1], "B")

    def test_bank_reference_is_counted_not_followed(self):
        data = image()
        put(data, 0x200, bytes.fromhex("4eb9") + long_be(0x200100) + RTS)
        disc = mcc.Discovery(data)
        disc.add_root(0x200, "test", "A")
        self.assertEqual(disc.bank_refs, {0x200: 0x200100})
        self.assertEqual(sorted(disc.instrs), [0x200, 0x206])

    def test_base_roots_read_vectors_and_header(self):
        data = image(0x400)
        put(data, 4, long_be(0xc00402))  # BIOS: ignored
        put(data, 8, long_be(0x202))
        put(data, 0x20, long_be(0x202))  # duplicate target kept once
        put(data, 0x122, bytes.fromhex("4ef9") + long_be(0x300))
        put(data, 0x202, RTS)
        put(data, 0x300, RTS)
        disc = mcc.Discovery(data)
        roots = mcc.base_roots(disc)
        self.assertEqual([(a, k) for a, k, _ in roots],
                         [(0x202, "vector"), (0x122, "neogeo_header_jmp")])

    def test_run_discovery_layers(self):
        data = image(0x400)
        put(data, 8, long_be(0x202))
        put(data, 0x202, RTS)
        put(data, 0x300, NOP + RTS)
        atoms = [{"start": 0x300, "end": 0x304, "kind": "range"}]
        disc, sweep = mcc.run_discovery(data, atoms, do_sweep=False)
        self.assertEqual(disc.instrs[0x202][1], "A")
        self.assertEqual(disc.instrs[0x300][1], "R")
        self.assertEqual(sweep, {})


class CoverageTests(unittest.TestCase):
    def test_summary_buckets_and_runs(self):
        routed = mcc.IntervalSet([(0x200, 0x206)])
        instrs = {0x200: (2, "A", 0), 0x202: (2, "A", 0), 0x204: (2, "A", 0),
                  0x206: (2, "B", 1), 0x208: (2, "B", 1), 0x20c: (2, "B", 1)}
        summary = mcc.coverage_summary(instrs, routed, lambda layer: True)
        self.assertEqual(summary["instructions"], 6)
        self.assertEqual(summary["covered_instructions"], 3)
        self.assertEqual(summary["instruction_coverage"], 0.5)
        only_a = mcc.coverage_summary(instrs, routed, lambda layer: layer == "A")
        self.assertEqual(only_a["instruction_coverage"], 1.0)
        buckets = mcc.bucket_summary(instrs, routed, 0x20000)
        self.assertEqual(len(buckets), 2)
        self.assertEqual(buckets[0]["instructions"], 6)
        self.assertEqual(buckets[1]["instruction_coverage"], None)
        roots = [{"addr": 0x200, "kind": "vector", "source_pc": None},
                 {"addr": 0x206, "kind": "lea", "source_pc": 0x204}]
        runs, info = mcc.uncovered_runs(instrs, routed, mcc.IntervalSet([]), roots, 5)
        self.assertEqual(info, {"runs": 2, "uncovered_bytes": 6})
        self.assertEqual(runs[0]["start"], "0x000206")
        self.assertEqual(runs[0]["bytes"], 4)
        self.assertEqual(runs[0]["first_reached_from"]["kind"], "lea")
        self.assertEqual(runs[1]["start"], "0x00020c")

    def test_routed_gap_report(self):
        instrs = {0x200: (4, "A", 0), 0x204: (2, "A", 0)}
        report = mcc.routed_gap_report(instrs, [(0x200, 0x20a)], 5)
        self.assertEqual(report["routed_bytes"], 10)
        self.assertEqual(report["routed_bytes_discovered"], 6)
        self.assertEqual(report["largest_routed_undiscovered_gaps"],
                         [{"start": "0x000206", "end": "0x00020a", "bytes": 4}])

    def test_sweep_requires_terminator_and_min_length(self):
        data = image()
        put(data, 0x200, NOP * 4 + RTS)   # 5 instructions ending in rts: accepted
        put(data, 0x300, NOP * 2 + RTS)   # too short
        disc = mcc.Discovery(data)
        found = disc.sweep()
        self.assertEqual(sorted(a for a in found if a < 0x300), [0x200, 0x202, 0x204, 0x206, 0x208])
        self.assertNotIn(0x300, found)


if __name__ == "__main__":
    unittest.main()
