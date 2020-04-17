from pydantic import BaseModel

from apix.dependencies.utils import get_dependant, get_body_field


def test_body_field():
    class Item(BaseModel):
        pass

    def foo(item: Item) -> Item:
        ...

    dependant = get_dependant(path='/', call=foo, name='foo')
    body_field = get_body_field(dependant=dependant, name='foo')
    print(body_field)
