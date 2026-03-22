"""Optional S3-compatible storage (e.g. MinIO) for rendered outputs and upload staging."""
from __future__ import annotations

import logging
import os
from pathlib import Path

_log = logging.getLogger("brainrot.s3")

_client = None


def is_enabled() -> bool:
    return bool(os.environ.get("S3_ENDPOINT_URL", "").strip())


def _bucket() -> str:
    return os.environ.get("S3_BUCKET", "brainrot").strip()


def _client_s3():
    global _client
    if _client is not None:
        return _client
    import boto3
    from botocore.config import Config

    endpoint = os.environ["S3_ENDPOINT_URL"].strip()
    key = os.environ.get("AWS_ACCESS_KEY_ID", "minioadmin").strip()
    secret = os.environ.get("AWS_SECRET_ACCESS_KEY", "minioadmin").strip()
    region = os.environ.get("AWS_REGION", "us-east-1").strip()
    _client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=key,
        aws_secret_access_key=secret,
        region_name=region,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )
    return _client


def ensure_bucket() -> None:
    if not is_enabled():
        print("[s3] ensure_bucket: S3_ENDPOINT_URL not set, skipping", flush=True)
        return
    s3 = _client_s3()
    b = _bucket()
    ep = os.environ.get("S3_ENDPOINT_URL", "").strip()
    print(f"[s3] ensure_bucket endpoint={ep!r} bucket={b!r}", flush=True)
    try:
        s3.head_bucket(Bucket=b)
        print(f"[s3] head_bucket ok {b!r}", flush=True)
    except Exception:
        try:
            s3.create_bucket(Bucket=b)
            print(f"[s3] create_bucket ok {b!r}", flush=True)
        except Exception as e:
            print(f"[s3] create_bucket raised {e!r}, trying head again …", flush=True)
            _log.warning("create_bucket: %s", e)
            # MinIO may return BucketAlreadyOwnedByYou etc.
            s3.head_bucket(Bucket=b)


def put_file(key: str, local_path: Path) -> None:
    try:
        sz = local_path.stat().st_size
    except OSError:
        sz = -1
    print(f"[s3] put_file key={key!r} local_bytes={sz}", flush=True)
    s3 = _client_s3()
    s3.upload_file(str(local_path), _bucket(), key)
    print(f"[s3] put_file done key={key!r}", flush=True)


def delete_object(key: str) -> None:
    s3 = _client_s3()
    s3.delete_object(Bucket=_bucket(), Key=key)


def download_to_path(key: str, dest: Path) -> None:
    print(f"[s3] download_to_path key={key!r} → {dest}", flush=True)
    s3 = _client_s3()
    dest.parent.mkdir(parents=True, exist_ok=True)
    s3.download_file(_bucket(), key, str(dest))
    try:
        dz = dest.stat().st_size
    except OSError:
        dz = -1
    print(f"[s3] download_to_path done bytes={dz}", flush=True)


def exists(key: str) -> bool:
    from botocore.exceptions import ClientError

    s3 = _client_s3()
    try:
        s3.head_object(Bucket=_bucket(), Key=key)
        return True
    except ClientError as e:
        code = str(e.response.get("Error", {}).get("Code", ""))
        http = int(e.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0) or 0)
        if code in ("404", "NoSuchKey", "NotFound") or http == 404:
            return False
        raise


def response_for_key(key: str, download_name: str, mimetype: str):
    """Stream object body as a Flask Response."""
    from flask import Response

    s3 = _client_s3()
    obj = s3.get_object(Bucket=_bucket(), Key=key)
    body = obj["Body"]

    def generate():
        try:
            for chunk in body.iter_chunks(chunk_size=64 * 1024):
                yield chunk
        finally:
            body.close()

    return Response(
        generate(),
        mimetype=mimetype,
        headers={"Content-Disposition": f'inline; filename="{download_name}"'},
    )
