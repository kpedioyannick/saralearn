-- =====================================================================
-- 026 — les titres que Wikipédia ne sait pas traduire, écrits à la main
--
-- La migration 025 prend les titres français aux LIENS DE LANGUE de
-- Wikipédia : exact par construction, gratuit, et « Sun dog » y devient
-- « Parhélie » là où une machine dirait « chien du soleil ». Elle a rendu
-- 1 632 titres sur 2 187.
--
-- Restent ceux dont l'article anglais n'a pas de version française. Le
-- lien n'existe pas — vérifié article par article sur l'API : les 26 du
-- catalogue visible rendent tous une liste de liens vide. Relancer le
-- script ne les remplira jamais ; il n'y a rien à aller chercher.
--
-- Et ça se voyait : « La Terre · 36 apprentissages » alignait « Océan »,
-- « Abiogenèse », « Cryosphère » puis, au milieu, « Satellite system
-- (astronomy) », « Gravity of Earth », « Early Earth ». Les Oiseaux
-- avaient quatre lignes anglaises sur quatorze, dont « Bird flight », le
-- seul du rayon qui porte des exercices.
--
-- Donc la main, comme pour les onze jours de la création en 025. Vingt-six
-- titres ne valent pas un appel réseau, et un traducteur automatique n'a
-- ici aucun filet : c'est lui qui a rendu « the metre is defined as » par
-- « le compteur est défini comme ». `source = 'humain'` garde la
-- distinction — on doit pouvoir repasser sur ce qu'une machine a produit
-- sans toucher à ce qu'un humain a écrit.
--
-- Trois choix qui ne sont pas des traductions mot à mot :
--
--   · « Dusk » → « Tombée de la nuit », parce que « Crépuscule » est déjà
--     pris : c'est le titre français de « Twilight », qui est dans le même
--     rayon. Deux lignes identiques dans une liste de six ne se
--     distinguent plus ;
--   · « Marine worm » → « Ver marin » et « Sea worm » → « Ver de mer ».
--     Deux articles anglais distincts, dans le même rayon, que le même
--     mot français aurait confondus ;
--   · « Solar eclipses on the Moon » → « Éclipses solaires vues de la
--     Lune ». L'article parle de ce qu'on verrait EN ÉTANT sur la Lune ;
--     « sur la Lune » se lirait comme une éclipse qui s'y produit.
--
-- Le rapprochement se fait sur le titre anglais, pas sur l'identifiant :
-- un même article est rangé sous deux jours de la création quand les deux
-- le concernent — « Sunlight » est à la fois du Soleil et de la Lumière.
-- Les deux méritent le titre français.
-- =====================================================================

INSERT OR IGNORE INTO chapter_translation (chapter_id, lang, title, source)
SELECT ch.id, 'fr', v.fr, 'humain'
  FROM chapter ch
  JOIN (
              SELECT 'Dusk'                          AS en, 'Tombée de la nuit'                    AS fr
    UNION ALL SELECT 'Early Earth',                        'Terre primitive'
    UNION ALL SELECT 'Earth''s internal heat budget',      'Bilan thermique interne de la Terre'
    UNION ALL SELECT 'Gravity of Earth',                   'Pesanteur terrestre'
    UNION ALL SELECT 'Planetary surface',                  'Surface planétaire'
    UNION ALL SELECT 'Satellite system (astronomy)',       'Système satellitaire'
    UNION ALL SELECT 'Sunlight',                           'Lumière du Soleil'
    UNION ALL SELECT 'Solar eclipses on the Moon',         'Éclipses solaires vues de la Lune'
    UNION ALL SELECT 'Theory of tides',                    'Théorie des marées'
    UNION ALL SELECT 'Volcanism on the Moon',              'Volcanisme lunaire'
    UNION ALL SELECT 'Diversity of fish',                  'Diversité des poissons'
    UNION ALL SELECT 'Ichthyoplankton',                    'Ichtyoplancton'
    UNION ALL SELECT 'Marine invertebrates',               'Invertébrés marins'
    UNION ALL SELECT 'Marine protists',                    'Protistes marins'
    UNION ALL SELECT 'Marine vertebrate',                  'Vertébrés marins'
    UNION ALL SELECT 'Marine worm',                        'Ver marin'
    UNION ALL SELECT 'Mycoplankton',                       'Mycoplancton'
    UNION ALL SELECT 'Sea worm',                           'Ver de mer'
    UNION ALL SELECT 'Bird flight',                        'Vol des oiseaux'
    UNION ALL SELECT 'Origin of birds',                    'Origine des oiseaux'
    UNION ALL SELECT 'Parental care in birds',             'Soins parentaux chez les oiseaux'
    UNION ALL SELECT 'Sexual selection in birds',          'Sélection sexuelle chez les oiseaux'
    UNION ALL SELECT 'Land snail',                         'Escargot terrestre'
    UNION ALL SELECT 'Semi-slug',                          'Semi-limace'
    UNION ALL SELECT 'Composition of the human body',      'Composition du corps humain'
    UNION ALL SELECT 'Human reproductive system',          'Système reproducteur humain'
  ) v ON v.en = ch.title
 WHERE NOT EXISTS (
         SELECT 1 FROM chapter_translation t
          WHERE t.chapter_id = ch.id AND t.lang = 'fr');
