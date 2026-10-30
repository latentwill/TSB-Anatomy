# Attribution and license scope

TSB-Anatomy is an independent adaptation, not an official OpenSkeleton release. No endorsement by the source creators or their institutions is implied.

## Which license applies?

| Material | License |
| --- | --- |
| TSB-Anatomy's derived model assets, including `public/models/*.glb`, original atlas metadata such as `public/models/manifest.json`, and project prose/documentation | **Creative Commons Attribution-ShareAlike 4.0 International** (`CC-BY-SA-4.0`), full text in [LICENSE](LICENSE) |
| Original software: `src/`, `scripts/`, HTML/CSS/JavaScript, package/project configuration, lockfiles, and GitHub workflow/issue-form configuration | **MIT** (`MIT`), full text in [LICENSE-CODE](LICENSE-CODE) |
| Unmodified OpenSkeleton data and copied upstream descriptive metadata, including the preserved Zenodo record in `sources/` | **Creative Commons Attribution 4.0 International** (`CC-BY-4.0`), as declared by the upstream record; [legal text](https://creativecommons.org/licenses/by/4.0/legalcode.en) |
| Third-party dependencies or other separately attributed material | Their respective upstream licenses; neither project license replaces those terms |

The ShareAlike license applies to this project's copyrightable contributions to its adapted atlas, not retroactively to the upstream OpenSkeleton dataset. Attribution obligations for the underlying CC BY work continue to apply. Raw source data downloaded for generation remains upstream material, whether or not committed to this repository. License texts retain their own legal status; this scope table does not modify either standard license. Facts and other material outside applicable copyright or similar rights are not made exclusive by these notices.

Copyright in original TSB-Anatomy contributions: © 2026 TSB-Anatomy contributors.

## Upstream dataset

**Title:** OpenSkeleton: Open, Sex-Specific Full-Body Skeletal dataset for Statistical Shape Modeling  
**Creators, in the order listed by Zenodo:** Kate Duquesne; BioCAT; Thibau Destryker; Veerle Segers; Emmanuel Audenaert.  
**Publication date:** September 18, 2026.  
**Version-specific DOI:** [10.5281/zenodo.22833546](https://doi.org/10.5281/zenodo.22833546).  
**Record:** [Zenodo 22833546](https://zenodo.org/records/22833546).  
**Declared license:** [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Creator identifiers supplied by that record:

- Kate Duquesne: [0000-0003-4951-9738](https://orcid.org/0000-0003-4951-9738)
- Veerle Segers: [0000-0002-0740-3297](https://orcid.org/0000-0002-0740-3297)
- Emmanuel Audenaert: [0000-0001-5508-6743](https://orcid.org/0000-0001-5508-6743)

The preserved record is [`sources/openskeleton-22833546.json`](sources/openskeleton-22833546.json). Its description reports anatomically corresponding meshes from CT data of 102 subjects (51 female and 51 male), 182 skeletal structures, and source scans from the **New Mexico Decedent Image Database (NMDID)**. These are upstream dataset claims, not counts independently established by this attribution document and not a claim that every supplied structure is present in every exported atlas model.

## Adaptation and limitations

TSB-Anatomy's adaptation consists of **sex-stratified averaging** of corresponding skeletal geometry, **documented uniform height normalization** for comparison, and **post-average rigid arm articulation** into an arms-at-sides display pose, exported as named meshes with shoulder/elbow/wrist transform nodes. The original source-pose means remain in the float64 NPZ references. Estimated joint pivots and rest/posed matrices are recorded; they are not validated anatomical landmarks. Exact inclusion/exclusion counts, correspondence checks, processing order, coordinate transforms, target height, and additional changes are documented by the generation pipeline, README, and model manifest.

Female/male grouping follows the source's recorded sex categories; the atlas does not infer gender identity. A cohort mean is not an individual specimen or a universal anatomical ideal. Uniformly matching displayed skeletal height is not a measurement of living stature and does not establish population representativeness. Averaging may obscure individual variation, asymmetry, pathology, or segmentation/registration artifacts. A mean shape is not guaranteed to be anatomically correct merely because its inputs have corresponding vertices.

**The derived atlas has not been clinically validated.** It is a reference/visualization resource, not a validated diagnostic, treatment, surgical-planning, or measurement tool. Review labels record the scope of documented review; they do not imply medical certification. These statements describe limitations, not additional restrictions on the permissions granted by the licenses. Both standard licenses contain warranty and liability disclaimers.

The upstream Zenodo record establishes the declared dataset license and credited creators. This project does not independently establish the original NMDID scan consent, the complete rights chain, or additional upstream acknowledgments that may accompany source files. Do not assume that the license for these released meshes grants access to, or relicenses, the original CT scans. Preserve any additional applicable notices supplied with source material, and report a provenance concern through an issue.

## Reusing the atlas

A concise attribution suitable for a credits panel or accompanying file is:

> TSB-Anatomy, by TSB-Anatomy contributors, https://github.com/latentwill/TSB-Anatomy, licensed CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/). Adapted from OpenSkeleton: Open, Sex-Specific Full-Body Skeletal dataset for Statistical Shape Modeling, by Kate Duquesne, BioCAT, Thibau Destryker, Veerle Segers, and Emmanuel Audenaert, https://doi.org/10.5281/zenodo.22833546, licensed CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Changes include sex-stratified averaging, uniform height normalization, rigid arm articulation using estimated joint pivots, and named-mesh GLB export. The derived atlas is not clinically validated.

Retain applicable source attribution, license links, warranty notices, and indications of prior changes. Identify your own modifications when sharing them. Share adaptations of this project's CC BY-SA material under the terms permitted by that license, without adding legal or technological restrictions prohibited by it. Reusing only the MIT software does not relicense the model assets as MIT. See the full legal texts for binding terms.

## Standard legal text sources

- `LICENSE`: complete SPDX `CC-BY-SA-4.0` text from [spdx/license-list-data](https://github.com/spdx/license-list-data/blob/main/text/CC-BY-SA-4.0.txt); [official Creative Commons legal code](https://creativecommons.org/licenses/by-sa/4.0/legalcode.en).
- `LICENSE-CODE`: complete SPDX `MIT` text from [spdx/license-list-data](https://github.com/spdx/license-list-data/blob/main/text/MIT.txt), with its copyright placeholder filled for this project.

## Design workflow

The viewer was developed with [Taste Skill](https://github.com/leonxlnx/taste-skill), revision `12af471f627f866411b4bd785b19646d3672784c`, copyright © 2026 Leonxlnx, MIT licensed. Library-derived direction material in `.taste-skill/direction.json` retains that MIT notice; see [LICENSES/taste-skill-MIT.txt](LICENSES/taste-skill-MIT.txt). The development skill is not bundled into the viewer. Its use does not change the anatomical assets' licenses.
