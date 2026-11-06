# Module responsibility

Alibek owns the materials and upload UI and coordinates contracts with Daryn.

MaterialsPage.jsx lists and searches real records, with category/course filters,
pagination, retry and request cancellation. Materials.jsx remains a compatibility
alias. MaterialList.jsx supports authenticated downloads; UploadForm.jsx loads
taxonomy and sends multipart data through the central API client.

The backend now mounts GET /api/materials, GET /api/categories and GET /api/courses,
plus authenticated upload/download routes. The page ships no sample data; isolated
browser tests supply contract-shaped responses, while week10.spec.js checks real
PostgreSQL upload, search and download.

Implementation prepared by Codex; personal owner review pending.
