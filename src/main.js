import './style.css';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const $ = (id) => document.getElementById(id);
const ui = {
  viewport: $('viewport'), host: $('canvas-host'), labels: $('model-labels'),
  panel: $('load-panel'), title: $('load-title'), message: $('load-message'),
  status: $('viewer-status'), search: $('structure-search'), list: $('structure-list'),
  count: $('structure-count'), hide: $('toggle-visibility'), isolate: $('isolate'),
  resetVisibility: $('reset-visibility'),
};
const state = {
  manifest: null, structures: new Map(), models: new Map(), mode: 'compare',
  selected: null, hidden: new Set(), isolated: null, failures: [], ready: false,
};
let renderer;
let scene;
let camera;
let controls;
let framePending = false;
let framingBox;
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const MODEL_IDS = ['female', 'male'];
// Render both sides of source faces; this does not repair source winding defects.
const boneMaterial = new THREE.MeshStandardMaterial({ color: '#e4dbc9', roughness: .77, metalness: 0, side: THREE.DoubleSide });
const selectedMaterial = new THREE.MeshStandardMaterial({ color: '#5caaa0', roughness: .72, metalness: 0, side: THREE.DoubleSide });
const number = new Intl.NumberFormat(undefined, { maximumFractionDigits: 3 });
const assetURL = (path) => new URL(path, new URL(import.meta.env.BASE_URL, document.baseURI)).href;

function requestRender() {
  if (framePending || !renderer) return;
  framePending = true;
  requestAnimationFrame(() => {
    framePending = false;
    const width = ui.viewport.clientWidth;
    const height = ui.viewport.clientHeight;
    if (state.ready && state.mode === 'compare') {
      // Independent viewports share one camera: side views must not occlude each other.
      renderer.setScissorTest(true);
      for (const model of state.models.values()) model.root.visible = false;
      MODEL_IDS.forEach((id, index) => {
        const model = state.models.get(id);
        model.root.visible = true;
        renderer.setViewport(index * width / 2, 0, width / 2, height);
        renderer.setScissor(index * width / 2, 0, width / 2, height);
        renderer.render(scene, camera);
        model.root.visible = false;
      });
      for (const model of state.models.values()) model.root.visible = true;
    } else {
      renderer.setScissorTest(false);
      renderer.setViewport(0, 0, width, height);
      renderer.render(scene, camera);
    }
  });
}

function setStatus(message, error = false) {
  ui.status.textContent = message;
  ui.status.classList.toggle('is-error', error);
}

function showFailure(title, message) {
  ui.panel.hidden = false;
  ui.panel.classList.add('is-error');
  ui.title.textContent = title;
  ui.message.textContent = message;
  $('retry-load').hidden = false;
  ui.viewport.setAttribute('aria-busy', 'false');
  if (!state.manifest) {
    $('cohort-note').textContent = 'Source information is unavailable. No substitute geometry is shown.';
    $('source-note').textContent = 'The source manifest could not load. Reload the atlas or consult the repository below.';
    ui.count.textContent = 'Structure index unavailable until the manifest loads';
  }
  setStatus(message, true);
}

