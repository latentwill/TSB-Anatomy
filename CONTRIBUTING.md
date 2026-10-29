# Contributing

Anatomical corrections, clearer provenance, accessibility improvements, and reproducible software changes are welcome. An anatomical claim requires evidence; an attractive mesh or a successful build is not proof of correctness.

## Propose an anatomical correction

Open an [anatomical correction issue](https://github.com/latentwill/TSB-Anatomy/issues/new?template=anatomical-correction.yml) before submitting changed geometry. Include:

1. **Affected artifact:** commit/release, female or male model, and exact structure ID from `public/models/manifest.json` (also the GLB mesh node name). For a missing structure, provide the proposed anatomical name and neighboring IDs; for a global issue, explicitly say it affects all structures.
2. **Before and after:** describe the observed problem and proposed correction, with comparable views, orientation, landmarks, units, and measurements where relevant. Screenshots help locate the problem but do not replace a reproducible explanation. Identify whether the issue is in source geometry, averaging, coordinates/scale, labels, or viewer presentation.
3. **Anatomical evidence:** cite a stable URL/DOI, page/figure or other precise locator, and explain why it supports the correction. State uncertainty, conflicting evidence, and the population or specimen to which the reference applies. Do not upload restricted publications or identifiable medical data.
4. **Variation versus error:** explain why the finding is a labeling, segmentation, registration, or processing error rather than plausible specimen variation, asymmetry, age/sex/population variation, pathology, or an effect of averaging. If that distinction is unresolved, say so; unresolved reports are still useful.
5. **License provenance:** identify the creator, source URL, version, license, and changes for every proposed replacement mesh, diagram, image, or dataset. A citation is not permission to redistribute. For your own work, say it is original and identify any inputs or references. Do not submit assets with unknown or incompatible redistribution rights.

Do not reshape a cohort mean to match an individual reference without discussing the methodological implications. Report misleading height claims separately from mesh size errors: displayed skeletal height is not measured living stature.

## Implement a correction

- Fork the repository and use a focused branch; link the issue in the pull request.
- Prefer correcting the responsible source mapping or generation step and regenerating assets over hand-editing only an exported GLB. If a direct mesh correction is necessary, document how to reproduce it and why the pipeline cannot express it.
- Keep stable structure IDs where anatomically appropriate. Explain any intentional rename/removal and update affected metadata and references together.
- Include before/after evidence and the exact commands and inputs used. Record subject inclusion changes, transform/normalization changes, and expected effects on other structures or models. Do not present new cohort statistics without reproducible support.
- Update the model metadata and relevant documentation when a change affects provenance, limitations, generation, or interpretation. Retain source attribution and add any required new notices to [ATTRIBUTION.md](ATTRIBUTION.md).
- Use the repository's documented setup and checks. The viewer build workflow runs `npm ci` and `npm run build`; a successful build only establishes a software build result, not anatomy validation. Report which checks you actually ran, results, and any checks not run. Do not invent test commands or claim manual review you did not perform.

## Review is explicit, not automatic

A submitted issue, merged pull request, passing CI run, or contributor's clinical title does **not** automatically promote an asset to reviewed or clinically validated status.

Maintainers assess the evidence, provenance, effect on other structures, reproducibility, and whether the proposed change confuses natural variation with error. They may request domain-expert input or retain an unresolved report instead of changing the mesh. Anatomical review must be recorded in the linked issue/pull request with the reviewer, date, artifact/commit, structure scope, evidence considered, conclusion, and remaining limitations. A reviewer should not silently certify their own change.

Only a maintainer's explicit, documented decision may change `reviewStatus` or a displayed review claim. If an asset changes after review, reassess the affected review scope and reset or qualify stale status. Review is limited to the stated structures and questions; it is never a blanket claim of clinical validation. The project currently makes no clinical-validation claim.

## Contribution licensing

By intentionally submitting a contribution for inclusion, you offer your own contribution under the license applicable to its material: **CC BY-SA 4.0** for original derived atlas assets, atlas metadata, and prose/documentation; **MIT** for original software, scripts, and configuration. See [ATTRIBUTION.md](ATTRIBUTION.md) for exact scope and third-party exceptions, [LICENSE](LICENSE), and [LICENSE-CODE](LICENSE-CODE) for the standard terms. This is not a copyright assignment.

You must have the rights needed to submit the material under those terms. Identify third-party material explicitly and preserve its applicable license, attribution, and change notices; do not claim authorship of upstream work or relabel unmodified OpenSkeleton data as newly licensed by this project. Maintainers may decline material whose provenance or compatibility cannot be established.

## Software and documentation issues

For a software issue, include the commit/release, browser/OS, steps to reproduce, expected versus actual behavior, and relevant error output without secrets. Keep changes focused and avoid adding services or paid dependencies. For prose changes that alter anatomical claims, supply evidence using the same standard as a geometry correction.
