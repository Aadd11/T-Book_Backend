from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends
from app.schemas.genre import GenrePublic
from app.schemas.author import AuthorPublic
from app.schemas.book import SearchRequest, SearchResponse, BookPublic
from app.schemas.common import PaginatedResponse
from app.tasks.scrape import process_search_query
from app.services.search_service import search_books_in_es
from app.core.es import get_es_client
from elasticsearch import AsyncElasticsearch

router = APIRouter()

@router.post("/", response_model=SearchResponse, status_code=status.HTTP_202_ACCEPTED)
async def initiate_search(
    search_request: SearchRequest,
    background_tasks: BackgroundTasks,
    es_client: AsyncElasticsearch = Depends(get_es_client)
):
    """
    Accepts a search query, optionally returns immediate results from Elasticsearch,
    and triggers a background task to fetch/update data from external sources
    (now searches OpenLib & Google by Author & Title).
    """
    print(f"Received explicit search request via POST: {search_request.query}")

    initial_results, total_hits = await search_books_in_es(
        query=search_request.query,
        page=search_request.page,
        page_size=search_request.page_size,
    )

    if search_request.query and search_request.query.strip():
        task = process_search_query.delay(search_request.query)
        print(f"Dispatched background task {task.id} for query: {search_request.query}")
        message = "Search task accepted. Returning initial results from existing data. Index will be updated in the background from multiple sources."
        task_id = task.id
    else:
        print("No query provided in search request, background task not dispatched.")
        message = "No query provided. Returning initial results based on filters/defaults only. No background task dispatched."
        task_id = None

    public_results = [
        BookPublic(
            **{k: v for k, v in result.items() if k not in ['authors', 'genres']},
            authors=[AuthorPublic(**a) for a in result.get("authors", [])],
            genres=[GenrePublic(**g) for g in result.get("genres", [])]
        )
        for result in initial_results
    ]

    return SearchResponse(
        task_id=task_id,
        message=message,
        initial_results=public_results,
        total_hits=total_hits
    )