function createRenderer() {
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor('#e5ebef');
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.1;
  renderer.domElement.tabIndex = 0;
  renderer.domElement.setAttribute('aria-label', 'Interactive skeleton. Arrow keys orbit; plus and minus zoom. Use the structure list to select bones without a pointer.');
  renderer.domElement.setAttribute('aria-describedby', 'camera-help viewer-status');
  ui.host.append(renderer.domElement);
  scene = new THREE.Scene();
  camera = new THREE.OrthographicCamera(-1, 1, 1, -1, .01, 100);
  camera.position.set(0, .85, 5);
  scene.add(new THREE.HemisphereLight('#ffffff', '#8799a6', 2.5));
  const key = new THREE.DirectionalLight('#fff6e6', 3.1);
  key.position.set(-3, 5, 5);
  scene.add(key);
  const fill = new THREE.DirectionalLight('#e3efff', 1.8);
  fill.position.set(3, 2, -4);
  scene.add(fill);
  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = false;
  controls.enablePan = true;
  controls.screenSpacePanning = true;
  controls.minZoom = .5;
  controls.maxZoom = 12;
  controls.target.set(0, .85, 0);
  controls.addEventListener('change', requestRender);
  renderer.domElement.addEventListener('webglcontextlost', (event) => {
    event.preventDefault();
    showFailure('The 3D view was interrupted', 'Your browser lost its graphics context. Reload the atlas to restore the viewer.');
  });
  renderer.domElement.addEventListener('keydown', keyboardCamera);
  let pointerStart = null;
  let dragged = false;
  renderer.domElement.addEventListener('pointerdown', (event) => {
    if (pointerStart) dragged = true;
    else { pointerStart = { x: event.clientX, y: event.clientY, id: event.pointerId }; dragged = false; }
  });
  renderer.domElement.addEventListener('pointermove', (event) => {
    if (pointerStart && Math.hypot(event.clientX - pointerStart.x, event.clientY - pointerStart.y) > 5) dragged = true;
  });
  renderer.domElement.addEventListener('pointercancel', () => { pointerStart = null; });
  renderer.domElement.addEventListener('pointerup', (event) => {
    if (pointerStart?.id === event.pointerId && !dragged && event.button === 0) pickBone(event);
    pointerStart = null;
  });
  new ResizeObserver(resize).observe(ui.viewport);
  resize();
}

function keyboardCamera(event) {
  if (!state.ready) return;
  const delta = .12;
  const spherical = new THREE.Spherical().setFromVector3(camera.position.clone().sub(controls.target));
  switch (event.key) {
    case 'ArrowLeft': spherical.theta -= delta; break;
    case 'ArrowRight': spherical.theta += delta; break;
    case 'ArrowUp': spherical.phi = Math.max(.05, spherical.phi - delta); break;
    case 'ArrowDown': spherical.phi = Math.min(Math.PI - .05, spherical.phi + delta); break;
    case '+': case '=': camera.zoom = Math.min(controls.maxZoom, camera.zoom * 1.15); break;
    case '-': case '_': camera.zoom = Math.max(controls.minZoom, camera.zoom / 1.15); break;
    case 'Home': setView('front'); event.preventDefault(); return;
    default: return;
  }
  event.preventDefault();
  camera.position.copy(controls.target).add(new THREE.Vector3().setFromSpherical(spherical));
  camera.updateProjectionMatrix();
  controls.update();
  requestRender();
}

function resize() {
  const width = ui.viewport.clientWidth;
  const height = ui.viewport.clientHeight;
  if (!renderer || !width || !height) return;
  renderer.setSize(width, height);
  const size = framingBox?.getSize(new THREE.Vector3()) || new THREE.Vector3(1, 1.7, .5);
  const columns = state.mode === 'compare' && state.models.size === 2 ? 2 : 1;
  const aspect = width / columns / height;
  const halfHeight = Math.max(size.y / 2, Math.max(size.x, size.z) / (2 * aspect)) * 1.25;
  camera.top = halfHeight;
  camera.bottom = -halfHeight;
  camera.left = -halfHeight * aspect;
  camera.right = halfHeight * aspect;
  camera.updateProjectionMatrix();
  requestRender();
}

function setView(view) {
  if (!framingBox) return;
  framingBox.getCenter(controls.target);
  const offset = view === 'back' ? [0, 0, -5] : view === 'side' ? [5, 0, 0] : [0, 0, 5];
  camera.position.copy(controls.target).add(new THREE.Vector3(...offset));
  camera.up.set(0, 1, 0);
  camera.zoom = 1;
  camera.updateProjectionMatrix();
  controls.update();
  requestRender();
}

function setMode(mode) {
  if (mode === 'compare' && state.models.size !== 2) return;
  if (mode !== 'compare' && !state.models.has(mode)) return;
  state.mode = mode;
  for (const [id, model] of state.models) {
    model.root.visible = mode === 'compare' || mode === id;
    model.label.hidden = !model.root.visible;
    model.root.position.x = -model.centerX;
    model.label.style.left = mode === 'compare' ? (id === 'female' ? '25%' : '75%') : '50%';
  }
  framingBox = new THREE.Box3();
  for (const model of state.models.values()) {
    if (model.root.visible) framingBox.union(new THREE.Box3().setFromObject(model.root));
  }
  document.querySelectorAll('[data-mode]').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.mode === mode)));
  resize();
  setView('front');
  updateSelection();
  const names = [...state.models.values()].filter((model) => model.root.visible).map((model) => model.meta.label).join(' and ');
  setStatus(`${names}. ${mode === 'compare' ? 'Shared camera and structure selection.' : 'Select a bone to inspect.'}${state.failures.length ? ` Unavailable: ${state.failures.join(', ')}. Reload to retry.` : ''}`, state.failures.length > 0);
}

