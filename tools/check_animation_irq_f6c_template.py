"""Template proof of unit F6c (IRQ sprite writer families; contract docs/analysis/animation-machine-irq-f6c-contract.md).

Reads the canonical BE ROM (read only) and proves, for every routine k = 0..7 of family A (table f226, forward) and family B (table
13b46, reverse), that the routine is the frame-head routine k (H8 ce62 table for A, H4 11792 table for B) with exactly these edits:
  V1 (V = bit 1 of k):  MOVEQ #0,D4; MOVE.B D7,D4; LSL.W #4,D4; NOT.W D6; ADD.W D4,D6     after MOVE.W (A3)+,D7 [H: NEG.W D5]
  N  (not S):           LSL.W #7,D6; MOVE.W 8(A2),D4; ANDI.W #ff80,D4; ADD.W D4,D6; OR.B D7,D6   after ADD.W 2(A2),D5
  S  (S = bit 2 of k):  MOVEQ #0,D2; MOVE.B 5(A2),D2; ADDQ.W #1,D2; MOVE.W D6,D3; MULS.W D2,D3; CLR.B D3; ASR.L #1,D3; MOVE.W D3,D6;
                        MOVE.W 8(A2),D3; ANDI.W #ff80,D3; ADD.W D3,D6; MOVEQ #0,D3; MOVE.B D7,D3; MULU.W D2,D3; ADDI.W #ff,D3;
                        LSR.W #8,D3; OR.B D3,D6                                         after V1 (or its anchor)
  T  test operand:      A: CMP.W 6(A4),D6 -> CMP.W 2(A4),D6;   B: CMP.W 4(A4),D6 -> CMP.W (A4),D6
  C  column head:       MOVE.L #8201,D2; MOVE.L D6,D0; ADD.W D2,D0; SWAP D0; MOVE.L D0,(A6); CMP.W 6(A4),D6; BMI.B skip (A)
                        ... CMP.W 4(A4),D6; BPL.B step (B)         before the column's MOVE.W D6,D0 (A) / after SUBQ.W #1,D6 (B)
Instruction text is compared exactly (immediates included); every branch / computed-jump target of the IRQ routine must be the image of
the head routine's target under the instruction mapping (the inserted BMI.B targets the image of H8's unreached ADDQ.W #1,D6 at step - 2,
the inserted BPL.B the image of H4's step).  It then derives the role table of every routine, the 624 / 616 block-start lists and the
128 / 128 Duff entries, checks the contract SHA256 values, checks the Duff index range (SUBQ.B #1; ANDI.B #1f; ADD.B D7,D7 at height,
D7.B unchanged up to the Duff head: D3.W = 4 * D7.B = 0..f8 step 8) and compares the role table with the FAMILIES table of
engine/src/animation_machine_irq_f6c.cpp.  Exit status 0 = proof holds.

Usage: .venv/bin/python -I tools/check_animation_irq_f6c_template.py [--json out.json]
"""
import hashlib
import json
from pathlib import Path
import re
import sys

import capstone

ROOT = Path(__file__).resolve().parent.parent
ROM_PATH = ROOT / 'extracted/program/maincpu.decrypted.be.bin'
ROM_SHA = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
CPP = ROOT / 'engine/src/animation_machine_irq_f6c.cpp'
CONTRACT_SHA = {'A': ('81029d4d9dab58cef7e73c45469ae5f061c2dcdc05d4b12cb5d3834c178fd381', '1487c88d15fcaf87f20e6de4e2a4b8a4be1b9e6ae63032b3cb9bab4aa4aaeb3e'),
                'B': ('ccfe82248baf2fd17774a8da0e2865064e1b1ffe3f786ea1556f567f8dd908d5', 'd10a59d9f24bd78cece9ffcdeb42bc9de308e56160d9d6f842b09a783817b0e0')}
FAMILIES = (('A', 0xf226, 0x11792, 0xce62, 0xf226, True), ('B', 0x13b46, 0x16092, 0x11792, 0x13b46, False))
V1 = ['moveq #$0, d4', 'move.b d7, d4', 'lsl.w #$4, d4', 'not.w d6', 'add.w d4, d6']
N = ['lsl.w #$7, d6', 'move.w $8(a2), d4', 'andi.w #$ff80, d4', 'add.w d4, d6', 'or.b d7, d6']
S = ['moveq #$0, d2', 'move.b $5(a2), d2', 'addq.w #$1, d2', 'move.w d6, d3', 'muls.w d2, d3', 'clr.b d3', 'asr.l #$1, d3', 'move.w d3, d6',
     'move.w $8(a2), d3', 'andi.w #$ff80, d3', 'add.w d3, d6', 'moveq #$0, d3', 'move.b d7, d3', 'mulu.w d2, d3', 'addi.w #$ff, d3', 'lsr.w #$8, d3',
     'or.b d3, d6']
ROLE_NAMES = ('head', 'swap7', 'outer', 'height', 'skip', 'step', 'advance', 'test', 'scale', 'clip', 'scb3', 'column', 'table', 'cells', 'duff',
              'next', 'finish', 'end')
