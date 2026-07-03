from hdfs import InsecureClient
from pathlib import Path

HDFS_URL = "http://localhost:9870"
HDFS_USER = "root"

client = InsecureClient(HDFS_URL, user=HDFS_USER)


def upload_to_hdfs(local_path: str, hdfs_dir: str) -> str:
    """Upload un fichier local vers HDFS et retourne le chemin HDFS complet."""
    local_path = Path(local_path)
    hdfs_path = f"{hdfs_dir}/{local_path.name}"

    client.makedirs(hdfs_dir)
    client.upload(hdfs_path, str(local_path), overwrite=True)

    return hdfs_path