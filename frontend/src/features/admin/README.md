# Module responsibility

Arnur owns admin features and role tests. AdminPage.jsx shows the overview, course and download reports and storage check. UserManagement.jsx lists users and changes roles and blocking. TaxonomyForms.jsx adds categories and courses.

Hiding this page is not authorization: every route under /api/admin is checked on the server. Personal owner review is pending.
