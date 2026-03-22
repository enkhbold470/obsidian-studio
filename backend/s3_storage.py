"""Optional S3-compatible storage (e.g. MinIO) for rendered outputs and upload staging."""
from __future__ import annotations

import os
from pathlib import Path

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
        return
    s3 = _client_s3()
    b = _bucket()
    try:
        s3.head_bucket(Bucket=b)
    except Exception:
        try:
            s3.create_bucket(Bucket=b)
        except Exception:
            # MinIO may return BucketAlreadyOwnedByYou etc.
            s3.head_bucket(Bucket=b)


def put_file(key: str, local_path: Path) -> None:
    s3 = _client_s3()
    s3.upload_file(str(local_path), _bucket(), key)


def delete_object(key: str) -> None:
    s3 = _client_s3()
    s3.delete_object(Bucket=_bucket(), Key=key)


def download_to_path(key: str, dest: Path) -> None:
    s3 = _client_s3()
    dest.parent.mkdir(parents=True, exist_ok=True)
    s3.download_file(_bucket(), key, str(dest))


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