function structureId(object) {
  let node = object;
  while (node) {
    if (state.structures.has(node.name)) return node.name;
    node = node.parent;
  }
  return null;
}

function pickBone(event) {
  if (!state.ready) return;
  const rect = renderer.domElement.getBoundingClientRect();
  const columnWidth = state.mode === 'compare' ? rect.width / 2 : rect.width;
  const column = state.mode === 'compare' && event.clientX - rect.left >= columnWidth ? 1 : 0;
  pointer.set(((event.clientX - rect.left - column * columnWidth) / columnWidth) * 2 - 1, -((event.clientY - rect.top) / rect.height) * 2 + 1);
  raycaster.setFromCamera(pointer, camera);
  const meshes = [];
  for (const [id, model] of state.models) {
    if (state.mode === 'compare' && id !== MODEL_IDS[column]) continue;
    if (model.root.visible) for (const mesh of model.meshes) if (mesh.visible) meshes.push(mesh);
  }
  const hit = raycaster.intersectObjects(meshes, false)[0];
  if (hit) selectStructure(hit.object.userData.structureId, true);
}

function selectStructure(id, revealInList = false) {
  if (!state.structures.has(id)) return;
  state.selected = id;
  if (revealInList) { ui.search.value = ''; renderStructureList(); }
  ui.list.value = id;
  updateVisibility();
}

function isVisible(id) {
  return !state.hidden.has(id) && (!state.isolated || state.isolated === id);
}

function updateVisibility() {
  for (const model of state.models.values()) {
    for (const mesh of model.meshes) {
      const id = mesh.userData.structureId;
      mesh.visible = isVisible(id);
      mesh.material = id === state.selected ? selectedMaterial : boneMaterial;
    }
  }
  for (const option of ui.list.options) {
    const structure = state.structures.get(option.value);
    option.textContent = `${structure.label}${isVisible(structure.id) ? '' : ' (hidden)'}`;
  }
  const hiddenCount = [...state.structures.keys()].filter((id) => !isVisible(id)).length;
  $('visibility-status').textContent = state.isolated ? `Isolating ${state.structures.get(state.isolated).label}` : hiddenCount ? `${hiddenCount} structures hidden` : 'All structures visible';
  ui.resetVisibility.disabled = !state.ready || (!state.hidden.size && !state.isolated);
  updateSelection();
  requestRender();
}

function updateSelection() {
  const structure = state.structures.get(state.selected);
  ui.hide.disabled = !structure || !state.ready;
  ui.isolate.disabled = !structure || !state.ready;
  $('view-selection').disabled = !structure || !state.ready;
  if (!structure) return;
  $('selected-name').textContent = structure.label;
  $('inspector-selection').textContent = structure.label;
  $('selected-region').textContent = structure.region || 'Source-defined structure';
  const present = [...state.models.values()].filter((model) => model.ids.has(structure.id)).map((model) => model.meta.label);
  $('selected-detail').textContent = `${present.length ? `Present in: ${present.join(', ')}.` : 'Not present in the loaded geometry.'} ${isVisible(structure.id) ? 'Visible' : 'Hidden'} in the current visibility settings. Names follow the source; this is not a diagnostic label.`;
  ui.hide.textContent = isVisible(structure.id) ? 'Hide bone' : 'Show bone';
  ui.isolate.textContent = state.isolated === structure.id ? 'End isolation' : 'Isolate bone';
}

function renderStructureList() {
  const query = ui.search.value.trim().toLocaleLowerCase();
  const structures = [...state.structures.values()].filter((item) => `${item.label} ${item.region} ${item.id}`.toLocaleLowerCase().includes(query));
  const fragment = document.createDocumentFragment();
  for (const structure of structures) {
    const option = document.createElement('option');
    option.value = structure.id;
    option.textContent = `${structure.label}${isVisible(structure.id) ? '' : ' (hidden)'}`;
    fragment.append(option);
  }
  ui.list.replaceChildren(fragment);
  ui.list.value = state.selected || '';
  ui.count.textContent = `${structures.length} of ${state.structures.size} structures`;
  $('no-results').hidden = structures.length > 0;
  ui.list.hidden = structures.length === 0;
}

