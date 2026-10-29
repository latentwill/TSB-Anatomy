"""Inspect source storage and geometric coverage without exporting personal metadata."""
import json
from pathlib import Path
from collections import Counter
import h5py
import numpy as np
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/22833546'


def describe(obj, depth=0):
    if isinstance(obj, h5py.Dataset):
        result = {'shape': list(obj.shape), 'dtype': str(obj.dtype)}
        if obj.dtype.kind in 'fiu' and obj.size:
            a = obj[()]
            result['min'] = float(np.nanmin(a))
            result['max'] = float(np.nanmax(a))
            if a.ndim == 2 and 3 in a.shape:
                points = a if a.shape[1] == 3 else a.T
                result['bounds'] = [points.min(axis=0).tolist(), points.max(axis=0).tolist()]
        return result
    names = list(obj.keys())
    return {'keys': names, 'sample': {name: describe(obj[name], depth+1) for name in names[:3]} if depth < 3 else {}}


def main():
    metadata = loadmat(RAW/'Metadata.mat', simplify_cells=True)['Metadata']
    faces = loadmat(RAW/'Faces.mat', simplify_cells=True)
    faces = {k:v for k,v in faces.items() if not k.startswith('__')}
    result = {'cohort': dict(Counter(x['sex_code'] for x in metadata.values())), 'faces': {}}
    for root, entries in faces.items():
        if isinstance(entries, dict):
            result['faces'][root] = {k: {'shape': list(v.shape), 'min': int(np.min(v)), 'max': int(np.max(v))} for k,v in entries.items()}
    with h5py.File(RAW/'NM_combined.mat','r') as data:
        result['root_keys'] = list(data.keys())
        result['geometry'] = describe(data['NM_combined'])
    out = ROOT/'reports/source-inventory.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
