# Third-party components

## Gavrog space-group table (included)

`third-party/sgtable.data` is copied unchanged from Olaf Delgado-Friedrichs's Gavrog,
commit `15f3cad6c8150847fa9347397235a24f728274a9`, file `src/org/gavrog/joss/geometry/sgtable.data`.

- Source: https://raw.githubusercontent.com/odf/gavrog/15f3cad6c8150847fa9347397235a24f728274a9/src/org/gavrog/joss/geometry/sgtable.data
- SHA-256: `19f54403accd6b0feeff0f4c14a9f9004c5d8ac25186b43ee1eb1eaebb23dad9`
- Copyright 2005 Olaf Delgado-Friedrichs; the notice is kept in the file.
- Licence: Apache License, Version 2.0; full text in `third-party/Apache-2.0.txt`.
- The file is not modified. Our code reads the operation strings from it at run time.
- The Gavrog tree at that commit has no NOTICE file, so there is no upstream NOTICE text to reproduce.

## RCSR data (not included)

`3dall.txt` and the optional `RCSRnets.arc` from the RCSR-content repository (commit
`580316c9352b747f5c309a93acd21a3a2b4034a3`) are downloaded by the user at run time and checked against
fixed SHA-256 values. They are not part of this repository, and neither are graphs, balls, maps or figures
derived from them. No licence file or redistribution terms were found in that repository at the pinned commit.
Fetching the files at run time does not settle the terms under which they may be used; users should check
these for their own purposes.

The Apache-2.0 licence of the Gavrog table, and the licences of this repository (see `LICENSE`), do not
apply to RCSR data. Citing RCSR and Gavrog implies no endorsement of this work by their authors.
