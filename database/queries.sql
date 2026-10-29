-- Identify courses with few or no materials to guide contribution efforts.
SELECT c.course_name, COUNT(m.material_id) AS material_count
FROM courses AS c
LEFT JOIN materials AS m ON m.course_id = c.course_id
GROUP BY c.course_id, c.course_name
ORDER BY material_count, c.course_name;
