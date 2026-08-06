import json
import struct
import unittest

from glb_intake import validate_glb


def glb(document):
    payload = json.dumps(document).encode()
    payload += b" " * ((4 - len(payload) % 4) % 4)
    length = 20 + len(payload)
    return b"glTF" + struct.pack("<II", 2, length) + struct.pack("<II", len(payload), 0x4E4F534A) + payload


class GlbValidationTest(unittest.TestCase):
    def test_accepts_mesh_primitive(self):
        self.assertEqual(validate_glb(glb({"asset": {"version": "2.0"}, "meshes": [{"primitives": [{}]}]}))["primitives"], 1)

    def test_rejects_non_glb(self):
        with self.assertRaisesRegex(ValueError, "not a binary"):
            validate_glb(b"hello")

    def test_rejects_empty_scene(self):
        with self.assertRaisesRegex(ValueError, "no mesh"):
            validate_glb(glb({"asset": {"version": "2.0"}}))


if __name__ == "__main__":
    unittest.main()