function populateProvenance(manifest) {
  const source = document.createElement('a');
  source.textContent = manifest.source.title;
  const sourceURL = new URL(manifest.source.url);
  if (!['https:', 'http:'].includes(sourceURL.protocol)) throw new Error('The source link is not a web URL.');
  source.href = sourceURL.href;
  source.target = '_blank';
  source.rel = 'noreferrer';
  $('source-note').replaceChildren('Source: ', source, `. Upstream license: ${manifest.source.license}.`);
  $('model-license').textContent = manifest.license;
  $('method-note').textContent = `Method: ${manifest.method}`;
  $('normalization-note').textContent = manifest.normalization.note;
  $('height-note').textContent = `${number.format(manifest.normalization.targetHeightM)} m target skeletal height · not living stature`;
  $('cohort-note').textContent = `${manifest.models.map((model) => `${model.label}: ${number.format(model.subjects)} subjects`).join('; ')}. Source: ${manifest.source.title}.`;
  for (const model of manifest.models) {
    const row = document.createElement('tr');
    for (const value of [model.label, model.subjects, model.structures, `${number.format(model.heightM)} m`, model.reviewStatus]) {
      const cell = document.createElement('td');
      cell.textContent = value;
      row.append(cell);
    }
    $('model-metadata').append(row);
  }
  for (const limitation of manifest.limitations || []) {
    const item = document.createElement('li');
    item.textContent = limitation;
    $('limitations').append(item);
  }
}

async function loadModel(meta) {
  const gltf = await new GLTFLoader().loadAsync(assetURL(meta.url));
  const root = gltf.scene;
  const meshes = [];
  const ids = new Set();
  const oldMaterials = new Set();
  root.traverse((node) => {
    if (!node.isMesh) return;
    const id = structureId(node);
    if (!id) throw new Error(`${meta.label}: mesh ${node.name || '(unnamed)'} has no matching structure in the manifest.`);
    meshes.push(node);
    ids.add(id);
    node.userData.structureId = id;
    (Array.isArray(node.material) ? node.material : [node.material]).forEach((material) => oldMaterials.add(material));
    node.material = boneMaterial;
  });
  if (!meshes.length) throw new Error(`${meta.label} contains no bone meshes.`);
  oldMaterials.forEach((material) => material.dispose());
  const bounds = new THREE.Box3().setFromObject(root);
  const center = bounds.getCenter(new THREE.Vector3());
  const label = document.createElement('span');
  label.className = 'model-label';
  label.textContent = meta.label;
  label.hidden = true;
  ui.labels.append(label);
  root.visible = false;
  scene.add(root);
  state.models.set(meta.id, { root, meshes, ids, meta, centerX: center.x, label });
}

