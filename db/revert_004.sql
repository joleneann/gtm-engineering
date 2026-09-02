-- revert 004: put the four industry codes back to the PDF's ampersand spelling.
--
-- Reverting restores codes that match no filing, so scoring will halt on any
-- company in those groups. Only run this to undo a mistaken apply.

begin;

update industry_scores set industry_group_type = 'Hospitals & Physicians'
 where industry_group_type = 'Hospitals and Physicians';

update industry_scores set industry_group_type = 'Airlines & Airports'
 where industry_group_type = 'Airlines and Airports';

update industry_scores set industry_group_type = 'Lodging & Conventions'
 where industry_group_type = 'Lodging and Conventions';

update industry_scores set industry_group_type = 'Tourism & Travel Services'
 where industry_group_type = 'Tourism and Travel Services';

commit;
