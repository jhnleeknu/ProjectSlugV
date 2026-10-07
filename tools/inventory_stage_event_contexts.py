"""Raw stage event pointers and main-confirmed e905c gate-skip candidates.

No complete event grammar, resource extent, execution or reachability claim.
"""
import hashlib
import json
from pathlib import Path
import struct

import capstone

from disassemble_program import load_verified_program, disassemble_range
from inventory_scene_general_initialization import SOURCE_SHA256, context_inventory

WINDOWS = ((0xe905c, 0xe90ca), (0x47aca, 0x47af0))
MAX_GATES = 4096


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fixed_span(program, address, size, even=False):
    return 0 <= address <= min(len(program), 0x100000)-size and (not even or address % 2 == 0)


def signed16(value):
    return value-0x10000 if value & 0x8000 else value


def skipped_range(program, start, end):
    """Preserve only the positive interval passed over by the explicit jump."""
    if end <= start:
        return dict(start_cpu_address=start, end_cpu_address_exclusive=end,
                    classification='No positive skipped interval; no opaque span invented')
    if not fixed_span(program, start, end-start):
        return dict(start_cpu_address=start, end_cpu_address_exclusive=end,
                    classification='Jump interval outside fixed ROM; no bytes read')
    raw = program[start:end]
    return dict(start_cpu_address=start, start_rom_offset=start,
                end_cpu_address_exclusive=end, end_rom_offset_exclusive=end,
                byte_count=end-start, raw_sha256=sha(raw),
                classification='Opaque jump-skipped bytes; not decoded as event records')


def read_header(program, stream):
    if not fixed_span(program, stream, 2, True):
        return None
    header = struct.unpack_from('>H', program, stream)[0]
    after = stream+2
    destination = after+signed16(header)
    return dict(cpu_address=stream, rom_offset=stream, raw_hex=program[stream:after].hex(),
                word=header, signed_jump=signed16(header), after_header_cpu_address=after,
                after_header_rom_offset=after,
                jump_destination_cpu_address=destination,
                jump_destination_rom_offset=destination if fixed_span(program, destination, 1) else None,
                opaque_skipped_range=skipped_range(program, after, destination))


def walk_gates(program, stream, target=None):
    """None enumerates the gate chain; a WORD target applies the caller's stop test."""
    result = dict(stream_cpu_address=stream, stream_rom_offset=stream if stream else None,
                  target_word=target, header=None, gates=[], selected_cursor_cpu_address=None,
                  selected_cursor_rom_offset=None,
                  terminal=None, unsupported=None)
    if stream == 0:
        result.update(status='null_stream', selected_cursor_cpu_address=0)
        return result
    header = read_header(program, stream)
    if header is None:
        result.update(status='unsupported_header_span', unsupported=dict(cpu_address=stream))
        return result
    result['header'] = header
    if target == 0:
        result.update(status='selected_after_header_target_zero',
                      selected_cursor_cpu_address=header['after_header_cpu_address'],
                      selected_cursor_rom_offset=header['after_header_rom_offset'])
        return result
    cursor = header['jump_destination_cpu_address']
    visited = set()
    for _ in range(MAX_GATES):
        if cursor in visited:
            result.update(status='unsupported_cycle', unsupported=dict(cpu_address=cursor))
            return result
        visited.add(cursor)
        if not fixed_span(program, cursor, 1):
            result.update(status='unsupported_marker_span', unsupported=dict(cpu_address=cursor))
            return result
        marker = program[cursor]
        if marker == 0xff:
            result.update(status='terminal_ff' if target is None else 'selected_terminal_ff',
                selected_cursor_cpu_address=cursor if target is not None else None,
                selected_cursor_rom_offset=cursor if target is not None else None,
                terminal=dict(cpu_address=cursor, rom_offset=cursor, raw_hex='ff',
                    classification='Gate-skip ff stop byte only; not entire event resource end'))
            return result
        if marker != 0:
            result.update(status='unsupported_trap_marker', unsupported=dict(cpu_address=cursor,
                rom_offset=cursor, raw_hex='%02x' % marker, marker_byte=marker,
                reason='Other byte invokes TRAP15 in confirmed skip algorithm; no grammar invented'))
            return result
        if not fixed_span(program, cursor, 6, True):
            result.update(status='unsupported_gate_span', unsupported=dict(cpu_address=cursor))
            return result
        gate = struct.unpack_from('>H', program, cursor+2)[0]
        jump = struct.unpack_from('>H', program, cursor+4)[0]
        following = cursor+signed16(jump)
        row = dict(cpu_address=cursor, rom_offset=cursor, marker_byte=marker,
                   raw_hex=program[cursor:cursor+6].hex(), gate_word=gate,
                   next_offset_word=jump, next_offset_signed=signed16(jump),
                   next_cpu_address=following,
                   next_rom_offset=following if fixed_span(program, following, 1) else None,
                   opaque_skipped_range=skipped_range(program, cursor+6, following))
        result['gates'].append(row)
        if target is not None and target <= gate:
            result.update(status='selected_gate', selected_cursor_cpu_address=cursor,
                          selected_cursor_rom_offset=cursor)
            return result
        cursor = following
    result.update(status='unsupported_gate_budget', unsupported=dict(cpu_address=cursor, max_gates=MAX_GATES))
    return result


