"""Static code-coverage baseline: how much discoverable program code is routed
through engine/src/animation_machine.cpp.

Method (see docs/analysis/code-coverage-baseline.md):
  1. Recursive-descent discovery over the fixed program ROM (CPU 0..fffff, CPU
     address == file offset) with Capstone M68K (68000) used only for instruction
     size/validity; control flow is classified from opcode bits here.
  2. Layer A: cartridge vectors (0..7f) and the Neo Geo header JMPs, followed
     through direct control flow only.
     Layer B: plus immediate code pointers (MOVE.L #imm / LEA / PEA) and BRA
     jump tables found in already discovered code [I].
     Layer R: plus roots taken from the routed PCs of animation_machine.cpp.
     Layer C (optional): heuristic linear sweep of the remaining gaps [I]; it is
     reported separately and never followed or mixed into A/B/R.
  3. Coverage = discovered instructions whose start PC lies in a routed range.

Indirect jumps (JMP/JSR through An or computed offsets other than BRA tables)
stay unresolved, and code/data ambiguity is not resolved. This is a baseline
measurement, not an analysis result. The ROM is only read.
"""

import argparse
import bisect
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import capstone

ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(__file__).resolve().parent
FIXED_LIMIT = 0x100000
BANK_START = 0x200000
BANK_END = 0x2fdfff
BUCKET = 0x10000
MIN_ENTRY = 0x100
DECODE_WINDOW = 24
MAX_TABLE_ENTRIES = 256
SWEEP_MIN_INSTRUCTIONS = 4
SWEEP_MAX_BYTES = 4096
LAYER_ORDER = ('A', 'B', 'R')
SCHEMA_VERSION = 1


def hx(value):
    return '0x%06x' % value


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def s16(value):
    return value - 0x10000 if value & 0x8000 else value


def s8(value):
    return value - 0x100 if value & 0x80 else value


# ---------------------------------------------------------------------------
# Routed ranges of animation_machine.cpp and documented ranges
# ---------------------------------------------------------------------------

_HEX = r'(0x[0-9a-fA-F]+)'
_RANGE_RE = re.compile(
    r'\(\s*next\.pc>=' + _HEX + r'\s*&&\s*next\.pc(<=|<)' + _HEX +
    r'((?:\s*&&\s*next\.pc!=' + _HEX + r')*)\s*\)')
_SINGLE_RE = re.compile(r'next\.pc==' + _HEX)
_EXCL_RE = re.compile(r'next\.pc!=' + _HEX)


def parse_routed_atoms(text):
    """Return (atoms, expected_ge_count).

    Each atom is {'start', 'end' (exclusive), 'kind'} where kind is 'range' or
    'single'; exclusions (&& next.pc!=X) split a range. Predicates that are not
    plain PC comparisons (e.g. stage_event_ops_trap) are not modelled.
    """
    atoms = []
    for match in _RANGE_RE.finditer(text):
        lo = int(match.group(1), 16)
        hi = int(match.group(3), 16) + (1 if match.group(2) == '<=' else 0)
        excluded = sorted(int(m, 16) for m in _EXCL_RE.findall(match.group(4)))
        cursor = lo
        for point in excluded:
            if lo <= point < hi:
                if point > cursor:
                    atoms.append({'start': cursor, 'end': point, 'kind': 'range'})
                cursor = point + 1
        if cursor < hi:
            atoms.append({'start': cursor, 'end': hi, 'kind': 'range'})
    for match in _SINGLE_RE.finditer(text):
        value = int(match.group(1), 16)
        atoms.append({'start': value, 'end': value + 1, 'kind': 'single'})
    atoms.sort(key=lambda a: (a['start'], a['end'], a['kind']))
    return atoms, text.count('next.pc>=') + text.count('next.pc==0x')


def matched_comparison_count(text):
    return len(_RANGE_RE.findall(text)) + len(_SINGLE_RE.findall(text))


def merge_intervals(intervals):
    """Merge [start, end) intervals that overlap or touch."""
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            if end > merged[-1][1]:
                merged[-1][1] = end
        else:
            merged.append([start, end])
    return [(a, b) for a, b in merged]


