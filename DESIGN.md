# TSB Anatomy design

## Direction

The supplied brief fixes the direction: an anatomy inspection surface whose real bone geometry is the dominant visual content. No decorative anatomy, generated imagery, promotional hero, or animation competes with it. The page is code-led, with an intentionally quiet control layer.

The composition was evaluated against a generic dashboard alternative: repeated cards and metric summaries would displace the actual skeleton and imply more statistical authority than the data warrants. Instead, one continuous slate viewing field sits beside a narrow searchable index. The only strong accent identifies actions and the selected bone.

## Tokens

| Role | Value |
| --- | --- |
| Canvas | `#e5ebef` |
| Interface surface | `#f5f7f8` |
| Primary ink | `#263b46` |
| Secondary ink | `#526872` |
| Divider | `#c6d1d7` |
| Action teal | `#286e69` |
| Selected control surface | `#dbeae6` |
| Keyboard focus | `#176b83` |
| Error ink | `#873c2b` |
| Bone material | `#e4dbc9` |
| Selected bone material | `#5caaa0` |

The geometry uses physically lit Three.js standard materials. Its perceived colors vary with lighting, orientation, and tone mapping; CSS controls use the tokens directly.

## Type

Public Sans Variable is bundled locally from its npm font package. A single sans family serves both controls and content. Main title: 1.2rem/650; section headings: 1rem/650; ordinary controls and supporting text: .8125rem. Small status and specimen labels use .75rem or .6875rem with adequate contrast. Mobile search and structure selection use 1rem to preserve legibility and avoid input zoom. Metadata tables use tabular numerals, not a decorative monospace face.

## Composition

```text
Identity                                  Sources & limitations
Structure search | Female / Male / Compare       Skeletal height
Named bone list  |                                             
                 |             Actual 3D geometry              
Selected bone    |                                             
Visibility       |          Front / Back / Side / Reset         
                 | Pointer guidance and load state             
Limitations summary             Expandable method and provenance
```

Desktop uses a 280px index and a flexible viewing field, expanding the index to 320px on wide screens. Controls and copy align left; specimen labels follow each model horizontally. At 640px and below the viewer comes first, followed by the searchable index and selection controls, then provenance. The 3D viewport remains tall enough for full skeleton inspection without forcing a tiny embedded frame.

## Interaction

Selecting a name or mesh colors the corresponding structure in every loaded example. Comparison uses a single orthographic camera so rotation and zoom are genuinely shared. Front faces anterior +Z; back looks from −Z; side looks from +X. Changing displayed examples reframes them; hiding and isolating bones preserve the camera. Show all structures restores visibility without discarding selection.

Pointer drag orbits; scroll or pinch zooms; OrbitControls supports pan. With canvas focus, arrow keys orbit, plus/minus zoom, and Home restores the front view. The searchable native selector is the equivalent non-pointer path to selecting geometry. Rendering is requested only for changes, loads, resize, or input; there is no continuous idle animation.

## States and source truth

Loading and fatal failures appear within the viewer with an explicit reload action. Partial model failures keep the successfully loaded example available, disable unavailable modes, and report the failure in the status line. Manifest-derived counts, review statuses, method, normalization note, and limitations appear under the provenance disclosure. Geometry is never replaced by a placeholder skeleton.

## Ownership and inspection

Implementation lives in index.html, src/main.js, and src/style.css. Data generation, licensing prose, and scientific assessment are separate concerns. Automated build and browser inspection are performed by the integrating parent after all assets land; this design record does not claim visual or clinical validation.
