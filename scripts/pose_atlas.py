"""Export an arms-at-sides rigid hierarchy without modifying the source-pose means."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation
import trimesh

ROOT = Path(__file__).resolve().parents[1]
ABDUCTION_DEG = 8.0
FLEXION_DEG = 5.0
POSE = {
    'id': 'relaxed-standing',
    'label': 'Arms at sides',
    'description': 'Post-average rigid arm articulation: 8° shoulder abduction and 5° elbow flexion, with hands following the forearms. The source-pose float64 means are preserved unchanged. Joint centers are surface estimates, not validated anatomical landmarks.',
    'rig': 'Rigid shoulder → elbow → wrist nodes on each side; no skinning, IK, joint limits or animation clips. Other structures retain their source-derived posture.',
}
POSE_LIMITATION = 'Cohort averaging uses whole-body orientation and uniform scale, not per-subject joint-pose normalization. Post-average arm articulation cannot undo pose-blurred means. Estimated pivots, joint congruence and intersections require anatomical review; the shoulder girdle and finger posture are unchanged.'


def unit(vector):
    length = np.linalg.norm(vector)
    if not np.isfinite(length) or length < 1e-10:
        raise ValueError('Degenerate arm landmark direction')
    return vector / length


def matrix(rotation=None, translation=None):
    result = np.eye(4)
    if rotation is not None:
        result[:3, :3] = rotation
    if translation is not None:
        result[:3, 3] = translation
    return result


def fit_round_surface(points):
    """Algebraic sphere fit in a centered frame; return radius and RMS residual."""
    origin = points.mean(axis=0)
    centered = points - origin
    design = np.column_stack((2 * centered, np.ones(len(points))))
    fit, _, rank, _ = np.linalg.lstsq(design, np.sum(centered ** 2, axis=1), rcond=None)
    if rank != design.shape[1]:
        raise ValueError('Joint surface fit is rank deficient')
    center = origin + fit[:-1]
    radius_squared = fit[-1] + fit[:-1] @ fit[:-1]
    if not np.isfinite(radius_squared) or radius_squared <= 0:
        raise ValueError('Joint surface fit has invalid radius')
    radius = np.sqrt(radius_squared)
    rms = np.sqrt(np.mean((np.linalg.norm(points - center, axis=1) - radius) ** 2))
    return center, float(radius), float(rms)


def estimate_arm(bones, side):
    """Surface-based display pivots. These are deliberately reported as estimates."""
    sign = 1 if side == 'L' else -1
    humerus = bones[f'Humerus_{side}']
    centered = humerus - humerus.mean(axis=0)
    _, _, axes = np.linalg.svd(centered, full_matrices=False)
    superior = axes[0] * (1 if axes[0, 1] > 0 else -1)
    projection = centered @ superior
    span = np.ptp(projection)
    # Medial half of the proximal 18%: head cap, rather than the entire tuberosity.
    cap = humerus[projection > projection.max() - .18 * span]
    cap = cap[sign * cap[:, 0] < np.median(sign * cap[:, 0])]
    shoulder, head_radius, head_rms = fit_round_surface(cap)
    distal = humerus[projection < projection.min() + .12 * span]
    # A distal-region centroid is only a display pivot. Do not treat the
    # trochlea/epicondyles as a spherical or circular articular surface.
    elbow = distal.mean(axis=0)
    wrist = (bones[f'HandLuna_{side}'].mean(axis=0) + bones[f'HandScaphoid_{side}'].mean(axis=0)) / 2
    if not .02 * span < head_radius < .15 * span or head_rms > .25 * head_radius:
        raise ValueError(f'{side}: estimated humeral head needs review (radius={head_radius}, RMS={head_rms})')
    audit = {'method': 'Humeral head sphere fit to medial half of proximal 18% along PCA axis; approximate elbow pivot at distal 12% vertex centroid; wrist midpoint of lunate/scaphoid vertex centroids. Elbow axis is estimated from upper-arm and forearm directions, not epicondylar landmarks.',
             'headRadiusM': head_radius, 'headFitRmsM': head_rms}
    return shoulder, elbow, wrist, audit


def arm_rig(bones, side):
    shoulder, elbow, wrist, audit = estimate_arm(bones, side)
    down = unit(elbow - shoulder)
    forearm = unit(wrist - elbow)
    bend = unit(forearm - down * np.dot(forearm, down))
    hinge = unit(np.cross(down, bend))
    source_frame = np.column_stack((down, bend, hinge))
    sign = 1 if side == 'L' else -1
    angle = np.deg2rad(ABDUCTION_DEG)
    target_down = np.array([sign * np.sin(angle), -np.cos(angle), 0.0])
    target_bend = np.array([0.0, 0.0, 1.0])
    target_frame = np.column_stack((target_down, target_bend, np.cross(target_down, target_bend)))
    shoulder_rotation = target_frame @ source_frame.T
    source_flexion = np.arctan2(np.dot(forearm, bend), np.dot(forearm, down))
    elbow_rotation = Rotation.from_rotvec(hinge * (np.deg2rad(FLEXION_DEG) - source_flexion)).as_matrix()
    audit['sourceFlexionDeg'] = float(np.rad2deg(source_flexion))
    joints = [
        {'id': f'shoulder_{side}', 'parent': 'world', 'sourcePivotM': shoulder.tolist(),
         'restLocalMatrix': matrix(translation=shoulder).tolist(),
         'localMatrix': matrix(shoulder_rotation, shoulder).tolist(), 'structures': [f'Humerus_{side}']},
        {'id': f'elbow_{side}', 'parent': f'shoulder_{side}', 'sourcePivotM': elbow.tolist(),
         'restLocalMatrix': matrix(translation=elbow - shoulder).tolist(),
         'localMatrix': matrix(elbow_rotation, elbow - shoulder).tolist(), 'structures': [f'Radius_{side}', f'Ulna_{side}']},
        {'id': f'wrist_{side}', 'parent': f'elbow_{side}', 'sourcePivotM': wrist.tolist(),
         'restLocalMatrix': matrix(translation=wrist - elbow).tolist(),
         'localMatrix': matrix(translation=wrist - elbow).tolist(),
         'structures': sorted(k for k in bones if k.startswith('Hand') and k.endswith('_' + side))},
    ]
    return joints, audit


def articulated_scene(bones, faces, metadata):
    scene = trimesh.Scene(metadata={**metadata, 'pose': POSE})
    material = trimesh.visual.material.PBRMaterial(name='bone', baseColorFactor=[228, 219, 201, 255], metallicFactor=0, roughnessFactor=.77)
    rig = {'pose': POSE['id'], 'shoulderAbductionDeg': ABDUCTION_DEG, 'elbowFlexionDeg': FLEXION_DEG,
           'reviewStatus': 'Estimated display rig, not anatomically validated', 'joints': [], 'landmarkEstimates': {}}
    attachments = {}
    for side in ('L', 'R'):
        joints, audit = arm_rig(bones, side)
        rig['joints'].extend(joints)
        rig['landmarkEstimates'][side] = audit
        for joint in joints:
            scene.graph.update(frame_to=joint['id'], frame_from=joint['parent'], matrix=np.array(joint['localMatrix']))
            for name in joint['structures']:
                attachments[name] = joint
    for name, vertices in bones.items():
        joint = attachments.get(name)
        local = vertices - joint['sourcePivotM'] if joint else vertices
        mesh = trimesh.Trimesh(vertices=local, faces=faces[name], process=False)
        mesh.visual = trimesh.visual.TextureVisuals(material=material)
        scene.add_geometry(mesh, node_name=name, geom_name=name, parent_node_name=joint['id'] if joint else 'world',
                           metadata={'sourceStructure': name, 'license': 'CC-BY-SA-4.0'})
    return scene, rig


def export_model(sex, bones, faces, source_url):
    scene, rig = articulated_scene(bones, faces, {'license': 'CC-BY-SA-4.0', 'source': source_url, 'reviewStatus': 'Unreviewed cohort mean'})
    path = ROOT / 'public/models' / f'{sex}.glb'
    scene.export(path, file_type='glb')
    reference = ROOT / 'data/derived' / f'{sex}.npz'
    rig['reference'] = {'path': str(reference.relative_to(ROOT)), 'sha256': hashlib.sha256(reference.read_bytes()).hexdigest(),
                        'pose': 'Unchanged source-derived flexed-arm cohort mean; coordinates in meters'}
    return {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'boundsM': scene.bounds.tolist(),
            'glbBytes': path.stat().st_size, 'poseRig': rig}


def main():
    manifest_path = ROOT / 'public/models/manifest.json'
    report_path = ROOT / 'reports/generation.json'
    manifest = json.loads(manifest_path.read_text())
    report = json.loads(report_path.read_text())
    for model in manifest['models']:
        with np.load(ROOT / 'data/derived' / (model['id'] + '.npz')) as master:
            bones = {k.removesuffix('_vertices'): master[k] for k in master.files if k.endswith('_vertices')}
            faces = {k.removesuffix('_faces'): master[k] for k in master.files if k.endswith('_faces')}
        result = export_model(model['id'], bones, faces, manifest['source']['url'])
        model['sha256'] = result.pop('sha256')
        next(m for m in report['models'] if m['id'] == model['id']).update(result)
        print(f"{model['id']}: exported {len(bones)} rigid meshes in {POSE['label']} pose")
    manifest['pose'] = POSE
    manifest['limitations'] = [note for note in manifest['limitations'] if note != POSE_LIMITATION]
    manifest['limitations'].insert(3, POSE_LIMITATION)
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    report_path.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
