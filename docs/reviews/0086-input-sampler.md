# Native31d6 input sampler review

Base commit: `2ea0565`.

Root analyzed the complete31d6..35a0 instructions, derived replay grammar and implemented the C++ sampler. gpt-6.1-sol / medium agents handled native resource packaging, CLI/diagnostic trace, unit checks and original-ROM comparison in separate files. Root reviewed each delivered file.

Key review points: the two player reads in mode0 are independent; repeat counters wrap even with no held input; mode1 uses generated input on its terminal invocation; replay limit markers distinguish continuation from an event; bit15 toggles the high byte of the input word; previous-event indexing is signed16; exhaustion omits the final cursor store. Resource bounds errors roll back raw input writes and all output parameters. Exhausted cursors do not require a resource read.

Native resource extraction pins program, selector, full payload and pointer tables. All four buffers and adjacent tables are preserved in existing MS5D, without changing the resource format. Synthetic fixtures are used in tracked unit tests; no ROM bytes or generated assets are committed.

`make all test` passed67 Python tests and all C++ tests. Build/test log: `artifacts/input_sampler_build_test.log`. The packer regenerated6192 bytes with SHA256 `5fd8e6f40f544d2c0c75d3559a885968d570277ca992076023e000ab0477ec0c`.

The CLI trace is a diagnostic artifact. This API does not reconstruct CPU register outputs, live MMIO timing, interrupts,3162 initialization,349c recording or subsequentb68 processing. Native selector180==0 is the explicit image contract. Whole-game completion is not claimed.

Original-ROM verification passed4,301 whole-RAM cases (4,261 isolated +40 carried mode0). Native streams matched689,769 post-call47-byte trace records and final64KiB RAM: f01fe371,165 calls ends with cursor0600; f07fe318,604 calls ends with cursor05ff. Both setmode2. Hooks assert byte-width MMIO ordering, absence of writes outside the input state window and unchanged fixed ROM. These are decoder calls, not measured hardware frames or intended demo lengths.

Nine negative cases preserve output, including one original-executed signed−1 read atf01fd outside the retained resource. The same signed index on the second buffer remains supported. Initial Cartesian verification revealed this support boundary; classification now uses actual ROM read addresses rather than assuming every malformed state is supported. No C++ semantic change was needed.

Report: `artifacts/input_sampler/verification.json`, SHA256 `470067a8e214c46e03e4206e0f4ad57dea156690786917e6e5e2633782d1774f`. Root reviewed the actual verifier, report, C++ and packer, and confirmed build/tests and diff checks.
