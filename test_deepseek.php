<?php

$apiKey = getenv('DEEPSEEK_API_KEY');
if (!$apiKey) {
    echo "NO API KEY\n";
    exit;
}

$prompt = "Tu es un professeur expert en pédagogie et en création de contenu éducatif interactif.

Génère un cours complet au format JSON pour Reveal.js sur le thème suivant :
- **Chapitre** : Lire et écrire les nombres entiers jusqu'au milliard
- **Niveau** : CM2

Le JSON doit suivre EXACTEMENT cette structure :
{
  \"title\": \"Titre du cours\",
  \"description\": \"Brève description\",
  \"slides\": [
    {
      \"id\": 1,
      \"slide\": \"<section data-background-color='[COULEUR]'>[CONTENU HTML avec animations]</section>\",
      \"texte_audio\": \"[Texte narratif à dire]\"
    }
  ]
}

RÈGLES STRICTES À RESPECTER :

2. **Animations** : Utilise class=\"fragment\" 
3. **data-line-numbers** : Pour chaque bloc <pre><code>, ajoute data-line-numbers avec des étapes (ex: '1|2|3|4-5')
4. **Couleurs de fond** : Alterne les data-background-color (aquamarine, #ff9999, #99ccff, rgb(70,70,255), #ffcc99, etc.)
6. **Structure pédagogique** :
   - Slide 1 : Introduction / titre
   - Slides 2-4 : Définitions et vocabulaire
   - Slides 5-8 : Méthodes et techniques
   - Slides 9-11 : Propriétés ou règles importantes
   - Slides 12-13 : Astuces / exemples
   - Slide 14 : Exercices
   - Slide 15 : Corrections
   - Slide 16 : Résumé / conclusion
7. **Texte audio** : Rédige un commentaire clair, adapté au niveau indiqué, qui explique ce qui est affiché sans le lire mot à mot
8. **Accessibilité** : Utilise des couleurs contrastées et des balises simples

Le cours doit être :
- Progressif (du simple au complexe)
- Visuel (couleurs, emojis, mise en évidence)
- Interactif (animations fragment)
- Adapté à la classe , au chapitre

Génère maintenant le JSON complet.

En plus du cours Reveal.js ci-dessus, ajoute une clé \"mindmap\" à la racine du JSON avec :
{ \"content\": \"code PlantUML (@startmindmap ... @endmindmap)\", \"text_to_audio\": \"texte pour synthèse vocale décrivant la mind map\" }

Renvoie UN SEUL objet JSON avec les clés \"course\" (objet avec title, description, slides) et \"mindmap\" (objet avec content, text_to_audio).";


$ch = curl_init('https://api.deepseek.com/chat/completions');
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    'Content-Type: application/json',
    'Authorization: Bearer ' . $apiKey
]);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode([
    'model' => 'deepseek-chat',
    'messages' => [
        ['role' => 'system', 'content' => 'You are a helpful assistant.'],
        ['role' => 'user', 'content' => $prompt]
    ],
    'max_tokens' => 8000,
    'stream' => false
]));

$response = curl_exec($ch);
curl_close($ch);

echo strlen($response) . " bytes\n";
echo substr(json_decode($response, true)['choices'][0]['message']['content'], -500);
