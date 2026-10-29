"""Geometric invariants that protect laterality and physical proportions."""
import sys
from pathlib import Path
import unittest

import numpy as np
from scipy.spatial.transform import Rotation

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_atlas import checked_faces, normalize_skeleton


def skeleton():
    offsets = np.array([[x, y, z] for x in (-.02, .02) for y in (-.02, .02) for z in (-.02, .02)])
    centers = {'Head': [0, 1.6, 0], 'Pelvis_L': [.15, .85, 0], 'Pelvis_R': [-.15, .85, 0],
               'Cal_L': [.1, .02, 0], 'Cal_R': [-.1, .02, 0],
               'Sternum': [0, 1.2, .1], 'T8': [0, 1.2, -.1]}
    return {name: np.array(center) + offsets for name, center in centers.items()}


class GeometryTests(unittest.TestCase):
    def test_rigid_motion_and_source_units_do_not_change_normalized_anatomy(self):
        original = skeleton()
        rotation = Rotation.from_euler('xyz', [24, -37, 63], degrees=True).as_matrix()
        moved = {name: points @ rotation.T * 1000 + [150, -290, 700] for name, points in original.items()}
        expected, _ = normalize_skeleton(original, 1.7)
        actual, _ = normalize_skeleton(moved, 1.7)
        for name in original:
            np.testing.assert_allclose(actual[name], expected[name], atol=1e-12)
        self.assertGreater(actual['Pelvis_L'][:, 0].mean(), actual['Pelvis_R'][:, 0].mean())
        self.assertGreater(actual['Sternum'][:, 2].mean(), actual['T8'][:, 2].mean())
        self.assertAlmostEqual(actual['Head'][:, 1].max(), 1.7)
        self.assertAlmostEqual(min(actual[k][:, 1].min() for k in ('Cal_L', 'Cal_R')), 0)

    def test_uniform_scaling_preserves_relative_bone_dimensions(self):
        small, _ = normalize_skeleton(skeleton(), 1.5)
        large, _ = normalize_skeleton(skeleton(), 1.8)
        for name in small:
            np.testing.assert_allclose(large[name], small[name] * 1.2, atol=1e-12)

    def test_reflection_and_invalid_height_are_not_silently_accepted(self):
        reflected = {name: points * [-1, 1, 1] for name, points in skeleton().items()}
        with self.assertRaisesRegex(ValueError, 'handedness'):
            normalize_skeleton(reflected, 1.7)
        for height in (0, -1, float('nan'), float('inf')):
            with self.subTest(height=height), self.assertRaises(ValueError):
                normalize_skeleton(skeleton(), height)

    def test_matlab_indices_convert_and_invalid_connectivity_is_rejected(self):
        np.testing.assert_array_equal(checked_faces(np.array([[1., 2., 3.]]), 3, 'bone'), [[0, 1, 2]])
        for triangle in ([0, 1, 2], [1, 2, 4], [1, 1, 3], [1, 2.5, 3], [1, 2, float('nan')]):
            with self.subTest(triangle=triangle), self.assertRaises(ValueError):
                checked_faces(np.array([triangle]), 3, 'bone')


if __name__ == '__main__':
    unittest.main()
