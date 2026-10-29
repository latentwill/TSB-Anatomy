# TSB Anatomy design

## Direction

This is an Operate surface: an anatomy inspection editor, not a marketing page. The requested `leonxlnx/taste-skill` application workflow was read in full and executed locally. `draw.mjs --app` offered Achromatic ledger and Framed sheet; **Framed sheet**, seed **27220256**, was selected for sustained geometry inspection with a searchable structure palette. No redraws. Palette and type were explicitly kept from the existing brief.

The style's move is one cool, tinted L-frame around a white inset work sheet, with 16px corners, an 8px window inset, and no shadow. The actual 3D field keeps the brief's slate background inside that sheet. Navigation is neutral; teal belongs chiefly to selected geometry. The chosen face is the cool anatomical inspection frame; the signature element is two source-derived skeleton means under one camera, at the same manifest-defined skeletal extent. This is not a generic dashboard with anatomy pasted into a card.

**First question:** How do the female and male source-derived skeletons compare at matched skeletal height? The dual-skeleton view therefore opens by default. **Finding:** matched skeletal extent is not living stature, and the geometry is not clinically validated. This evidence belongs beside the mode controls, not only in a footer.

Data/job inventory: (1) two sex-specific model entries; (2) manifest subject counts; (3) named structure IDs and labels; (4) anatomical regions; (5) real GLB meshes in meters; (6) normalized skeletal extent; (7) shared selected structure; (8) hidden and isolated structures; (9) source DOI and license; (10) review status and limitations. Users compare, search, select, orbit, hide, and isolate; selection must work by keyboard and on phones. No invented measurements, chart data, or illustrative anatomy are used.

## Tokens

| Role | Value |
| --- | --- |
| Canvas | `#e5ebef` |
| Interface surface | `#f5f7f8` |
| Primary ink | `#263b46` |
| Secondary ink | `#526872` |
| Sheet edge | `#dfe5e8` |
| Control divider | `#c6d1d7` |
| Selection teal | `#286e69` |
| Active chrome | `#e9edef` |
| Work sheet | `#ffffff` |
| Keyboard focus | `#176b83` |
| Error ink | `#873c2b` |
| Bone material | `#e4dbc9` |
| Selected bone material | `#5caaa0` |

The geometry uses physically lit Three.js standard materials. Its perceived colors vary with lighting, orientation, and tone mapping; CSS controls use the tokens directly.

## Type

Public Sans Variable remains bundled locally from its npm font package (`--keep palette,type`), not a remote-font fallback. One family serves controls and content. The compact product title is 20px/650, section headings 16px/600, ordinary controls 14px, and supporting metadata 12px. Mobile search and structure selection use 16px. Numeric table columns are right-aligned with tabular figures.

## Composition

```text
Identity / Skeleton atlas                       Sources & limitations
Structure search | Female / Male / Compare          Skeletal extent
Named bone list  | Manifest subject counts / source evidence
                 |                                              
Selected bone    |       Two real skeletons, one camera           
Visibility       |                                              
Source caveat    | Front / Back / Side / Reset      Input guidance
                 | Loading / availability status
Limitations summary                 Expandable method and provenance
```

Desktop grid arithmetic: 264px palette + flexible sheet + 8px outer inset = window width; at 1440px the sheet is 1168px wide. The header is 48px and shares the frame ground without a dividing rule. Sheet internals use a 24px alignment gutter. The camera controls sit outside the viewport rather than occluding feet. At 900px and below the inspector becomes an inline native disclosure above the full-width viewer; it starts closed and its summary names the selected bone. Search, selection and visibility remain available without a modal. An explicit “View selected bone” action returns focus to the canvas and closes the mobile inspector.

## Interaction

Selecting a name or mesh colors the corresponding structure in every loaded example. Comparison uses two independent scissored viewports with one orthographic camera: rotation and zoom are shared, but neither skeleton can occlude the other in side views. Labels remain over their own viewport, and picking is mapped into the clicked viewport. Front faces anterior +Z; back looks from −Z; side looks from +X. Changing displayed examples reframes them; hiding and isolating bones preserve the camera. Show all structures restores visibility without discarding selection.

Pointer drag orbits; scroll or pinch zooms; OrbitControls supports pan. With canvas focus, arrow keys orbit, plus/minus zoom, and Home restores the front view. The searchable native selector is the equivalent non-pointer path to selecting geometry. Rendering is requested only for changes, loads, resize, or input; there is no continuous idle animation.

## States and source truth

