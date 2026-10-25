"""Controlled object API for HTTP/SQL integration; never a real S3 acceptance."""

from datetime import UTC, datetime
import io
import threading

from botocore.exceptions import ClientError


class SyntheticS3Objects:
    def __init__(self):
        self.objects = {}
        self.modified = {}
        self.closed = False
        self.lock = threading.Lock()

    def put_object(self, **arguments):
        with self.lock:
            assert not self.closed and arguments["IfNoneMatch"] == "*"
            key = arguments["Key"]
            if key in self.objects:
                raise ClientError({"Error": {"Code": "PreconditionFailed"}}, "PutObject")
            self.objects[key] = arguments["Body"]
            self.modified[key] = datetime.now(UTC)
        return {}

    def get_object(self, **arguments):
        with self.lock:
            assert not self.closed
            try:
                payload = self.objects[arguments["Key"]]
            except KeyError:
                raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject") from None
            return {"Body": io.BytesIO(payload), "ContentLength": len(payload)}

    def delete_object(self, **arguments):
        with self.lock:
            assert not self.closed
            self.objects.pop(arguments["Key"], None)
            self.modified.pop(arguments["Key"], None)
        return {}

    def list_objects_v2(self, **arguments):
        with self.lock:
            assert not self.closed and arguments["Prefix"] == "v1/"
            keys = [key for key in sorted(self.objects) if key > arguments.get("ContinuationToken", "")]
            chosen = keys[:arguments["MaxKeys"]]
            truncated = len(keys) > len(chosen)
            return {"IsTruncated": truncated,
                    "NextContinuationToken": chosen[-1] if truncated else "",
                    "Contents": [{"Key": key, "LastModified": self.modified[key]} for key in chosen]}

    def close(self):
        self.closed = True
