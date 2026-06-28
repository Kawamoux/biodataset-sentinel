# BioDataset Sentinel

## Français

BioDataset Sentinel est un outil de contrôle qualité pré-analyse pour les jeux
de données biologiques. Son objectif est simple : détecter les erreurs
silencieuses avant qu'elles ne deviennent des résultats, des figures, des
conclusions ou des décisions de recherche. Le projet se concentre sur un cas
très fréquent en biologie computationnelle : une table d'échantillons, une
matrice de mesures biologiques et, si nécessaire, une table d'annotation des
features.

Un pipeline peut être statistiquement impeccable tout en produisant des
conclusions fragiles si les échantillons ne sont pas alignés, si une variable de
lot est confondue avec le phénotype, si une colonne dérivée de la cible fuit
dans les métadonnées, ou si une matrice contient des valeurs non numériques
introduites par erreur. BioDataset Sentinel transforme ces points faibles en
vérifications explicites, reproductibles et documentées.

### Pourquoi ce projet existe

Les équipes de recherche manipulent souvent des fichiers CSV, TSV ou exports de
LIMS avant d'entrer dans des outils plus spécialisés. À ce stade, plusieurs
erreurs peuvent passer inaperçues :

- échantillons présents dans la matrice mais absents de la table metadata ;
- doublons d'identifiants après fusion manuelle ;
- lignes de matrice constantes ou entièrement nulles ;
- distributions de profondeur de séquençage très déséquilibrées ;
- lots expérimentaux quasiment équivalents aux groupes biologiques ;
- colonnes de métadonnées contenant des chemins locaux, adresses e-mail ou
  informations non destinées à être partagées ;
- labels réutilisés par inadvertance dans des colonnes d'analyse.

Ces problèmes ne se voient pas toujours dans les tests unitaires d'un pipeline,
car ils appartiennent aux données elles-mêmes. BioDataset Sentinel sert de
garde-fou avant l'analyse, avant le dépôt public et avant la revue interne.

### Ce que l'outil vérifie

BioDataset Sentinel produit une liste structurée d'observations classées par
sévérité. Les catégories actuelles sont :

- **Schéma** : colonnes requises, noms de colonnes dupliqués, identifiants vides
  ou dupliqués.
- **Alignement** : correspondance entre les échantillons de la table metadata et
  les colonnes de la matrice.
- **Numérique** : valeurs manquantes, valeurs non numériques, valeurs négatives
  inattendues dans une matrice de comptages.
- **Sparsité** : proportion de zéros par échantillon et par feature.
- **Signal utile** : features constantes, features entièrement nulles,
  échantillons sans signal.
- **Profondeur / intensité globale** : taille de bibliothèque ou somme des
  mesures par échantillon, avec détection robuste des valeurs atypiques.
- **Réplicats** : groupes expérimentaux trop peu représentés pour une analyse
  fiable.
- **Confusion phénotype-lot** : association forte entre une colonne de lot et la
  variable d'intérêt.
- **Fuite potentielle de label** : colonnes de métadonnées qui prédisent
  parfaitement la cible et doivent être examinées.
- **Confidentialité** : motifs compatibles avec des chemins de fichiers locaux,
  adresses e-mail, numéros de téléphone ou jetons longs.

Chaque observation contient un identifiant stable, une sévérité, un message
court, un contexte exploitable et une recommandation. Les rapports peuvent être
consommés par un humain, un notebook ou une intégration CI.

### Installation

Depuis un clone du dépôt :

```bash
python -m pip install .
```

Pour développer et lancer les tests :

```bash
python -m pip install -e .
python -m unittest discover -s tests
```

Le projet ne dépend d'aucune bibliothèque externe pour son exécution. Cette
décision rend l'outil facile à auditer, simple à installer dans un environnement
isolé et stable dans les pipelines à long terme.

### Démarrage rapide

```bash
biosentinel audit \
  --samples examples/samples.csv \
  --matrix examples/counts.csv \
  --features examples/features.csv \
  --outcome-column condition \
  --batch-column batch \
  --html-report report.html \
  --json-report report.json
```

Le rapport HTML est destiné à la lecture humaine. Le rapport JSON est destiné à
l'archivage, au suivi de qualité, aux notebooks et aux contrôles automatisés.

