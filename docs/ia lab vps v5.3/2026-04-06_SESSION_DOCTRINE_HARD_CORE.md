# Session Doctrine Hard Core

Statut: regle de travail active pour toutes les prochaines sessions Codex sur V5.3.

## Regle

Chaque session Codex doit commencer avec un context brief explicite.

## Contenu obligatoire du context brief

- le module en cours
- les invariants globaux du systeme a preserver
- les modules qui doivent etre relies au module courant
- l'interface imposee pour ces connexions
- les defaults interdits sur la tranche en cours
- la checklist de verification explicite apres generation

## Format obligatoire

- `Tu travailles sur le module X.`
- `Le systeme global a ces invariants: [liste].`
- `Les modules Y et Z doivent etre connectes a X via [interface].`
- `Les defaults interdits sont: [liste].`
- `Apres generation, verifie explicitement: [checklist].`

## Intentions

- forcer l'ancrage de contexte au debut de chaque session
- reduire les changements implicites ou hors invariant
- rendre les defaults interdits visibles avant edition
- imposer une verification explicite et non implicite apres generation

## Portee

- s'applique aux sessions Codex de travail, audit, refactor, wiring et integration
- ne remplace pas le canon V5.3
- s'ajoute a la methodologie existante:
  - fondations canoniques avant raffinements visibles
  - gouvernance typee avant logique implicite
  - rail VPS sur avant ouverture Lab/control-plane