class IntervalSet(object):
    def __init__(self, intervals):
        self.intervals = merge_intervals(intervals)
        self.starts = [a for a, _ in self.intervals]

    def contains(self, value):
        index = bisect.bisect_right(self.starts, value) - 1
        return index >= 0 and value < self.intervals[index][1]

    def overlap(self, start, end):
        total = 0
        index = max(bisect.bisect_right(self.starts, start) - 1, 0)
        while index < len(self.intervals) and self.intervals[index][0] < end:
            a, b = self.intervals[index]
            low, high = max(a, start), min(b, end)
            if high > low:
                total += high - low
            index += 1
        return total

    def total_bytes(self):
        return sum(b - a for a, b in self.intervals)


_DOC_RANGE_RE = re.compile(r'0x([0-9a-fA-F]{4,6})\s*\.\.\s*0x([0-9a-fA-F]{4,6})')


def parse_documented_ranges(analysis_dir):
    """Best-effort 0xA..0xB ranges inside fixed ROM from docs/analysis/*.md.

    Ranges are treated as [A, B) and may describe data tables or RAM-adjacent
    text; this is a loose signal [I]. Returns (merged intervals, sources).
    """
    sources = {}
    for path in sorted(Path(analysis_dir).glob('*.md')):
        for match in _DOC_RANGE_RE.finditer(path.read_text(encoding='utf-8')):
            lo, hi = int(match.group(1), 16), int(match.group(2), 16)
            if lo % 2 or lo < MIN_ENTRY or hi > FIXED_LIMIT or hi <= lo or hi - lo > 0x8000:
                continue
            sources.setdefault((lo, hi), set()).add(path.name)
    intervals = sorted(sources)
    listing = [{'start': hx(lo), 'end': hx(hi), 'files': sorted(sources[(lo, hi)])}
               for lo, hi in intervals]
    return merge_intervals(intervals), listing


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

TERMINATOR_OPS = (0x4e75, 0x4e73, 0x4e77, 0x4afc)


def is_terminator(op):
    """RTS/RTE/RTR/ILLEGAL, JMP, or BRA: flow does not fall through."""
    return (op in TERMINATOR_OPS or (op & 0xffc0) == 0x4ec0 or (op & 0xff00) == 0x6000)


class Flow(object):
    """Control-flow facts of one decoded instruction."""
    __slots__ = ('fall', 'targets', 'pointers', 'tables', 'bank_refs',
                 'unresolved', 'bad')

    def __init__(self):
        self.fall = True
        self.targets = []
        self.pointers = []
        self.tables = []
        self.bank_refs = []
        self.unresolved = None
        self.bad = False


