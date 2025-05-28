import requests
import logging


logger = logging.getLogger(__name__)



async def search_records_by_name(search_name: str) -> list[int]:
    """
    Searchs for records relating to Customers
    Searches for records by name using an external API and returns their primary keys.

    Args:
        search_name: The name to search for.

    Returns:
        A list of primary keys (integers) of matching records.
    """
    return [1,2, 3, 5, 7, 11, 13, 17, 19, 23, 29] # Mocked data for testing purposes


    headers = {}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    params = {'search': search_name}
    response = requests.get(api_url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    # Assuming the API returns a list of records with a 'primary_key' field
    return [record['primary_key'] for record in data.get('results', [])]


async def delete_record_by_id(record_id: int) -> bool:
    """
    Deletes records for Customers by primary key
    Deletes a record by its primary key using an external API.

    Args:
        record_id: The primary key of the record to delete.

    Returns:
        True if the deletion was successful, False otherwise.
    """
    logger.debug(f'Deleting record with ID: {record_id}')
    return True # Mocked data for testing purposes

    headers = {}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    response = requests.delete(f'{api_url}/{record_id}', headers=headers)
    return response.status_code == 204
