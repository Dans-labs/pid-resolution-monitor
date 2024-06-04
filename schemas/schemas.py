from typing import List, Optional

from pydantic import BaseModel


class Pid(BaseModel):
    pids: List[str]

    class Config:
        json_schema_extra = {
            "example": {
                "pids": ["https://doi.org/10.15167/tomasi-federico_phd2019-03-14", "10.5281/zenodo.4672413"]
            }
        }


class ResolutionMode(BaseModel):
    mode: str
    name: str
    endpoint: Optional[str] = None


class ContentItem(BaseModel):
    id: int
    type: str
    name: str
    description: str
    resolution_modes: List[ResolutionMode]
    examples: List[str]


class PIDMRRootSchema(BaseModel):
    size_of_page: int
    number_of_page: int
    total_elements: int
    total_pages: int
    content: List[ContentItem]

    class Config:
        json_schema_extra = {
            "example": {
                "size_of_page": 2,
                "number_of_page": 1,
                "total_elements": 100,
                "total_pages": 50,
                "content": [
                    {
                        "id": 1,
                        "type": "doi",
                        "name": "Digital Object Identifier",
                        "description": "A digital object identifier is a persistent identifier used to uniquely identify objects.",
                        "resolution_modes": [
                            {
                                "mode": "metadata",
                                "name": "Metadata Resolution"
                            },
                            {
                                "mode": "landingpage",
                                "name": "Landing Page Resolution"
                            }
                        ],
                        "examples": [
                            "10.1000/xyz123"
                        ]
                    },
                    {
                        "id": 2,
                        "type": "isbn",
                        "name": "International Standard Book Number",
                        "description": "An ISBN is an International Standard Book Number.",
                        "resolution_modes": [
                            {
                                "mode": "resource",
                                "name": "Resource Resolution"
                            }
                        ],
                        "examples": [
                            "978-3-16-148410-0"
                        ]
                    }
                ],
                "links": []
            }
        }