class Discovery(object):
    def __init__(self, data):
        self.data = bytes(data)
        self.limit = min(len(self.data), FIXED_LIMIT)
        self.cs = capstone.Cs(capstone.CS_ARCH_M68K,
                              capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_000)
        self.cache = {}
        self.instrs = {}          # addr -> (size, layer, root_index)
        self.roots = []
        self.queue = {}           # target -> (kind, source_pc)
        self.queued = set()
        self.invalid_stops = {}   # addr -> reason
        self.unresolved = {}      # source pc -> description
        self.bank_refs = {}       # (source pc) -> target
        self.bad_targets = {'odd': 0, 'out_of_range': 0, 'low': 0, 'other_region': 0}
        self.rejected = {}        # kind -> count of implausible pointer roots

    # -- decoding ---------------------------------------------------------
    def word(self, addr):
        if addr < 0 or addr + 2 > self.limit:
            return None
        return (self.data[addr] << 8) | self.data[addr + 1]

    def long(self, addr):
        hi, lo = self.word(addr), self.word(addr + 2)
        if hi is None or lo is None:
            return None
        return (hi << 16) | lo

    def decode(self, addr):
        """Return (size, mnemonic) for a valid instruction, else None."""
        if addr in self.cache:
            return self.cache[addr]
        result = None
        if addr % 2 == 0 and 0 <= addr and addr + 2 <= self.limit:
            window = self.data[addr:min(addr + DECODE_WINDOW, self.limit)]
            window = window + bytes(DECODE_WINDOW - len(window))
            row = next(self.cs.disasm_lite(window, addr, count=1), None)
            if row is not None:
                size, mnemonic = row[1], row[2]
                if (mnemonic != 'dc.w' and size >= 2 and size % 2 == 0
                        and addr + size <= self.limit):
                    result = (size, mnemonic)
        self.cache[addr] = result
        return result

    # -- flow classification ---------------------------------------------
    def classify(self, addr, size):
        flow = Flow()
        op = self.word(addr)
        if op in TERMINATOR_OPS:
            flow.fall = False
            return flow
        top = op & 0xf000
        if top == 0x6000:
            cond = (op >> 8) & 0xf
            d8 = op & 0xff
            if d8 == 0:
                ext = self.word(addr + 2)
                disp = s16(ext) if ext is not None else 0
            elif d8 == 0xff:
                flow.bad = True
                flow.fall = False
                return flow
            else:
                disp = s8(d8)
            flow.targets.append((addr + 2 + disp, 'call' if cond == 1 else 'branch'))
            if cond == 0:
                flow.fall = False
            return flow
        if (op & 0xf0f8) == 0x50c8:
            ext = self.word(addr + 2)
            flow.targets.append((addr + 2 + s16(ext or 0), 'branch'))
            return flow
        if (op & 0xffc0) in (0x4ec0, 0x4e80):
            is_jmp = (op & 0xffc0) == 0x4ec0
            mode, reg = (op >> 3) & 7, op & 7
            kind = 'branch' if is_jmp else 'call'
            if mode == 7 and reg == 0:
                flow.targets.append((s16(self.word(addr + 2)) & 0xffffff, kind))
            elif mode == 7 and reg == 1:
                flow.targets.append((self.long(addr + 2) & 0xffffff, kind))
            elif mode == 7 and reg == 2:
                flow.targets.append((addr + 2 + s16(self.word(addr + 2)), kind))
            elif mode == 7 and reg == 3:
                ext = self.word(addr + 2)
                base = addr + 2 + s8(ext & 0xff)
                if ext & 0x0100:
                    flow.unresolved = 'full-format index extension'
                else:
                    flow.tables.append(base)
                    flow.unresolved = 'pc-indexed (BRA-table candidate)'
            else:
                flow.unresolved = ('(An)' if mode == 2 else 'd(An)' if mode == 5
                                   else 'indexed/other')
            if is_jmp:
                flow.fall = False
            return flow
        # Immediate code pointers.
        if top == 0x2000 and (op & 0x3f) == 0x3c:
            dst_mode, dst_reg = (op >> 6) & 7, (op >> 9) & 7
            if dst_mode == 7 and dst_reg in (0, 1):
                dst = 'abs'
            elif 1 <= dst_mode <= 6:
                dst = (None, 'An', '(An)', '(An)+', '-(An)', 'd(An)', 'd8(An,Xn)')[dst_mode]
            else:
                dst = None
            if dst is not None:
                flow.pointers.append((self.long(addr + 2), 'move.l #imm,' + dst))
            return flow
        if (op & 0xf1c0) == 0x41c0 and (op & 0x3f) in (0x38, 0x39, 0x3a):
            flow.pointers.append((self.ea_value(addr, op & 0x3f), 'lea'))
            return flow
        if (op & 0xffc0) == 0x4840 and (op & 0x3f) in (0x38, 0x39, 0x3a):
            flow.pointers.append((self.ea_value(addr, op & 0x3f), 'pea'))
            return flow
        return flow

    def ea_value(self, addr, ea):
        if ea == 0x38:
            return s16(self.word(addr + 2)) & 0xffffff
        if ea == 0x39:
            return self.long(addr + 2) & 0xffffff
        return addr + 2 + s16(self.word(addr + 2))

    # -- target validation ------------------------------------------------
    def check_target(self, target):
        """Return True for a usable fixed-ROM code target; count the rest."""
        if target is None:
            self.bad_targets['out_of_range'] += 1
            return False
        if target % 2:
            self.bad_targets['odd'] += 1
            return False
        if BANK_START <= target <= BANK_END:
            return False
        if target < MIN_ENTRY:
            self.bad_targets['low'] += 1
            return False
        if target >= self.limit:
            self.bad_targets['other_region'] += 1
            return False
        return True

    def plausible_entry(self, target):
        """Pointer-derived roots must start with 4 valid, non-fill instructions
        (or end earlier at a terminator/unconditional branch)."""
        pc = target
        for _ in range(4):
            decoded = self.decode(pc)
            op = self.word(pc)
            if decoded is None or op in (0x0000, 0xffff):
                return False
            if is_terminator(op):
                return True
            pc += decoded[0]
        return True

    # -- exploration ------------------------------------------------------
    def add_root(self, addr, kind, layer, source=None):
        index = len(self.roots)
        root = {'addr': addr, 'kind': kind, 'layer': layer,
                'source_pc': source, 'status': ''}
        self.roots.append(root)
        if not self.check_target(addr):
            root['status'] = 'unresolved_bank' if BANK_START <= addr <= BANK_END \
                else 'bad_target'
            if root['status'] == 'unresolved_bank' and source is not None:
                self.bank_refs[source] = addr
            return index
        if addr in self.instrs:
            root['status'] = 'already_discovered'
            return index
        before = len(self.instrs)
        self.explore(addr, layer, index)
        root['status'] = 'explored'
        root['new_instructions'] = len(self.instrs) - before
        return index

    def enqueue(self, target, kind, source):
        if target in self.queued:
            return
        self.queued.add(target)
        self.queue[target] = (kind, source)

    def explore(self, start, layer, root_index):
        stack = [start]
        while stack:
            pc = stack.pop()
            while True:
                if pc in self.instrs:
                    break
                if pc % 2:
                    self.invalid_stops[pc] = 'odd'
                    break
                decoded = self.decode(pc)
                if decoded is None:
                    self.invalid_stops[pc] = 'invalid_opcode'
                    break
                size = decoded[0]
                flow = self.classify(pc, size)
                if flow.bad:
                    self.invalid_stops[pc] = 'unsupported_68020_branch'
                    break
                self.instrs[pc] = (size, layer, root_index)
                for target, _ in flow.targets:
                    if self.check_target(target):
                        stack.append(target)
                    elif BANK_START <= (target or 0) <= BANK_END:
                        self.bank_refs[pc] = target
                for target, kind in flow.pointers:
                    if target is None:
                        continue
                    if BANK_START <= target <= BANK_END:
                        self.bank_refs[pc] = target
                    elif target not in self.instrs:
                        self.enqueue(target, kind, pc)
                for base in flow.tables:
                    self.collect_table(base, pc)
                if flow.unresolved and not flow.tables:
                    self.unresolved[pc] = flow.unresolved
                if not flow.fall:
                    break
                pc += size

    def collect_table(self, base, source):
        found = 0
        pc = base
        while found < MAX_TABLE_ENTRIES and pc % 2 == 0:
            op = self.word(pc)
            if op is None or (op & 0xff00) != 0x6000 or (op & 0xff) == 0xff:
                break
            size = 4 if (op & 0xff) == 0 else 2
            self.enqueue(pc, 'bra_table', source)
            found += 1
            pc += size
        if found == 0:
            self.unresolved[source] = 'pc-indexed, no BRA table at target'
        return found

    def drain(self, layer):
        while self.queue:
            batch = sorted(self.queue.items())
            self.queue = {}
            for target, (kind, source) in batch:
                if target in self.instrs:
                    continue
                if kind != 'bra_table' and not (
                        self.check_target(target) and self.plausible_entry(target)):
                    self.rejected[kind] = self.rejected.get(kind, 0) + 1
                    continue
                self.add_root(target, kind, layer, source)

    # -- heuristic sweep (layer C) ---------------------------------------
    def sweep(self):
        found = {}
        pc = MIN_ENTRY
        limit = self.limit
        while pc < limit:
            if pc in self.instrs:
                pc += self.instrs[pc][0]
                continue
            run = []
            cursor = pc
            ok = False
            while cursor < limit and cursor not in self.instrs and len(run) < 4096:
                decoded = self.decode(cursor)
                op = self.word(cursor)
                if decoded is None or op in (0x0000, 0xffff):
                    break
                run.append((cursor, decoded[0]))
                cursor += decoded[0]
                if (cursor - pc) > SWEEP_MAX_BYTES:
                    break
                if is_terminator(op):
                    ok = len(run) >= SWEEP_MIN_INSTRUCTIONS
                    break
            if ok:
                for addr, size in run:
                    found[addr] = size
                pc = cursor
            else:
                pc += 2
        return found


