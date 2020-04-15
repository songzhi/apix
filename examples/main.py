from typing import List

from pydantic import BaseModel

from apix.endpoint import get


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
    data: List[User]


@get('https://reqres.in/api/users')
def get_users(page: int) -> UsersResponse:
    ...


async def main():
    users = get_users(2)
    print(users)


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
