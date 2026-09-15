from knowledge_vector_store.contracts import VectorRecord
from knowledge_vector_store.milvus import MilvusVectorStore


class FakeMilvusClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.upserts = []
        self.searches = []

    def upsert(self, **kwargs):
        self.upserts.append(kwargs)

    def search(self, **kwargs):
        self.searches.append(kwargs)
        return [[{"id": "chunk-a", "distance": 0.9, "entity": {"tenant_id": "tenant-a"}}]]


def make_store():
    holder = {}

    def factory(**kwargs):
        holder["client"] = FakeMilvusClient(**kwargs)
        return holder["client"]

    return MilvusVectorStore(uri="http://milvus:19530", token=None, collection="chunks", client_factory=factory), holder


def test_upsert_carries_tenant_and_index_version():
    store, holder = make_store()
    count = store.upsert(
        [VectorRecord("c1", "tenant-a", "d1", "v1", "idx1", (0.1, 0.2))]
    )
    assert count == 1
    row = holder["client"].upserts[0]["data"][0]
    assert row["tenant_id"] == "tenant-a"
    assert row["index_version"] == "idx1"


def test_search_always_injects_tenant_and_index_filter():
    store, holder = make_store()
    store.search(tenant_id="tenant-a", index_version="idx1", embedding=[0.1, 0.2], limit=5)
    expression = holder["client"].searches[0]["filter"]
    assert 'tenant_id == "tenant-a"' in expression
    assert 'index_version == "idx1"' in expression


def test_search_rejects_missing_tenant_scope():
    store, _ = make_store()
    try:
        store.search(tenant_id="", index_version="idx1", embedding=[0.1], limit=5)
    except ValueError as exc:
        assert str(exc) == "tenant_id_and_index_version_are_required"
    else:
        raise AssertionError("missing tenant scope must be rejected")

