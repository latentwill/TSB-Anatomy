import * as THREE from 'three';

const JOINT_PARENTS = new Map([['stance', 'world']]);
for (const side of ['L', 'R']) {
  for (const [joint, parent] of [
    ['girdle', 'stance'], ['shoulder', 'girdle'], ['elbow', 'shoulder'],
    ['wrist', 'elbow'], ['hip', 'stance'], ['knee', 'hip'], ['ankle', 'knee'],
  ]) {
    JOINT_PARENTS.set(`${joint}_${side}`, parent === 'stance' ? parent : `${parent}_${side}`);
  }
}

function incompatible(message) {
  return new Error(`Incompatible anatomy rig: ${message}`);
}

function readMatrix(value, label) {
  const entries = Array.isArray(value) && value.length === 4
    && value.every((row) => Array.isArray(row) && row.length === 4)
    ? value.flat() : value;
  if (!Array.isArray(entries) || entries.length !== 16 || !entries.every(Number.isFinite)) {
    throw incompatible(`${label} must contain a finite row-major 4 × 4 matrix.`);
  }
  if (entries[12] !== 0 || entries[13] !== 0 || entries[14] !== 0 || entries[15] !== 1) {
    throw incompatible(`${label} must be an affine matrix.`);
  }
  // The report uses row-major arrays; Three.js stores column-major elements.
  const matrix = new THREE.Matrix4().fromArray(entries).transpose();
  if (Math.abs(matrix.determinant()) < 1e-12) {
    throw incompatible(`${label} must be invertible.`);
  }
  return matrix;
}

function isDescendant(node, root) {
  for (let ancestor = node; ancestor; ancestor = ancestor.parent) {
    if (ancestor === root) return true;
  }
  return false;
}

function isVisible(node) {
  for (let ancestor = node; ancestor; ancestor = ancestor.parent) {
    if (!ancestor.visible) return false;
  }
  return true;
}

