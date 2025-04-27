from elasticsearch import AsyncElasticsearch, NotFoundError
from elasticsearch.helpers import async_bulk
from app.core.config import settings
from app.core.es import get_es_client
from app.schemas.book import Book as BookSchema
from app.models.book import Book as BookModel
from typing import List, Dict, Any, Tuple

def _prepare_book_for_es(book: BookModel) -> Dict[str, Any]:
    """Converts a SQLAlchemy Book model to an Elasticsearch document dict."""
    authors = [{"id": str(a.id), "name": a.name} for a in book.authors]
    genres = [{"id": str(g.id), "name": g.name} for g in book.genres]

    search_text_parts = [book.title or ""]
    search_text_parts.extend(a["name"] for a in authors)
    search_text_parts.extend(g["name"] for g in genres)
    search_text_parts.append(book.summary or "")
    search_text = " ".join(filter(None, search_text_parts))

    title_sort = book.title.lower()
    for article in ["the ", "a ", "an "]:
        if title_sort.startswith(article):
            title_sort = title_sort[len(article):]
            break

    doc = {
        "id": str(book.id),
        "title": book.title,
        "title_sort": title_sort,
        "authors": authors,
        "year_published": book.year_published,
        "genres": genres,
        "summary": book.summary,
        "age_rating": book.age_rating,
        "language": book.language,
        "book_size_pages": book.book_size_pages,
        "average_rating": book.average_rating,
        "isbn_13": book.isbn_13,
        "search_text": search_text
    }
    return {k: v for k, v in doc.items() if v is not None}


async def index_book(book: BookModel):
    """Indexes or updates a single book in Elasticsearch."""
    client = get_es_client()
    index_name = settings.ELASTICSEARCH_INDEX_NAME
    doc_id = str(book.id)
    document = _prepare_book_for_es(book)

    try:
        await client.index(index=index_name, id=doc_id, document=document)
        print(f"Indexed book {doc_id} ({book.title})")
    except Exception as e:
        print(f"Error indexing book {doc_id}: {e}")


async def bulk_index_books(books: List[BookModel]):
    """Indexes a list of books using Elasticsearch bulk API."""
    client = get_es_client()
    index_name = settings.ELASTICSEARCH_INDEX_NAME

    actions = [
        {
            "_op_type": "index",
            "_index": index_name,
            "_id": str(book.id),
            "_source": _prepare_book_for_es(book)
        }
        for book in books
    ]

    if not actions:
        return

    try:
        success, failed = await async_bulk(client, actions, raise_on_error=False, raise_on_exception=False)
        print(f"Bulk indexed {success} books.")
        if failed:
            print(f"Failed to index {len(failed)} books: {failed[:5]}...")
    except Exception as e:
        print(f"Error during bulk indexing: {e}")


async def delete_book_from_index(book_id: str):
     """Deletes a book from the Elasticsearch index."""
     client = get_es_client()
     index_name = settings.ELASTICSEARCH_INDEX_NAME
     try:
         await client.delete(index=index_name, id=book_id)
         print(f"Deleted book {book_id} from index")
     except NotFoundError:
          print(f"Book {book_id} not found in index for deletion.")
     except Exception as e:
         print(f"Error deleting book {book_id} from index: {e}")


async def search_books_in_es(
    query: str | None = None,
    filters: Dict[str, Any] | None = None,
    sort_by: str | None = None,
    page: int = 1,
    page_size: int = 20
) -> Tuple[List[Dict[str, Any]], int]:
    """Performs search and filtering in Elasticsearch."""
    client = get_es_client()
    index_name = settings.ELASTICSEARCH_INDEX_NAME
    es_query: Dict[str, Any] = {"bool": {"must": [], "filter": []}}
    sort_criteria: List[Any] = []

    if query:
        es_query["bool"]["must"].append({
            "query_string": {
                "query": query,
                "fields": ["title^3", "authors^2", "summary", "search_text", "genres"],
                "default_operator": "AND"
            }
        })
    else:
         es_query["bool"]["must"].append({"match_all": {}})


    if filters:
        for field, value in filters.items():
            if value is None: continue

            if field == "min_year" and isinstance(value, int):
                es_query["bool"]["filter"].append({"range": {"year_published": {"gte": value}}})
            elif field == "max_year" and isinstance(value, int):
                 es_query["bool"]["filter"].append({"range": {"year_published": {"lte": value}}})
            elif field == "min_rating" and isinstance(value, (int, float)):
                 es_query["bool"]["filter"].append({"range": {"average_rating": {"gte": value}}})
            elif field in ["genre", "language", "author", "age_rating"]:
                 es_field = "genres" if field == "genre" else \
                            "authors" if field == "author" else \
                            field
                 es_query["bool"]["filter"].append({"term": {es_field: value}})

    if not es_query["bool"]["filter"]:
        del es_query["bool"]["filter"]


    if sort_by and sort_by != "relevance":
        field_map = {
            "rating": "average_rating",
            "year": "year_published",
            "size": "book_size_pages",
            "title": "title_sort",
        }
        order = "desc"
        sort_field = sort_by
        if sort_by.endswith("_asc"):
            order = "asc"
            sort_field = sort_by[:-4]
        elif sort_by.endswith("_desc"):
            order = "desc"
            sort_field = sort_by[:-5]

        es_sort_field = field_map.get(sort_field)
        if es_sort_field:
            sort_criteria.append({es_sort_field: {"order": order, "missing": "_last"}})

    sort_criteria.append({"_score": {"order": "desc"}})

    try:
        response = await client.search(
            index=index_name,
            query=es_query,
            sort=sort_criteria,
            from_=(page - 1) * page_size,
            size=page_size,
            track_total_hits=True
        )

        hits = response['hits']['hits']
        total_hits = response['hits']['total']['value']
        results = [hit['_source'] for hit in hits]
        return results, total_hits

    except Exception as e:
        print(f"Error searching Elasticsearch: {e}")
        return [], 0