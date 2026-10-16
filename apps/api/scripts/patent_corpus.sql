-- Battery recycling / upcycling patent corpus from Google Patents Public Data (BigQuery).
--
--   bq query --use_legacy_sql=false --dry_run < scripts/patent_corpus.sql      # check bytes scanned FIRST
--   bq query --use_legacy_sql=false --format=prettyjson --max_rows=1000000 < scripts/patent_corpus.sql \
--     | python scripts/bq_to_jsonl.py > ../../data/evidence/patents.jsonl
--   PATENT_CORPUS=../../data/evidence/patents.jsonl
--
-- BigQuery bills on-demand queries by bytes scanned; publications is a multi-terabyte table and claims
-- text is the largest column. Run the dry run, and consider a date floor or fewer columns, before paying.
--
-- CPC seed set (verify each code against the current CPC scheme before relying on it):
--   Y02W30/84 recycling of batteries | H01M10/54, H01M6/52 reclaiming parts of waste cells/accumulators
--   C22B7/00 non-ferrous metals from scrap | C22B23/00 Ni/Co | C22B26/12 Li | C22B47/00 Mn
--   C01D15 Li compounds | C01G51, C01G53, C01G45 Co/Ni/Mn compounds | H01M4/505, H01M4/525, H01M4/58 cathode actives
SELECT
  p.publication_number,
  p.family_id,
  p.country_code,
  p.kind_code,
  p.priority_date,
  p.publication_date,
  (SELECT t.text FROM UNNEST(p.title_localized) t ORDER BY IF(t.language = 'en', 0, 1) LIMIT 1) AS title,
  (SELECT a.text FROM UNNEST(p.abstract_localized) a ORDER BY IF(a.language = 'en', 0, 1) LIMIT 1) AS abstract,
  (SELECT c.text FROM UNNEST(p.claims_localized) c ORDER BY IF(c.language = 'en', 0, 1) LIMIT 1) AS claims,
  (SELECT t.language FROM UNNEST(p.title_localized) t ORDER BY IF(t.language = 'en', 0, 1) LIMIT 1) AS language,
  ARRAY(SELECT c.code FROM UNNEST(p.cpc) c) AS cpc,
  ARRAY(SELECT a.name FROM UNNEST(p.assignee_harmonized) a) AS assignees,
  ARRAY(SELECT c.publication_number FROM UNNEST(p.citation) c) AS cites
FROM `patents-public-data.patents.publications` p
WHERE p.publication_date >= 20000101
  AND EXISTS (
    SELECT 1 FROM UNNEST(p.cpc) c
    WHERE c.code LIKE 'Y02W30/84%' OR c.code LIKE 'H01M10/54%' OR c.code LIKE 'H01M6/52%'
       OR c.code LIKE 'C22B7/00%' OR c.code LIKE 'C22B23/0%' OR c.code LIKE 'C22B26/12%' OR c.code LIKE 'C22B47/00%'
       OR c.code LIKE 'C01D15/%' OR c.code LIKE 'C01G51/%' OR c.code LIKE 'C01G53/%' OR c.code LIKE 'C01G45/%'
  )
