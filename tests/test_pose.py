"""Arm pose, reversible rest coordinates and rigid hierarchy behavior on real means."""
import sys
from pathlib import Path
import unittest

import numpy as np
from scipy.spatial.transform import Rotation
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from pose_atlas import articulated_scene, matrix

ROOT = Path(__file__).resolve().parents[1]


def world_vertices(scene, name):
    return trimesh.transform_points(scene.geometry[name].vertices, scene.graph[name][0])


class PoseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.models = {}
        for sex in ('female', 'male'):
            with np.load(ROOT / 'data/derived' / f'{sex}.npz') as master:
                bones = {k.removesuffix('_vertices'): master[k] for k in master.files if k.endswith('_vertices')}
                faces = {k.removesuffix('_faces'): master[k] for k in master.files if k.endswith('_faces')}
            scene, rig = articulated_scene(bones, faces, {})
            cls.models[sex] = bones, scene, rig

    def test_arms_hang_beside_body_without_stretching_bones(self):
        for sex, (bones, scene, rig) in self.models.items():
            with self.subTest(sex=sex):
                for side, sign in (('L', 1), ('R', -1)):
                    shoulder, elbow, wrist = [scene.graph[f'{joint}_{side}'][0][:3, 3] for joint in ('shoulder', 'elbow', 'wrist')]
                    self.assertGreater(shoulder[1], elbow[1])
                    self.assertGreater(elbow[1], wrist[1])
                    self.assertGreater(sign * wrist[0], sign * shoulder[0])
                    self.assertGreater(wrist[2], elbow[2])
                    # Every hand vertex stays below the elbow and outside the hip bone.
                    hand = np.concatenate([world_vertices(scene, name) for name in bones if name.startswith('Hand') and name.endswith('_' + side)])
                    self.assertLess(hand[:, 1].max(), elbow[1])
                    self.assertGreater((sign * hand[:, 0]).min(), (sign * bones[f'Pelvis_{side}'][:, 0]).max())
                moved = {name for joint in rig['joints'] for name in joint['structures']}
                for name, source in bones.items():
                    posed = world_vertices(scene, name)
                    if name not in moved:
                        np.testing.assert_allclose(posed, source, atol=1e-12)
                    else:
                        # Triangle edge lengths must survive articulation, not just bounds.
                        edges = scene.geometry[name].edges_unique
                        before = np.linalg.norm(source[edges[:, 0]] - source[edges[:, 1]], axis=1)
                        after = np.linalg.norm(posed[edges[:, 0]] - posed[edges[:, 1]], axis=1)
                        np.testing.assert_allclose(after, before, atol=1e-12, rtol=0)

    def test_rest_matrices_recover_original_source_pose(self):
        for sex, (bones, posed, rig) in self.models.items():
            with self.subTest(sex=sex):
                scene = posed.copy()
                for joint in rig['joints']:
                    scene.graph.update(frame_to=joint['id'], frame_from=joint['parent'], matrix=np.array(joint['restLocalMatrix']))
                for name, source in bones.items():
                    np.testing.assert_allclose(world_vertices(scene, name), source, atol=1e-12)

    def test_elbow_rotation_carries_forearm_and_hand_but_not_humerus_or_torso(self):
        delta = Rotation.from_euler('z', 17, degrees=True).as_matrix()
        for sex, (_, posed, rig) in self.models.items():
            for side in ('L', 'R'):
                with self.subTest(sex=sex, side=side):
                    scene = posed.copy()
                    joint = next(j for j in rig['joints'] if j['id'] == f'elbow_{side}')
                    before = scene.graph[joint['id']][0]
                    pivot = before[:3, 3]
                    world_rotation = before[:3, :3] @ delta @ before[:3, :3].T
                    scene.graph.update(frame_to=joint['id'], frame_from=joint['parent'], matrix=np.array(joint['localMatrix']) @ matrix(delta))
                    for name in (f'Radius_{side}', f'Ulna_{side}', f'HandMeta3_{side}', f'HandDistP3_{side}'):
                        original = world_vertices(posed, name)
                        expected = (original - pivot) @ world_rotation.T + pivot
                        np.testing.assert_allclose(world_vertices(scene, name), expected, atol=1e-12)
                        self.assertGreater(np.linalg.norm(world_vertices(scene, name) - original), .001)
                    for name in (f'Humerus_{side}', 'Sternum', f'HandMeta3_{"R" if side == "L" else "L"}'):
                        np.testing.assert_array_equal(world_vertices(scene, name), world_vertices(posed, name))


if __name__ == '__main__':
    unittest.main()
