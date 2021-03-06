import os

import pytest

from jedi.api.project import Project
from test.helpers import root_dir


@pytest.mark.parametrize('type_', ['goto', 'infer'])
@pytest.mark.parametrize('way', ['direct', 'indirect'])
@pytest.mark.parametrize(
    'kwargs', [
        dict(only_stubs=False, prefer_stubs=False),
        dict(only_stubs=False, prefer_stubs=True),
        dict(only_stubs=True, prefer_stubs=False),
    ]
)
@pytest.mark.parametrize(
    ('code', 'full_name', 'has_stub', 'has_python', 'goto_changes'), [
        ['import os; os.walk', 'os.walk', True, True, {}],
        ['from collections import Counter', 'collections.Counter', True, True, {}],
        ['from collections', 'collections', True, True, {}],
        ['from collections import Counter; Counter', 'collections.Counter', True, True, {}],
        ['from collections import Counter; Counter()', 'collections.Counter', True, True, {}],
        ['from collections import Counter; Counter.most_common',
         'collections.Counter.most_common', True, True, {}],
        ['from collections import deque', 'collections.deque', True, False, {'has_python': True}],

        ['from keyword import kwlist; kwlist', 'typing.Sequence', True, True,
         {'full_name': 'keyword.kwlist'}],
        ['from keyword import kwlist', 'typing.Sequence', True, True,
         {'full_name': 'keyword.kwlist'}],

        ['from socket import AF_INET', 'socket.AddressFamily', True, False,
         {'full_name': 'socket.AF_INET'}],
        ['from socket import socket', 'socket.socket', True, True, {}],

        ['import with_stub', 'with_stub', True, True, {}],
        ['import with_stub', 'with_stub', True, True, {}],
        ['import with_stub_folder.python_only', 'with_stub_folder.python_only', False, True, {}],
        ['import stub_only', 'stub_only', True, False, {}],
    ])
def test_infer_and_goto(Script, code, full_name, has_stub, has_python, way,
                        kwargs, type_, goto_changes, environment):
    if environment.version_info < (3, 5):
        # We just don't care about much of the detailed Python 2 failures
        # anymore, because its end-of-life soon. (same for 3.4)
        pytest.skip()

    if type_ == 'infer' and full_name == 'typing.Sequence' and environment.version_info >= (3, 7):
        # In Python 3.7+ there's not really a sequence definition, there's just
        # a name that leads nowhere.
        has_python = False

    project = Project(os.path.join(root_dir, 'test', 'completion', 'stub_folder'))
    s = Script(code, _project=project)
    prefer_stubs = kwargs['prefer_stubs']
    only_stubs = kwargs['only_stubs']

    if type_ == 'goto':
        full_name = goto_changes.get('full_name', full_name)
        has_python = goto_changes.get('has_python', has_python)

    if way == 'direct':
        if type_ == 'goto':
            defs = s.goto_assignments(follow_imports=True, **kwargs)
        else:
            defs = s.goto_definitions(**kwargs)
    else:
        goto_defs = s.goto_assignments(
            # Prefering stubs when we want to go to python and vice versa
            prefer_stubs=not (prefer_stubs or only_stubs),
            follow_imports=True,
        )
        if type_ == 'goto':
            defs = [d for goto_def in goto_defs for d in goto_def.goto_assignments(**kwargs)]
        else:
            defs = [d for goto_def in goto_defs for d in goto_def.infer(**kwargs)]

    if not has_stub and only_stubs:
        assert not defs
    else:
        assert defs

    for d in defs:
        if prefer_stubs and has_stub:
            assert d.is_stub()
        elif only_stubs:
            assert d.is_stub()
        else:
            assert has_python == (not d.is_stub())
        assert d.full_name == full_name

        assert d.is_stub() == d.module_path.endswith('.pyi')