### Utiliser BioDataset Sentinel avec MicroTrace ou MetaTrace

Les rapports MicroTrace contiennent généralement un dossier avec `summary.csv`,
`objects.csv`, `statistics.csv` et `report.html`. BioDataset Sentinel peut
auditer directement ce dossier :

```bash
biosentinel audit-microtrace results/pollen-html \
  --json-report microtrace-audit.json \
  --html-report microtrace-audit.html
```

L'alias suivant est aussi disponible si votre projet ou vos notes utilisent le
nom MetaTrace :

```bash
biosentinel audit-metatrace results/pollen-html \
  --json-report metatrace-audit.json
```

Ce mode vérifie la cohérence entre `summary.csv` et `objects.csv`, recalcule les
agrégats principaux, signale les valeurs numériques invalides, détecte les
objets qui touchent les bords de l'image et applique les mêmes garde-fous de
confidentialité aux identifiants d'images et aux métadonnées exportées. Le
rapport BioDataset Sentinel ne conserve pas le chemin absolu du dossier audité.

### Format attendu des fichiers

La table d'échantillons doit contenir une colonne `sample_id`.

```csv
sample_id,condition,batch,organism
S01,control,B1,Arabidopsis thaliana
S02,treated,B1,Arabidopsis thaliana
```

La matrice doit contenir une première colonne `feature_id`, puis une colonne par
échantillon.

```csv
feature_id,S01,S02
gene_001,42,51
gene_002,0,3
```

La table de features est optionnelle. Lorsqu'elle est fournie, elle doit contenir
une colonne `feature_id`.

```csv
feature_id,biotype
gene_001,protein_coding
gene_002,lncRNA
```

Les fichiers CSV et TSV sont détectés automatiquement à partir de leur contenu.
Les valeurs sont lues comme du texte pour les tables de métadonnées et comme des
nombres pour la matrice.

### Utilisation en Python

```python
from biosentinel import audit_dataset

report = audit_dataset(
    samples_path="examples/samples.csv",
    matrix_path="examples/counts.csv",
    features_path="examples/features.csv",
    outcome_column="condition",
    batch_column="batch",
)

print(report.summary.status)
for issue in report.issues:
    print(issue.severity, issue.code, issue.message)
```

L'API renvoie des objets de données explicites. Elle ne conserve pas les chemins
absolus des fichiers d'entrée dans le rapport, afin de limiter les fuites
d'information lorsque les rapports sont partagés.

### Sévérités

- `error` : problème structurel qui peut invalider l'analyse ou empêcher une
  interprétation correcte.
- `warning` : risque important qui mérite une revue avant de continuer.
- `info` : observation utile pour documenter la qualité du jeu de données.

Par défaut, la commande CLI renvoie un code de sortie non nul si au moins une
erreur est détectée. Ce comportement permet une utilisation en intégration
continue.

### Confidentialité et partage

BioDataset Sentinel est conçu pour être utilisé avant le partage d'un jeu de
données. L'outil signale les valeurs ressemblant à :

- des chemins Windows, Unix ou réseau ;
- des adresses e-mail ;
- des numéros de téléphone ;
- des jetons longs ou identifiants techniques difficiles à distinguer de secrets.

Le détecteur de confidentialité est volontairement conservateur. Un signalement
ne signifie pas qu'une donnée est forcément sensible ; il indique qu'une revue
humaine est nécessaire. Les exemples fournis dans ce dépôt sont synthétiques et
ne représentent aucune personne, aucun patient et aucun projet réel.

### Fiabilité scientifique

BioDataset Sentinel ne remplace pas l'expertise biologique, la planification
expérimentale ou les analyses statistiques spécialisées. Il agit plus tôt dans
la chaîne : il vérifie que les entrées de l'analyse sont cohérentes, lisibles et
documentées. Cette position est importante, car une erreur d'alignement ou de
lot peut survivre jusqu'à la fin d'un pipeline sans provoquer d'exception
technique.

Les vérifications sont volontairement explicables. L'outil privilégie des
heuristiques robustes, inspectables et faciles à défendre dans une revue de
code scientifique. Les valeurs atypiques sont détectées avec la médiane et la
déviation absolue médiane lorsque c'est pertinent, afin de limiter l'influence
des points extrêmes.

