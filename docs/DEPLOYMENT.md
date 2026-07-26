# Déploiement production (Coolify)

Cible : `https://${DEPLOY_DOMAIN}` (proposé : `mission-radar.stefanoalletti.com`), via
Cloudflare → Traefik (Coolify) → services internes, sans port publié vers l'hôte. Même
pattern que `ai-evaluation-lab` et `photos-quality` : un seul service (`frontend`) exposé au
réseau `coolify`, tout le reste sur un réseau interne `app-network`.

## Fichiers introduits pour la production

| Fichier | Rôle |
|---|---|
| `docker-compose.prod.yml` | Compose de production : 7 services (postgres, rabbitmq, redis, backend, celery_worker, celery_beat, frontend), `expose` uniquement + labels Traefik sur `frontend`, healthchecks, `restart: unless-stopped` |
| `backend/docker/Dockerfile` | Image prod du backend : pas de `--reload`, dépendances `requirements/base.txt` uniquement (pas les deps dev/lint/test), torch CPU-only pré-installé, modèle d'embedding `all-MiniLM-L6-v2` pré-téléchargé au build, tourne en non-root |
| `backend/.dockerignore` | Exclut `.env`, tests, caches du contexte de build |
| `backend/scripts/init_production.sh` | Applique les migrations Alembic — à lancer manuellement après le premier déploiement (voir plus bas, pourquoi ce n'est pas automatique) |
| `frontend/Dockerfile` | Multi-stage : build Vite (Node 20) puis service Nginx |
| `frontend/nginx.conf` | Sert le SPA (`try_files ... /index.html`) et reverse-proxy en interne `/api`, `/mcp`, `/.well-known/oauth-protected-resource`, `/docs`, `/openapi.json` vers `backend:8000` |
| `frontend/.dockerignore` | Exclut `node_modules/`, `dist/` |
| `.env.production.example` | Référence des variables à saisir dans Coolify |

## Routage

Contrairement à `ai-evaluation-lab`, le backend de mission-radar-ai expose déjà ses routes
métier sous le préfixe `/api/...` (voir `backend/src/Infrastructure/Api/Controller/*.py`), donc
`frontend/nginx.conf` **ne retire pas** le préfixe en le transmettant à `backend:8000/api/...`
(à la différence du pattern `ai-evaluation-lab`, qui retire le préfixe car son backend n'en a
pas). Le serveur MCP monté sur `/mcp` (FastMCP, transport HTTP streamable) est proxifié à part
avec `proxy_buffering off` et un timeout long, car des clients MCP externes (Claude Desktop,
Claude Code) s'y connectent directement en gardant la connexion ouverte. Traefik n'a qu'un seul
routeur, sur tout le domaine, pointant vers `frontend` — c'est nginx qui fait le tri interne.

Aucun changement de code CORS n'a été nécessaire : le frontend appelle son API en same-origin
via ce proxy nginx, donc le FastAPI backend n'a jamais besoin d'autoriser une origine distante.

## Ce qui a changé par rapport au dev

- **Migrations non automatiques au démarrage** : `backend`, `celery_worker` et `celery_beat`
  partagent la même image et démarrent en parallèle (`depends_on` ne garantit pas d'ordre entre
  eux) ; faire tourner `alembic upgrade head` dans l'entrypoint de chacun créerait une course.
  À la place, `backend/scripts/init_production.sh` se lance à la main après le déploiement
  (une fois, puis à chaque déploiement qui ajoute une migration) — depuis le terminal Coolify
  du service `backend` (déjà dans le conteneur, `WORKDIR /app`) : `bash scripts/init_production.sh`,
  ou depuis l'hôte : `docker compose -f docker-compose.prod.yml exec backend bash scripts/init_production.sh`
- **Planification Celery Beat persistée** : le fichier de planification vit sur un volume nommé
  `celery_beat_data:/var/lib/celery` au lieu de `/tmp` (effacé à chaque redémarrage du
  conteneur en dev — sans conséquence en dev, mais aurait fait sauter le suivi des tâches dues
  en prod).
- **Identifiants RabbitMQ dédiés** : `RABBITMQ_USER`/`RABBITMQ_PASSWORD` doivent être définis
  (pas de `guest`/`guest` comme en dev) — voir `.env.production.example`.
- **Provider LLM** : `LLM_PROVIDER=groq` en prod (décision explicite, malgré la mention Claude
  dans le README — Groq est déjà validé en dev et évite d'ajouter une clé Anthropic).
- **`APIFY_PROVIDER=real`** (le mode `mock` reste réservé au dev/CI).

## Prérequis externes à préparer avant de déployer

### 1. Auth0 — ressources de production

Le tenant dev (`mission-radar-ai-dev.eu.auth0.com`, voir `docs/AUTH0_INTEGRATION.md`) a déjà
réservé un identifiant d'audience "prod" pour le MCP (`https://api.mission-radar.dev/mcp`,
marqué "réservée, pas utilisée en dev" dans la table de configuration) — à vérifier dans le
dashboard Auth0 si la ressource API correspondante existe réellement ou si ce n'est qu'un
identifiant prévu sur le papier. Dans le doute (l'utilisateur a indiqué qu'Auth0 prod est "à
créer"), à faire dans le tenant Auth0 :

1. Créer (ou confirmer l'existence de) l'API `Mission Radar AI - MCP Server` avec l'identifier
   `https://api.mission-radar.dev/mcp` → valeur de `AUTH0_MCP_AUDIENCE`.
2. Réutiliser l'API existante `Mission Radar AI - REST API` (identifier
   `https://api.mission-radar.dev`) comme `AUTH0_API_AUDIENCE` — c'est un identifiant opaque,
   il n'a pas besoin de résoudre vers une vraie URL.
3. Sur l'application SPA `Mission Radar AI - Web` : ajouter
   `https://${DEPLOY_DOMAIN}` aux **Allowed Callback URLs**, **Allowed Logout URLs** et
   **Allowed Web Origins** (en plus de `http://localhost:5173`, à garder pour continuer à
   développer en local).
4. Noter le Client ID de cette application → `AUTH0_WEB_CLIENT_ID` dans
   `.env.production.example` (utilisé comme argument de build du frontend).
5. `MCP_PROTECTED_RESOURCE_METADATA_URL` doit pointer vers la vraie URL publique déployée :
   `https://${DEPLOY_DOMAIN}/.well-known/oauth-protected-resource` — **pas** vers
   `api.mission-radar.dev`, qui n'est qu'un identifiant Auth0, pas un domaine hébergé.

### 2. Resend

Domaine d'envoi déjà vérifié (confirmé) — `MAIL_FROM` peut rester une adresse de ce domaine et
`DIGEST_ENABLED=true` dès le premier déploiement.

### 3. DNS

Pointer `${DEPLOY_DOMAIN}` (Cloudflare) vers le VPS Hostinger, comme pour les autres projets
sur ce même Traefik/Coolify.

## Étapes de déploiement Coolify

1. Committer les fichiers listés ci-dessus et pousser vers le remote connecté à Coolify.
2. Dans Coolify : nouvelle **Application → Docker Compose**, pointant sur `docker-compose.prod.yml`.
3. Configurer le domaine sur le service `frontend` (vérifier dans l'UI Coolify le nom réel du
   réseau Traefik externe et du `certresolver` — `coolify`/`letsencrypt` sont les valeurs
   utilisées par `ai-evaluation-lab`/`photos-quality`, à confirmer sur cette instance).
4. Renseigner toutes les variables de `.env.production.example` dans Coolify (Environment
   Variables), avec de vraies valeurs.
5. Vérifier le DNS Cloudflare de `${DEPLOY_DOMAIN}` vers le VPS.
6. Lancer le déploiement. Le premier démarrage du backend est plus lent (build inclut le
   pré-téléchargement du modèle d'embedding).
7. Appliquer les migrations une fois les conteneurs up — depuis le terminal Coolify du service
   `backend` : `bash scripts/init_production.sh` (ou depuis l'hôte :
   `docker compose -f docker-compose.prod.yml exec backend bash scripts/init_production.sh`)
8. Vérifier :
   - `https://${DEPLOY_DOMAIN}/` (SPA)
   - `https://${DEPLOY_DOMAIN}/api/health` via le reverse-proxy interne nginx (Postgres/RabbitMQ/Redis)
   - Connexion Auth0 depuis l'UI (bouton "Se connecter")
   - `https://${DEPLOY_DOMAIN}/.well-known/oauth-protected-resource` (metadata MCP)
   - Un client MCP externe (Claude Desktop/Code) pointé sur `https://${DEPLOY_DOMAIN}/mcp`

## Risque restant à traiter séparément

- Aucun rate-limiting ni Basic Auth devant l'API — à envisager si le trafic public augmente.
- `celery_worker` tourne avec un seul réplica implicite ; si le volume de scraping augmente,
  revoir le nombre de workers et la queue RabbitMQ avant de scaler horizontalement.

## Test local avant push

```bash
# Depuis la racine du repo, avec backend/.env déjà rempli (clés réelles) :
docker compose -f docker-compose.prod.yml config   # valide labels/réseaux/healthchecks sans démarrer

# Le réseau externe "coolify" n'existe pas en local — le créer une fois pour tester :
docker network create coolify

POSTGRES_PASSWORD=test RABBITMQ_USER=test RABBITMQ_PASSWORD=test \
GROQ_API_KEY=... APIFY_API_TOKEN=... RESEND_API_KEY=... MAIL_FROM=... \
AUTH0_DOMAIN=... AUTH0_API_AUDIENCE=... AUTH0_MCP_AUDIENCE=... \
MCP_PROTECTED_RESOURCE_METADATA_URL=http://localhost/.well-known/oauth-protected-resource \
AUTH0_WEB_CLIENT_ID=... DEPLOY_DOMAIN=localhost \
docker compose -f docker-compose.prod.yml up --build

docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs backend
```
