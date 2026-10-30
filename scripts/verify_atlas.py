"""Exercise shipped GLBs and float64 masters without needing the source download."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

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
            np.testing.assert_allclose(local[:3, :3].T @ local[:3, :3], np.eye(3), atol=1e-12)
            np.testing.assert_allclose(np.linalg.det(local[:3, :3]), 1, atol=1e-12)
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
        bones = scene.geometry
        np.testing.assert_allclose(bones['Head'].bounds[1, 1], manifest['normalization']['targetHeightM'], atol=1e-6)
        feet = [mesh for name, mesh in bones.items() if name.startswith(('Foot', 'Cal_', 'Tal_', 'Cub_', 'Nav_', 'MedCun_', 'InterCun_', 'LatCun_'))]
        np.testing.assert_allclose(min(m.bounds[0, 1] for m in feet), 0, atol=1e-6)
        if bones['Pelvis_L'].vertices[:, 0].mean() <= bones['Pelvis_R'].vertices[:, 0].mean():
            raise ValueError('Left/right orientation reversed')
        if bones['Sternum'].vertices[:, 2].mean() <= bones['T8'].vertices[:, 2].mean():
            raise ValueError('Anterior/posterior orientation reversed')
        report.append({'model': model['id'], 'subjects': model['subjects'], 'structures': len(bones),
                       'vertices': sum(len(m.vertices) for m in bones.values()),
                       'triangles': sum(len(m.faces) for m in bones.values()),
                       'boundsM': scene.bounds.tolist(), 'sha256': model['sha256'], 'rigJoints': len(rig['joints']),
                       'pose': manifest['pose']['label'], 'referenceSha256': rig['reference']['sha256']})
    print(json.dumps({'verified': report}, indent=2))


if __name__ == '__main__':
    main()