### Exemples de situations utiles

- préparation d'un dépôt public de données ;
- revue interne avant une analyse différentielle ;
- vérification rapide après fusion de métadonnées ;
- contrôle automatique dans un pipeline Snakemake, Nextflow ou Make ;
- audit de fichiers reçus d'un collaborateur ;
- documentation de la qualité d'un jeu de données dans un rapport de projet.

### Limites

L'outil ne détermine pas si un design expérimental est biologiquement optimal.
Il ne calcule pas de p-values pour les tests d'association, ne normalise pas les
données et ne choisit pas de modèle statistique. Les avertissements sur la
confusion ou la fuite de label doivent être interprétés avec le contexte du
projet.

### Feuille de route

- profils de validation adaptés à RNA-seq, protéomique et cytométrie ;
- export Markdown ;
- intégration optionnelle avec schémas déclaratifs ;
- seuils configurables par fichier YAML ;
- rapport comparatif entre plusieurs versions d'un même jeu de données.

### Contribution

Les contributions doivent rester reproductibles, testées et explicables. Toute
nouvelle vérification devrait inclure :

- un cas positif ;
- un cas négatif ;
- une recommandation claire pour l'utilisateur ;
- une justification scientifique courte dans la documentation ou le code.

---

## English

BioDataset Sentinel is a pre-analysis quality control tool for biological
datasets. Its purpose is straightforward: catch silent data problems before they
turn into results, figures, conclusions, or research decisions. The project
focuses on a common computational biology setup: a sample table, a biological
measurement matrix, and, when useful, a feature annotation table.

A pipeline can be statistically polished and still produce fragile conclusions
if samples are misaligned, a batch variable is confounded with the phenotype, a
target-derived column leaks into metadata, or a matrix contains accidental
non-numeric values. BioDataset Sentinel turns those weak points into explicit,
reproducible, documented checks.

### Why this project exists

Research teams often work with CSV, TSV, or LIMS exports before moving into more
specialized tools. At that stage, several errors can remain invisible:

- samples present in the matrix but missing from metadata;
- duplicated identifiers after manual merges;
- constant or all-zero matrix rows;
- strongly unbalanced sequencing depth or total signal;
- experimental batches nearly equivalent to biological groups;
- metadata columns containing local paths, e-mail addresses, or values that
  should not be shared;
- labels accidentally reused as analysis features.

These problems are not always caught by pipeline unit tests because they belong
to the data itself. BioDataset Sentinel is a guardrail before analysis, before
public deposition, and before internal review.

### What the tool checks

BioDataset Sentinel produces a structured list of findings grouped by severity.
Current categories include:

- **Schema**: required columns, duplicated column names, empty identifiers, and
  duplicated identifiers.
- **Alignment**: agreement between sample metadata rows and matrix columns.
- **Numeric validity**: missing values, non-numeric values, and unexpected
  negative values in count matrices.
- **Sparsity**: zero fraction by sample and by feature.
- **Useful signal**: constant features, all-zero features, and samples with no
  signal.
- **Depth / global intensity**: per-sample library size or total measurement
  signal, with robust outlier detection.
- **Replicates**: experimental groups with too few samples for reliable
  analysis.
- **Phenotype-batch confounding**: strong association between a batch column and
  the outcome of interest.
- **Possible label leakage**: metadata columns that perfectly predict the target
  and should be reviewed.
- **Privacy**: patterns compatible with local file paths, e-mail addresses,
  phone numbers, or long technical tokens.

Each finding contains a stable code, a severity, a short message, actionable
context, and a recommendation. Reports can be consumed by humans, notebooks, or
CI systems.

### Installation

From a local clone:

```bash
python -m pip install .
```

For development and tests:

```bash
python -m pip install -e .
python -m unittest discover -s tests
```

The runtime has no external dependency. This keeps the tool easy to audit,
simple to install in isolated environments, and stable in long-lived pipelines.

### Quick start

```bash
biosentinel audit \
  --samples examples/samples.csv \
  --matrix examples/counts.csv \
  --features examples/features.csv \
  --outcome-column condition \
  --batch-column batch \
  --html-report report.html \
  --json-report report.json
```

