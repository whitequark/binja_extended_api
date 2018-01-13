from __future__ import print_function
import sys, os, traceback
from functools import wraps
import binaryninja as bn
import sip
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Q_ARG, Q_RETURN_ARG
from ctypes import CDLL, CFUNCTYPE
from ctypes import byref as c_byref, cast as c_cast, sizeof as c_sizeof
from ctypes import c_int, c_void_p, c_char_p

from ._selfsym import resolve_symbol


def on_main_thread(func):
    """Wrap `func` to synchronously execute on the main thread."""

    # or the arguments would get replaced with *args, **kwargs
    if os.getenv('READTHEDOCS'): return func

    @wraps(func)
    def wrapper(*args, **kwargs):
        cell = [None] # no `nonlocal`
        def exn_wrapper():
            try:
                cell[0] = (True, func(*args, **kwargs))
            except Exception:
                bn.log.log_error(traceback.format_exc())
                cell[0] = (False, sys.exc_value)

        bn.mainthread.execute_on_main_thread_and_wait(exn_wrapper)

        is_ok, result = cell[0]
        if is_ok:
            return result
        else:
            print("An exception has occurred while running a function on the main thread.\n"
                  "See the log window for the rest of the backtrace.",
                  file=sys.stderr)
            raise result
    return wrapper


def _q_meta_object_for_name(name):
    return sip.wrapinstance(resolve_symbol('_ZN{}16staticMetaObjectE'.format(name)),
                            QtCore.QMetaObject)

def _q_iter_children(q_object):
    for child in q_object.children():
        yield child
        for deep_child in _q_iter_children(child):
            yield deep_child


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
            if func_name not in self._c_funcptrs:
                func_addr = resolve_symbol(func_name)
                if func_addr is None:
                    raise AttributeError("Symbol {} is not defined".format(func_name))
                self._c_funcptrs[func_name] = func_addr
            func_addr = self._c_funcptrs[func_name]

            proxy = _CMethodProxy(func_sig(func_addr), self._c_ptr)
            setattr(self, attr, proxy)
            return proxy
        else:
            raise AttributeError("undefined method '{}'".format(attr))

    def _pointer(self):
        return sip.unwrapinstance(self._c_ptr)


class _QMethodProxy(object):
    def __init__(self, q_meta_object, q_self, name):
        self._q_meta_object = q_meta_object
        self._q_self = q_self
        self.name = name

    def __call__(self, *args):
        self._q_meta_object.invokeMethod(self._q_self, self.name, *args)


class _QObjectProxy(_CObjectProxy):
    _q_methods = {}
    _q_properties = {}

    def __init__(self, q_meta_object, q_object, c_api={}):
        _CObjectProxy.__init__(self, sip.unwrapinstance(q_object), c_api)
        self._q_meta_object = q_meta_object
        self._q_object = q_object

        if self._q_meta_object != q_object.metaObject():
            raise TypeError("proxy for '{}' cannot be initialized from a pointer to '{}'"
                            .format(q_meta_object.className(),
                                    q_object.metaObject().className()))

        if self._q_meta_object not in self._q_methods:
            self._q_methods[self._q_meta_object] = \
                [str(self._q_meta_object.method(n).name())
                 for n in range(self._q_meta_object.methodCount())]
        if self._q_meta_object not in self._q_properties:
            self._q_properties[self._q_meta_object] = \
                [str(self._q_meta_object.property(n).name())
                 for n in range(self._q_meta_object.propertyCount())]

    def __getattr__(self, attr):
        if attr in self._q_methods[self._q_meta_object]:
            proxy = _QMethodProxy(self._q_meta_object, self._q_object, attr)
            setattr(self, attr, proxy)
            return proxy
        elif attr in self._c_api:
            return _CObjectProxy.__getattr__(self, attr)
        else:
            return getattr(self._q_object, attr)

    def _className(self):
        return self._q_meta_object.className()

    def _methods(self):
        return self._q_methods[self._q_meta_object]

    def _properties(self):
        return self._q_properties[self._q_meta_object]


_self_dll = CDLL("binaryninja", handle=0)

_new = CFUNCTYPE(c_void_p, c_int)(('_Znwm', _self_dll))
_delete = CFUNCTYPE(None, c_void_p)(('_ZdlPv', _self_dll))


# PyQt5 doesn't provide QString anymore, so we have to bind it ourselves.
class _QString(object):
    _c_api = {
        'QString':    ('_ZN7QStringC2EPKc', CFUNCTYPE(None, c_void_p, c_char_p)),
        '_d_QString': ('_ZN7QStringD2Ev',   CFUNCTYPE(None, c_void_p)),
    }

    def __init__(self, value=None):
        self._owned = False
        if isinstance(value, c_void_p):
            self._c = _CObjectProxy(value, self._c_api)
        elif value is None or isinstance(value, str):
            _c_ptr = _new(c_sizeof(c_void_p))
            self._c = _CObjectProxy(_c_ptr, self._c_api)
            self._c.QString(value)
            self._owned = True
        else:
            raise TypeError("QString can only be initialized with None, str, or a pointer")

    def __del__(self):
        if self._owned:
            self._c._d_QString()
            _delete(self._pointer())

    def _pointer(self):
        return self._c._c_ptr


