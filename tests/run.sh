#!/usr/bin/env bash
# Toute la suite, en un appel.
#
#   ./tests/run.sh                                    # contre le local
#   SARA_URL=https://learn.sara.education ./tests/run.sh   # contre la prod
#
# SARA_API se déduit de SARA_URL si elle n'est pas donnée : en
# production l'API vit sous /api du même domaine.
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SARA_URL="${SARA_URL:-http://localhost:4178}"
if [ -z "${SARA_API:-}" ]; then
  case "$SARA_URL" in
    http://localhost:4178|http://127.0.0.1:4178) SARA_API="http://127.0.0.1:8010" ;;
    *) SARA_API="${SARA_URL%/}/api" ;;
  esac
fi
export SARA_URL SARA_API

echo "API   : $SARA_API"
echo "Front : $SARA_URL"

fail=0

echo
echo "######## API ########"
python3 "$ROOT/tests/test_api.py" || fail=1

echo
echo "######## Mise en page ########"
if node "$ROOT/tests/test_layout.mjs"; then :; else
  # Un Chromium absent n'est pas un échec de l'application : on le dit
  # et on n'invente pas un vert qu'on n'a pas mesuré.
  [ $? -eq 2 ] && echo "  (ignoré : Chromium indisponible)" || fail=1
fi

echo
[ $fail -eq 0 ] && echo "TOUT EST VERT" || echo "DES TESTS ONT ÉCHOUÉ"
exit $fail