# ---------------------------------------------------------------------------
# Roots from the ROM image
# ---------------------------------------------------------------------------

def base_roots(disc):
    """Cartridge vectors 0..7f (entries pointing into fixed ROM) and the Neo Geo
    header JMP slots at 0x122/0x128/0x12e/0x134 when they hold JMP abs.l."""
    roots = []
    for vector_addr in range(4, 0x80, 4):
        target = disc.long(vector_addr)
        if target is not None and MIN_ENTRY <= target < disc.limit and target % 2 == 0:
            if not any(r[0] == target for r in roots):
                roots.append((target, 'vector', vector_addr))
    for slot in (0x122, 0x128, 0x12e, 0x134):
        if disc.word(slot) == 0x4ef9:
            roots.append((slot, 'neogeo_header_jmp', slot))
    return roots


def routed_roots(atoms):
    seen = set()
    roots = []
    for atom in atoms:
        start = (atom['start'] + 1) & ~1  # an excluded PC leaves an odd start
        if start not in seen:
            seen.add(start)
            roots.append((start, 'animation_machine_routed_pc', None))
    return sorted(roots)


def run_discovery(data, atoms, do_sweep=True):
    disc = Discovery(data)
    for addr, kind, source in base_roots(disc):
        disc.add_root(addr, kind, 'A', source)
    disc.drain('B')
    for addr, kind, source in routed_roots(atoms):
        if addr in disc.instrs:
            disc.roots.append({'addr': addr, 'kind': kind, 'layer': 'R',
                               'source_pc': source, 'status': 'already_discovered'})
        else:
            if disc.check_target(addr) and disc.decode(addr) is not None:
                disc.add_root(addr, kind, 'R', source)
            else:
                disc.roots.append({'addr': addr, 'kind': kind, 'layer': 'R',
                                   'source_pc': source, 'status': 'rejected_not_code'})
        disc.drain('R')
    sweep = disc.sweep() if do_sweep else {}
    return disc, sweep


