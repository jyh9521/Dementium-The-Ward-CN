# 第一阶段实际验证记录

以下是本机离线执行的字面输出；不代表游戏内测试。所有退出码为实测。

```text
Phase 1 verification - 2026-10-23
Game was not launched; installation input was read-only.
Changed field: loc/en/UISSFrontend.tbl:0000
New Game -> New Game [offline probe] (ASCII archive probe, not Chinese proof)
MODIFIED_FILE: C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\phase1\MODIFIED_FILE.zar
DIFF_FILE: C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\phase1\DIFF_FILE.json
VERIFICATION: C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\phase1\VERIFICATION.txt
ROLLBACK: C:\Users\noway\Downloads\Dementium-The-Ward-CN\tools\ROLLBACK.sh

SCAN
COMMAND: C:\Users\noway\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 tools/investigate.py scan --game "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward"
INPUT: C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward
OUTPUT (literal):
SCAN appid=3909960 build=21501403 files=9 ZAR=668 TAR=2555 EN=278/131 PNG=0
EXIT: 0

TESTS
COMMAND: C:\Users\noway\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 -m unittest discover -s tests -v
INPUT: synthetic fixtures
OUTPUT (literal):
test_byte_encoding_is_explicit (test_content.ContentTests.test_byte_encoding_is_explicit) ... ok
test_document_linebreak_and_controls (test_content.ContentTests.test_document_linebreak_and_controls) ... ok
test_duplicate_missing_stale (test_content.ContentTests.test_duplicate_missing_stale) ... ok
test_external_and_mismatch_guard (test_content.ContentTests.test_external_and_mismatch_guard) ... ok
test_extract_all_types_and_blanks (test_content.ContentTests.test_extract_all_types_and_blanks) ... ok
test_growth_order_payloads_and_headers (test_content.ContentTests.test_growth_order_payloads_and_headers) ... ok
test_invalid_checksum (test_content.ContentTests.test_invalid_checksum) ... ok
test_nested_dual_index_growth (test_content.ContentTests.test_nested_dual_index_growth) ... ok
test_noop (test_content.ContentTests.test_noop) ... ok
test_offsets (test_content.ContentTests.test_offsets) ... ok
test_reimport_preserves_newlines_and_tokens (test_content.ContentTests.test_reimport_preserves_newlines_and_tokens) ... ok
test_table_line_injection (test_content.ContentTests.test_table_line_injection) ... ok
test_truncation_and_bad_trailer (test_content.ContentTests.test_truncation_and_bad_trailer) ... ok
test_unknown_chinese_encoding_rejected (test_content.ContentTests.test_unknown_chinese_encoding_rejected) ... ok
test_unknown_member (test_content.ContentTests.test_unknown_member) ... ok
test_unsafe_names (test_content.ContentTests.test_unsafe_names) ... ok
test_bad_index_rejected (test_vfs_index.VfsIndexTests.test_bad_index_rejected) ... ok
test_flagged_entry_resize_rejected (test_vfs_index.VfsIndexTests.test_flagged_entry_resize_rejected) ... ok
test_manually_replaced_index_rejected (test_vfs_index.VfsIndexTests.test_manually_replaced_index_rejected) ... ok
test_noop_keeps_index_byte_identical (test_vfs_index.VfsIndexTests.test_noop_keeps_index_byte_identical) ... ok
test_only_size_fields_change (test_vfs_index.VfsIndexTests.test_only_size_fields_change) ... ok
test_resize_updates_secondary_size_manifest (test_vfs_index.VfsIndexTests.test_resize_updates_secondary_size_manifest) ... ok
test_table_growth_updates_secondary_size_manifest (test_vfs_index.VfsIndexTests.test_table_growth_updates_secondary_size_manifest) ... ok
test_unterminated_and_duplicate_index_names (test_vfs_index.VfsIndexTests.test_unterminated_and_duplicate_index_names) ... ok
test_bad_magic (test_zar.ArchiveTests.test_bad_magic) ... ok
test_duplicate_names_and_traversal (test_zar.ArchiveTests.test_duplicate_names_and_traversal) ... ok
test_header_variants (test_zar.ArchiveTests.test_header_variants) ... ok
test_member_bounds_alignment_and_metadata (test_zar.ArchiveTests.test_member_bounds_alignment_and_metadata) ... ok
test_noop_is_byte_identical (test_zar.ArchiveTests.test_noop_is_byte_identical) ... ok
test_overlap (test_zar.ArchiveTests.test_overlap) ... ok
test_resize_preserves_other_members (test_zar.ArchiveTests.test_resize_preserves_other_members) ... ok
test_truncated (test_zar.ArchiveTests.test_truncated) ... ok
test_unknown_replacement (test_zar.ArchiveTests.test_unknown_replacement) ... ok
test_apply_and_rollback (test_zar.DeltaTests.test_apply_and_rollback) ... ok
test_noop (test_zar.DeltaTests.test_noop) ... ok
test_seeded_payload_sizes (test_zar.DeltaTests.test_seeded_payload_sizes) ... ok
test_tampered_append_runs_and_hash (test_zar.DeltaTests.test_tampered_append_runs_and_hash) ... ok
test_wrong_build_and_double_apply (test_zar.DeltaTests.test_wrong_build_and_double_apply) ... ok

----------------------------------------------------------------------
Ran 38 tests in 0.025s

OK
EXIT: 0

BASELINE
COMMAND: C:\Users\noway\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 tools/investigate.py baseline --game "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward"
INPUT: C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward
OUTPUT (literal):
BASELINE PASS ZAR=668 TAR=2555 records=278 noop=byte-identical dual-index=consistent
EXIT: 0

MODIFIED
COMMAND: C:\Users\noway\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 tools/investigate.py modified --game "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward"
INPUT: C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward
OUTPUT (literal):
MODIFIED PASS field=loc/en/UISSFrontend.tbl:0000 changed_outer=1 changed_inner=1 tokens=preserved delta=roundtrip growth-dual-index=consistent
EXIT: 0

ROLLBACK
COMMAND: "C:\Program Files\Git\bin\bash.exe" tools/ROLLBACK.sh
INPUT: C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\phase1\MODIFIED_FILE.zar
OUTPUT (literal):
ROLLBACK PASS isolated-copy=original-sha256 field=New Game modified-file=retained
EXIT: 0

INPUT
COMMAND: C:\Users\noway\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 tools/investigate.py check-input --game "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward"
INPUT: C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward
OUTPUT (literal):
INPUT PASS all-files=original-sha256 game-not-launched=true
EXIT: 0

Original SHA-256: 9a9ceffb4bbf5fd9a22d5b9d0b87b963ab3abf1bf4afa7e49c5bdf44875fd42c
Modified SHA-256: 0fcf7e5017a5716087cd26bda6b57b63e589132373bbbdda2b51454c421eb347
Rollback SHA-256: 9a9ceffb4bbf5fd9a22d5b9d0b87b963ab3abf1bf4afa7e49c5bdf44875fd42c
Restored behavior/status: field=New Game; original archive byte-identical; modified output retained.
Runtime/Chinese display: NOT_TESTED.
```
