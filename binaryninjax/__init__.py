from ctypes import byref as c_byref, cast as c_cast, CFUNCTYPE, c_int, c_void_p, c_char_p
import sip
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Q_ARG, Q_RETURN_ARG
import binaryninja

from ._selfsym import resolve_symbol


_q_app = QtWidgets.QApplication.instance()


def _on_main_thread(func):
    def wrapper(*args, **kwargs):
        binaryninja.mainthread.execute_on_main_thread_and_wait(lambda: func(*args, **kwargs))
    return wrapper


class _CMethodProxy(object):
    def __init__(self, func, this_ptr):
        self._func = func
        self._this_ptr = this_ptr

    def __call__(self, *args):
        return self._func(self._this_ptr, *args)


class _CObjectProxy(object):
    _c_funcptrs = {}

    def __init__(self, c_ptr, c_api):
        self._c_ptr = c_ptr
        self._c_api = c_api

    def __getattr__(self, attr):
        if attr in self._c_api:
            func_name, func_sig = self._c_api[attr]
            if func_name not in self.__class__._c_funcptrs:
                func_addr = resolve_symbol(func_name)
                if func_addr is None:
                    raise AttributeError("Symbol {} is not defined".format(func_name))
                self.__class__._c_funcptrs[func_name] = func_addr
            func_addr = self.__class__._c_funcptrs[func_name]

            proxy = _CMethodProxy(func_sig(func_addr), self._c_ptr)
            setattr(self, attr, proxy)
            return proxy
        else:
            raise AttributeError("undefined method '{}'".format(attr))

    def _pointer(self):
        return sip.unwrapinstance(self._c_ptr)


class _QMethodProxy(object):
    def __init__(self, q_metaobject, q_self, name):
        self._q_metaobject = q_metaobject
        self._q_self = q_self
        self.name = name

    def __call__(self, *args):
        self._q_metaobject.invokeMethod(self._q_self, self.name, *args)


class _QObjectProxy(_CObjectProxy):
    _q_methods = {}
    _q_properties = {}

    def __init__(self, q_object, c_api={}):
        _CObjectProxy.__init__(self, sip.unwrapinstance(q_object), c_api)

        self._q_object = q_object
        self._q_metaobject = q_object.metaObject()
        if self._q_metaobject not in self.__class__._q_methods:
            self.__class__._q_methods[self._q_metaobject] = \
                [str(self._q_metaobject.method(n).name())
                 for n in range(self._q_metaobject.methodCount())]
        if self._q_metaobject not in self.__class__._q_properties:
            self.__class__._q_properties[self._q_metaobject] = \
                [str(self._q_metaobject.property(n).name())
                 for n in range(self._q_metaobject.propertyCount())]

    def __getattr__(self, attr):
        if attr in self.__class__._q_methods[self._q_metaobject]:
            proxy = _QMethodProxy(self._q_metaobject, self._q_object, attr)
            setattr(self, attr, proxy)
            return proxy
        else:
            try:
                return _CObjectProxy.__getattr__(self, attr)
            except AttributeError:
                raise AttributeError("class '{}' does not have method '{}'"
                                     .format(self._className(), attr))

    def _className(self):
        return self._q_metaobject.className()

    def _methods(self):
        return self.__class__._q_methods[self._q_metaobject]

    def _properties(self):
        return self.__class__._q_properties[self._q_metaobject]


# PyQt5 doesn't provide QString anymore, so we have to bind it ourselves.
class _QString(object):
    _c_api = {
        'QString':    ('_ZN7QStringC2EPKc', CFUNCTYPE(None, c_void_p, c_char_p)),
        '_d_QString': ('_ZN7QStringD2Ev',   CFUNCTYPE(None, c_void_p))
    }

    def __init__(self, value=None):
        self._data = c_void_p() # a QString is a single QStringData *
        try:
            self._c = _CObjectProxy(c_byref(self._data),
                                    self.__class__._c_api)
            self._c.QString(value)
        except:
            self._c = None
            raise

    def __del__(self):
        if self._c is not None:
            self._c._d_QString()


class MainWindow(object):
    """Main Binary Ninja window."""

    _c_api = {
        'openFilename':         ('_ZN10MainWindow12openFilenameERK7QString',
                                 CFUNCTYPE(c_int, c_void_p, c_void_p)),
        'openUrl':              ('_ZN10MainWindow7openUrlERK4QUrl',
                                 CFUNCTYPE(c_int, c_void_p, c_void_p)),
        'getCurrentView':       ('_ZN10MainWindow14getCurrentViewEv',
                                 CFUNCTYPE(c_void_p, c_void_p))
    }

    @classmethod
    def active(cls):
        """Return the main window that currently has focus, or None if there isn't any.
        This includes the case where a dock window or a menu is active."""
        q_active_window = _q_app.activeWindow()
        if q_active_window is not None:
            if q_active_window.metaObject().className() == "MainWindow":
                return cls(q_active_window)

    def __init__(self, q_main_window):
        self._q = _QObjectProxy(q_main_window, self.__class__._c_api)

    def newWindow(self):
        """Opens a new window."""
        self._q.newWindow()

    def newTab(self):
        """Opens a new tab."""
        self._q.newTab()

    def newBinary(self):
        """Opens a new tab with a new binary file."""
        self._q.newBinary()

    def nextTab(self):
        """Switches to next tab."""
        self._q.nextTab()

    def previousTab(self):
        """Switches to previous tab."""
        self._q.previousTab()

    def newWindowForTab(self):
        """Extracts the current tab into a new window."""
        self._q.newWindowForTab()

    def splitToNewTab(self):
        """Splits the current view into a new tab."""
        self._q.splitToNewTab()

    def splitToNewWindow(self):
        """Splits the current view into a new window."""
        self._q.splitToNewWindow()

    def closeTab(self):
        """Closes the current tab."""
        self._q.closeTab()

    def closeAll(self):
        """Closes all tabs."""
        self._q.closeTab()

    def navigateBack(self):
        """Navigates back in history."""
        self._q.navigateBack(Q_ARG(bool, False))

    def navigateForward(self):
        """Navigates forward in history."""
        self._q.navigateForward(Q_ARG(bool, False))

    def open(self):
        """Opens the file open dialog."""
        self._q.open()

    @_on_main_thread
    def openFilename(self, filename):
        """Opens the given filename."""
        q_filename = _QString(filename)
        self._q.openFilename(c_byref(q_filename._data))

    def openUrlDialog(self):
        """Opens the URL open dialog."""
        self._q.openUrlDialog()

    @_on_main_thread
    def openUrl(self, url):
        """Opens the given URL."""
        q_url = QtCore.QUrl(url)
        self._q.openUrl(sip.unwrapinstance(q_url))

    def save(self):
        """Saves the database."""
        self._q.saveDatabase()

    def saveAs(self):
        """Opens the binary contents save dialog."""
        self._q.saveAs()

    def getCurrentView(self):
        """Returns the currently active view."""
        view = self._q.getCurrentView()


def active_window():
    """Returns the focused main window. See :meth:`MainWindow.active`."""
    return MainWindow.active()
