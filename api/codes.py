"""Le code de partage d'une connaissance.

Six caractères qu'on dicte à voix haute. Il ouvre le quiz même privé,
donc il ne doit pas se deviner : le tirage passe par `secrets`, pas par
`random`, dont la suite est reproductible à partir de deux sorties.

L'alphabet écarte tout ce qui se confond quand on lit ou qu'on épelle :

    O et 0, I et 1 et L, S et 5, B et 8, U et V

Il reste 24 caractères. Six positions donnent 191 millions de
combinaisons — assez pour que l'essai en boucle ne mène nulle part à
cette échelle, tout en tenant sur une diapositive.

Ce qui reste vrai malgré tout : le code EST le verrou. Un quiz privé
dont le code circule n'est plus privé. C'est le contrat du partage par
code, pas un défaut de cette implémentation.
"""

from __future__ import annotations

import secrets
import sqlite3

# Sans O/0, I/1/L, S/5, B/8, U — les paires qui se confondent à l'oral
# comme à la lecture. « 2 » et « Z » restent : ils ne se ressemblent
# dans aucune des deux polices de l'app.
ALPHABET = "ACDEFGHJKMNPQRTVWXY23479"
LENGTH = 6


def new_code() -> str:
    """Un code tiré au hasard, sans garantie d'unicité — voir `unique_code`."""
    return "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))


def unique_code(conn: sqlite3.Connection, tries: int = 12) -> str:
    """Un code libre en base.

    On boucle plutôt que de s'en remettre à la seule contrainte d'unicité :
    une collision doit coûter un tirage de plus, pas une erreur remontée
    à l'auteur au moment où il crée sa connaissance.
    """
    for _ in range(tries):
        code = new_code()
        row = conn.execute("SELECT 1 FROM theme WHERE code = ?", (code,)).fetchone()
        if row is None:
            return code
    raise RuntimeError("Impossible de tirer un code libre — l'espace est-il saturé ?")


def normalize(raw: str) -> str:
    """Ce que l'utilisateur tape, ramené à ce qui est stocké.

    On accepte les minuscules, les espaces et les tirets : un code se
    recopie depuis un message, une diapositive ou un tableau, et il
    arrive rarement propre.
    """
    return "".join(c for c in raw.upper() if c in ALPHABET)
