# Module responsibility

Alibek owns materials and upload UI; coordinate contracts with Daryn.

`MaterialsPage.jsx` lists and searches materials through `src/api/client.js`, following the planned `GET /api/materials`, `GET /api/categories` and `GET /api/courses` contracts in `docs/API_CONTRACT.md`. Those endpoints are not mounted yet, so the page reports that materials are not available until Talgat and Daryn add them. The page ships no sample data; browser tests supply their own contract-shaped responses.

Upload and download UI and all file operations are still planned.
