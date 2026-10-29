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
        with np.load(ROOT / 'data/derived' / (model['id'] + '.npz')) as master:
            for name, mesh in scene.geometry.items():
                if not np.isfinite(mesh.vertices).all():
                    raise ValueError(f'{name}: nonfinite coordinates')
                np.testing.assert_allclose(mesh.vertices, master[name + '_vertices'], atol=1e-7, rtol=0)
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
                       'boundsM': scene.bounds.tolist(), 'sha256': model['sha256']})
    print(json.dumps({'verified': report}, indent=2))


if __name__ == '__main__':
    main()
