## Typed HTTP Client for Humans
It's inspired by [FastAPI](https://fastapi.tiangolo.com/) and 
based on [pydantic](https://pydantic-docs.helpmanual.io/) and 
[httpx](https://www.python-httpx.org/).
It's currently a very rough demo for experiment.
 
## Example
```python
from typing import List

from pydantic import BaseModel

from apix import get, Service, Query


class User(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    avatar: str


class UsersResponse(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int
    data: List['User']


class Paging(BaseModel):
    page: int


class UserService(Service):
    # `@staticmethod` or `@classmethod` for specified-level client
    @get('/api/users')
    def get_users(self, paging: Paging = Query(...)) -> UsersResponse:
        ...
# or 

@get('https://reqres.in/api/users')
def get_users(self, paging: Paging = Query(...)) -> UsersResponse:
    ...


def main():
    paging = Paging(page=1)
    print(UserService(base_url='https://reqres.in').get_users(paging))
    print(UserService.get_users(paging))
    print(UserService.get_users(UserService(base_url='https://reqres.in'),paging))
    print(get_users(paging))

if __name__ == '__main__':
    main()
```

## Features
### Multi-level 'client'
if using single decorator like `get`, all endpoints sharing one client.
if defined in a class, there will be a class-level client and instance-level
client.