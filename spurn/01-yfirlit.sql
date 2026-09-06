-- spurn/01-yfirlit.sql
.mode markdown
.headers on

SELECT 'laws' AS tafla, COUNT(*) AS fjoldi, MIN(year) AS fra, MAX(year) AS til FROM laws
UNION ALL SELECT 'law_amendments', COUNT(*), MIN(amend_year), MAX(amend_year) FROM law_amendments
UNION ALL SELECT 'regulations', COUNT(*), NULL, NULL FROM regulations
UNION ALL SELECT 'court_cases', COUNT(*), NULL, NULL FROM court_cases
UNION ALL SELECT 'alyktanir', COUNT(*), MIN(thing), MAX(thing) FROM alyktanir;

SELECT law_nr, year, heiti, effective, LENGTH(body_text) AS staerd
FROM laws WHERE law_nr IN ('123','30','85','81','80','44','52','36','91','43','2','99','4')
  AND year IN (2010,2002,2007,2004,1998,2016,1994,1991,2000,1993,1995)
ORDER BY year, law_nr;

SELECT filename, COUNT(*) AS breytingar, MAX(amend_year) AS nyjast
FROM law_amendments WHERE filename LIKE '%2007085%' OR filename LIKE '%2010123%'
GROUP BY filename;

SELECT name, title, published_date, LENGTH(body_text) AS staerd
FROM regulations WHERE name LIKE '%1084%' OR name LIKE '%1277%' OR name LIKE '%1426%'
ORDER BY name;
