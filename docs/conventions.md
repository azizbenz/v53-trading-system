# V5.3 — Conventions

## Tests
- pytest, tests/ miroir de src/
- Marqueurs: @pytest.mark.build1, @pytest.mark.slow
- Chaque module P0 a des contract tests

## Logs
- Format JSON structuré
- Champs: timestamp, level, module, message, pair?, engine_id?
- Niveaux: DEBUG, INFO, WARNING, ERROR, CRITICAL

## Nommage
- Modules: snake_case
- Classes: PascalCase
- Enums: PascalCase, valeurs snake_case
- Constantes: UPPER_SNAKE_CASE

## Merge Gates
- Tous les tests verts
- DAG validator pass
- Audit croisé (ChatGPT audit du code Claude)
- Pas de dépendance cachée
