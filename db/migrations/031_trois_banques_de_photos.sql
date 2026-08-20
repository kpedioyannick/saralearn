-- D'OÙ VIENT LA PHOTO. Une seule banque servait, son nom était écrit en
-- dur dans le front (« · Unsplash » dans PhaseBlocks.tsx). À trois, le
-- nom doit voyager avec la photo : les trois exigent d'être nommées,
-- et créditer Pexels sous le nom d'Unsplash serait pire que rien.
ALTER TABLE exercise ADD COLUMN image_source TEXT;

-- Les cinquante déjà posées viennent toutes d'Unsplash — vérifié sur
-- le préfixe de leur URL, images.unsplash.com pour les cinquante.
UPDATE exercise
   SET image_source = 'Unsplash'
 WHERE image_url IS NOT NULL AND image_url <> '';
