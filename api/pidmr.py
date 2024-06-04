from schemas.schemas import PIDMRRootSchema


def save_pidmr_event(event: PIDMRRootSchema) -> dict:
    # TODO: implement
    return {event.content.id}

# from schemas.schemas import University
# def get_all_universities_for_country(country: str) -> dict:
#     print('get_all_universities_for_country ', country)
#     params = {'country': country}
#     client = httpx.Client()
#     response = client.get("http://universities.hipolabs.com/search", params=params)
#     response_json = json.loads(response.text)
#     universities = []
#     for university in response_json:
#         university_obj = University.parse_obj(university)
#         universities.append(university_obj)
#     return {country: universities}
