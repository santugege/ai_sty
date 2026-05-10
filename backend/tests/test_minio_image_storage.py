from app.image_storage import MinioImageStorage


class FakeS3Client:
    def __init__(self):
        self.objects = {}
        self.deleted = []

    def put_object(self, Bucket, Key, Body, ContentType):
        self.objects[(Bucket, Key)] = {
            "body": Body,
            "content_type": ContentType,
        }

    def get_object(self, Bucket, Key):
        class Body:
            def read(self_inner):
                return self.objects[(Bucket, Key)]["body"]

        return {"Body": Body()}

    def delete_object(self, Bucket, Key):
        self.deleted.append((Bucket, Key))


def test_minio_storage_writes_reads_and_deletes_image():
    client = FakeS3Client()
    storage = MinioImageStorage(
        bucket="agent-images",
        client=client,
        public_endpoint="http://localhost:9000",
    )

    stored = storage.write_image(
        b"image-bytes",
        mime_type="image/png",
        prefix="agent-sessions/session-1",
    )

    assert stored.storage_key.startswith("agent-sessions/session-1/")
    assert stored.public_url == f"http://localhost:9000/agent-images/{stored.storage_key}"
    assert storage.read_image(stored.storage_key) == b"image-bytes"

    storage.delete_image(stored.storage_key)

    assert client.deleted == [("agent-images", stored.storage_key)]
