"""Input-path configuration of the PVC bank observer; no ROM needed."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from tools import observe_animation_machine_pvc_banks as O

GLOBALS = ('INPUT_TREE', 'INPUT_ROUTING', 'INPUT_BUS', 'INPUT_U06_CPP', 'REF_PVC', 'REF_NEOGEO')
TREE_FILES = ('animation_machine.cpp', 'program_bus.cpp', 'animation_machine_objects_u06.cpp')


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

    def test_defaults(self):
        self.assertEqual(self.saved['INPUT_TREE'], Path('/Users/start/Workspce/metalslug-input'))
        self.assertEqual(self.saved['INPUT_ROUTING'], self.saved['INPUT_TREE'] / 'engine/src/animation_machine.cpp')
        self.assertEqual(self.saved['INPUT_BUS'], self.saved['INPUT_TREE'] / 'engine/src/program_bus.cpp')
        self.assertEqual(self.saved['INPUT_U06_CPP'], self.saved['INPUT_TREE'] / 'engine/src/animation_machine_objects_u06.cpp')
        self.assertEqual(self.saved['REF_PVC'], O.ROOT / 'artifacts/reference/prot_pvc.cpp')
        self.assertEqual(self.saved['REF_NEOGEO'], O.ROOT / 'artifacts/reference/neogeo.cpp')
        a = O.build_parser().parse_args([])
        self.assertEqual(a.input_tree, '/Users/start/Workspce/metalslug-input')
        self.assertEqual(a.reference_dir, str(O.ROOT / 'artifacts/reference'))

    def test_configure_sets_globals(self):
        tree, ref = make_dirs(self.tmp.name)
        O.configure_inputs(str(tree), str(ref))
        self.assertEqual(O.INPUT_TREE, tree)
        self.assertEqual(O.INPUT_ROUTING, tree / 'engine/src/animation_machine.cpp')
        self.assertEqual(O.INPUT_BUS, tree / 'engine/src/program_bus.cpp')
        self.assertEqual(O.INPUT_U06_CPP, tree / 'engine/src/animation_machine_objects_u06.cpp')
        self.assertEqual(O.REF_PVC, ref / 'prot_pvc.cpp')
        self.assertEqual(O.REF_NEOGEO, ref / 'neogeo.cpp')

    def test_missing_lists_all(self):
        tree, ref = make_dirs(self.tmp.name)
        (tree / 'engine/src/program_bus.cpp').unlink()
        (ref / 'neogeo.cpp').unlink()
        with self.assertRaises(SystemExit) as cm:
            O.configure_inputs(tree, ref)
        msg = str(cm.exception)
        self.assertIn(str(tree / 'engine/src/program_bus.cpp'), msg)
        self.assertIn(str(ref / 'neogeo.cpp'), msg)
        self.assertNotIn('prot_pvc.cpp', msg)
        self.assertEqual(O.INPUT_TREE, self.saved['INPUT_TREE'])

    def test_input_pins_keys(self):
        tree, ref = make_dirs(self.tmp.name)
        O.configure_inputs(tree, ref)
        h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        self.assertEqual(O.input_pins(), {
            'artifacts/reference/prot_pvc.cpp': h(ref / 'prot_pvc.cpp'),
            'artifacts/reference/neogeo.cpp': h(ref / 'neogeo.cpp'),
            'metalslug-input/engine/src/animation_machine.cpp': h(tree / 'engine/src/animation_machine.cpp'),
            'metalslug-input/engine/src/program_bus.cpp': h(tree / 'engine/src/program_bus.cpp'),
            'metalslug-input/engine/src/animation_machine_objects_u06.cpp': h(tree / 'engine/src/animation_machine_objects_u06.cpp'),
        })

    def test_main_bad_tree_fails_before_output(self):
        out = Path(self.tmp.name) / 'out'
        with self.assertRaises(SystemExit):
            O.main(['--input-tree', str(Path(self.tmp.name) / 'nope'), '--out', str(out)])
        self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
