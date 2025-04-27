import time
import random
import asyncio
import httpx
import json
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlencode
import traceback

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.crud.crud_book import find_existing_book, create_book, update_book
from app.schemas.book import BookCreate, BookUpdate
from app.services.search_service import index_book

DEFAULT_MAX_RESULTS_PER_CALL = 5
SEARCH_SOURCES = ["openlib", "google"]
SEARCH_FIELDS = ["author", "title"]

def parse_external_book(book_data: Dict[str, Any], authors_map: Dict[str, str], genres_map: Dict[str, str], book_author_rels: Dict[str, List[str]], book_genre_rels: Dict[str, List[str]]) -> Optional[BookCreate]:
    """
    Parses a book dictionary from the external API into a BookCreate schema.
    """
    book_id = book_data.get("id")
    if not book_id:
        return None

    author_ids_for_book = book_author_rels.get(book_id, [])
    genre_ids_for_book = book_genre_rels.get(book_id, [])

    author_names = [authors_map[author_id] for author_id in author_ids_for_book if author_id in authors_map]
    genre_names = [genres_map[genre_id] for genre_id in genre_ids_for_book if genre_id in genres_map]

    rating_details_raw = book_data.get("rating_details")
    rating_details_parsed = None
    if isinstance(rating_details_raw, str):
        try:
            rating_details_parsed = json.loads(rating_details_raw)
            if isinstance(rating_details_parsed, dict):
                 if "open_library" in rating_details_parsed:
                     ol_data = rating_details_parsed["open_library"]
                     rating_details_parsed = [{
                         "source": "OpenLibrary",
                         "rating": ol_data.get("rating"),
                         "votes": ol_data.get("votes")
                     }]
                 else:
                    rating_details_parsed = [rating_details_parsed]
            elif not isinstance(rating_details_parsed, list):
                rating_details_parsed = None
        except json.JSONDecodeError:
            print(f"Warning: Could not parse rating_details JSON for book {book_id}: {rating_details_raw}")
            rating_details_parsed = None
    elif isinstance(rating_details_raw, list):
        rating_details_parsed = rating_details_raw

    try:
        return BookCreate(
            title=book_data.get("title"),
            year_published=book_data.get("year_published"),
            summary=book_data.get("summary") if book_data.get("summary") != "No description available" else None,
            age_rating=book_data.get("age_rating"),
            language=book_data.get("language"),
            book_size_pages=book_data.get("book_size_pages"),
            book_size_description=book_data.get("book_size_description"),
            average_rating=book_data.get("average_rating"),
            rating_details=rating_details_parsed,
            source_url=book_data.get("source_url"),
            isbn_10=book_data.get("isbn_10"),
            isbn_13=book_data.get("isbn_13"),
            author_names=author_names,
            genre_names=genre_names,
        )
    except Exception as e:
        print(f"Error creating BookCreate schema for book {book_id} ('{book_data.get('title')}'): {e}")
        return None

