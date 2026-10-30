"""Exercise shipped GLBs and float64 masters without needing the source download."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh
from pose_atlas import FOOT_PREFIXES, foot_regions

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / 'public/models/manifest.json').read_text())
    expected = {x['id'] for x in manifest['structures']}
    generation = json.loads((ROOT / 'reports/generation.json').read_text())
    if len(expected) != 182 or len(manifest['models']) != 2:
        raise ValueError('Unexpected skeleton inventory')
    report = []
    for model in manifest['models']:
        path = ROOT / 'public' / model['url']
        if hashlib.sha256(path.read_bytes()).hexdigest() != model['sha256']:
            raise ValueError(f'{path}: SHA256 mismatch')
        scene = trimesh.load_scene(path, process=False)
        if set(scene.geometry) != expected:
            raise ValueError(f'{path}: missing or renamed GLB structures')
        rig = next(m['poseRig'] for m in generation['models'] if m['id'] == model['id'])
        reference = ROOT / rig['reference']['path']
        if hashlib.sha256(reference.read_bytes()).hexdigest() != rig['reference']['sha256']:
            raise ValueError(f'{reference}: source-pose reference changed')
        worlds = {'world': np.eye(4)}
        attachments = {}
        parents = {child: parent for parent, child, _ in scene.graph.to_edgelist()}
        for joint in rig['joints']:
            local = np.array(joint['localMatrix'])
            scale = rig['normalization']['uniformScale'] if joint['id'] == 'stance' else 1.
            rotation = local[:3, :3] / scale
            np.testing.assert_allclose(rotation.T @ rotation, np.eye(3), atol=1e-12)
            np.testing.assert_allclose(np.linalg.det(rotation), 1, atol=1e-12)
            worlds[joint['id']] = worlds[joint['parent']] @ local
            if parents[joint['id']] != joint['parent']:
                raise ValueError(f"{joint['id']}: incorrect joint parent")
            np.testing.assert_allclose(scene.graph[joint['id']][0], worlds[joint['id']], atol=1e-12)
            for name in joint['structures']:
                attachments[name] = joint
        with np.load(ROOT / 'data/derived' / (model['id'] + '.npz')) as master:
            for name, mesh in scene.geometry.items():
                if not np.isfinite(mesh.vertices).all():
                    raise ValueError(f'{name}: nonfinite coordinates')
                joint = attachments.get(name)
                pivot = np.array(joint['sourcePivotM']) if joint else np.zeros(3)
                if parents[name] != (joint['id'] if joint else 'world'):
                    raise ValueError(f'{name}: incorrect rigid attachment')
                np.testing.assert_allclose(mesh.vertices + pivot, master[name + '_vertices'], atol=1e-7, rtol=0)
                np.testing.assert_array_equal(mesh.faces, master[name + '_faces'])
        bones = {name: trimesh.transform_points(mesh.vertices, scene.graph[name][0]) for name, mesh in scene.geometry.items()}
        np.testing.assert_allclose(bones['Head'][:, 1].max(), manifest['normalization']['targetHeightM'], atol=1e-6)
        if min(points[:, 1].min() for points in bones.values()) < -1e-6:
            raise ValueError('Anatomy penetrates the ground plane')
        contacts = {}
        for side in ('L', 'R'):
            contacts[side] = {}
            for region, names in foot_regions(bones, side).items():
                gap = min(bones[name][:, 1].min() for name in names)
                np.testing.assert_allclose(gap, manifest['pose']['groundY'], atol=1e-6, rtol=0)
                contacts[side][region] = float(gap * 1000)
                recorded = rig['groundContacts'][side][region]
                np.testing.assert_allclose(bones[recorded['structure']][recorded['vertexIndex']], recorded['positionM'], atol=1e-7)
            foot_low = min(points[:, 1].min() for name, points in bones.items() if name.startswith(FOOT_PREFIXES) and name.endswith('_' + side))
            np.testing.assert_allclose(foot_low, 0, atol=1e-6)
        if bones['Pelvis_L'][:, 0].mean() <= bones['Pelvis_R'][:, 0].mean():
            raise ValueError('Left/right orientation reversed')
        if bones['Sternum'][:, 2].mean() <= bones['T8'][:, 2].mean():
            raise ValueError('Anterior/posterior orientation reversed')
        report.append({'model': model['id'], 'subjects': model['subjects'], 'structures': len(bones),
                       'vertices': sum(len(mesh.vertices) for mesh in scene.geometry.values()),
                       'triangles': sum(len(mesh.faces) for mesh in scene.geometry.values()), 'supportGapsMm': contacts,
                       'boundsM': scene.bounds.tolist(), 'sha256': model['sha256'], 'rigJoints': len(rig['joints']),
                       'pose': manifest['pose']['label'], 'referenceSha256': rig['reference']['sha256']})
    print(json.dumps({'verified': report}, indent=2))


if __name__ == '__main__':
    main()
