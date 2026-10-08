"""Observe real animation MOVEM.W restore instructions without patching ROM.

This isolated instruction probe is not a full animation execution proof.
"""
import hashlib
import itertools
import json
from pathlib import Path

from disassemble_program import load_verified_program, disassemble_range
from musashi_oracle import MusashiOracle
from observe_scene_motion_pair import oracle_provenance


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    cpu = MusashiOracle()
    cpu.load(0, program[:0x100000])
    stack = 0x1feffc
    keys = ['d'+str(i) for i in range(8)]+['a'+str(i) for i in range(7)]
    rows = []
    for entry in (0x4a222, 0x4a376, 0x4a460):
        instruction = disassemble_range(program, entry, 4, entry)[0]
        assert instruction['mnemonic'] == 'movem.w'
        for d0, d7 in itertools.product((0, 1, 0x7fff, 0x8000, 0xffff), repeat=2):
            cpu.reset()
            cpu.set_reg('sr', 0x2000)
            cpu.set_reg('a7', stack)
            before = {key: (0x89abcdef+i*0x1020304)&0xffffffff for i,key in enumerate(keys)}
            for key, value in before.items():
                cpu.set_reg(key, value)
            payload = d0.to_bytes(2, 'big')+d7.to_bytes(2, 'big')
            cpu.load(stack-16, b'\x5a'*16+payload+b'\xa5'*16)
            cpu.set_reg('pc', entry)
            result = cpu.run(1, entry+4)
            assert result['status'] == 'sentinel' and result['instructions'] == 1
            after = {key: cpu.get_reg(key) for key in keys}
            expected = before.copy()
            expected.update(d0=d0 if d0<0x8000 else d0|0xffff0000,
                            d7=d7 if d7<0x8000 else d7|0xffff0000)
            assert after == expected and cpu.get_reg('a7') == stack+4
            assert result['cpu_writes'] == 0
            assert cpu.read(stack-16, 36) == b'\x5a'*16+payload+b'\xa5'*16
            assert cpu.read(0, 0x100000) == program[:0x100000]
            rows.append(dict(entry=entry, instruction=instruction, stack_words=[d0,d7],
                             incoming=before, result=after, final_a7=stack+4))
    folder = root/'artifacts/animation_word_restore'
    folder.mkdir(parents=True, exist_ok=True)
    inputs = {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in
              ('tools/observe_animation_word_restore.py', 'tools/disassemble_program.py',
               'tools/musashi_oracle.py', 'tools/observe_scene_motion_pair.py')}
    report = dict(source=source, oracle=oracle_provenance(root), inputs=inputs,
                  cases=len(rows), results=rows, original_program_modified=False,
                  scope='Only original MOVEM.W restore at three animation sites; '
                  'sign extends saved D0/D7 WORDs into whole 32-bit registers. '
                  'Synthetic incoming stack. Not whole49fc6/callback/pending/PVC proof.')
    path = folder/'observation.json'
    path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows), sha256=hashlib.sha256(path.read_bytes()).hexdigest())))


if __name__ == '__main__':
    main()
