-- =====================================================================
-- 023 — publier les 2 187 chapitres
--
-- Le crawl pose tout en `visibility='private'` et `status='draft'` :
-- c'est prudent tant que personne n'a relu, et ça l'a été. Les coupes
-- ont eu lieu, 723 chapitres sur 2 910 sont partis, ce qui reste est ce
-- qu'on garde.
--
-- Sans ça, `/themes` rend une liste vide même une fois l'API réparée :
-- il filtre sur `visibility = 'public'`, et aucune ligne ne l'était.
-- L'écran affichait « 0 learning » pour deux raisons superposées — une
-- table `category` disparue, et un catalogue entièrement privé. La
-- première est corrigée dans le code, voici la seconde.
--
-- Les chapitres n'ont AUCUN exercice à cette heure : `exercise` est
-- vide. Publier montre donc un catalogue de titres, pas de questions.
-- C'est voulu — c'est la structure qu'on veut voir à l'écran, et elle se
-- remplira au fur et à mesure de la rédaction.
-- =====================================================================

UPDATE chapter
   SET visibility   = 'public',
       status       = 'validated',
       published_at = datetime('now'),
       updated_at   = datetime('now')
 WHERE status <> 'rejected';
