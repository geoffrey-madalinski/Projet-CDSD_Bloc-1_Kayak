"""
data_lake.py
------------
Gestion du data lake AWS S3.

Le data lake stocke les fichiers bruts/nettoyés tels quels (ici en CSV).
C'est une zone de stockage peu coûteuse et capable d'accueillir de gros
volumes : on y dépose les données avant l'étape ETL vers l'entrepôt.

Les identifiants AWS ne sont JAMAIS écrits ici : ils sont lus depuis
les variables d'environnement (chargées depuis le .env), pour rester
conforme aux bonnes pratiques de sécurité.
"""

import os
import pandas as pd
import boto3
from . import config


def _client_s3():
    """Crée un client S3 à partir des identifiants présents dans le .env."""
    return boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=config.S3_REGION,
    )


def uploader_csv(chemin_local, nom_objet, bucket=None):
    """Envoie un fichier CSV local vers le bucket S3 sous le préfixe configuré."""
    bucket = bucket or config.S3_BUCKET
    cle = config.S3_PREFIX + nom_objet
    client = _client_s3()
    client.upload_file(str(chemin_local), bucket, cle)
    print(f"  [OK] upload : s3://{bucket}/{cle}")


def telecharger_csv(nom_objet, bucket=None):
    """
    Lit un CSV directement depuis S3 et le renvoie comme DataFrame.

    On lit le flux sans le sauvegarder sur disque : utile pour l'étape
    Extract de l'ETL.
    """

    bucket = bucket or config.S3_BUCKET
    cle = config.S3_PREFIX + nom_objet
    client = _client_s3()
    objet = client.get_object(Bucket=bucket, Key=cle)
    return pd.read_csv(objet["Body"])