The HTML report is intended for human review. The JSON report is intended for
archival, quality tracking, notebooks, and automated checks.

### Using BioDataset Sentinel with MicroTrace or MetaTrace

MicroTrace reports usually contain a directory with `summary.csv`, `objects.csv`,
`statistics.csv`, and `report.html`. BioDataset Sentinel can audit that directory
directly:

```bash
biosentinel audit-microtrace results/pollen-html \
  --json-report microtrace-audit.json \
  --html-report microtrace-audit.html
```

The following alias is also available if your project or notes use the MetaTrace
name:

```bash
biosentinel audit-metatrace results/pollen-html \
  --json-report metatrace-audit.json
```

This mode checks consistency between `summary.csv` and `objects.csv`,
recalculates key aggregates, flags invalid numeric values, detects segmented
objects touching image boundaries, and applies the same privacy guardrails to
image identifiers and exported metadata. The BioDataset Sentinel report does not
store the absolute path of the audited directory.

### Expected file format

The sample table must contain a `sample_id` column.

```csv
sample_id,condition,batch,organism
S01,control,B1,Arabidopsis thaliana
S02,treated,B1,Arabidopsis thaliana
```

The matrix must contain a first `feature_id` column followed by one column per
sample.

```csv
feature_id,S01,S02
gene_001,42,51
gene_002,0,3
```

The feature table is optional. When provided, it must contain a `feature_id`
column.

```csv
feature_id,biotype
gene_001,protein_coding
gene_002,lncRNA
```

CSV and TSV files are detected from their content. Metadata tables are read as
text, and matrices are parsed as numeric values.

### Python API

```python
from biosentinel import audit_dataset

report = audit_dataset(
    samples_path="examples/samples.csv",
    matrix_path="examples/counts.csv",
    features_path="examples/features.csv",
    outcome_column="condition",
    batch_column="batch",
)

print(report.summary.status)
for issue in report.issues:
    print(issue.severity, issue.code, issue.message)
```

The API returns explicit data objects. It does not store absolute input file
paths in the report, limiting accidental information leakage when reports are
shared.

### Severities

- `error`: structural problem that can invalidate analysis or prevent correct
  interpretation.
- `warning`: important risk that should be reviewed before continuing.
- `info`: useful observation for documenting dataset quality.

By default, the CLI exits with a non-zero status when at least one error is
detected. This makes it suitable for continuous integration.

### Privacy and sharing

BioDataset Sentinel is designed to be used before sharing a dataset. It flags
values that look like:

- Windows, Unix, or network paths;
- e-mail addresses;
- phone numbers;
- long tokens or technical identifiers that are difficult to distinguish from
  secrets.

The privacy detector is intentionally conservative. A finding does not prove
that a value is sensitive; it means human review is required. The examples in
this repository are synthetic and do not represent any person, patient, or real
project.

### Scientific reliability

BioDataset Sentinel does not replace biological expertise, experimental design,
or specialized statistical analysis. It operates earlier in the chain: it checks
that analysis inputs are coherent, readable, and documented. This matters
because alignment and batch problems can survive until the end of a pipeline
without causing a technical exception.

The checks are intentionally explainable. The tool favors robust, inspectable
heuristics that are easy to defend in scientific code review. Outliers are
detected with the median and median absolute deviation when appropriate, so
extreme values have limited influence.

### Useful scenarios

- preparing a public data release;
- internal review before differential analysis;
- quick verification after metadata merges;
- automated checks in Snakemake, Nextflow, or Make pipelines;
- auditing files received from collaborators;
- documenting dataset quality in project reports.

### Limitations

The tool does not decide whether an experimental design is biologically optimal.
It does not compute association p-values, normalize data, or select a
statistical model. Confounding and leakage warnings must be interpreted in the
context of the project.

### Roadmap

- validation profiles for RNA-seq, proteomics, and cytometry;
- Markdown export;
- optional integration with declarative schemas;
- YAML-configurable thresholds;
- comparative reports across multiple versions of a dataset.

### Contributing

Contributions should remain reproducible, tested, and explainable. Each new
check should include:

- a positive case;
- a negative case;
- a clear recommendation for the user;
- a short scientific rationale in documentation or code.
