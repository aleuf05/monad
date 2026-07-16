import importlib.util,tempfile,unittest
from pathlib import Path
P=Path(__file__).with_name('generate.py'); S=importlib.util.spec_from_file_location('g',P); g=importlib.util.module_from_spec(S); S.loader.exec_module(g)
class T(unittest.TestCase):
 def test_bounded_sources(self):
  class A: radius=10;size=20;minor=3;name='test-shape'
  for x in ('sphere','box','torus'): self.assertIn('set-bounds!',g.scheme(x,A))
  with self.assertRaises(ValueError): g.scheme('raw-scheme',A)
 def test_rejects_unsafe_names_and_dimensions(self):
  class A: radius=10;size=20;minor=3;name='../escape'
  with self.assertRaisesRegex(ValueError,'name'): g.scheme('sphere',A)
  A.name='valid'; A.radius=0
  with self.assertRaisesRegex(ValueError,'radius'): g.scheme('sphere',A)
  A.radius=3; A.minor=3
  with self.assertRaisesRegex(ValueError,'smaller'): g.scheme('torus',A)
if __name__=='__main__': unittest.main()