/** Bind saved poses and read-only landmark overlays to an exported GLB hierarchy. */
export function createRigView(root, meshes, rig) {
  if (!root?.isObject3D || !Array.isArray(rig?.joints) || rig.joints.length !== JOINT_PARENTS.size) {
    throw incompatible('expected a scene root and all 15 saved joints.');
  }
  if (!Array.isArray(meshes) || !meshes.length || meshes.some((mesh) => (
    !mesh?.isMesh || mesh.isSkinnedMesh || mesh.isInstancedMesh || !mesh.geometry?.attributes.position
    || !isDescendant(mesh, root)
  ))) {
    throw incompatible('expected static bone meshes belonging to this scene.');
  }

  const nodes = new Map();
  root.traverse((node) => {
    if (!JOINT_PARENTS.has(node.name)) return;
    if (nodes.has(node.name)) throw incompatible(`duplicate joint node ${node.name}.`);
    nodes.set(node.name, node);
  });

  const joints = new Map();
  for (const data of rig.joints) {
    if (!data || !JOINT_PARENTS.has(data.id) || joints.has(data.id)) {
      throw incompatible('joint IDs must be unique and match the exported anatomy hierarchy.');
    }
    const node = nodes.get(data.id);
    const parent = JOINT_PARENTS.get(data.id);
    if (!node || node === root || data.parent !== parent || node.parent?.name !== parent) {
      throw incompatible(`missing or incorrectly parented joint ${data.id}; expected parent ${parent}.`);
    }
    if (!Array.isArray(data.sourcePivotM) || data.sourcePivotM.length !== 3
      || !data.sourcePivotM.every(Number.isFinite)) {
      throw incompatible(`${data.id} has no finite source pivot in meters.`);
    }
    joints.set(data.id, {
      node,
      standing: readMatrix(data.localMatrix, `${data.id}.localMatrix`),
      original: readMatrix(data.restLocalMatrix, `${data.id}.restLocalMatrix`),
    });
  }

  // Cache bone-only geometry bounds before adding any overlay objects.
  const bones = meshes.map((mesh) => {
    if (!mesh.geometry.boundingBox) mesh.geometry.computeBoundingBox();
    return { mesh, bounds: mesh.geometry.boundingBox.clone() };
  });
  const jointIds = [...joints.keys()].filter((id) => id !== 'stance');
  const markerGeometry = new THREE.SphereGeometry(0.009, 12, 8);
  const markerMaterial = new THREE.MeshBasicMaterial({
    color: 0xf4c66b, transparent: true, opacity: 0.95, depthTest: false, depthWrite: false,
  });
  const selectedMaterial = new THREE.MeshBasicMaterial({
    color: 0xfff3d6, transparent: true, opacity: 1, depthTest: false, depthWrite: false,
  });
  const markers = [];
  const overlays = [];
  for (const id of jointIds) {
    const overlay = new THREE.Group();
    overlay.name = `joint-overlay-${id}`;
    overlay.visible = false;
    const marker = new THREE.Mesh(markerGeometry, markerMaterial);
    marker.name = `joint-marker-${id}`;
    marker.userData.jointId = id;
    marker.renderOrder = 1000;
    overlay.add(marker);
    joints.get(id).node.add(overlay);
    markers.push(marker);
    overlays.push(overlay);
  }

  const axisGeometry = new THREE.BufferGeometry();
  axisGeometry.setAttribute('position', new THREE.Float32BufferAttribute([
    0, 0, 0, 0.055, 0, 0,
    0, 0, 0, 0, 0.055, 0,
    0, 0, 0, 0, 0, 0.055,
  ], 3));
  const colors = [];
  for (const hex of [0xa33f3f, 0x367447, 0x3268a8]) {
    const color = new THREE.Color(hex);
    colors.push(color.r, color.g, color.b, color.r, color.g, color.b);
  }
  axisGeometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
  const axisMaterial = new THREE.LineBasicMaterial({
    vertexColors: true, transparent: true, opacity: 1, depthTest: false, depthWrite: false,
  });
  const axes = new THREE.LineSegments(axisGeometry, axisMaterial);
  axes.name = 'selected-joint-local-axes';
  axes.renderOrder = 1002;
  axes.visible = false;

  const rootInverse = new THREE.Matrix4();
  const modelMatrix = new THREE.Matrix4();
  const vector = new THREE.Vector3();
  const boneBounds = new THREE.Box3();
  const candidates = [];
  const intersections = [];
  let overlayEnabled = false;
  let disposed = false;

  function applyPose(pose) {
    if (pose !== 'standing' && pose !== 'original') {
      throw new RangeError(`Unknown anatomy pose: ${pose}`);
    }
    if (disposed) return;
    for (const joint of joints.values()) {
      joint.node.matrixAutoUpdate = false;
      joint.node.matrix.copy(joint[pose]);
      joint.node.matrixWorldNeedsUpdate = true;
    }
    root.updateWorldMatrix(true, true);
  }

  function setOverlay(enabled, selectedId = null) {
    if (selectedId !== null && (!joints.has(selectedId) || selectedId === 'stance')) {
      throw new RangeError(`Unknown selectable joint: ${selectedId}`);
    }
    if (disposed) return;
    overlayEnabled = Boolean(enabled);
    for (let index = 0; index < markers.length; index += 1) {
      const marker = markers[index];
      const selected = marker.userData.jointId === selectedId;
      overlays[index].visible = overlayEnabled;
      marker.material = selected ? selectedMaterial : markerMaterial;
      marker.scale.setScalar(selected ? 1.5 : 1);
      marker.renderOrder = selected ? 1001 : 1000;
    }
    axes.removeFromParent();
    axes.visible = overlayEnabled && selectedId !== null;
    if (selectedId !== null) joints.get(selectedId).node.add(axes);
    root.updateWorldMatrix(true, true);
  }

  function pick(raycaster) {
    if (disposed || !overlayEnabled || !isVisible(root)) return null;
    root.updateWorldMatrix(true, true);
    candidates.length = 0;
    intersections.length = 0;
    for (const marker of markers) if (isVisible(marker)) candidates.push(marker);
    raycaster.intersectObjects(candidates, false, intersections);
    return intersections.length ? intersections[0].object.userData.jointId : null;
  }

  function getJoint(id) {
    const joint = joints.get(id);
    if (disposed || !joint) return null;
    root.updateWorldMatrix(true, true);
    // Remove viewer placement (and its ancestors), retaining the saved stance transform.
    rootInverse.copy(root.matrixWorld).invert();
    modelMatrix.multiplyMatrices(rootInverse, joint.node.matrixWorld);
    const position = vector.setFromMatrixPosition(modelMatrix).toArray();
    const directions = [];
    for (let index = 0; index < 3; index += 1) {
      directions.push(vector.setFromMatrixColumn(modelMatrix, index).normalize().toArray());
    }
    return { id, position, axes: directions };
  }

  function getBounds(target) {
    target.makeEmpty();
    if (disposed) return target;
    root.updateWorldMatrix(true, true);
    // Hidden bones still define framing; overlays never participate.
    for (const { mesh, bounds } of bones) {
      target.union(boneBounds.copy(bounds).applyMatrix4(mesh.matrixWorld));
    }
    return target;
  }

  function dispose() {
    if (disposed) return;
    disposed = true;
    axes.removeFromParent();
    for (const overlay of overlays) overlay.removeFromParent();
    markerGeometry.dispose();
    markerMaterial.dispose();
    selectedMaterial.dispose();
    axisGeometry.dispose();
    axisMaterial.dispose();
    candidates.length = 0;
    intersections.length = 0;
  }

  return { data: rig, jointIds, applyPose, setOverlay, pick, getJoint, getBounds, dispose };
}