Loading and fatal failures appear within the viewer with an explicit reload action and real per-model completion text, not simulated percentage progress. Partial model failures keep the successful example available, disable unavailable modes with explanatory titles, and provide a reload action in the status strip. Manifest-derived subject counts and source identity sit beside the viewing controls; review statuses, method, normalization note, and limitations appear in the provenance disclosure. Source links open that disclosure. Search has a count, a readable empty state and a clear-search action. Geometry is never replaced by a placeholder skeleton.

Bone materials render both sides of source faces so known upstream winding defects do not silently cull visible anatomy. This rendering choice does not repair or validate the source topology; the generation manifest remains the authority for measured defects.

## Ownership and inspection

Implementation lives in index.html, src/main.js, and src/style.css. Data generation, licensing prose, and scientific assessment are separate concerns. Production-build browser checks covered the actual generated assets; the scope is interface behavior and geometry-file integrity, not anatomical or clinical validation.

## Taste workflow provenance

Commands executed from the repository root:

Skill revision: `12af471f627f866411b4bd785b19646d3672784c`. To reproduce the local skill checkout, run `gh repo clone leonxlnx/taste-skill .scratch/taste-skill`, then `git -C .scratch/taste-skill checkout 12af471f627f866411b4bd785b19646d3672784c`. The skill is a development tool, not a runtime dependency.

```sh
node .scratch/taste-skill/skills/taste-skill/scripts/draw.mjs --app --list kinds
node .scratch/taste-skill/skills/taste-skill/scripts/draw.mjs --app --kind builder --brief "TSB Anatomy: inspect real source-derived female and male skeleton means at matched skeletal height, with linked bone selection and transparent provenance" --screens builder,detail --theme light --keep palette,type --options 3
node .scratch/taste-skill/skills/taste-skill/scripts/draw.mjs --app --kind builder --brief "TSB Anatomy: inspect real source-derived female and male skeleton means at matched skeletal height, with linked bone selection and transparent provenance" --screens builder,detail --theme light --keep palette,type --style framed-sheet
```

The sheet is recorded in `.taste-skill/direction.json`. The builder pattern supplies the palette/canvas relationship; the detail pattern supplies neutral mode tabs and evidence beside inspection. Graph nodes, KPIs and charts were not transplanted because the actual objects are anatomical meshes, not a graph or an analytics report. The clinical and normalization caveats are product constraints, not sample copy. No sample data needs replacement.

## Verification and critique

Production inspection: `node .scratch/taste-skill/skills/taste-skill/scripts/inspect.mjs --app http://127.0.0.1:5183/`. Final measured result: **0 failures, 0 warnings** at 1440px, 768px and 390px. Reports and screenshot sheets are retained in `.taste-skill/inspect/`. The earlier dev-server warning was resolved by inspecting the built preview. Vite still reports its standard >500 kB chunk advisory for the Three.js bundle; it was not suppressed.

An additional static Impeccable detector reported a flat-type warning using 16px for every role. The actual browser measurements are 20px product title and 14px body; this warning is not representative of the loaded CSS. The app deliberately avoids a marketing-scale heading.

Browser smoke: both models load with 182 meshes and no runtime errors; both viewport picking paths select the skull; search, empty search/clear, shared selection, hide (181 visible), isolate (1 visible), restore (182 visible), female/male modes, front/back/side/reset, keyboard orbit/zoom, and mobile inspector return were exercised. A deliberately failed male GLB request leaves the female model usable, disables male/comparison modes and exposes reload. At 390px there is no horizontal document overflow.

ROUND 2 — final app-screen review

Seen in one second: two source-derived skeletons, ready to compare.

Idea: a common skeletal extent and synchronized views turn the two cohort means into a direct anatomical comparison.

Live thing: selecting a real bone highlights the corresponding structure in both examples.

Layout words by section: shell=frame / workspace=paired canvas / inspector=index / evidence=disclosure.

Scores (subjective interface assessment): design 7.5 · usability 8 · creativity 7 · content 9 → overall 7.7.

Caps applied: app-screen rules apply; marketing requirements for photographs, large hero type and automatic motion do not apply to an anatomical inspection editor.

Top three observed problems and resolutions:

1. Side comparison previously overlapped the skeletons and labels. Independent viewports now preserve both examples at every camera angle; confirmed in the production browser.
2. Model labels crowded each other at tablet width. Separate viewport-centered labels now remain distinct in the final tablet screenshot.
3. Hiding the mobile caption's line break joined adjacent words. Explicit whitespace now preserves the sentence boundary.

Remaining tradeoff: both detailed GLBs load initially (about 42 MB total); no claim of performance on physical low-end mobile hardware is made. The source's flexed-arm pose and known mesh defects remain visible scientific limitations, not styling defects to conceal.
