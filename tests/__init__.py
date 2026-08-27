"""The suite is a package.

Not decoration: `tests/core/conftest.py` and `tests/conftest.py` are two modules with the
same name, and without `__init__.py` files mypy cannot tell them apart and refuses to check
either. The tests are type-checked under the same `strict` setting as `src/`, because a
test that does not type-check is a test that can quietly stop asserting what it says.
"""
