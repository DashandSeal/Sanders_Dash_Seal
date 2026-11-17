# Sanders Corporations Secretary — Corporate Seal Assets

The approved full-color seal artworks listed below are installed as local static assets in the Secretary application. These are public-source copies of artwork already present in the public repository under `sanders-twostep/`. The archival electronic originals and transparent, stamp, embosser and letterhead variants remain in the user's Business Library.

| Corporate identity | Application asset | Historical designation |
| --- | --- | --- |
| Sanders Corporate Headquarters | `/static/assets/Headquarters_Electronic_Master_Full_Color.png` | Separate approved headquarters crest |
| Sanders Home Healthcare & Caregivers LLC | `/static/assets/Home_Healthcare_Electronic_Master_Full_Color.png` | EST. 2025 · Colorado SOS ID 20251946893 |
| Sanders Senior Living LLC | `/static/assets/Senior_Living_Electronic_Master_Full_Color.png` | EST. 2025 · Colorado SOS ID 20258000764 |
| Sanders Legal Helpers LLC (DBA Sanders Dash & Seal) | `/static/assets/Legal_Helpers_Electronic_Master_Full_Color.png` | EST. 2025 · Colorado SOS ID 20258029131 |

The dashboard masthead references `/static/assets/sanders_headquarters_seal.png`, which is an additional copy of the exact headquarters crest. Both the dashboard masthead and the four registered asset names now point to files present in the source tree.

The Secretary's existing `GET /api/seals` endpoint lists these four master filenames. These are brand and document-production assets, not cryptographic signing keys or evidence that a legal filing has been executed.

S & G Security Inc. (owner-provided founding year 1996) remains a distinct corporate entity. An individual S & G Security seal has not yet been approved or included here.

Business Library archive: `/Sanders Family of Companies/Official Corporate Seals/Electronic Seals`.

Publishing these file assets to the public GitHub `main` branch makes them available to the application after installation of the new source revision. Actual Oracle deployment remains a separate state.
