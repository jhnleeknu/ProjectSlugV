# Native input sampler and replay streams

Canonical decrypted program SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
All addresses below are fixed ROM CPU addresses, equal to canonical program offsets. RAM offsets refer to base100000.

`sample_input` reconstructs31d6..349a and its native352a replay helper. Raw active-low port samples are supplied by a hardware boundary:380000,300000,340000, followed in mode0 by300000 and340000 again. The two reads of each player port are independent. The API returns consumed read count3 or5, not CPU register/CCR results.

System input is inverted/masked to0f, stored4cb4, and its newly pressed bits stored4cb5. The first P1/P2 reads update six-byte blocks4cb6/4cbc. Each block preserves byte0; byte1 becomes previous byte2; byte2 is current held input; byte3 is `(old XOR current)&current`. A nonzero edge becomes byte4 and reloads byte5 from4cd2. Otherwise byte5 decrements modulo256, including when no buttons are held. When it reaches zero, byte4 becomes current held input and byte5 reloads4cd3; otherwise byte4 clears.

Mode4cd4==0 copiesfd94/fd9a into gameplay block byte0 at4ca8/4cae and updates these blocks from the second pair of port reads. Mode1 calls352a then updates gameplay from4cc2/4cc3. Other modes update gameplay with zero. Modes other than0 preserve gameplay byte0. Mode1 still uses generated input on the invocation that352a changes mode to2; only subsequent invocations use the zero-input branch.

## Replay encoding and mutation order

ROMword180 is0000 in the pinned image, so3358 selects352a rather than349c. The implementation fixes this native-image contract. The developer recorder branch is not implemented or claimed as naturally reached.

Replay base is RAMlong4cc4; cursor isword4cce; previous event index isword4ccc; elapsed duration isbyte4cd0; generated input isword4cc2.352a first checks unsigned cursor>=600, then setsmode2 without storing a new cursor. Otherwise it reads the byte at base+signed16(cursor). At the previous event index only the low nibble is a duration; elsewhere the full byte is used.

If elapsed differs from duration, store cursor and increment elapsed modulo256. On equality reset elapsed, advance cursor, and compare duration against0f for an event byte orff for a continuation byte. At this limit, a nonzero following byte defers the toggle, stores advanced cursor and sets elapsed1. A zero following byte is skipped. Then save advanced cursor as previous event index and toggle the input-word bit named by the high nibble at the OLD previous event index. Dynamic BCHG uses a data register: bit15 is valid and must not be reduced modulo8. Continue parsing until a duration must wait or cursor reaches600. On exhaustion the last cursor store is omitted even if input, elapsed and previous index have changed.

The following-byte peek can cross the600-byte buffer end into the next native region. Preserve adjacency; do not split buffers into host arrays with implicit zero padding. Signed16 previous-event indexing is bounds checked against the complete extracted window. Unsupported reads fail transactionally after rolling back earlier raw-input updates; native exhausted-cursor paths require no resource access.

## Native project resource

`tools/pack_input_streams.py` packsf01fe..f1a0e into MS5D v1 kind1. Payload6160 bytes includes all four600-byte buffers and both BE32 pointer tables. Tablef0dfe points tof01fe/f07fe; tablef1a06 points tof0e06/f1406. Record targets and unused bytes are retained without asserting that every byte is a live replay event. The packer pins the full program hash, selector, tables and payload hash. The existing C++ MS5D loader validates header, mapping, length and CRC. Runtime uses native bytes directly, with no PNG/audio conversion.

Resource stable ID: `input-streams:000f01fe`.
Resource SHA256: `5fd8e6f40f544d2c0c75d3559a885968d570277ca992076023e000ab0477ec0c`.
Payload SHA256: `e1dc1a531699c43bf6ad556832ec749ba859268e203f8e316436bfe48e016615`.

Build `make build/sample_input`; regenerate via `python3 tools/pack_input_streams.py`.
CLI: `build/sample_input INPUT_RAM INPUT_MS5D OUTPUT_RAM SYSTEM P1_RAW P2_RAW P1_GAME P2_GAME`. Numeric samples are raw bytes0..255, decimal or0xhex.

The diagnostic `--playback` CLI carries input state through repeated calls and emits a47-byte per-frame trace (RAM4ca8..4cd5 plus read count) and final64KiB RAM. This trace is verification output, not a game resource format.

Initializer3162, recorder349c, subsequentb68 bookkeeping, CPU register propagation, interrupts and bus timing remain outside this API. Direct input sampling is not proof of whole-game boot or synchronized gameplay.

Reproduce original-ROM comparison with `.venv/bin/python tools/verify_input_sampler.py`. The supported replay contract requires every actually accessed byte to lie in the retained MS5D window. A malformed previous index offfff is signed−1: it can read the preceding byte for the second buffer, but falls outside the retained window at the first buffer base. The latter is an explicit support error, not a substitute value or a native CPU fault.

## Next integration boundaries confirmed from instructions

3162 always clears both six-byte gameplay blocks first. Unsigned D0.word>=2 then sets mode0 and returns without clearing replay pointers/cursors. Selectors0/1 setmode1, load playback pointer fromf0dfe and record pointer fromf1a06 using selector*4, and clear4ccc/4cce/4cc2 words and4cd0 byte. Native ROM selector0 then returns without filling the record target. The next reconstruction must retain this partial-reset distinction.

The subsequentb68 copiesfdaf to0012, clearsf007, and visits bits3 through0 of f006. Clearing a previously set bit writes1 to the matching byte atfdb6. Each slot then initializes D6.word=4 and adds its byte to D6.B; the effective lookup index is `(4 + slot_byte) & 255`. A nonzero byte atb58+index sets the slot bit in the finalf007. Only f006's low nibble is consumed. Although the bytes beforeb68 look like a small table, the complete machine-level lookup can reachb58..c58 and overlap instructions. A future resource must either preserve this complete256-byte lookup window or explicitly validate a proven state domain; it must not silently assume all slot bytes are below12. This is static instruction evidence, not an assertion that every slot value naturally occurs.

## Verification result

Unmodified M68000 original31d6 matched4,301 full64KiB RAM cases, including40 carried mode0 calls. Both streams were then carried untilmode2:371,165 and318,604 calls,689,769 total. Every post-call46-byte input-state window and read count matched; finalwholeRAM matched and original writes outside the input-state window were absent. The final stored cursor differed between streams (0600 vs05ff), confirming terminal mutation order. Nine unsupported-input checks preserved output. Report SHA256: `470067a8e214c46e03e4206e0f4ad57dea156690786917e6e5e2633782d1774f`.
