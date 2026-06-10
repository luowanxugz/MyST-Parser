import copy
from typing import Any, Iterable, List


def transform_tokens(token_stream):
    result = []
    for i, token in enumerate(token_stream):
        if token.type == 'heading':
            new_token = copy.deepcopy(token)
            new_token.content = token.content.upper()
        result.append(new_token)
    return result


def transform_tokens_fixed(token_stream: Iterable[Any]) -> List[Any]:
    if token_stream is None:
        return []
    result = []
    for token in token_stream:
        try:
            if token is None:
                continue
            if getattr(token, 'type', None) == 'heading':
                new_token = copy.deepcopy(token)
                content = getattr(new_token, 'content', None)
                new_token.content = content.upper() if content is not None else content
                result.append(new_token)
            else:
                result.append(token)
        except Exception as exc:
            print(f"[transform_tokens] skipped token due to error: {exc!r}")
            if token is not None:
                result.append(token)
    return result


if __name__ == '__main__':
    class Token:
        def __init__(self, type_, content=None):
            self.type = type_
            self.content = content

        def __repr__(self):
            return f"Token({self.type!r}, {self.content!r})"

    tokens = [
        Token('heading', 'introduction'),
        Token('paragraph', 'hello world'),
        Token('heading', None),
        None,
        Token('heading', 'details'),
    ]

    print("original :", tokens)
    print("fixed    :", transform_tokens_fixed(tokens))
    print("None     :", transform_tokens_fixed(None))
    print("empty    :", transform_tokens_fixed([]))