def instruction_windows(program):
    windows = []
    for start, end in WINDOWS:
        rows = disassemble_range(program, start, end-start, start)
        cursor = start
        for row in rows:
            require(row['cpu_address'] == cursor and row['rom_offset'] == cursor
                    and row['size'] > 0 and cursor+row['size'] <= end,
                    'Instruction window gap, overlap or bounds mismatch')
            require(bytes.fromhex(row['raw']) == program[cursor:cursor+row['size']],
                    'Instruction raw bytes/source mismatch')
            cursor += row['size']
        require(cursor == end, 'Incomplete instruction window')
        undecoded = [r for r in rows if r['classification'] != 'candidate_instruction']
        windows.append(dict(start_cpu_address=start, start_rom_offset=start,
            end_cpu_address_exclusive=end, end_rom_offset_exclusive=end,
            raw_sha256=sha(program[start:end]), instructions=rows, undecoded_rows=undecoded))
    return windows


def inventory(root):
    program, source = load_verified_program(root)
    require(source['sha256'] == SOURCE_SHA256 and sha(program) == SOURCE_SHA256,
            'Unsupported canonical source')
    contexts = context_inventory(root, program, source)
    records = []
    streams = {}
    for record in contexts['records']:
        cpu = record['record_cpu_address']
        pointer = struct.unpack_from('>I', program, cpu+0x0a)[0]
        stream = 0
        dereference = None
        if pointer:
            require(fixed_span(program, pointer, 4, True), 'Unsupported catalog event indirection span')
            raw = program[pointer:pointer+4]
            stream = struct.unpack('>I', raw)[0]
            dereference = dict(cpu_address=pointer, rom_offset=pointer, raw_hex=raw.hex(),
                               raw_sha256=sha(raw), stream_pointer_long=stream)
        target = record['target_word']
        selected = walk_gates(program, stream, target)
        item = dict(group=record['group'], area=record['area'], record_cpu_address=cpu,
            record_rom_offset=cpu, record_length=record['record_length'],
            record_raw_sha256=record['record_raw_sha256'], pointer_field_offset=0x0a,
            pointer_field_cpu_address=cpu+0x0a, pointer_field_rom_offset=cpu+0x0a,
            pointer_raw_hex=program[cpu+0x0a:cpu+0x0e].hex(), indirect_pointer_long=pointer,
            dereference=dereference, stream_pointer_long=stream,
            null_status='null_indirect_pointer' if not pointer else 'null_dereferenced_stream' if not stream else 'nonzero_stream',
            target_field_offset=0x0e, target_field_cpu_address=cpu+0x0e,
            target_field_rom_offset=cpu+0x0e, target_raw_hex=record['target_raw_hex'],
            target_word=target, target_selection=selected)
        records.append(item)
        if stream:
            if stream not in streams:
                streams[stream] = walk_gates(program, stream)
                streams[stream]['record_references'] = []
            streams[stream]['record_references'].append(dict(group=record['group'], area=record['area'],
                record_cpu_address=cpu, target_word=target))
    gates = sorted({g['cpu_address'] for s in streams.values() for g in s['gates']})
    windows = instruction_windows(program)
    counts = dict(records=len(records), null_indirect_records=sum(not r['indirect_pointer_long'] for r in records),
        null_dereferenced_stream_records=sum(r['indirect_pointer_long'] != 0 and r['stream_pointer_long'] == 0 for r in records),
        nonzero_stream_records=sum(r['stream_pointer_long'] != 0 for r in records),
        distinct_nonzero_indirect_pointers=len({r['indirect_pointer_long'] for r in records}-{0}),
        distinct_nonzero_streams=len(streams), unique_gate_addresses=len(gates),
        gate_chain_rows=sum(len(s['gates']) for s in streams.values()),
        terminal_ff_streams=sum(s['status'] == 'terminal_ff' for s in streams.values()),
        unsupported_streams=sum(s['status'].startswith('unsupported_') for s in streams.values()),
        unsupported_target_selections=sum(r['target_selection']['status'].startswith('unsupported_') for r in records),
        windows=len(windows), instruction_rows=sum(len(w['instructions']) for w in windows),
        undecoded_rows=sum(len(w['undecoded_rows']) for w in windows))
    require(counts['records'] == 59, 'Unexpected catalog record closure')
    require(sha(program) == SOURCE_SHA256, 'Source changed during inventory')
    return dict(schema_version=1, source=source, program_code_modified=False,
        provenance='Source-verified existing stage catalog context_inventory; immutable pinned canonical ROM. Instruction candidates are padded bounded decoder output, not native execution.',
        decoder='Capstone '+capstone.__version__,
        stage_catalog_manifest_sha256=contexts['stage_catalog_manifest_sha256'],
        mapping='Fixed first1MiB CPU addresses equal ROM file offsets; RAM/MMIO distinct.',
        counts=counts, records=records, streams=[streams[a] for a in sorted(streams)],
        gate_cpu_addresses=gates, windows=windows, limits=dict(max_gates_per_walk=MAX_GATES),
        scope='Main-confirmed e905c gate-skip algorithm only. Positive target follows signed header jump then unsigned target<=gate stop tests and signed next offsets; target0 deliberately returns after the header without following its jump. Full gate-chain inventory ignores target and follows only00/ff markers. Other marker bytes preserve unsupported TRAP evidence. Header/jump-skipped intervals stay opaque. ff is a skip stop, not entire stream end. No complete event grammar, resource extent, callback semantics, packing, native execution, natural reachability or C++ equivalence claim.')


def main():
    root = Path(__file__).resolve().parents[1]
    report = inventory(root)
    path = root/'artifacts/stage_event_contexts.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(counts=report['counts'], stage_catalog_manifest_sha256=report['stage_catalog_manifest_sha256'],
                          report_sha256=sha(path.read_bytes()))))


if __name__ == '__main__':
    main()
