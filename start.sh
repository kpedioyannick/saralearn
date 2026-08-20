#!/bin/bash
# Lance via : pm2 start /var/www/saralearn/start.sh --name sara-learn
#
# L'API n'écoute que sur la boucle locale : elle n'est jamais jointe en
# direct, Apache lui passe /api/ (voir le vhost 040-learn.sara.education).
# `--root-path /api` lui dit sous quel préfixe elle est montée, sans quoi
# les URL qu'elle fabrique elle-même partiraient de la racine.
#
# Aucune variable n'est posée ici : `api/config.py` lit `.env` au
# démarrage, et ne remplace jamais une variable déjà définie. Le `.env`
# reste donc la seule source, et les secrets ne traînent pas dans ce
# fichier ni dans la table des process.
cd /var/www/saralearn
exec /usr/bin/python3.12 -m uvicorn api.main:app \
  --host 127.0.0.1 \
  --port 8010 \
  --root-path /api \
  --proxy-headers \
  --forwarded-allow-ips 127.0.0.1
