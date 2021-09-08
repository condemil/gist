GIST_LIST = [{
    'id': 'gist1',
    'owner': {'login': 'some_user'},
    'description': 'some shell gist',
    'files': {
        'some_test.sh': {}
    }
},
{
    'id': 'gist2',
    'owner': {'login': 'some_user'},
    'description': 'some python gist',
    'files': {
        'file_one.py': {},
        'file_two.py': {}
    }
}]

GIST_STARRED_LIST = [{
    'id': 'gist3',
    'description': 'some starred gist',
    'owner': {'login': 'some_user'},
    'files': {
        'some_test.sh': {}
    }
}]

GIST_WITHOUT_DESCRIPTION = {
    'id': 'gist4',
    'owner': {'login': 'some_user'},
    'files': {
        'some_file.txt': {},
        'another_file.cpp': {}
    }
}

GIST_WITH_DESCRIPTION = {
    'id': 'gist5',
    'owner': {'login': 'some_user'},
    'description': 'some description',
    'files': {
        'some_file.txt': {},
        'another_file.cpp': {}
    }
}

GIST_WITH_FILE_CONTENT_AND_TYPE = {
    'id': 'gist6',
    'html_url': 'some html url',
    'description': 'some description',
    'url': 'some url',
    'files': {
        'some_file1.txt': {'type': 'text/plain', 'content': 'some content'},
        'some_file2.txt': {'type': 'application/something', 'content': 'another content'},
        'some_file3.txt': {'type': 'not_allowed_type/plain', 'content': 'another content'}
    }
}

GIST_WITH_RAW_URL = {
    'id': 'gist7',
    'files': {
        'some_file1.txt': {'raw_url': 'some raw url', 'content': 'some content'},
        'some_file2.txt': {'raw_url': 'some another raw url', 'content': 'another content'}
    }
}
