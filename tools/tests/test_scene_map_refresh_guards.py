"""Synthetic evidence-reuse guards; no original ROM or report files required."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observe_scene_map_refresh import fixture, validate_extra_base
from verify_scene_map_refresh import validate_previous


class SceneMapRefreshGuardTests(unittest.TestCase):
    def setUp(self):
        self.case = dict(entry=0x18702, descriptor=0x60000, slot=0xffff,
                         profile=0, flags=0, label='synthetic-guard-only')
        self.source = dict(sha256='synthetic-original-identity')
        self.row = dict(case_index=0, fixture=self.case, returned=True,
                        input_ram_sha256=hashlib.sha256(fixture(0, self.case)).hexdigest(),
                        output_ram_sha256='synthetic-output-RAM',
                        ports_sha256='synthetic-port-trace', port_count=2,
                        incoming=dict(d0=0))
        self.base = dict(source=self.source, smoke=False, cases=1,
                         completed_cases=1, ports=2, results=[self.row], failure=None,
                         fixed_rom_immutable=True, physical_bank_payload_immutable=True,
                         scope='Synthetic metadata, no native execution claim')
        self.resources = {'synthetic.ms5d': 'synthetic-resource-sha'}
        self.previous = dict(binary_sha256='synthetic-binary',
                             resources_sha256=self.resources, cases=1, ports=2,
                             native_observation_sha256=self.digest(self.base),
                             results=[dict(case_index=0, entry=self.case['entry'],
                                           label=self.case['label'], writes=2,
                                           ram_sha256=self.row['output_ram_sha256'],
                                           ports_sha256=self.row['ports_sha256'])])
        self.native = copy.deepcopy(self.base)
        appended = copy.deepcopy(self.row)
        appended['case_index'] = 1
        self.native['results'].append(appended)
        self.native['cases'] = self.native['completed_cases'] = 2
        self.native['ports'] = 4

    @staticmethod
    def digest(value):
        return hashlib.sha256((json.dumps(value, indent=2)+'\n').encode()).hexdigest()

    def validate(self, previous=None, native=None):
        validate_previous(self.previous if previous is None else previous,
                          self.native if native is None else native,
                          'synthetic-binary', self.resources)

    def test_exact_previous_prefix_is_accepted(self):
        self.validate()
        validate_extra_base(self.base, self.source, [self.case])

    def test_binary_resources_and_row_count_changes_rejected(self):
        for field, value in (('binary_sha256', 'changed'), ('resources_sha256', {}),
                             ('cases', 0), ('cases', 3)):
            with self.subTest(field=field, value=value):
                changed = copy.deepcopy(self.previous)
                changed[field] = value
                with self.assertRaises(AssertionError):
                    self.validate(previous=changed)

    def test_changed_serialized_native_prefix_rejected(self):
        changed = copy.deepcopy(self.native)
        changed['results'][0]['incoming']['d0'] = 1
        with self.assertRaises(AssertionError):
            self.validate(native=changed)
        changed = copy.deepcopy(self.previous)
        changed['native_observation_sha256'] = 'changed'
        with self.assertRaises(AssertionError):
            self.validate(previous=changed)

    def test_previous_comparison_rows_must_match_native(self):
        for field, value in (('case_index', 1), ('entry', 0), ('label', 'changed'),
                             ('ram_sha256', 'changed'), ('ports_sha256', 'changed'),
                             ('writes', 3)):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.previous)
                changed['results'][0][field] = value
                with self.assertRaises(AssertionError):
                    self.validate(previous=changed)

    def test_native_completion_and_failure_checked(self):
        for field, value in (('smoke', True), ('failure', {'synthetic': True}),
                             ('completed_cases', 1), ('cases', 1)):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.native)
                changed[field] = value
                with self.assertRaises(AssertionError):
                    self.validate(native=changed)

    def test_repeated_extra_append_rejected(self):
        with self.assertRaises(AssertionError):
            validate_extra_base(self.native, self.source, [self.case])

    def test_extra_base_identity_and_completion_checked(self):
        for field, value in (('source', {}), ('smoke', True), ('failure', {'error': 1}),
                             ('completed_cases', 0), ('fixed_rom_immutable', False),
                             ('physical_bank_payload_immutable', False), ('ports', 3)):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.base)
                changed[field] = value
                with self.assertRaises(AssertionError):
                    validate_extra_base(changed, self.source, [self.case])

    def test_extra_base_fixture_and_input_RAM_reproduced(self):
        changed = copy.deepcopy(self.base)
        changed['results'][0]['fixture']['slot'] = 0
        with self.assertRaises(AssertionError):
            validate_extra_base(changed, self.source, [self.case])
        changed = copy.deepcopy(self.base)
        changed['results'][0]['input_ram_sha256'] = 'changed'
        with self.assertRaises(AssertionError):
            validate_extra_base(changed, self.source, [self.case])


if __name__ == '__main__':
    unittest.main()
