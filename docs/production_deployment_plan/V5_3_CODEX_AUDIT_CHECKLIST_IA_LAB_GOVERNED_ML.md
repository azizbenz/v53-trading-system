# V5.3 — Checklist d’audit commune (toi + moi) pour les slices Codex

## 0. But
Cette checklist sert à auditer chaque slice Codex sans flou et sans récit trompeur.

---

## 1. Doctrine
- [ ] Le slice décrit correctement le IA Lab comme rail gouverné local
- [ ] Le slice ne le décrit pas comme un classical ML lab souverain
- [ ] Le slice ne prétend pas que la couche ML bornée est déjà ouverte si ce n’est pas le cas
- [ ] Le slice ne réintroduit pas une deuxième architecture
- [ ] Le slice ne remet pas en backlog les forecast seams C/D comme manquants

---

## 2. Scope
- [ ] Le scope est borné
- [ ] Les fichiers interdits sont explicitement listés
- [ ] Les formules touchées sont explicitement écrites
- [ ] Les modules non concernés ne sont pas modifiés

---

## 3. Quant
- [ ] PSR / DSR / POT-GPD / Energy non touchés si pas d’arbitrage humain
- [ ] Aucun test vert n’a été obtenu en trafiquant une formule canonique
- [ ] Les ancres quant restantes sont décrites honnêtement comme BLOCKED / PARTIAL si nécessaire

---

## 4. Forecast / scoring / drift
- [ ] Forecast normalizer : `E[|F_normalised|] ≈ 10`
- [ ] Break-even : comparateur strict `>` à la frontière
- [ ] Cost drift : formule du biais correcte
- [ ] Les caps moteurs ne sont pas modifiés sans raison doctrinale explicite

---

## 5. Couche ML
- [ ] Le training reste local / offline
- [ ] Le VPS n’entraîne rien
- [ ] Le ML ne peut pas choisir seul le side
- [ ] Le ML ne bypass pas hard blocks / gating / portfolio
- [ ] Le ML produit un artefact versionné ou un comportement borné clair
- [ ] Modèle absent -> dégradation gracieuse

---

## 6. Tests
- [ ] Les tests ciblés annoncés existent vraiment
- [ ] Les résultats annoncés sont précis
- [ ] Le repo global n’est pas vendu comme vert si seul le slice l’est
- [ ] DAG PASS
- [ ] `new_violations=0`
- [ ] Aucun nouveau fichier `src/` ne dépasse le cap guardrail

---

## 7. Honnêteté du verdict
- [ ] COMPLETE seulement si le scope est réellement fermé
- [ ] PARTIAL si le slice est bon mais qu’un résidu externe reste ouvert
- [ ] BLOCKED si la décision humaine manque
- [ ] Le "Next safe step" est concret et non hallucinatoire

---

## 8. Verdict final de revue

### GREENLIGHT
À cocher seulement si tout est bon :
- [ ] doctrine respectée
- [ ] math respectées
- [ ] tests verts ciblés
- [ ] pas de dérive ML
- [ ] auditabilité forte

### REQUEST_FIX
À cocher si au moins un point majeur casse :
- [ ] formule floue ou changée sans autorisation
- [ ] scope non maîtrisé
- [ ] récit exagéré
- [ ] ML trop souverain
- [ ] résultat non reproductible