BRANCHES = ('bra', 'bcs', 'bcc', 'bmi', 'bpl', 'ble', 'bgt', 'beq', 'bne', 'jmp')


def require(ok, detail):
    if not ok:
        raise SystemExit('template proof failed: %s' % (detail,))


ROM = ROM_PATH.read_bytes()
require(hashlib.sha256(ROM).hexdigest() == ROM_SHA, 'canonical BE ROM SHA256')
MD = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_000)


def disasm(lo, hi):
    out, pc = [], lo
    for i in MD.disasm(ROM[lo:hi], lo):
        require(i.address == pc, ('decode gap', hex(pc)))
        out.append((i.address, i.mnemonic, i.op_str))
        pc += i.size
    require(pc == hi, ('decode end', hex(pc), hex(hi)))
    return out


def target(op):
    return int(re.search(r'\$([0-9a-f]+)', op).group(1), 16)


def is_branch(m):
    return m.split('.')[0] in BRANCHES


def text(ins):
    m, o = ins[1], ins[2]
    return m + ' ' + ('$T' + o[o.index('('):] if m == 'jmp' else '$T') if is_branch(m) else m + ' ' + o


def routines(table):
    out = []
    for k in range(8):
        require(ROM[table + 4 * k:table + 4 * k + 2] == b'\x60\x00', ('BRA.W slot', hex(table + 4 * k)))
        d = int.from_bytes(ROM[table + 4 * k + 2:table + 4 * k + 4], 'big', signed=True)
        out.append(table + 4 * k + 2 + d)
    return out


def expected(head, fwd, h, v, s):
    """Head routine instruction list -> list of (head index or None, text) after the edits."""
    t = [text(x) for x in head]
    out = [(i, x) for i, x in enumerate(t)]
    def find(pattern, start=0):
        for j in range(start, len(out)):
            if out[j][1] == pattern:
                return j
        require(False, ('anchor', pattern))
    a = find('move.w (a3)+, d7', find('neg.w d6'))     # the outer block's read (the head block reads (A3)+ into D7 first)
    if h:
        require(out[a + 1][1] == 'neg.w d5', 'H anchor')
        a += 1
    ins = (V1 if v else []) + (S if s else [])
    out[a + 1:a + 1] = [(None, x) for x in ins]
    if not s:
        b = find('add.w $2(a2), d5')
        out[b + 1:b + 1] = [(None, x) for x in N]
    j = find('cmp.w $6(a4), d6' if fwd else 'cmp.w $4(a4), d6')
    out[j] = (out[j][0], 'cmp.w $2(a4), d6' if fwd else 'cmp.w (a4), d6')
    col = ['move.l #$8201, d2', 'move.l d6, d0', 'add.w d2, d0', 'swap d0', 'move.l d0, (a6)']
    if fwd:
        c = find('addi.w #$8401, d0') - 1
        out[c:c] = [(None, x) for x in col + ['cmp.w $6(a4), d6', 'bmi.b $T']]
    else:
        c = find('addi.w #$8401, d0') - 2
        require(out[c][1] == 'subq.w #$1, d6', 'B column anchor')
        out[c + 1:c + 1] = [(None, x) for x in col + ['cmp.w $4(a4), d6', 'bpl.b $T']]
    return out


def prove_routine(fam, k, head, irq, fwd):
    h, v, s = bool(k & 1), bool(k & 2), bool(k & 4)
    exp = expected(head, fwd, h, v, s)
    require(len(exp) == len(irq), (fam, k, 'length', len(exp), len(irq)))
    image = {}
    for (hi, t), ins in zip(exp, irq):
        require(t == text(ins), (fam, k, hex(ins[0]), t, text(ins)))
        if hi is not None:
            image[head[hi][0]] = ins[0]
    # branch targets: images of the head routine targets
    hpos = {x[0]: i for i, x in enumerate(head)}
    for (hi, t), ins in zip(exp, irq):
        if not is_branch(ins[1]):
            continue
        tg = target(ins[2])
        if hi is None:
            if fwd:   # image of H8's unreached ADDQ.W #1,D6 (step - 2)
                step_h = [x[0] for x in head if text(x) == 'moveq #$2, d2'][0]
                want = image[head[hpos[step_h] - 1][0]]
                require(text(head[hpos[step_h] - 1]) == 'addq.w #$1, d6', 'H8 step - 2')
            else:
                want = image[[x[0] for x in head if text(x) == 'moveq #$2, d2'][0]]
        else:
            ht = target(head[hi][2])
            want = image.get(ht)
            require(want is not None, (fam, k, 'unmapped target', hex(ht)))
        require(tg == want, (fam, k, hex(ins[0]), hex(tg), hex(want)))
    return image