class MainWindow(object):
    """
    Main Binary Ninja window.

    :ivar q: underlying Qt widget proxy
    """

    _q_meta_object = _q_meta_object_for_name('10MainWindow')

    _c_active_window = None

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
        if cls._c_active_window is None:
            cls._c_active_window = \
                CFUNCTYPE(c_void_p)(resolve_symbol('_ZN10MainWindow15getActiveWindowEv'))
        """Return the main window that currently has focus, or None if there isn't any.
        This includes the case where a dock window or a menu is active."""
        return cls(sip.wrapinstance(cls._c_active_window(), QtWidgets.QMainWindow))

    def __init__(self, q_main_window):
        self.q = _QObjectProxy(self._q_meta_object, q_main_window, self._c_api)

    def newWindow(self):
        """Opens a new window."""
        self.q.newWindow()

    def newTab(self):
        """Opens a new tab."""
        self.q.newTab()

    def newBinary(self):
        """Opens a new tab with a new binary file."""
        self.q.newBinary()

    def nextTab(self):
        """Switches to next tab."""
        self.q.nextTab()

    def previousTab(self):
        """Switches to previous tab."""
        self.q.previousTab()

    def newWindowForTab(self):
        """Extracts the current tab into a new window."""
        self.q.newWindowForTab()

    def splitToNewTab(self):
        """Splits the current view into a new tab."""
        self.q.splitToNewTab()

    def splitToNewWindow(self):
        """Splits the current view into a new window."""
        self.q.splitToNewWindow()

    def closeTab(self):
        """Closes the current tab."""
        self.q.closeTab()

    def closeAll(self):
        """Closes all tabs."""
        self.q.closeTab()

    def navigateBack(self):
        """Navigates back in history."""
        self.q.navigateBack(Q_ARG(bool, False))

    def navigateForward(self):
        """Navigates forward in history."""
        self.q.navigateForward(Q_ARG(bool, False))

    def open(self):
        """Opens the file open dialog."""
        self.q.open()

    @on_main_thread
    def openFilename(self, filename):
        """Opens the given filename in a new tab."""
        q_filename = _QString(filename)
        self.q.openFilename(q_filename._pointer())

    def openUrlDialog(self):
        """Opens the URL open dialog."""
        self.q.openUrlDialog()

    @on_main_thread
    def openUrl(self, url):
        """Opens the given URL in a new tab."""
        q_url = QtCore.QUrl(url)
        self.q.openUrl(sip.unwrapinstance(q_url))

    def save(self):
        """Saves the database."""
        self.q.saveDatabase()

    def saveAs(self):
        """Opens the binary contents save dialog."""
        self.q.saveAs()

    def getCurrentView(self):
        """
        :return: view frame for the currently active tab
        :rtype: :class:`ViewFrame`
        """
        p_view_frame = self.q.getCurrentView()
        if p_view_frame:
            q_view_frame = sip.wrapinstance(p_view_frame, QtWidgets.QWidget)
            return ViewFrame(q_view_frame)


class ViewFrame(object):
    """
    A view frame, that is, the info panel and the disassembly view bound to a particular
    binary view.

    :ivar q: underlying Qt widget proxy
    """

    _q_meta_object = _q_meta_object_for_name('9ViewFrame')

    _c_api = {
        'back':                 ('_ZN9ViewFrame4backEv',
                                 CFUNCTYPE(None, c_void_p)),
        'forward':              ('_ZN9ViewFrame7forwardEv',
                                 CFUNCTYPE(None, c_void_p)),
        'setInfoType':          ('_ZN9ViewFrame11setInfoTypeERK7QString',
                                 CFUNCTYPE(c_int, c_void_p, c_void_p)),
        'setViewType':          ('_ZN9ViewFrame11setViewTypeERK7QString',
                                 CFUNCTYPE(c_int, c_void_p, c_void_p)),
    }

    def __init__(self, q):
        self.q = _QObjectProxy(self._q_meta_object, q, self._c_api)

    @on_main_thread
    def back(self):
        """Navigates back in history."""
        self.q.back()

    @on_main_thread
    def forward(self):
        """Navigates forward in history."""
        self.q.forward()

    @on_main_thread
    def setViewType(self, binary_view_type, disasm_view_type):
        """
        Sets the type of binary view and type of disassembly view.

        :param binary_view_type:
            registered binary view type, e.g. ``"ELF"``
        :param disasm_view_type:
            pre-existing types are ``"Hex"``, ``"Graph"``, ``"Linear"``, ``"Strings"``,
            and ``"Types"``
        :return: ``True`` if successful, ``False`` otherwise
        """
        q_ident = _QString(binary_view_type + ":" + disasm_view_type)
        return self.q.setViewType(q_ident._pointer()) != 0

    def getInfoPanel(self):
        """
        :return: the info panel of this view frame
        :rtype: :class:`InfoPanel`"""
        for child in _q_iter_children(self.q):
            if child.metaObject() == InfoPanel._q_meta_object:
                return InfoPanel(child)
        return None


class InfoPanel(object):
    """
    An info panel of a view frame.

    :ivar q: underlying Qt widget proxy
    """

    _q_meta_object = _q_meta_object_for_name('9InfoPanel')

    def __init__(self, q):
        self.q = _QObjectProxy(self._q_meta_object, q)

    def getTabWidget(self):
        """
        :return: the tab widget of this info panel
        :rtype: ``QtWidgets.QTabWidget``
        """
        for child in _q_iter_children(self.q):
            if child.metaObject() == QtWidgets.QTabWidget.staticMetaObject:
                return child


def active_window():
    """Returns the focused main window. See :meth:`MainWindow.active`."""
    return MainWindow.active()