# ---------------------------------------------------------------------------
# Coverage computation
# ---------------------------------------------------------------------------

def ratio(num, den):
    return round(num / den, 6) if den else None


def coverage_summary(instrs, routed, selector):
    """instrs: addr->(size,...) restricted by selector(layer)->bool."""
    n = covered_n = nbytes = covered_bytes = 0
    for addr, info in instrs.items():
        if not selector(info[1]):
            continue
        n += 1
        nbytes += info[0]
        if routed.contains(addr):
            covered_n += 1
            covered_bytes += info[0]
    return {'instructions': n, 'covered_instructions': covered_n,
            'instruction_coverage': ratio(covered_n, n),
            'bytes': nbytes, 'covered_bytes': covered_bytes,
            'byte_coverage': ratio(covered_bytes, nbytes)}


def bucket_summary(instrs, routed, limit):
    rows = []
    for index in range(0, (limit + BUCKET - 1) // BUCKET):
        rows.append({'bucket': '%06x..%06x' % (index * BUCKET, (index + 1) * BUCKET - 1),
                     'instructions': 0, 'covered_instructions': 0,
                     'bytes': 0, 'covered_bytes': 0})
    for addr, info in instrs.items():
        row = rows[addr // BUCKET]
        row['instructions'] += 1
        row['bytes'] += info[0]
        if routed.contains(addr):
            row['covered_instructions'] += 1
            row['covered_bytes'] += info[0]
    for row in rows:
        row['instruction_coverage'] = ratio(row['covered_instructions'], row['instructions'])
    return rows


def uncovered_runs(instrs, routed, doc_set, roots, top):
    """Contiguous (end == next start) runs of discovered, non-routed instructions."""
    runs = []
    current = None
    for addr in sorted(instrs):
        size, layer, root_index = instrs[addr]
        if routed.contains(addr):
            current = None
            continue
        if current is not None and current['end'] == addr:
            current['end'] = addr + size
            current['instructions'] += 1
            current['root_indexes'].add(root_index)
            current['layers'].add(layer)
        else:
            current = {'start': addr, 'end': addr + size, 'instructions': 1,
                       'first_layer': layer, 'first_root': root_index,
                       'root_indexes': set([root_index]), 'layers': set([layer])}
            runs.append(current)
    runs.sort(key=lambda r: (-(r['end'] - r['start']), r['start']))
    rows = []
    for run in runs[:top]:
        root = roots[run['first_root']]
        length = run['end'] - run['start']
        rows.append({
            'start': hx(run['start']), 'end': hx(run['end']), 'bytes': length,
            'instructions': run['instructions'],
            'first_layer': run['first_layer'],
            'layers': sorted(run['layers']),
            'first_reached_from': {'addr': hx(root['addr']), 'kind': root['kind'],
                                   'source_pc': None if root['source_pc'] is None
                                   else hx(root['source_pc'])},
            'distinct_roots': len(run['root_indexes']),
            'documented_range_overlap_bytes': doc_set.overlap(run['start'], run['end'])})
    total = sum(r['end'] - r['start'] for r in runs)
    return rows, {'runs': len(runs), 'uncovered_bytes': total}


def routed_gap_report(instrs, merged_routed, top):
    """Routed bytes that no discovered instruction covers (data, or code missed
    by static flow)."""
    starts = sorted(instrs)
    ends = [a + instrs[a][0] for a in starts]
    gaps = []
    covered_total = routed_total = 0
    for lo, hi in merged_routed:
        routed_total += hi - lo
        cursor = lo
        index = max(bisect.bisect_right(starts, lo) - 1, 0)
        # An instruction starting before lo may straddle into the range.
        while index < len(starts) and starts[index] < hi:
            a, b = starts[index], ends[index]
            if b > lo:
                begin, finish = max(a, lo), min(b, hi)
                if begin > cursor:
                    gaps.append((cursor, begin))
                covered_total += finish - begin
                cursor = max(cursor, finish)
            index += 1
        if cursor < hi:
            gaps.append((cursor, hi))
    gaps.sort(key=lambda g: (-(g[1] - g[0]), g[0]))
    return {'routed_bytes': routed_total, 'routed_bytes_discovered': covered_total,
            'routed_bytes_discovered_ratio': ratio(covered_total, routed_total),
            'routed_undiscovered_gaps': len(gaps),
            'largest_routed_undiscovered_gaps': [
                {'start': hx(a), 'end': hx(b), 'bytes': b - a} for a, b in gaps[:top]]}


def build_report(root, data, rom_source, do_sweep=True, top=40):
    cpp_path = root / 'engine/src/animation_machine.cpp'
    cpp_text = cpp_path.read_text(encoding='utf-8')
    atoms, _ = parse_routed_atoms(cpp_text)
    matched = matched_comparison_count(cpp_text)
    ge_total = cpp_text.count('next.pc>=') + cpp_text.count('next.pc==0x')
    routed_intervals = [(a['start'], a['end']) for a in atoms]
    routed = IntervalSet(routed_intervals)
    doc_intervals, doc_listing = parse_documented_ranges(root / 'docs/analysis')
    doc_set = IntervalSet(doc_intervals)

    disc, sweep = run_discovery(data, atoms, do_sweep)
    instrs = disc.instrs
    cumulative = {
        'A': coverage_summary(instrs, routed, lambda l: l == 'A'),
        'A+B': coverage_summary(instrs, routed, lambda l: l in ('A', 'B')),
        'A+B+R': coverage_summary(instrs, routed, lambda l: True)}
    per_layer = {}
    for layer in LAYER_ORDER:
        count = sum(1 for v in instrs.values() if v[1] == layer)
        per_layer[layer] = {'instructions': count,
                            'bytes': sum(v[0] for v in instrs.values() if v[1] == layer)}
    union_set = IntervalSet(routed_intervals + doc_intervals)
    with_docs = coverage_summary(instrs, union_set, lambda l: True)

    sweep_info = None
    if do_sweep:
        sweep_entries = dict((a, (s, 'C', -1)) for a, s in sweep.items())
        sweep_info = {
            'label': '[I] heuristic only; not part of A/B/R',
            'instructions': len(sweep),
            'bytes': sum(sweep.values()),
            'inside_routed_instructions': sum(1 for a in sweep if routed.contains(a)),
            'outside_routed_instructions': sum(1 for a in sweep if not routed.contains(a)),
            'outside_routed_bytes': sum(s for a, s in sweep.items() if not routed.contains(a)),
            'per_bucket': bucket_summary(sweep_entries, routed, disc.limit)}

    runs, run_summary = uncovered_runs(instrs, routed, doc_set, disc.roots, top)

    # Instruction overlap (an instruction start inside another instruction body).
    overlaps = []
    previous_end = 0
    previous = None
    for addr in sorted(instrs):
        if addr < previous_end:
            overlaps.append((previous, addr))
        end = addr + instrs[addr][0]
        if end > previous_end:
            previous_end = end
            previous = addr

    root_kinds = {}
    for r in disc.roots:
        key = (r['layer'], r['kind'], r['status'])
        root_kinds[key] = root_kinds.get(key, 0) + 1
    root_rows = [{'layer': k[0], 'kind': k[1], 'status': k[2], 'count': v}
                 for k, v in sorted(root_kinds.items())]
    named_roots = [{'addr': hx(r['addr']), 'kind': r['kind'], 'layer': r['layer'],
                    'status': r['status'], 'new_instructions': r.get('new_instructions', 0)}
                   for r in disc.roots if r['layer'] == 'A']

    unresolved_kinds = {}
    for desc in disc.unresolved.values():
        unresolved_kinds[desc] = unresolved_kinds.get(desc, 0) + 1

    tool_path = Path(__file__).resolve()
    report = {
        'schema_version': SCHEMA_VERSION,
        'format': 'mslug5-static-code-coverage-baseline',
        'status': 'baseline measurement; static discovery is a candidate set, not analysis',
        'inputs': {
            'rom_image': {'path': rom_source['path'], 'sha256': rom_source['sha256'],
                          'size': rom_source['size']},
            'animation_machine_cpp': {'path': 'engine/src/animation_machine.cpp',
                                      'sha256': sha256_file(cpp_path)},
            'tool': {'path': 'tools/measure_code_coverage.py',
                     'sha256': sha256_file(tool_path)},
            'decoder': {'name': 'capstone', 'version': capstone.__version__,
                        'architecture': 'M68K', 'cpu': '68000', 'byte_order': 'big'},
            'documented_range_sources': sorted(set(f for e in doc_listing for f in e['files'])),
        },
        'parameters': {'bucket_bytes': BUCKET, 'min_entry': hx(MIN_ENTRY),
                       'max_table_entries': MAX_TABLE_ENTRIES,
                       'sweep_enabled': bool(do_sweep),
                       'sweep_min_instructions': SWEEP_MIN_INSTRUCTIONS,
                       'sweep_max_bytes': SWEEP_MAX_BYTES, 'top_runs': top},
        'routed_ranges': {
            'source': 'engine/src/animation_machine.cpp next.pc comparisons',
            'comparison_atoms_matched': matched,
            'comparison_atoms_expected': ge_total,
            'comparison_atoms_note': 'next.pc==stop_pc is not a constant and is ignored',
            'atoms': len(atoms),
            'merged_ranges': len(routed.intervals),
            'merged_bytes': routed.total_bytes(),
            'above_fixed_rom': sum(1 for a, _ in routed.intervals if a >= FIXED_LIMIT),
            'not_modelled': 'non-PC predicates such as stage_event_ops_trap(next.pc)',
            'merged': [{'start': hx(a), 'end': hx(b)} for a, b in routed.intervals]},
        'documented_ranges': {
            'label': '[I] best-effort 0xA..0xB ranges in docs/analysis/*.md (fixed ROM, '
                     '<=0x8000 bytes); may include data tables',
            'ranges': len(doc_listing), 'merged_bytes': doc_set.total_bytes()},
        'discovery': {
            'regions': {'fixed_0_fffff': {
                'cpu_equals_file_offset': True, 'limit': hx(disc.limit)},
                'banked_200000_2fdfff': {
                    'discovered_instructions': 0,
                    'note': 'bank_base is unknown statically; references are counted, '
                            'not followed',
                    'referenced_targets': len(disc.bank_refs)}},
            'layers': per_layer,
            'total_instructions': len(instrs),
            'total_bytes': sum(v[0] for v in instrs.values()),
            'base_roots': named_roots,
            'root_summary': root_rows,
            'routed_roots_rejected_not_code': [hx(r['addr']) for r in disc.roots
                                               if r['status'] == 'rejected_not_code'],
            'pointer_candidates_rejected_as_implausible': dict(sorted(disc.rejected.items())),
            'invalid_stops': len(disc.invalid_stops),
            'invalid_stop_reasons': dict(sorted(
                (reason, sum(1 for v in disc.invalid_stops.values() if v == reason))
                for reason in set(disc.invalid_stops.values()))),
            'unresolved_indirect_jumps': len(disc.unresolved),
            'unresolved_indirect_by_kind': dict(sorted(unresolved_kinds.items())),
            'bad_flow_targets': disc.bad_targets,
            'instruction_overlaps': len(overlaps),
            'instruction_overlap_samples': [[hx(a), hx(b)] for a, b in overlaps[:10]]},
        'coverage': {
            'definition': 'discovered instructions whose start PC lies in a merged routed range',
            'cumulative': cumulative,
            'with_documented_ranges_added': dict(with_docs, label='[I]'),
            'per_bucket_A+B+R': bucket_summary(instrs, routed, disc.limit),
            'banked_200000_2fdfff': {'instructions': 0, 'covered_instructions': 0},
            'routed_vs_discovered': routed_gap_report(instrs, routed.intervals, 20)},
        'uncovered': dict(run_summary, largest_runs=runs,
                          basis='A+B+R discovered instructions outside routed ranges, '
                                'contiguous end==start'),
        'heuristic_sweep': sweep_info,
    }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--root', default=str(ROOT))
    parser.add_argument('--output', default='artifacts/code_coverage/report.json')
    parser.add_argument('--no-sweep', action='store_true')
    parser.add_argument('--top', type=int, default=40)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    sys.path.insert(0, str(TOOLS))
    from disassemble_program import load_verified_program
    started = time.time()
    data, source = load_verified_program(root)
    report = build_report(root, data, source, do_sweep=not args.no_sweep, top=args.top)
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    if output.suffix != '.json':
        raise SystemExit('Output must use the .json suffix')
    if (root / 'artifacts').resolve() not in output.resolve().parents:
        raise SystemExit('Output must be inside the artifacts directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    cov = report['coverage']['cumulative']
    for name in ('A', 'A+B', 'A+B+R'):
        c = cov[name]
        print('%-6s instr=%d covered=%d (%.2f%%) bytes=%d covered=%d (%.2f%%)' % (
            name, c['instructions'], c['covered_instructions'],
            100.0 * (c['instruction_coverage'] or 0), c['bytes'], c['covered_bytes'],
            100.0 * (c['byte_coverage'] or 0)))
    print('wrote %s in %.1fs' % (output, time.time() - started))


if __name__ == '__main__':
    main()