def roles(lo, hi, fwd):
    L = disasm(lo, hi)
    at = {x[0]: i for i, x in enumerate(L)}
    R = dict(head=lo, end=hi)
    i = next(i for i, x in enumerate(L) if x[1] == 'bcs.w')
    R['finish'], R['swap7'], R['outer'] = target(L[i][2]), L[i + 1][0], L[i + 2][0]
    R['height'] = next(x[0] for x in L if text(x) == 'subq.b #$1, d7')
    st = next(i for i, x in enumerate(L) if text(x) == 'moveq #$2, d2' and text(L[i + 1]) == 'add.b d7, d2')
    R['step'], R['skip'] = L[st][0], (L[st - 1][0] if fwd else 0)
    require(L[st + 5][1] == 'bcs.w', 'step BCS')
    R['next'] = target(L[st + 5][2])
    t = next(i for i, x in enumerate(L) if x[1] == 'cmp.w' and x[2].endswith('(a4), d6'))
    R['test'] = L[t][0]
    R['advance'] = L[st + 6][0] if L[st + 6][0] != R['test'] else 0
    j = t + 2
    R['scale'] = 0
    if text(L[j]) == 'andi.w #$ff, d4':
        R['scale'] = L[j][0]
        j += 3
    R['clip'] = L[j][0]
    c = next(i for i, x in enumerate(L) if text(x) == 'move.l #$8201, d2')
    R['scb3'] = L[c][0] if fwd else L[c - 1][0]
    R['column'] = L[c + 7][0]
    jm = [x for x in L if x[1] == 'jmp']
    R['table'] = target(jm[0][2])
    entries = [target(L[at[R['table'] + 4 * e]][2]) for e in range(32)]
    R['cells'] = entries[31]
    require(all(entries[e] == R['cells'] + 18 * (31 - e) for e in range(32)), 'cell table')
    R['duff'] = target(jm[1][2]) if len(jm) > 1 else 0
    # Duff index: height block SUBQ.B #1,D7; ANDI.B #1f,D7; ADD.B D7,D7 and the Duff head SWAP D3; CLR.W D3; MOVE.B D7,D3; ADD.W D3,D3 x2.
    hh = at[R['height']]
    require([text(x) for x in L[hh:hh + 3]] == ['subq.b #$1, d7', 'andi.b #$1f, d7', 'add.b d7, d7'], 'height block')
    if R['duff']:
        d = [i for i, x in enumerate(L) if x[1] == 'jmp'][1]
        require([text(x) for x in L[d - 2:d]] == ['add.w d3, d3', 'add.w d3, d3'], 'Duff index')
        require(R['duff'] + 8 * 31 + (16 if fwd else 14) == R['next'], 'Duff tail')   # SWAP D3; MOVEM; [A: ADDQ]; SUBI; BCC
    return R


def starts_of(table, rs):
    out = [table + 4 * k for k in range(8)]
    duff = []
    for R in rs:
        out += [R[x] for x in ('head', 'swap7', 'outer', 'height', 'skip', 'step', 'advance', 'test', 'scale', 'clip', 'scb3', 'column', 'next', 'finish') if R[x]]
        out += [R['table'] + 4 * e for e in range(32)] + [R['cells'] + 18 * e for e in range(32)]
        if R['duff']:
            duff += [R['duff'] + 8 * e for e in range(32)]
    return sorted(set(out)), duff


def cpp_table():
    src = CPP.read_text()
    out = {}
    for fam in ('A', 'B'):
        m = re.search(r'const F6cRoutine F6C_%s\[8\]=\{(.*?)\};' % fam, src, re.S)
        require(m, ('C++ table', fam))
        rows = re.findall(r'\{([^{}]*)\}', m.group(1))
        out[fam] = [[int(v, 16) if v.startswith('0x') else (v == 'true' if v in ('true', 'false') else int(v)) for v in re.sub(r'\s', '', r).split(',')] for r in rows]
    return out


def main():
    report = {}
    cpp = cpp_table()
    for fam, table, end, htable, hend, fwd in FAMILIES:
        irq = routines(table) + [end]
        head = routines(htable) + [hend]
        require(irq[0] == table + 32 and head[0] == htable + 32 and all(irq[k] < irq[k + 1] for k in range(8)), (fam, 'routine order'))
        rs = []
        for k in range(8):
            prove_routine(fam, k, disasm(head[k], head[k + 1]), disasm(irq[k], irq[k + 1]), fwd)
            R = roles(irq[k], irq[k + 1], fwd)
            rs.append(R)
            row = [R[n] for n in ROLE_NAMES] + [bool(k & 1), bool(k & 2), bool(k & 4)]
            require(cpp[fam][k] == row, (fam, k, 'C++ role row', cpp[fam][k], row))
        starts, duff = starts_of(table, rs)
        sa = hashlib.sha256(' '.join('%x' % x for x in starts).encode()).hexdigest()
        sd = hashlib.sha256(' '.join('%x' % x for x in duff).encode()).hexdigest()
        require((sa, sd) == CONTRACT_SHA[fam], (fam, 'contract SHA', sa, sd))
        report[fam] = dict(starts=len(starts), duff=len(duff), routines=[{n: R[n] for n in ROLE_NAMES} for R in rs], starts_sha=sa, duff_sha=sd)
        print('family %s: 8 routines = head family + edits (exact text, mapped targets); %d starts, %d Duff entries; contract SHA ok; C++ table ok'
              % (fam, len(starts), len(duff)))
    if '--json' in sys.argv:
        Path(sys.argv[sys.argv.index('--json') + 1]).write_text(json.dumps(report, indent=1, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
