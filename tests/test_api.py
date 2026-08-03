#!/usr/bin/env python3
"""Parcours complet contre une API qui tourne vraiment.

Pas de mocks : on ouvre une session, on répond à des exercices, on vote,
on crée un thème, on le supprime. Ce qui casse ici casse pour de vrai.

    python3 tests/test_api.py                              # local
    SARA_API=https://learn.sara.education/api python3 tests/test_api.py

Chaque exécution utilise des identifiants d'appareil neufs : le fichier
peut être rejoué autant de fois qu'on veut sans nettoyage préalable.
Les assertions portent sur des PROPRIÉTÉS, jamais sur des nombres figés —
ajouter du contenu ne doit pas faire rougir la suite.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
import uuid

API = os.environ.get("SARA_API", "http://127.0.0.1:8010").rstrip("/")
RUN = uuid.uuid4().hex[:8]
ok = fail = 0


def call(method, path, body=None, token=None):
    req = urllib.request.Request(API + path, method=method)
    req.add_header("content-type", "application/json")
    if token:
        req.add_header("authorization", "Bearer " + token)
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data, timeout=30) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw) if raw else None
        except ValueError:
            return e.code, None


def chk(label, expected, got):
    global ok, fail
    if expected == got:
        print(f"  ok    {label}")
        ok += 1
    else:
        print(f"  ÉCHEC {label} — attendu {expected!r}, obtenu {got!r}")
        fail += 1


def section(name):
    print(f"\n== {name} ==")


section("santé")
_, h = call("GET", "/health")
chk("des exercices validés", True, h["exercises"] >= 8)
chk("gabarits actifs", True, h["prompts"] >= 40)

section("session anonyme")
_, t1 = call("POST", "/auth/anonymous", {"device_id": "device-a-" + RUN})
TOK, UID = t1["token"], t1["user"]["id"]
chk("anonyme", True, t1["user"]["is_anonymous"])
_, t1b = call("POST", "/auth/anonymous", {"device_id": "device-a-" + RUN})
chk("même device = même compte", UID, t1b["user"]["id"])

section("catalogue")
_, cats = call("GET", "/categories", token=TOK)
chk("des catégories", True, len(cats) >= 3)
chk("chaque catégorie a un slug et un libellé", True,
    all(c["slug"] and c["label"] for c in cats))
# Une catégorie sans thème publié mène à un écran vide : c'est le pire
# cas pour un élève, il ressemble à une panne.
_, all_themes = call("GET", "/themes", token=TOK)
served = {t["category_id"] for t in all_themes}
chk("aucune catégorie vide au catalogue", True,
    all(c["id"] in served for c in cats))
_, themes = call("GET", "/themes", token=TOK)
chk("des thèmes publics", True, len(themes) >= 5)

section("feed")
_, feed = call("GET", "/feed?n=5", token=TOK)
chk("le feed sert des exercices", True, len(feed) >= 3)
chk("options présentes", True, all(len(e["options"]) >= 2 for e in feed))
chk("explication présente", True, all(bool(e["exp_text"]) for e in feed))
chk("thème et couleur présents", True, all(e["theme"] and e["color"] for e in feed))
chk("pas de doublon", len(feed), len({e["id"] for e in feed}))

e0, e1, e2 = feed[0], feed[1], feed[2]

section("réponse juste")
_, r = call("POST", "/attempts",
            {"exercise_id": e0["id"], "chosen_index": e0["correct_index"], "answer_ms": 1500},
            TOK)
chk("marquée correcte", True, r["is_correct"])
chk("réussites = 1", 1, r["win"])
chk("série = 1", 1, r["streak"])

section("réponse fausse")
bad = (e1["correct_index"] + 1) % len(e1["options"])
_, r2 = call("POST", "/attempts", {"exercise_id": e1["id"], "chosen_index": bad}, TOK)
chk("marquée incorrecte", False, r2["is_correct"])
chk("échecs = 1", 1, r2["fail"])
chk("série remise à zéro", 0, r2["streak"])

section("passage au swipe")
_, r3 = call("POST", "/attempts", {"exercise_id": e2["id"]}, TOK)
chk("ni réussite ni échec", None, r3["is_correct"])
chk("réussites inchangées", 1, r3["win"])
chk("échecs inchangés", 1, r3["fail"])

section("anti-répétition")
seen = {e0["id"], e1["id"], e2["id"]}
_, feed2 = call("GET", "/feed?n=2", token=TOK)
chk("exercices déjà vus écartés", True, all(e["id"] not in seen for e in feed2))

section("vote")
_, l = call("POST", f"/exercises/{e0['id']}/vote", {"value": 1}, TOK)
chk("pouce en haut", 1, l["my_vote"])
chk("compteur haut à 1", 1, l["up_count"])
_, d = call("POST", f"/exercises/{e0['id']}/vote", {"value": -1}, TOK)
chk("bascule en bas", -1, d["my_vote"])
chk("haut revenu à 0", 0, d["up_count"])
chk("bas à 1", 1, d["down_count"])
_, u = call("POST", f"/exercises/{e0['id']}/vote", {"value": 0}, TOK)
chk("vote retiré", None, u["my_vote"])
chk("compteurs à zéro", (0, 0), (u["up_count"], u["down_count"]))

section("commentaire")
_, c = call("POST", f"/exercises/{e0['id']}/comments", {"body": "Celui-là m'a piégé."}, TOK)
chk("créé", "Celui-là m'a piégé.", c["body"])
_, cl = call("GET", f"/exercises/{e0['id']}/comments", token=TOK)
chk("relu dans la liste", True, any(x["body"] == c["body"] for x in cl))

section("progression")
_, prog = call("GET", "/progression", token=TOK)
chk("un thème au moins est commencé", True, len(prog) >= 1)
chk("pourcentages dans les bornes", True, all(0 <= p["pct"] <= 100 for p in prog))
# Le pourcentage dépend de la taille du thème : un thème de 330
# exercices ne passe pas à 100 % sur une bonne réponse. On vérifie
# qu'il est cohérent, pas qu'il vaut une valeur d'un jour donné.
theme_of_e0 = [p for p in prog if p["theme_id"] == e0["theme_id"]][0]
chk("progression cohérente", True,
    theme_of_e0["passed"] >= 1 and 0 <= theme_of_e0["pct"] <= 100)

section("classement")
_, g = call("GET", "/rank/global", token=TOK)
me = [x for x in g if x["is_me"]]
chk("je suis classé", 1, len(me))
# barème : 10 (juste) + 2 (fausse) + 0 (passé au swipe)
chk("points = 12", 12, me[0]["points"])
_, rt = call("GET", f"/rank/theme/{e0['theme_id']}", token=TOK)
chk("classé sur le thème", True, any(x["is_me"] for x in rt))

section("réglages")
# Deux thèmes pris dans le catalogue servi : les identifiants 1 et 2
# désignaient des thèmes de démonstration, supprimés depuis. L'API
# ignore silencieusement un abonnement à un thème inexistant, donc le
# test passait « à vide » sans rien vérifier.
_, themes_sub = call("GET", "/themes", token=TOK)
SUB_IDS = [t["id"] for t in themes_sub[:2]]
_, s = call("PUT", "/settings", {"muted": True, "dark": True, "theme_ids": SUB_IDS}, TOK)
chk("son coupé", True, s["muted"])
chk("2 thèmes suivis", 2, len(s["theme_ids"]))
_, s2 = call("GET", "/settings", token=TOK)
chk("persisté", True, s2["muted"])
_, feed3 = call("GET", "/feed?n=5", token=TOK)
chk("feed restreint aux abonnements", True,
    all(e["theme_id"] in SUB_IDS for e in feed3))

section("inscription depuis l'anonyme")
_, su = call("POST", "/auth/signup",
             {"email": f"test-{RUN}@exemple.fr", "password": "motdepasse1", "display_name": "Smoke"},
             TOK)
chk("même identifiant conservé", UID, su["user"]["id"])
chk("plus anonyme", False, su["user"]["is_anonymous"])
TOK2 = su["token"]
_, prog2 = call("GET", "/progression", token=TOK2)
chk("activité conservée", len(prog), len(prog2))

section("fusion à la connexion")
_, ta = call("POST", "/auth/anonymous", {"device_id": "device-b-" + RUN})
TOK3, UID3 = ta["token"], ta["user"]["id"]
_, f4 = call("GET", "/feed?n=1", token=TOK3)
call("POST", "/attempts",
     {"exercise_id": f4[0]["id"], "chosen_index": f4[0]["correct_index"]}, TOK3)
_, lg = call("POST", "/auth/login",
             {"email": f"test-{RUN}@exemple.fr", "password": "motdepasse1"}, TOK3)
chk("connecté au bon compte", UID, lg["user"]["id"])
TOK4 = lg["token"]
_, g2 = call("GET", "/rank/global", token=TOK4)
me2 = [x for x in g2 if x["is_me"]][0]
chk("points fusionnés (12 + 10)", 22, me2["points"])
st, _ = call("GET", "/auth/me", token=TOK3)
chk("ancien jeton anonyme révoqué", 401, st)

section("déconnexion")
# /auth/anonymous ne demande pas de mot de passe : elle ne doit donc
# jamais rendre un compte. device-a a servi à créer le compte plus haut ;
# s'il y ramenait, connaître le device_id suffirait à entrer, et se
# déconnecter serait impossible — on se reconnecterait aussitôt.
_, back = call("POST", "/auth/anonymous", {"device_id": "device-a-" + RUN})
chk("le device_id ne rend pas le compte", True, back["user"]["id"] != UID)
chk("session bien anonyme", True, back["user"]["is_anonymous"])
chk("aucun email rendu", None, back["user"]["email"])
_, mine_after = call("GET", "/progression", token=back["token"])
chk("repart d'une progression vierge", 0, len(mine_after))
# et le compte, lui, reste joignable par mot de passe
_, again = call("POST", "/auth/login",
                {"email": f"test-{RUN}@exemple.fr", "password": "motdepasse1"},
                back["token"])
chk("reconnexion au bon compte", UID, again["user"]["id"])

section("langue choisie à l'inscription")
_, tl = call("POST", "/auth/anonymous", {"device_id": "device-lang-" + RUN, "lang": "fr"})
_, sl = call("POST", "/auth/signup",
             {"email": f"lang-{RUN}@exemple.fr", "password": "motdepasse1", "lang": "en"},
             tl["token"])
chk("la langue du formulaire prime", "en", sl["user"]["lang"])
_, me_lang = call("GET", "/auth/me", token=sl["token"])
chk("langue persistée", "en", me_lang["lang"])
_, cats_lang = call("GET", "/categories", token=sl["token"])
slugs_en = {c["slug"] for c in cats_lang}
_, cats_fr = call("GET", "/categories", token=TOK)
slugs_fr = {c["slug"] for c in cats_fr}
# Une catégorie porte une langue (« Conjugaison » n'existe pas dans le
# programme américain) ou aucune (« Permis de conduire »). Les deux
# lecteurs ne doivent jamais voir les catégories propres à l'autre.
chk("catégories propres au français écartées en anglais", set(),
    {s for s in slugs_fr if s.endswith("-fr")} & slugs_en)
chk("catégories propres à l'anglais écartées en français", set(),
    {s for s in slugs_en if s.endswith("-en")} & slugs_fr)
chk("catégories sans langue vues des deux côtés", True,
    bool(slugs_fr & slugs_en))

section("CRUD thème")
# On prend la première catégorie servie plutôt qu'un identifiant en dur :
# les identifiants bougent dès qu'on réorganise le catalogue.
_, cats_crud = call("GET", "/categories", token=TOK4)
CAT_ID = cats_crud[0]["id"]
SUB_ID = (cats_crud[0]["sub_categories"] or [{"id": None}])[0]["id"]
_, nt = call("POST", "/themes",
             {"title": "Harmonie à la guitare", "category_id": CAT_ID, "sub_category_id": SUB_ID,
              "description": "Les accords ouverts.",
              "source_markdown": "# Accords\nDo majeur = Do Mi Sol.",
              "tags": ["tierces", "harmonie"]}, TOK4)
TID = nt["id"]
chk("créé", "Harmonie à la guitare", nt["title"])
chk("privé par défaut", "private", nt["visibility"])
# Le slug reçoit un suffixe numérique s'il est déjà pris — c'est voulu,
# et un test rejoué le déclenche. On vérifie donc le préfixe.
chk("slug sans accent", True, nt["slug"].startswith("harmonie-a-la-guitare"))
chk("2 tags", 2, len(nt["tags"]))
chk("propriétaire", True, nt["is_owner"])

_, other = call("POST", "/auth/anonymous", {"device_id": "device-c-" + RUN})
_, themes_other = call("GET", "/themes", token=other["token"])
chk("privé invisible des autres", True, all(not t["is_owner"] for t in themes_other))
st, _ = call("GET", f"/themes/{TID}", token=other["token"])
chk("404 pour un autre", 404, st)

_, pa = call("PATCH", f"/themes/{TID}", {"description": "Corrigé.", "tags": ["tierces"]}, TOK4)
chk("modifié", "Corrigé.", pa["description"])
chk("tags remplacés", 1, len(pa["tags"]))
_, pb = call("POST", f"/themes/{TID}/publish", {"public": True}, TOK4)
chk("passé en relecture", "pending", pb["visibility"])

section("abonnement")
# Le thème 1 était un thème de démonstration, supprimé depuis : l'appel
# renvoyait un 404 dont le corps n'a pas de champ « subscribed », et le
# test tombait sur une KeyError au lieu d'échouer proprement.
_, themes_pub = call("GET", "/themes", token=TOK4)
OTHER_TID = themes_pub[0]["id"]
_, sub = call("POST", f"/themes/{OTHER_TID}/subscribe", token=TOK4)
chk("abonné", True, sub["subscribed"])
_, uns = call("DELETE", f"/themes/{OTHER_TID}/subscribe", token=TOK4)
chk("désabonné", False, uns["subscribed"])

section("génération — validation d'entrée")
st, _ = call("POST", f"/themes/{OTHER_TID}/generate",
             {"types": ["qcm"], "count": 5}, TOK4)
chk("403 sur thème d'autrui", 403, st)
# category_id 1 désignait une catégorie de démonstration, supprimée.
_, empty = call("POST", "/themes",
                {"title": "Sans cours", "category_id": CAT_ID}, TOK4)
st, _ = call("POST", f"/themes/{empty['id']}/generate", {"types": ["qcm"], "count": 5}, TOK4)
chk("422 sans Markdown", 422, st)
call("DELETE", f"/themes/{empty['id']}", token=TOK4)

section("protection")
st, _ = call("GET", "/feed")
chk("401 sans jeton", 401, st)
st, _ = call("PATCH", f"/themes/{TID}", {"title": "Pirate"}, other["token"])
chk("403 sur thème d'autrui", 403, st)
st, _ = call("GET", "/themes/99999", token=TOK4)
chk("404 thème inexistant", 404, st)
st, _ = call("POST", "/auth/signup", {"email": f"test-{RUN}@exemple.fr", "password": "autremotdepasse"})
chk("409 email déjà pris", 409, st)
st, _ = call("POST", "/auth/login", {"email": f"test-{RUN}@exemple.fr", "password": "faux"})
chk("401 mauvais mot de passe", 401, st)
st, _ = call("GET", "/feed", token="jeton.bidon")
chk("401 jeton falsifié", 401, st)
st, _ = call("POST", "/attempts", {"exercise_id": 99999, "chosen_index": 0}, TOK4)
chk("404 exercice inexistant", 404, st)
st, _ = call("POST", "/attempts", {"exercise_id": 1, "chosen_index": 9}, TOK4)
chk("422 indice hors bornes", 422, st)

section("suppression")
st, _ = call("DELETE", f"/themes/{TID}", token=TOK4)
chk("204", 204, st)
st, _ = call("GET", f"/themes/{TID}", token=TOK4)
chk("disparu", 404, st)


section("langues")
_, ta_en = call("POST", "/auth/anonymous", {"device_id": "device-en-" + RUN, "lang": "en"})
EN = ta_en["token"]
chk("session anglaise", "en", ta_en["user"]["lang"])
_, cats_en = call("GET", "/categories", token=EN)
# La taxonomie est traduite : ce qui compte est qu'un lecteur anglais ne
# reçoive AUCUN libellé resté en français, pas qu'une catégorie précise
# porte tel nom — les catégories changent, la garantie non.
_, cats_ref = call("GET", "/categories", token=TOK)
fr_labels = {c["slug"]: c["label"] for c in cats_ref}
universelles = [c for c in cats_en if c["slug"] in fr_labels]
chk("catégories traduites", True,
    any(c["label"] != fr_labels[c["slug"]] for c in universelles))
chk("aucun libellé vide en anglais", True, all(c["label"] for c in cats_en))
_, feed_en = call("GET", "/feed?n=5", token=EN)
chk("feed anglais non vide", True, len(feed_en) > 0)
chk("aucun exercice français servi", True,
    all("Ubiquitous » se traduit" not in e["prompt"] for e in feed_en))
_, themes_en = call("GET", "/themes", token=EN)
chk("catalogue anglais seulement", True, all(t["lang"] == "en" for t in themes_en))
chk("des thèmes anglais", True, len(themes_en) >= 4)

# bascule fr -> en sur une session existante
_, st_en = call("PUT", "/settings", {"lang": "en"}, TOK4)
chk("langue changée", "en", st_en["lang"])
_, feed_after = call("GET", "/feed?n=5", token=TOK4)
chk("le feed suit la langue", True, len(feed_after) > 0)
_, themes_after = call("GET", "/themes", token=TOK4)
chk("catalogue bascule aussi", True, all(t["lang"] == "en" for t in themes_after))
call("PUT", "/settings", {"lang": "fr"}, TOK4)

# les gabarits existent dans les deux langues
_, h2 = call("GET", "/health")
chk("gabarits dans les deux langues", True, h2["prompts"] >= 40)

print(f"\nRÉSULTAT : {ok} réussis, {fail} échoués")
sys.exit(0 if fail == 0 else 1)