async def _fetch_from_external_api(
    client: httpx.AsyncClient,
    source: str,
    params: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Makes a single call to the external API and returns the 'data' part or None on error."""
    base_url = settings.EXTERNAL_SEARCH_API_BASE_URL
    if not base_url:
        return None

    encoded_params = urlencode({k: v for k, v in params.items() if v is not None})
    api_url = f"{base_url}/api/search/{source}?{encoded_params}"
    print(f"--> Calling external API: {api_url}")

    try:
        response = await client.get(api_url)
        response.raise_for_status()
        raw_data = response.json()
        print(f"<-- API call successful for: {api_url} (status: {response.status_code})")
        if raw_data and "data" in raw_data:
            return raw_data["data"]
        else:
            print(f"Warning: Invalid or empty data structure received from {api_url}")
            return None
    except httpx.TimeoutException:
        print(f"Error: Timeout occurred calling {api_url}")
        return None
    except httpx.HTTPStatusError as e:
        print(f"Error: HTTP error calling {api_url}: {e.response.status_code} - {e.request.url}")
        return None
    except (httpx.RequestError, json.JSONDecodeError) as e:
        print(f"Error: Failed to call or parse response from {api_url}: {type(e).__name__} - {e}")
        return None
    except Exception as e:
        print(f"Error: Unexpected error during API call to {api_url}: {type(e).__name__} - {e}")
        return None

@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
async def process_search_query(self, query: str):
    """
    Celery task to fetch book data from multiple external API sources (Google, OpenLib)
    searching by both author and title using the provided query.
    It aggregates results, saves/updates them in the database, and indexes in Elasticsearch.
    Ensures the return value is always pickleable, even on failure.
    """
    if not query or not query.strip():
        print("Task skipped: Received empty query.")
        return {"query": query, "status": "skipped", "message": "Empty query"}

    print(f"TASK STARTED for query: '{query}'")
    print(f"Sources: {SEARCH_SOURCES}, Fields: {SEARCH_FIELDS}")

    processed_count = 0
    created_count = 0
    updated_count = 0
    failed_processing_count = 0
    unique_books_api_count = 0
    api_calls_made = 0
    successful_api_calls = 0
    api_errors_encountered = 0

    try:
        base_url = settings.EXTERNAL_SEARCH_API_BASE_URL
        if not base_url:
            print("Error: EXTERNAL_SEARCH_API_BASE_URL is not configured. Aborting task.")
            return {"query": query, "status": "error", "message": "External API URL not configured"}

        all_books_api: List[Dict[str, Any]] = []
        all_authors_api: List[Dict[str, Any]] = []
        all_genres_api: List[Dict[str, Any]] = []
        all_book_author_rels_api: List[Dict[str, str]] = []
        all_book_genre_rels_api: List[Dict[str, str]] = []
        api_calls_made = 0
        successful_api_calls = 0
        api_errors_encountered = 0

        async with httpx.AsyncClient(timeout=60.0) as client:
            for source in SEARCH_SOURCES:
                for field in SEARCH_FIELDS:
                    params = {
                        "author": query if field == "author" else None,
                        "title": query if field == "title" else None,
                        "max_results": DEFAULT_MAX_RESULTS_PER_CALL,
                        "language": "en"
                    }

                    if not params.get("author") and not params.get("title"):
                        print(f"Skipping API call for source={source}, field={field}: Query resulted in empty params.")
                        continue

                    api_calls_made += 1
                    api_data = await _fetch_from_external_api(client, source, params)

                    if api_data:
                        successful_api_calls += 1
                        all_books_api.extend(api_data.get("books", []))
                        all_authors_api.extend(api_data.get("authors", []))
                        all_genres_api.extend(api_data.get("genres", []))
                        relationships = api_data.get("relationships", {})
                        all_book_author_rels_api.extend(relationships.get("book_authors", []))
                        all_book_genre_rels_api.extend(relationships.get("book_genres", []))
                    else:
                        print(f"API call failed or returned no data for source={source}, field={field}.")
                        api_errors_encountered += 1

                    await asyncio.sleep(random.uniform(0.5, 1.5))

        print(f"Finished API calls. Made: {api_calls_made}, Successful: {successful_api_calls}, Errors: {api_errors_encountered}.")
        print(f"Aggregated: {len(all_books_api)} books, {len(all_authors_api)} authors, {len(all_genres_api)} genres.")

        if not all_books_api:
            print(f"No books found in total for query '{query}' from external APIs.")
            return {
                "query": query,
                "status": "completed_no_results",
                "message": "No books found from APIs",
                "api_calls_made": int(api_calls_made),
                "successful_api_calls": int(successful_api_calls),
                "api_errors_encountered": int(api_errors_encountered),
            }

        authors_map = {a["id"]: a["name"] for a in all_authors_api if "id" in a and "name" in a}
        genres_map = {g["id"]: g.get("original_name", g.get("name")) for g in all_genres_api if "id" in g and ("name" in g or "original_name" in g)}

        book_author_rels: Dict[str, set[str]] = {}
        for rel in all_book_author_rels_api:
            book_id = rel.get("book_id")
            author_id = rel.get("author_id")
            if book_id and author_id:
                book_author_rels.setdefault(book_id, set()).add(author_id)

        book_genre_rels: Dict[str, set[str]] = {}
        for rel in all_book_genre_rels_api:
            book_id = rel.get("book_id")
            genre_id = rel.get("genre_id")
            if book_id and genre_id:
                book_genre_rels.setdefault(book_id, set()).add(genre_id)

        book_author_rels_list: Dict[str, List[str]] = {k: list(v) for k, v in book_author_rels.items()}
        book_genre_rels_list: Dict[str, List[str]] = {k: list(v) for k, v in book_genre_rels.items()}

        unique_books_api: Dict[str, Dict[str, Any]] = {}
        for book in all_books_api:
            book_id = book.get("id")
            if book_id:
                if book_id not in unique_books_api:
                     unique_books_api[book_id] = book
        unique_books_api_count = len(unique_books_api)
        print(f"Processing {unique_books_api_count} unique books (by ID) after aggregation.")


        processed_count = 0
        created_count = 0
        updated_count = 0
        failed_processing_count = 0
        async with AsyncSessionLocal() as db:
            for book_api_data in unique_books_api.values():
                book_create_schema = parse_external_book(
                    book_api_data, authors_map, genres_map, book_author_rels_list, book_genre_rels_list
                )

                if not book_create_schema:
                    failed_processing_count += 1
                    continue

                try:
                    existing_book = await find_existing_book(db, book_create_schema)

                    if existing_book:
                        update_data = BookUpdate(
                            **book_create_schema.model_dump(exclude_unset=True, exclude={'author_names', 'genre_names'})
                        )
                        updated_book = await update_book(db, existing_book, update_data)
                        await index_book(updated_book)
                        updated_count += 1
                    else:
                        new_book = await create_book(db, book_create_schema)
                        await index_book(new_book)
                        created_count += 1

                    processed_count += 1
                    if processed_count > 0 and processed_count % 10 == 0:
                        try:
                            await db.commit()
                            print(f"Committed batch at {processed_count} processed books.")
                        except Exception as commit_e:
                            print(f"ERROR during batch commit at {processed_count}: {type(commit_e).__name__} - {commit_e}")
                            await db.rollback()

                except Exception as book_process_e:
                    failed_processing_count += 1
                    print(f"Error processing book '{book_create_schema.title}' (ID: {book_api_data.get('id')}): {type(book_process_e).__name__} - {book_process_e}")
                    await db.rollback()

            try:
                await db.commit()
                print("Committed final batch.")
            except Exception as final_commit_e:
                 print(f"ERROR during final commit for query '{query}': {type(final_commit_e).__name__} - {final_commit_e}")
                 traceback.print_exc()
                 await db.rollback()

        print(f"TASK FINISHED SUCCESSFULLY for query: '{query}'.")
        print(f"Results => Processed: {processed_count}, Created: {created_count}, Updated: {updated_count}, Failed (processing): {failed_processing_count} (out of {unique_books_api_count} unique books fetched).")
        return {
            "query": str(query),
            "status": "completed",
            "processed_count": int(processed_count),
            "created_count": int(created_count),
            "updated_count": int(updated_count),
            "failed_processing_count": int(failed_processing_count),
            "unique_books_fetched": int(unique_books_api_count),
            "api_calls_made": int(api_calls_made),
            "successful_api_calls": int(successful_api_calls),
            "api_errors_encountered": int(api_errors_encountered),
        }

    except Exception as overall_task_e:
        error_type = type(overall_task_e).__name__
        error_message = str(overall_task_e)
        print(f"OVERALL TASK FAILED for query '{query}': {error_type} - {error_message}")
        traceback.print_exc()

        return {
            "query": query,
            "status": "failed",
            "error_type": error_type,
            "error_message": "Task failed due to an internal error. Check worker logs for details.",
            "processed_count_before_failure": int(processed_count),
            "failed_processing_count": int(failed_processing_count),
            "unique_books_fetched": int(unique_books_api_count),
            "api_calls_made": int(api_calls_made),
            "successful_api_calls": int(successful_api_calls),
            "api_errors_encountered": int(api_errors_encountered),
        }