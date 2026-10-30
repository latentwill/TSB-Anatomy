# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Vite, vanilla JavaScript, and Three.js, as specified in the implementation brief. Static hosting, including the GitHub project Pages path, must work without a backend. Dependencies are installed with npm and locked in package-lock.json.

## Product Purpose

TSB Anatomy is a standalone open skeleton atlas for inspecting source-derived female and male skeletal examples. Users can compare examples at matched displayed skeletal height, find named bones, inspect selection, and hide or isolate structures.

## Users

The confirmed job is practical anatomy inspection and reuse of open geometry. A narrower audience and clinical use are not established; the viewer must not claim clinical validation.

## Capabilities and Constraints

- Consume the generated manifest and real GLB geometry in public/models; do not invent anatomy or substitute illustrative assets.
- Female, male, and side-by-side comparison share a camera and structure selection. Comparison is the initial view when both real models load; a single successful model remains usable if the other fails.
- Models use meters, Y-up, an invisible support reference at Y=0, and anterior +Z. No earth plane, floor outline or cast shadows are rendered. The manifest, rather than interface copy, supplies population counts, review status, height, and methodological limitations.
- Matching skeletal height is not a measurement of living stature.
- Tooling is MIT; derived model assets are CC BY-SA 4.0 with attribution to the upstream CC BY 4.0 OpenSkeleton source.
- No paid services or paid generation; no modification to the separate thespiritualbody project.

## Brand Commitments

A practical, viewer-led inspection surface rather than a promotional landing page. The brief specifies cool slate canvas, warm ivory actual bone geometry, muted teal selection, readable sans typography, a narrow structure sidebar, and responsive controls. The user-requested `leonxlnx/taste-skill` app workflow supplies the Framed sheet direction: quiet tinted frame, white inset work sheet, neutral navigation, and real anatomical geometry as the dominant content. Palette and locally bundled Public Sans are preserved explicitly by the draw's keep flags.

## Evidence on Hand

The parent generation workflow supplies public/models/manifest.json, female.glb, and male.glb. The source record is OpenSkeleton, DOI 10.5281/zenodo.22833546. Source metadata and geometry are owned by that workflow; the viewer does not establish correspondence, population representativeness, or medical accuracy.

## Product Principles

- Let the actual geometry lead, with selection and visibility controls close to it.
- Keep provenance, normalization, and review caveats discoverable beside inspection.
- Treat unavailable geometry as an explicit failure, never a reason to show fabricated anatomy.
- Make structure selection possible without pointing at the 3D canvas.

## Accessibility & Inclusion

Search and a native named-structure selector provide keyboard access to selection. Camera presets and canvas keyboard controls supplement pointer orbit. The inspector folds into a native disclosure on tablets and phones; an explicit return-to-view action keeps selection and visibility available without a modal. Visible focus, mobile sizing, honest load/error states, readable contrast, and on-demand rendering are required. No remote font requests or invented loading percentages.
