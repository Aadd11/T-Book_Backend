from elasticsearch import AsyncElasticsearch
from .config import settings
from functools import lru_cache

@lru_cache()
def get_es_client() -> AsyncElasticsearch:
    return AsyncElasticsearch(
        hosts=[settings.ELASTICSEARCH_URL],
        retry_on_timeout=True,
        verify_certs=False,
        max_retries=10,
        request_timeout=30
    )

async def close_es_client():
    client = get_es_client()
    await client.close()

async def check_and_create_es_index():
    client = get_es_client()
    index_name = settings.ELASTICSEARCH_INDEX_NAME
    try:
        if not await client.ping():
            raise ConnectionError("Elasticsearch connection failed")

        if not await client.indices.exists(index=index_name):
            print(f"Creating Elasticsearch index: {index_name}")
            mapping = {
                "properties": {
                    "id": {"type": "keyword"},
                    "title": {"type": "text", "analyzer": "standard"},
                    "title_sort": {"type": "keyword"},
                    "year_published": {"type": "integer"},
                    "summary": {"type": "text", "analyzer": "standard"},
                    "age_rating": {"type": "keyword"},
                    "language": {"type": "keyword"},
                    "book_size_pages": {"type": "integer"},
                    "average_rating": {"type": "float"},
                    "isbn_13": {"type": "keyword"},
                    "authors": {
                        "type": "nested",
                        "properties": {
                            "id": {"type": "keyword"},
                            "name": {"type": "text"}
                        }
                    },
                    "genres": {
                        "type": "nested", 
                        "properties": {
                            "id": {"type": "keyword"},
                            "name": {"type": "text"}
                        }
                    },
                    "search_text": {"type": "text", "analyzer": "standard"}
                }
            }
            await client.indices.create(index=index_name, mappings=mapping)
            print(f"Index {index_name} created.")
        else:
             print(f"Elasticsearch index {index_name} already exists.")

    except Exception as e:
        print(f"Error connecting to or setting up Elasticsearch: {e}")