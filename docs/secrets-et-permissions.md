# A5 — Secrets GitHub Actions, GITHUB_TOKEN et Kubernetes Secrets

## Secrets GitHub Actions

Un secret GitHub Actions (Settings → Secrets and variables → Actions) est stocké **chiffré** par GitHub et n'est déchiffré qu'au moment où un job y fait référence (`${{ secrets.NOM }}`). Il est **masqué** dans les logs (remplacé par `***`). Bonnes pratiques : un secret par usage et par environnement ; secrets d'**environnement** (`production`) protégés par des *required reviewers* ; ne jamais les exposer aux workflows déclenchés par des forks (`pull_request_target` à éviter) ; préférer l'**OIDC** (jeton fédéré de courte durée vers AWS/Azure/GCP/Vault) à une clé longue durée. Le masquage n'est pas une protection : un `echo $SECRET | base64` contourne le masque, d'où la revue des workflows.

## Permissions minimales du GITHUB_TOKEN

GitHub crée un `GITHUB_TOKEN` éphémère pour chaque exécution. Par défaut, selon le paramétrage du dépôt ou de l'organisation, il peut avoir des droits d'écriture larges. Notre workflow déclare au niveau racine :

```yaml
permissions:
  contents: read
```

Toutes les permissions non listées passent à `none`. Un job qui en a besoin élève ses droits **localement** (ex. `security-events: write` uniquement pour le job qui publie un rapport SARIF). On ajoute `persist-credentials: false` au checkout pour que le jeton ne reste pas dans `.git/config` à disposition des étapes suivantes. Si un outil du pipeline est compromis, il ne peut donc ni pousser du code, ni créer de release, ni modifier les workflows.

## Pourquoi un Kubernetes Secret non chiffré côté stockage n'est pas un coffre-fort

Un `Secret` Kubernetes est par défaut simplement **encodé en base64** (réversible, ce n'est pas du chiffrement) et stocké dans **etcd en clair** si l'*encryption at rest* n'est pas configurée (`EncryptionConfiguration` avec un fournisseur KMS). Conséquences : quiconque lit etcd ou ses sauvegardes lit les secrets ; tout utilisateur ayant `get secrets` dans le namespace (RBAC) les lit ; tout pod du namespace peut monter le secret ; le secret apparaît dans les manifestes s'il est versionné. Il manque aussi ce qu'apporte un vrai coffre (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault…) : **chiffrement avec clés gérées**, **journal d'audit** des accès, **rotation** automatique, **secrets dynamiques** à durée de vie courte, contrôle d'accès fin. Approche recommandée : chiffrement d'etcd via KMS, RBAC restrictif, et synchronisation depuis un coffre (External Secrets Operator, Vault Agent, ou Sealed Secrets/SOPS pour le GitOps).
