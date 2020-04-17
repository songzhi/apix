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
    print(get_users(paging))


if __name__ == '__main__':
    main()
