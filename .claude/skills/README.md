# Skills Claude Code

Les skills propres au projet vivent dans :

```text
.claude/skills/<nom-du-skill>/SKILL.md
```

Pour ajouter un skill :

1. Copier le dossier `_template`.
2. Renommer le dossier en kebab-case, par exemple `review-domain-layer`.
3. Renommer `SKILL.md.example` en `SKILL.md`.
4. Renseigner précisément `name` et `description`.
5. Supprimer les dossiers optionnels inutilisés.

Claude utilise la `description` pour décider quand charger le skill. Elle doit donc
décrire à la fois sa responsabilité et les situations dans lesquelles l'utiliser.

## Structure

```text
<nom-du-skill>/
├── SKILL.md        # Obligatoire
├── scripts/        # Scripts exécutables et déterministes
├── references/     # Documentation chargée uniquement si nécessaire
└── assets/         # Templates et fichiers utilisés dans les livrables
```

Le dossier `_template` n'est pas un skill actif tant que `SKILL.md.example` n'est
pas renommé en `SKILL.md`.
