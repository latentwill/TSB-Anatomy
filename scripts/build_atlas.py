"""Build size-normalized, sex-stratified OpenSkeleton cohort means (not clinical models)."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

import h5py
import numpy as np
from scipy.io import loadmat
import trimesh

from fetch_source import digest, RECORD

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw' / RECORD
OUTPUT = ROOT / 'public/models'
FOOT_PREFIXES = ('Foot', 'Cal_', 'Tal_', 'Cub_', 'Nav_', 'MedCun_', 'InterCun_', 'LatCun_')


def unit(vector):
    length = np.linalg.norm(vector)
    if not np.isfinite(length) or length < 1e-9:
        raise ValueError('Degenerate anatomical orientation landmarks')
    return vector / length


def normalize_skeleton(bones, height):
    """One rigid anatomical frame and one uniform scale for the entire skeleton."""
    if not np.isfinite(height) or height <= 0:
        raise ValueError('Target height must be positive and finite')
    left = bones['Pelvis_L'].mean(axis=0)
    right = bones['Pelvis_R'].mean(axis=0)
    feet = [v for k, v in bones.items() if k.startswith(FOOT_PREFIXES)]
    if not feet:
        raise ValueError('Foot geometry is required for skeletal height')
    foot_center = (bones['Cal_L'].mean(axis=0) + bones['Cal_R'].mean(axis=0)) / 2
    y = unit(bones['Head'].mean(axis=0) - foot_center)
    lateral = left - right
    x = unit(lateral - y * np.dot(lateral, y))
    z = unit(np.cross(x, y))
    rotation = np.column_stack((x, y, z))
    anterior = bones['Sternum'].mean(axis=0) - bones['T8'].mean(axis=0)
    if np.dot(anterior, z) <= 0:
        raise ValueError('Anatomical handedness check failed: sternum is not anterior to T8')
    origin = (left + right) / 2
    oriented = {k: (v - origin) @ rotation for k, v in bones.items()}
    bottom = min(v[:, 1].min() for k, v in oriented.items() if k.startswith(FOOT_PREFIXES))
    top = oriented['Head'][:, 1].max()
    span = float(top - bottom)
    if not np.isfinite(span) or span <= 0:
        raise ValueError('Invalid skull-to-foot extent')
    scale = height / span
    for points in oriented.values():
        points[:, 1] -= bottom
        points *= scale
    return oriented, {'sourceSkeletalExtent': span, 'scaleToMeters': scale,
                      'rotation': rotation.tolist(), 'origin': origin.tolist(), 'footBaseline': float(bottom)}


def label_structure(name):
    side = 'Left ' if name.endswith('_L') else 'Right ' if name.endswith('_R') else ''
    stem = name[:-2] if side else name
    simple = {'Head': ('Skull (combined)', 'Head'), 'Jaw': ('Mandible', 'Head'),
              'Pelvis': ('hip bone', 'Pelvis'), 'Sacrum': ('Sacrum', 'Pelvis'),
              'Sternum': ('Sternum', 'Thorax'), 'Clavicula': ('clavicle', 'Shoulder'),
              'Scapula': ('scapula', 'Shoulder'), 'Femur': ('femur', 'Lower limb'),
              'Tibia': ('tibia', 'Lower limb'), 'Fibula': ('fibula', 'Lower limb'),
              'Patella': ('patella', 'Lower limb'), 'Humerus': ('humerus', 'Upper limb'),
              'Radius': ('radius', 'Upper limb'), 'Ulna': ('ulna', 'Upper limb'),
              'Cal': ('calcaneus', 'Foot'), 'Tal': ('talus', 'Foot'), 'Cub': ('cuboid', 'Foot'),
              'Nav': ('navicular', 'Foot'), 'MedCun': ('medial cuneiform', 'Foot'),
              'InterCun': ('intermediate cuneiform', 'Foot'), 'LatCun': ('lateral cuneiform', 'Foot'),
              'FootSesaLat': ('lateral hallux sesamoid', 'Foot'), 'FootSesaMed': ('medial hallux sesamoid', 'Foot'),
              'HandCapitatum': ('capitate', 'Hand'), 'HandHamata': ('hamate', 'Hand'),
              'HandLuna': ('lunate', 'Hand'), 'HandPisiform': ('pisiform', 'Hand'),
              'HandScaphoid': ('scaphoid', 'Hand'), 'HandTrapezium': ('trapezium', 'Hand'),
              'HandTrapezoideum': ('trapezoid', 'Hand'), 'HandTriquetrum': ('triquetrum', 'Hand')}
    if stem in simple:
        label, region = simple[stem]
    elif re.fullmatch(r'[CTL]\d+', stem):
        label, region = f"{'Cervical' if stem[0] == 'C' else 'Thoracic' if stem[0] == 'T' else 'Lumbar'} vertebra {stem}", 'Spine'
    elif stem.startswith('Rib'):
        label, region = f'rib {stem[3:]}', 'Thorax'
    elif match := re.fullmatch(r'(Hand|Foot)(Meta|ProxP|MidP|DistP)([1-5])', stem):
        limb, part, digit = match.groups()
        kind = {'Meta': 'metacarpal' if limb == 'Hand' else 'metatarsal', 'ProxP': 'proximal phalanx', 'MidP': 'middle phalanx', 'DistP': 'distal phalanx'}[part]
        label, region = f'{kind} {digit} ({limb.lower()})', limb
    else:
        raise ValueError(f'Unmapped source structure: {name}')
    return {'id': name, 'label': (side + label) if side else label, 'region': region}


def checked_faces(values, vertices, name):
    if values.ndim != 2 or values.shape[1] != 3 or not np.isfinite(values).all():
        raise ValueError(f'{name}: invalid triangular connectivity')
    if not np.equal(values, np.floor(values)).all() or values.min() < 1 or values.max() > vertices:
        raise ValueError(f'{name}: invalid MATLAB vertex indices')
    faces = values.astype(np.int64) - 1
    if np.any((faces[:, 0] == faces[:, 1]) | (faces[:, 0] == faces[:, 2]) | (faces[:, 1] == faces[:, 2])):
        raise ValueError(f'{name}: repeated triangle vertex')
    return faces


def verify_source():
    record = json.loads((ROOT / f'sources/openskeleton-{RECORD}.json').read_text())
    for item in record['files']:
        if item['key'] not in ('Metadata.mat', 'Faces.mat', 'NM_combined.mat'):
            continue
        path = RAW / item['key']
        if path.stat().st_size != item['size'] or digest(path) != item['checksum'].removeprefix('md5:'):
            raise ValueError(f"Source integrity mismatch: {item['key']}")
    return record


def build(height=1.7):
    record = verify_source()
    metadata = loadmat(RAW / 'Metadata.mat', simplify_cells=True)['Metadata']
    source_faces = loadmat(RAW / 'Faces.mat', simplify_cells=True)['Faces']
    names = sorted(k[1:] for k in source_faces)
    structures = [label_structure(name) for name in names]
    accumulators = {sex: {} for sex in ('female', 'male')}
    counts = Counter()
    transforms = []
    faces = {}
    shapes = {}
    with h5py.File(RAW / 'NM_combined.mat', 'r') as data:
        subjects = data['NM_combined']
        if set(subjects) != set(metadata):
            raise ValueError('Geometry and metadata subject IDs do not match')
        for subject_id in sorted(subjects):
            subject = subjects[subject_id]
            sex = metadata[subject_id]['sex_code'].lower()
            if sex not in accumulators or set(subject) != set(names):
                raise ValueError(f'{subject_id}: unexpected sex or missing/extra structures')
            bones = {}
            for name in names:
                vertices = subject[name]['Registered'][()].T
                if vertices.ndim != 2 or vertices.shape[1] != 3 or not np.isfinite(vertices).all():
                    raise ValueError(f'{subject_id}/{name}: invalid coordinates')
                if name not in shapes:
                    shapes[name] = vertices.shape
                    faces[name] = checked_faces(source_faces['F' + name], len(vertices), name)
                if vertices.shape != shapes[name]:
                    raise ValueError(f'{subject_id}/{name}: vertex correspondence shape differs')
                actual_faces = subject[name]['FRegistered'][()].T
                if not np.array_equal(actual_faces, source_faces['F' + name]):
                    raise ValueError(f'{subject_id}/{name}: registered connectivity differs from canonical Faces')
                bones[name] = vertices
            normalized, transform = normalize_skeleton(bones, height)
            for name, vertices in normalized.items():
                if name not in accumulators[sex]:
                    accumulators[sex][name] = np.zeros_like(vertices)
                accumulators[sex][name] += vertices
            counts[sex] += 1
            transforms.append({'subject': subject_id, 'sex': sex, **transform})
            print(f'Accumulated {sum(counts.values())}/{len(subjects)}', flush=True)
    if counts != {'female': 51, 'male': 51}:
        raise ValueError(f'Unexpected cohort counts: {counts}')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    report = {'sourceRecord': RECORD, 'cohortCounts': dict(counts), 'structures': len(names),
              'sourceVerticesPerSkeleton': sum(s[0] for s in shapes.values()),
              'sourceTrianglesPerSkeleton': sum(len(f) for f in faces.values()),
              'transforms': transforms, 'models': []}
    models = []
    material = trimesh.visual.material.PBRMaterial(name='bone', baseColorFactor=[228, 219, 201, 255], metallicFactor=0, roughnessFactor=.77)
    for sex in ('female', 'male'):
        mean = {name: total / counts[sex] for name, total in accumulators[sex].items()}
        # Averaging can shrink the extrema. One final whole-body scale restores the display height.
        low = min(v[:, 1].min() for k, v in mean.items() if k.startswith(FOOT_PREFIXES))
        span = mean['Head'][:, 1].max() - low
        final_scale = height / span
        scene = trimesh.Scene()
        mesh_audit = []
        master = {}
        for name, vertices in mean.items():
            vertices[:, 1] -= low
            vertices *= final_scale
            mesh = trimesh.Trimesh(vertices=vertices, faces=faces[name], process=False)
            if not np.isfinite(mesh.area_faces).all() or np.any(mesh.area_faces < 1e-16):
                bad = np.flatnonzero(mesh.area_faces < 1e-16)
                evidence = {'mean': mesh.area_faces[bad].tolist(), 'faces': bad.tolist(), 'sourceAreas': {}}
                with h5py.File(RAW / 'NM_combined.mat', 'r') as source:
                    for subject_id in sorted(source['NM_combined']):
                        if metadata[subject_id]['sex_code'].lower() != sex:
                            continue
                        points = source['NM_combined'][subject_id][name]['Registered'][()].T
                        triangles = points[faces[name][bad]]
                        areas = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]), axis=1) / 2
                        evidence['sourceAreas'][subject_id] = areas.tolist()
                print('[DEBUG-degeneracy] ' + json.dumps(evidence), flush=True)
                raise ValueError(f'{sex}/{name}: degenerate mean surface')
            mesh.visual = trimesh.visual.TextureVisuals(material=material)
            scene.add_geometry(mesh, node_name=name, geom_name=name, metadata={'sourceStructure': name, 'license': 'CC-BY-SA-4.0'})
            master[name + '_vertices'] = vertices
            master[name + '_faces'] = faces[name].astype(np.int32)
            mesh_audit.append({'id': name, 'vertices': len(vertices), 'triangles': len(faces[name]),
                               'watertight': bool(mesh.is_watertight), 'windingConsistent': bool(mesh.is_winding_consistent)})
        scene.metadata = {'license': 'CC-BY-SA-4.0', 'source': record['doi_url'], 'reviewStatus': 'Unreviewed cohort mean'}
        path = OUTPUT / f'{sex}.glb'
        scene.export(path, file_type='glb')
        # Float64 reference means retain source topology; GLB is the float32 viewing copy.
        master_dir = ROOT / 'data/derived'
        master_dir.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(master_dir / f'{sex}.npz', **master)
        bounds = scene.bounds
        models.append({'id': sex, 'label': sex.capitalize() + ' cohort mean', 'url': f'models/{sex}.glb',
                       'subjects': counts[sex], 'structures': len(names), 'heightM': height,
                       'reviewStatus': 'Unreviewed cohort mean', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        report['models'].append({'id': sex, 'finalScale': float(final_scale), 'boundsM': bounds.tolist(),
                                 'glbBytes': path.stat().st_size, 'meshAudit': mesh_audit})
    limitations = [
        'Unreviewed cohort means, not clinically validated or population-representative reference anatomy.',
        'Source-recorded sex groups; not an inference of gender identity.',
        'A common skull-to-foot skeletal extent is not measured living stature. No soft-tissue height is modeled.',
        'Whole-body rigid orientation and uniform scaling only. Joint posture differences remain and can blur or distort cohort means.',
        'Vertex counts and connectivity are checked; anatomical correspondence is supplied by OpenSkeleton, not independently validated here.',
        'Skull is a combined source structure. No separately selectable skull bones, teeth, auditory ossicles, hyoid or coccyx are identified in the inventory.',
        'Source mesh defects are reported, not silently repaired. Inter-bone intersections and joint congruence require anatomical review.',
        'No organs, muscles, cartilage, ligaments or clinical measurements are included.',
    ]
    manifest = {'title': 'TSB-Anatomy skeletal atlas', 'license': 'CC-BY-SA-4.0',
                'source': {'title': record['title'], 'url': record['doi_url'], 'license': 'CC-BY-4.0'},
                'method': 'Equal-weight arithmetic mean of corresponding vertices from 51 subjects per source-recorded sex. Each skeleton is rigidly oriented and uniformly height-normalized before averaging; a final uniform scale restores the common extent. No smoothing or decimation.',
                'normalization': {'targetHeightM': height, 'kind': 'Skull-to-foot skeletal extent',
                                  'note': f'Both means have {height:.2f} m skull-to-foot skeletal extent. This is a display normalization, not living stature.'},
                'coordinates': {'units': 'meters', 'x': 'anatomical left', 'y': 'superior', 'z': 'anterior'},
                'models': models, 'structures': structures, 'limitations': limitations}
    (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (ROOT / 'reports').mkdir(exist_ok=True)
    (ROOT / 'reports/generation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'models': models, 'vertices': report['sourceVerticesPerSkeleton'], 'triangles': report['sourceTrianglesPerSkeleton']}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--height', type=float, default=1.7, help='Common skull-to-foot skeletal extent in meters (not living stature)')
    build(parser.parse_args().height)
