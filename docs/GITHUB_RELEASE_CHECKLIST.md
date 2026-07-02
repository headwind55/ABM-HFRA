# GitHub Release Checklist

Use this checklist before making ABM-IRM public.

## Repository Metadata

- Confirm the repository name: `ABM-IRM`.
- Confirm the expanded model name: `Agent-based model for intra-regional migration`.
- Confirm repository authors: Shi Feng and Tomohiro Tanaka.
- Add ORCID identifiers if desired.
- Add a stable contact email or issue-reporting policy.

## License and Data Rights

- MIT software license has been added in `LICENSE`; confirm this is acceptable to the project manager and institution before public release.
- Decide whether prepared data can be redistributed publicly.
- Check source licenses for ESRI Japan, e-Stat, IPSS, GSI/MLIT, OpenStreetMap, and BODIK-derived files.
- If any data cannot be redistributed, remove those files and provide instructions for users to request or recreate them.
- `DATA_LICENSE.md` has been added; update it after confirming which prepared data files can be redistributed.

## Citation

- Update `CITATION.cff` after the related paper is accepted or published.
- Add DOI, journal, year, and final title when available.
- Consider archiving a release on Zenodo if a software DOI is needed.

## Documentation

- Keep `README.md`, `data/README.md`, and `docs/DATA_PREPARATION.md` synchronized with actual file names.
- State clearly that upstream spatial preprocessing is documented but not fully automated.
- Include a minimal example run using one supported start year.
- Add expected output summaries or checksums if exact regression testing is required.

## Privacy and Cleanup

- Do not commit personal temporary files, logs, cache folders, or manuscript drafts.
- Check for absolute local paths inside scripts and documentation.
- Confirm `runtime/` contains only `.gitkeep` placeholders before release.
- Run `python tests/smoke_imports.py` before tagging a release.

## Analysis Code

- Analysis scripts are intentionally not included in the first public release; add selected analysis code in a later release.
- When analysis scripts are added, document required inputs, outputs, and expected command order.

## Optional Improvements

- Add an environment file such as `environment.yml` for conda users.
- Add GitHub Actions for import/smoke tests.
- Add a small synthetic dataset if public redistribution of the Kuma River data is restricted.
- Add diagrams showing the HDM/IRM workflow and data preparation process.
