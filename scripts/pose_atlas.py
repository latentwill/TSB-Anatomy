"""Export a reversible, grounded standing pose without modifying the reference means."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
import trimesh

ROOT = Path(__file__).resolve().parents[1]
ABDUCTION_DEG = 8.0
FLEXION_DEG = 5.0
CLAVICLE_ELEVATION_DEG = 10.0
MIN_KNEE_FLEXION_DEG = 5.0
FOOT_PREFIXES = ('Foot', 'Cal_', 'Tal_', 'Cub_', 'Nav_', 'MedCun_', 'InterCun_', 'LatCun_')
POSE = {
    'id': 'relaxed-standing',
    'label': 'Grounded standing',
    'groundY': 0.0,
    'description': 'Post-average standing articulation: clavicle elevation set to 10°, arms at sides with 8° abduction and 5° elbow flexion, rigid feet leveled onto heel and medial/lateral forefoot supports. Hip/knee articulation closes both leg chains without stretching. One final whole-body uniform scale restores the reference skeletal height. Original float64 means remain unchanged; pivots and pose targets are display estimates, not validated anatomical landmarks or clinical norms.',
    'rig': 'Rigid sternoclavicular → shoulder → elbow → wrist and hip → knee → ankle chains, under one height-normalization node. No skinning, biomechanical joint limits or animation clips. Spine, finger and internal foot shape are preserved; no cartilage or plantar soft tissue is modeled.',
}
POSE_LIMITATION = 'Cohort averaging uses whole-body orientation and uniform scale, not per-subject joint-pose normalization. Post-average standing articulation cannot undo pose-blurred means. Shoulder-girdle motion, joint centers, knee tracking and bone-ground supports are estimates requiring anatomical review. Rigid arches are preserved, not flattened; bone contact is not a modeled soft-tissue sole or a validated weight-bearing posture.'


def unit(vector):
    length = np.linalg.norm(vector)
    if not np.isfinite(length) or length < 1e-10:
        raise ValueError('Degenerate anatomical landmark direction')
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


def rotation_between(source, target):
    return Rotation.align_vectors(unit(target)[None, :], unit(source)[None, :])[0].as_matrix()


def foot_regions(bones, side):
    forefoot = [name for name in bones if name.startswith('Foot') and name.endswith('_' + side)]
    return {'heel': [f'Cal_{side}'],
            'medialForefoot': [name for name in forefoot if name[-3] in '12' or name.startswith('FootSesa')],
            'lateralForefoot': [name for name in forefoot if name[-3] in '345']}


def level_foot(bones, side, ankle):
    """Find a supporting plane, not a flattening deformation of the foot/arch."""
    sign = 1 if side == 'L' else -1
    heel = bones[f'Cal_{side}'].mean(axis=0)
    medial = bones[f'FootMeta1_{side}'].mean(axis=0)
    lateral = bones[f'FootMeta5_{side}'].mean(axis=0)
    x = unit(sign * (lateral - medial))
    forward = (medial + lateral) / 2 - heel
    z = unit(forward - x * np.dot(forward, x))
    y = unit(np.cross(z, x))
    target_z = unit(np.array([z[0], 0., z[2]]))
    initial = np.column_stack((np.cross([0., 1., 0.], target_z), [0., 1., 0.], target_z)) @ np.column_stack((x, y, z)).T
    regions = foot_regions(bones, side)
    points = [np.concatenate([bones[name] for name in names]) for names in regions.values()]

    def rotation(angles):
        return Rotation.from_rotvec([angles[0], 0., angles[1]]).as_matrix() @ initial

    def residual(angles):
        up = rotation(angles)[1]
        low = np.array([np.min(group @ up) for group in points])
        return low[1:] - low[0]

    result = least_squares(residual, [0., 0.], bounds=(-np.pi / 6, np.pi / 6),
                           xtol=1e-13, ftol=1e-13, gtol=1e-13, max_nfev=200)
    if not result.success or np.max(np.abs(residual(result.x))) > 1e-8:
        raise ValueError(f'{side}: could not find a three-region foot support plane')
    rotate = rotation(result.x)
    up = rotate[1]
    support_y = min(np.min(group @ up) for group in points)
    names = [name for name in bones if name.startswith(FOOT_PREFIXES) and name.endswith('_' + side)]
    if min(np.min(bones[name] @ up) for name in names) < support_y - 1e-8:
        raise ValueError(f'{side}: a foot bone penetrates the proposed support plane')
    contacts = {}
    for region, members in regions.items():
        name = min(members, key=lambda item: np.min(bones[item] @ up))
        contacts[region] = {'structure': name, 'vertexIndex': int(np.argmin(bones[name] @ up))}
    return rotate, float(np.dot(ankle, up) - support_y), contacts


def estimate_leg(bones, side):
    sign = 1 if side == 'L' else -1
    femur = bones[f'Femur_{side}']
    centered = femur - femur.mean(axis=0)
    _, _, axes = np.linalg.svd(centered, full_matrices=False)
    superior = axes[0] * (1 if axes[0, 1] > 0 else -1)
    projection = centered @ superior
    span = np.ptp(projection)
    # The proximal cap excludes the femoral neck and greater trochanter.
    cap = femur[projection > projection.max() - .08 * span]
    cap = cap[sign * cap[:, 0] < np.quantile(sign * cap[:, 0], .45)]
    hip, radius, rms = fit_round_surface(cap)
    if not .02 * span < radius < .15 * span or rms > .15 * radius:
        raise ValueError(f'{side}: femoral head estimate requires review')
    knee = femur[projection < projection.min() + .12 * span].mean(axis=0)
    talus = bones[f'Tal_{side}']
    ankle = talus[talus[:, 1] >= np.quantile(talus[:, 1], .75)].mean(axis=0)
    rotate, ankle_height, contacts = level_foot(bones, side, ankle)
    return {'hip': hip, 'knee': knee, 'ankle': ankle, 'footRotation': rotate, 'ankleHeight': ankle_height,
            'contacts': contacts, 'audit': {'method': 'Hip sphere fit to medial 45% of proximal 8% femoral cap; knee at distal 12% femoral vertex centroid; ankle at superior quartile talus centroid. Two-link leg solve preserves segment lengths; patella follows femur, not a modeled patellar tracking mechanism.',
                                           'hipRadiusM': radius, 'hipFitRmsM': rms}}


def standing_rig(bones):
    legs = {side: estimate_leg(bones, side) for side in ('L', 'R')}
    required_ground = []
    for leg in legs.values():
        hip, knee, ankle = (leg[key] for key in ('hip', 'knee', 'ankle'))
        upper, lower = np.linalg.norm(knee - hip), np.linalg.norm(ankle - knee)
        reach_squared = upper ** 2 + lower ** 2 + 2 * upper * lower * np.cos(np.deg2rad(MIN_KNEE_FLEXION_DEG))
        horizontal_squared = np.sum((hip[[0, 2]] - ankle[[0, 2]]) ** 2)
        if reach_squared <= horizontal_squared:
            raise ValueError('The requested foot placement exceeds the leg reach')
        required_ground.append(hip[1] - leg['ankleHeight'] - np.sqrt(reach_squared - horizontal_squared))
    # One body translation, not independently floating/dislocated ankle offsets.
    ground = max(required_ground)
    source_low = min(vertices[:, 1].min() for name, vertices in bones.items() if name.startswith(FOOT_PREFIXES))
    target_height = bones['Head'][:, 1].max() - source_low
    scale = float(target_height / (bones['Head'][:, 1].max() - ground))
    root = {'id': 'stance', 'parent': 'world', 'sourcePivotM': [0., 0., 0.], 'structures': [],
            'restLocalMatrix': np.eye(4).tolist(), 'localMatrix': matrix(np.eye(3) * scale, [0., -ground * scale, 0.]).tolist()}
    joints = [root]
    for side, leg in legs.items():
        hip, knee, ankle = (leg[key] for key in ('hip', 'knee', 'ankle'))
        target_ankle = ankle.copy()
        target_ankle[1] = ground + leg['ankleHeight']
        upper, lower = np.linalg.norm(knee - hip), np.linalg.norm(ankle - knee)
        distance = np.linalg.norm(target_ankle - hip)
        if distance > upper + lower + 1e-10 or distance < abs(upper - lower) - 1e-10:
            raise ValueError(f'{side}: ground target cannot be reached without changing segment lengths')
        axis = unit(target_ankle - hip)
        along = (upper ** 2 - lower ** 2 + distance ** 2) / (2 * distance)
        bend = unit(np.array([0., 0., 1.]) - axis * axis[2])
        target_knee = hip + axis * along + bend * np.sqrt(max(0., upper ** 2 - along ** 2))
        hip_rotation = rotation_between(knee - hip, target_knee - hip)
        shin_rotation = rotation_between(ankle - knee, target_ankle - target_knee)
        flexion = np.rad2deg(np.arccos(np.clip(np.dot(unit(target_knee - hip), unit(target_ankle - target_knee)), -1., 1.)))
        leg['audit']['posedKneeFlexionDeg'] = float(flexion)
        leg['audit']['footRotationDeg'] = float(np.rad2deg(Rotation.from_matrix(leg['footRotation']).magnitude()))
        joints.extend([
            {'id': f'hip_{side}', 'parent': 'stance', 'sourcePivotM': hip.tolist(),
             'restLocalMatrix': matrix(translation=hip).tolist(), 'localMatrix': matrix(hip_rotation, hip).tolist(),
             'structures': [f'Femur_{side}', f'Patella_{side}']},
            {'id': f'knee_{side}', 'parent': f'hip_{side}', 'sourcePivotM': knee.tolist(),
             'restLocalMatrix': matrix(translation=knee - hip).tolist(),
             'localMatrix': matrix(hip_rotation.T @ shin_rotation, knee - hip).tolist(),
             'structures': [f'Tibia_{side}', f'Fibula_{side}']},
            {'id': f'ankle_{side}', 'parent': f'knee_{side}', 'sourcePivotM': ankle.tolist(),
             'restLocalMatrix': matrix(translation=ankle - knee).tolist(),
             'localMatrix': matrix(shin_rotation.T @ leg['footRotation'], ankle - knee).tolist(),
             'structures': sorted(name for name in bones if name.startswith(FOOT_PREFIXES) and name.endswith('_' + side))},
        ])
    return joints, legs, {'uniformScale': scale, 'bodyTranslationBeforeScaleM': -float(ground),
                         'targetHeightM': float(target_height), 'groundY': 0.}


def shoulder_girdle(bones, side):
    sign = 1 if side == 'L' else -1
    clavicle = bones[f'Clavicula_{side}']
    across = sign * clavicle[:, 0]
    pivot = clavicle[across < np.quantile(across, .1)].mean(axis=0)
    lateral = clavicle[across > np.quantile(across, .9)].mean(axis=0)
    direction = lateral - pivot
    horizontal = unit(np.array([direction[0], 0., direction[2]]))
    elevation = np.deg2rad(CLAVICLE_ELEVATION_DEG)
    target = horizontal * np.cos(elevation) + np.array([0., np.sin(elevation), 0.])
    rotate = rotation_between(direction, target)
    joint = {'id': f'girdle_{side}', 'parent': 'stance', 'sourcePivotM': pivot.tolist(),
             'restLocalMatrix': matrix(translation=pivot).tolist(), 'localMatrix': matrix(rotate, pivot).tolist(),
             'structures': [f'Clavicula_{side}', f'Scapula_{side}']}
    audit = {'sourceClavicleElevationDeg': float(np.rad2deg(np.arctan2(direction[1], np.linalg.norm(direction[[0, 2]])))),
             'posedClavicleElevationDeg': CLAVICLE_ELEVATION_DEG,
             'method': 'Estimated sternoclavicular pivot at medial 10% vertex centroid; lateral 10% centroid defines elevation. Clavicle and scapula move together to retain their existing relationship. 10° is a display pose target, not a clinical norm; scapulothoracic glide is not modeled.'}
    return joint, rotate, audit


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
    girdle, girdle_rotation, girdle_audit = shoulder_girdle(bones, side)
    pivot = np.array(girdle['sourcePivotM'])
    audit['shoulderGirdle'] = girdle_audit
    joints = [
        girdle,
        {'id': f'shoulder_{side}', 'parent': girdle['id'], 'sourcePivotM': shoulder.tolist(),
         'restLocalMatrix': matrix(translation=shoulder - pivot).tolist(),
         'localMatrix': matrix(girdle_rotation.T @ shoulder_rotation, shoulder - pivot).tolist(), 'structures': [f'Humerus_{side}']},
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
    joints, legs, normalization = standing_rig(bones)
    rig = {'pose': POSE['id'], 'shoulderAbductionDeg': ABDUCTION_DEG, 'elbowFlexionDeg': FLEXION_DEG,
           'reviewStatus': 'Estimated display rig, not anatomically validated', 'joints': joints,
           'normalization': normalization, 'landmarkEstimates': {}, 'groundContacts': {}}
    attachments = {}
    for side in ('L', 'R'):
        arm_joints, audit = arm_rig(bones, side)
        joints.extend(arm_joints)
        rig['landmarkEstimates'][side] = {'arm': audit, 'leg': legs[side]['audit']}
    attached = {name for joint in joints for name in joint['structures']}
    joints[0]['structures'] = sorted(set(bones) - attached)
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
    for side, leg in legs.items():
        rig['groundContacts'][side] = {}
        for region, contact in leg['contacts'].items():
            name, index = contact['structure'], contact['vertexIndex']
            point = trimesh.transform_points(scene.geometry[name].vertices[[index]], scene.graph[name][0])[0]
            rig['groundContacts'][side][region] = {**contact, 'positionM': point.tolist()}
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
    limitation_index = next(i for i, note in enumerate(manifest['limitations']) if note.startswith('Cohort averaging uses whole-body orientation'))
    manifest['limitations'][limitation_index] = POSE_LIMITATION
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    report_path.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
