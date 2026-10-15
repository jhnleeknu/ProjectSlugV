"""Input-path wrapper of the PVC bank observer; no ROM needed."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import run_animation_machine_pvc_banks as R

O = R.O  # the wrapper imports the observer by bare name; share that module object

GLOBALS = ('INPUT_TREE', 'INPUT_ROUTING', 'INPUT_BUS', 'REF_PVC', 'REF_NEOGEO', 'tool_pins')
TREE_FILES = ('animation_machine.cpp', 'program_bus.cpp', 'animation_machine_objects_u06.cpp')
OBSERVER_SHA = '86ebf962e3b83eef6882c1f96845c117edfa735c3137960b1cbda6623768d3a0'


def make_dirs(base):
    tree = Path(base) / 'tree'
    ref = Path(base) / 'ref'
    (tree / 'engine/src').mkdir(parents=True)
    ref.mkdir()
    for n in TREE_FILES:
        (tree / 'engine/src' / n).write_bytes(b'tree ' + n.encode())
    for n in ('prot_pvc.cpp', 'neogeo.cpp'):
        (ref / n).write_bytes(b'ref ' + n.encode())
    return tree, ref


class PvcBanksPathTests(unittest.TestCase):
    def setUp(self):
        self.saved = {k: getattr(O, k) for k in GLOBALS}
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(O, k, v)

    def test_observer_unchanged(self):
        self.assertEqual(hashlib.sha256(Path(O.__file__).read_bytes()).hexdigest(), OBSERVER_SHA)

    def test_defaults(self):
        self.assertEqual(R.DEFAULT_INPUT_TREE, Path('/Users/start/Workspce/metalslug-input'))
        self.assertEqual(R.DEFAULT_REFERENCE_DIR, O.ROOT / 'artifacts/reference')
        a = R.build_parser().parse_args([])
        self.assertEqual(a.input_tree, '/Users/start/Workspce/metalslug-input')
        self.assertEqual(a.reference_dir, str(O.ROOT / 'artifacts/reference'))
        self.assertEqual(a.out, str(O.OUT))
        a, rest = R.build_parser().parse_known_args(['--workers', '2'])
        self.assertEqual(rest, ['--workers', '2'])

    def test_configure_sets_globals(self):
        tree, ref = make_dirs(self.tmp.name)
        R.configure_inputs(str(tree), str(ref))
        self.assertEqual(O.INPUT_TREE, tree)
        self.assertEqual(O.INPUT_ROUTING, tree / 'engine/src/animation_machine.cpp')
        self.assertEqual(O.INPUT_BUS, tree / 'engine/src/program_bus.cpp')
        self.assertEqual(O.REF_PVC, ref / 'prot_pvc.cpp')
        self.assertEqual(O.REF_NEOGEO, ref / 'neogeo.cpp')
        self.assertIs(O.tool_pins, R.tool_pins)

    def test_missing_lists_all(self):
        tree, ref = make_dirs(self.tmp.name)
        (tree / 'engine/src/program_bus.cpp').unlink()
        (ref / 'neogeo.cpp').unlink()
        with self.assertRaises(SystemExit) as cm:
            R.configure_inputs(tree, ref)
        msg = str(cm.exception)
        self.assertIn(str(tree / 'engine/src/program_bus.cpp'), msg)
        self.assertIn(str(ref / 'neogeo.cpp'), msg)
        self.assertNotIn('prot_pvc.cpp', msg)
        for k, v in self.saved.items():
            self.assertIs(getattr(O, k), v)

    def test_input_pins_keys(self):
        tree, ref = make_dirs(self.tmp.name)
        R.configure_inputs(tree, ref)
        h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        self.assertEqual(list(R.input_pins().items()), [
            ('artifacts/reference/prot_pvc.cpp', h(ref / 'prot_pvc.cpp')),
            ('artifacts/reference/neogeo.cpp', h(ref / 'neogeo.cpp')),
            ('metalslug-input/engine/src/animation_machine.cpp', h(tree / 'engine/src/animation_machine.cpp')),
            ('metalslug-input/engine/src/program_bus.cpp', h(tree / 'engine/src/program_bus.cpp')),
            ('metalslug-input/engine/src/animation_machine_objects_u06.cpp', h(tree / 'engine/src/animation_machine_objects_u06.cpp')),
        ])

    def test_tool_pins_matches_original(self):
        with mock.patch.object(Path, 'read_bytes', return_value=b''):
            orig = self.saved['tool_pins']()
            new = R.tool_pins()
        self.assertEqual(list(new.items()), list(orig.items()))

    def test_main_bad_tree_fails_before_output(self):
        out = Path(self.tmp.name) / 'out'
        with self.assertRaises(SystemExit):
            R.main(['--input-tree', str(Path(self.tmp.name) / 'nope'), '--out', str(out)])
        self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