async function initialize() {
  let manifest;
  try {
    const response = await fetch(assetURL('models/manifest.json'));
    if (!response.ok) throw new Error(`Manifest request returned HTTP ${response.status}.`);
    manifest = await response.json();
    if (!Array.isArray(manifest.structures) || !manifest.structures.length || !Array.isArray(manifest.models) || !manifest.models.length) throw new Error('The manifest must contain structures and model entries.');
    state.manifest = manifest;
    state.structures = new Map([...manifest.structures].sort((a, b) => a.label.localeCompare(b.label)).map((item) => [item.id, item]));
    populateProvenance(manifest);
    renderStructureList();
    ui.search.disabled = false;
  } catch (error) {
    showFailure('Model information could not load', `${error.message} Check that models/manifest.json is deployed with the atlas, then reload.`);
    return;
  }
  try {
    createRenderer();
  } catch (error) {
    showFailure('3D rendering is unavailable', 'This browser could not start WebGL. Enable hardware acceleration or try another browser. Source information and the structure list remain available.');
    ui.list.disabled = false;
    return;
  }
  ui.message.textContent = 'Loading source-derived bone geometry. Large models may take a moment.';
  let settledModels = 0;
  const outcomes = await Promise.allSettled(manifest.models.map(async (meta) => {
    try {
      await loadModel(meta);
    } finally {
      settledModels += 1;
      ui.message.textContent = `${settledModels} of ${manifest.models.length} model requests finished. Preparing source-derived geometry…`;
    }
  }));
  outcomes.forEach((outcome, index) => {
    if (outcome.status === 'rejected') {
      state.failures.push(manifest.models[index].label);
      console.error(`Could not load ${manifest.models[index].id}`, outcome.reason);
    }
  });
  if (!state.models.size) {
    showFailure('Skeleton geometry could not load', 'No model could be opened. Check your connection and that the GLB files match the manifest, then reload. Source information remains available below.');
    ui.list.disabled = false;
    return;
  }
  state.ready = true;
  ui.panel.hidden = true;
  ui.viewport.setAttribute('aria-busy', 'false');
  ui.list.disabled = false;
  document.querySelectorAll('[data-mode]').forEach((button) => {
    button.disabled = button.dataset.mode === 'compare' ? state.models.size !== 2 : !state.models.has(button.dataset.mode);
    button.title = button.disabled ? 'This view requires model geometry that could not load. Reload models to retry.' : '';
  });
  document.querySelectorAll('[data-view]').forEach((button) => { button.disabled = false; });
  updateVisibility();
  $('retry-models').hidden = state.failures.length === 0;
  setMode(state.models.size === 2 ? 'compare' : state.models.has('female') ? 'female' : 'male');
}

ui.search.addEventListener('input', renderStructureList);
ui.list.addEventListener('change', () => selectStructure(ui.list.value));
ui.hide.addEventListener('click', () => {
  if (!state.selected) return;
  if (isVisible(state.selected)) state.hidden.add(state.selected);
  else {
    state.hidden.delete(state.selected);
    if (state.isolated && state.isolated !== state.selected) state.isolated = null;
  }
  updateVisibility();
});
ui.isolate.addEventListener('click', () => {
  if (!state.selected) return;
  state.isolated = state.isolated === state.selected ? null : state.selected;
  state.hidden.delete(state.selected);
  updateVisibility();
});
ui.resetVisibility.addEventListener('click', () => {
  state.hidden.clear();
  state.isolated = null;
  updateVisibility();
});
document.querySelectorAll('[data-mode]').forEach((button) => button.addEventListener('click', () => setMode(button.dataset.mode)));
document.querySelectorAll('[data-view]').forEach((button) => button.addEventListener('click', () => setView(button.dataset.view)));
$('retry-load').addEventListener('click', () => window.location.reload());
$('retry-models').addEventListener('click', () => window.location.reload());
$('clear-search').addEventListener('click', () => {
  ui.search.value = '';
  renderStructureList();
  ui.search.focus();
});
const compactInspector = window.matchMedia('(max-width: 900px)');
const syncInspector = () => { $('inspector').open = !compactInspector.matches; };
syncInspector();
compactInspector.addEventListener('change', syncInspector);
$('view-selection').addEventListener('click', () => {
  if (!state.ready) return;
  if (compactInspector.matches) $('inspector').open = false;
  renderer.domElement.focus({ preventScroll: true });
  ui.viewport.scrollIntoView({ block: 'center' });
});
document.querySelector('.skip-link').addEventListener('click', (event) => {
  event.preventDefault();
  $('inspector').open = true;
  if (ui.search.disabled) $('structures-heading').scrollIntoView({ block: 'start' });
  else ui.search.focus();
});
document.querySelectorAll('a[href="#about"]').forEach((link) => link.addEventListener('click', () => {
  $('provenance').open = true;
}));
Object.defineProperty(window, '__atlas', {
  get: () => ({
    ready: state.ready, mode: state.mode, selected: state.selected,
    loadedModels: [...state.models.keys()], hidden: [...state.hidden], isolated: state.isolated,
    structures: state.structures.size, failures: [...state.failures],
    meshes: Object.fromEntries([...state.models].map(([id, model]) => [id, model.meshes.length])),
    visibleMeshes: Object.fromEntries([...state.models].map(([id, model]) => [id, model.root.visible ? model.meshes.filter((mesh) => mesh.visible).length : 0])),
  }),
});
initialize();
