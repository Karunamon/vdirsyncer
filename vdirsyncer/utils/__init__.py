# -*- coding: utf-8 -*-

import os
import sys

from .compat import iteritems
from .. import exceptions


_missing = object()


def expand_path(p):
    p = os.path.expanduser(p)
    p = os.path.normpath(p)
    return p


def split_dict(d, f):
    '''Puts key into first dict if f(key), otherwise in second dict'''
    a, b = split_sequence(iteritems(d), lambda item: f(item[0]))
    return dict(a), dict(b)


def split_sequence(s, f):
    '''Puts item into first list if f(item), else in second list'''
    a = []
    b = []
    for item in s:
        if f(item):
            a.append(item)
        else:
            b.append(item)

    return a, b


def uniq(s):
    '''Filter duplicates while preserving order. ``set`` can almost always be
    used instead of this, but preserving order might prove useful for
    debugging.'''
    d = set()
    for x in s:
        if x not in d:
            d.add(x)
            yield x


def get_etag_from_file(fpath):
    '''Get mtime-based etag from a filepath.'''
    stat = os.stat(fpath)
    mtime = getattr(stat, 'st_mtime_ns', None)
    if mtime is None:
        mtime = stat.st_mtime
    return '{:.9f}'.format(mtime)


def get_etag_from_fileobject(f):
    '''
    Get mtime-based etag from a local file's fileobject.

    This function will flush/sync the file as much as necessary to obtain a
    correct mtime.

    In filesystem-based storages, this is used instead of
    :py:func:`get_etag_from_file` to determine the correct etag *before*
    writing the temporary file to the target location.

    This works because, as far as I've tested, moving and linking a file
    doesn't change its mtime.
    '''
    f.flush()  # Only this is necessary on Linux
    if sys.platform == 'win32':
        os.fsync(f.fileno())  # Apparently necessary on Windows
    return get_etag_from_file(f.name)


def get_class_init_specs(cls, stop_at=object):
    if cls is stop_at:
        return ()
    import inspect
    spec = inspect.getargspec(cls.__init__)
    supercls = next(getattr(x.__init__, '__objclass__', x)
                    for x in cls.__mro__[1:])
    return (spec,) + get_class_init_specs(supercls, stop_at=stop_at)


def get_class_init_args(cls, stop_at=object):
    '''
    Get args which are taken during class initialization. Assumes that all
    classes' __init__ calls super().__init__ with the rest of the arguments.

    :param cls: The class to inspect.
    :returns: (all, required), where ``all`` is a set of all arguments the
        class can take, and ``required`` is the subset of arguments the class
        requires.
    '''
    all, required = set(), set()
    for spec in get_class_init_specs(cls, stop_at=stop_at):
        all.update(spec.args[1:])
        required.update(spec.args[1:-len(spec.defaults or ())])

    return all, required


def checkdir(path, create=False, mode=0o750):
    '''
    Check whether ``path`` is a directory.

    :param create: Whether to create the directory (and all parent directories)
        if it does not exist.
    :param mode: Mode to create missing directories with.
    '''

    if not os.path.isdir(path):
        if os.path.exists(path):
            raise IOError('{} is not a directory.'.format(path))
        if create:
            os.makedirs(path, mode)
        else:
            raise exceptions.CollectionNotFound('Directory {} does not exist.'
                                                .format(path))


def checkfile(path, create=False):
    '''
    Check whether ``path`` is a file.

    :param create: Whether to create the file's parent directories if they do
        not exist.
    '''
    checkdir(os.path.dirname(path), create=create)
    if not os.path.isfile(path):
        if os.path.exists(path):
            raise IOError('{} is not a file.'.format(path))
        if create:
            with open(path, 'wb'):
                pass
        else:
            raise exceptions.CollectionNotFound('File {} does not exist.'
                                                .format(path))


class cached_property(object):
    '''
    Copied from Werkzeug.
    Copyright 2007-2014 Armin Ronacher
    '''

    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, _missing)
        if value is _missing:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value
