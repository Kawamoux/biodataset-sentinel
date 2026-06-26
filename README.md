# BioDataset Sentinel

## Francais

BioDataset Sentinel est un outil de controle qualite pre-analyse pour les jeux
de donnees biologiques. Son objectif est simple : detecter les erreurs
silencieuses avant qu'elles ne deviennent des resultats, des figures, des
conclusions ou des decisions de recherche. Le projet se concentre sur un cas
tres frequent en biologie computationnelle : une table d'echantillons, une
matrice de mesures biologiques et, si necessaire, une table d'annotation des
features.

Un pipeline peut etre statistiquement impeccable tout en produisant des
conclusions fragiles si les echantillons ne sont pas alignes, si une variable de
lot est confondue avec le phenotype, si une colonne derivee de la cible fuit
dans les metadonnees, ou si une matrice contient des valeurs non numeriques
introduites par erreur. BioDataset Sentinel transforme ces points faibles en
verifications explicites, reproductibles et documentees.

### Pourquoi ce projet existe

Les equipes de recherche manipulent souvent des fichiers CSV, TSV ou exports de
LIMS avant d'entrer dans des outils plus specialises. A ce stade, plusieurs
erreurs peuvent passer inapercues :

- echantillons presents dans la matrice mais absents de la table metadata ;
- doublons d'identifiants apres fusion manuelle ;
- lignes de matrice constantes ou entierement nulles ;
- distributions de profondeur de sequencage tres desequilibrees ;
- lots experimentaux quasiment equivalents aux groupes biologiques ;
- colonnes de metadonnees contenant des chemins locaux, adresses e-mail ou
  informations non destinees a etre partagees ;
- labels reutilises par inadvertance dans des colonnes d'analyse.

Ces problemes ne se voient pas toujours dans les tests unitaires d'un pipeline,
car ils appartiennent aux donnees elles-memes. BioDataset Sentinel sert de
garde-fou avant l'analyse, avant le depot public et avant la revue interne.

### Ce que l'outil verifie

BioDataset Sentinel produit une liste structuree d'observations classees par
severite. Les categories actuelles sont :

- **Schema** : colonnes requises, noms de colonnes dupliques, identifiants vides
  ou dupliques.
- **Alignement** : correspondance entre les echantillons de la table metadata et
  les colonnes de la matrice.
- **Numerique** : valeurs manquantes, valeurs non numeriques, valeurs negatives
  inattendues dans une matrice de comptages.
- **Sparsity** : proportion de zeros par echantillon et par feature.
- **Signal utile** : features constantes, features entierement nulles,
  echantillons sans signal.
- **Profondeur / intensite globale** : taille de bibliotheque ou somme des
  mesures par echantillon, avec detection robuste des valeurs atypiques.
- **Replicats** : groupes experimentaux trop peu representes pour une analyse
  fiable.
- **Confusion phenotype-lot** : association forte entre une colonne de lot et la
  variable d'interet.
- **Fuite potentielle de label** : colonnes de metadonnees qui predisent
  parfaitement la cible et doivent etre examinees.
- **Confidentialite** : motifs compatibles avec des chemins de fichiers locaux,
  adresses e-mail, numeros de telephone ou jetons longs.

Chaque observation contient un identifiant stable, une severite, un message
court, un contexte exploitable et une recommandation. Les rapports peuvent etre
consommes par un humain, un notebook ou une integration CI.

### Installation

Depuis un clone du depot :

```bash
python -m pip install .
```

Pour developper et lancer les tests :

```bash
python -m pip install -e .
python -m unittest discover -s tests
```

Le projet ne depend d'aucune bibliotheque externe pour son execution. Cette
decision rend l'outil facile a auditer, simple a installer dans un environnement
isole et stable dans les pipelines a long terme.

### Demarrage rapide

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

Le rapport HTML est destine a la lecture humaine. Le rapport JSON est destine a
l'archivage, au suivi de qualite, aux notebooks et aux controles automatises.

### Format attendu des fichiers

La table d'echantillons doit contenir une colonne `sample_id`.

```csv
sample_id,condition,batch,organism
S01,control,B1,Arabidopsis thaliana
S02,treated,B1,Arabidopsis thaliana
```

La matrice doit contenir une premiere colonne `feature_id`, puis une colonne par
echantillon.

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

Les fichiers CSV et TSV sont detectes automatiquement a partir de leur contenu.
Les valeurs sont lues comme du texte pour les tables de metadonnees et comme des
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

L'API renvoie des objets de donnees explicites. Elle ne conserve pas les chemins
absolus des fichiers d'entree dans le rapport, afin de limiter les fuites
d'information lorsque les rapports sont partages.

### Severites

- `error` : probleme structurel qui peut invalider l'analyse ou empecher une
  interpretation correcte.
- `warning` : risque important qui merite une revue avant de continuer.
- `info` : observation utile pour documenter la qualite du jeu de donnees.

Par defaut, la commande CLI renvoie un code de sortie non nul si au moins une
erreur est detectee. Ce comportement permet une utilisation en integration
continue.

### Confidentialite et partage

BioDataset Sentinel est concu pour etre utilise avant le partage d'un jeu de
donnees. L'outil signale les valeurs ressemblant a :

- des chemins Windows, Unix ou reseau ;
- des adresses e-mail ;
- des numeros de telephone ;
- des jetons longs ou identifiants techniques difficiles a distinguer de secrets.

Le detecteur de confidentialite est volontairement conservateur. Un signalement
ne signifie pas qu'une donnee est forcement sensible ; il indique qu'une revue
humaine est necessaire. Les exemples fournis dans ce depot sont synthetiques et
ne representent aucune personne, aucun patient et aucun projet reel.

### Fiabilite scientifique

BioDataset Sentinel ne remplace pas l'expertise biologique, la planification
experimentale ou les analyses statistiques specialisees. Il agit plus tot dans
la chaine : il verifie que les entrees de l'analyse sont coherentes, lisibles et
documentees. Cette position est importante, car une erreur d'alignement ou de
lot peut survivre jusqu'a la fin d'un pipeline sans provoquer d'exception
technique.

Les verifications sont volontairement explicables. L'outil privilegie des
heuristiques robustes, inspectables et faciles a defendre dans une revue de
code scientifique. Les valeurs atypiques sont detectees avec la mediane et la
deviation absolue mediane lorsque c'est pertinent, afin de limiter l'influence
des points extremes.

### Exemples de situations utiles

- preparation d'un depot public de donnees ;
- revue interne avant une analyse differentielle ;
- verification rapide apres fusion de metadonnees ;
- controle automatique dans un pipeline Snakemake, Nextflow ou Make ;
- audit de fichiers recus d'un collaborateur ;
- documentation de la qualite d'un jeu de donnees dans un rapport de projet.

### Limites

L'outil ne determine pas si un design experimental est biologiquement optimal.
Il ne calcule pas de p-values pour les tests d'association, ne normalise pas les
donnees et ne choisit pas de modele statistique. Les avertissements sur la
confusion ou la fuite de label doivent etre interpretes avec le contexte du
projet.

### Feuille de route

- profils de validation adaptes a RNA-seq, proteomique et cytometrie ;
- export Markdown ;
- integration optionnelle avec schemas declaratifs ;
- seuils configurables par fichier YAML ;
- rapport comparatif entre plusieurs versions d'un meme jeu de donnees.

### Contribution

Les contributions doivent rester reproductibles, testees et explicables. Toute
nouvelle verification devrait inclure :

- un cas positif ;
- un cas negatif ;
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
