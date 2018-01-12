import ctypes

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Q_ARG, Q_RETURN_ARG


_q_app = QtWidgets.QApplication.instance()


class _QMethodProxy(object):
    def __init__(self, q_metaobject, q_self, name):
        self._q_metaobject = q_metaobject
        self._q_self = q_self
        self.name = name

    def __call__(self, *args):
        self._q_metaobject.invokeMethod(self._q_self, self.name, *args)


class _QObjectProxy(object):
    _q_methods = {}
    _q_properties = {}

    def __init__(self, q_object):
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
            raise TypeError("Class {} does not have method {}"
                            .format(self._className(), attr))

    def _className(self):
        return self._q_metaobject.className()

    def _methods(self):
        return self.__class__._q_methods[self._q_metaobject]

    def _properties(self):
        return self.__class__._q_properties[self._q_metaobject]


class MainWindow(object):
    """Main Binary Ninja window."""

    @classmethod
    def active(cls):
        """Return the main window that currently has focus, or None if there isn't any.
        This includes the case where a dock window or a menu is active."""
        q_active_window = _q_app.activeWindow()
        if q_active_window is not None:
            if q_active_window.metaObject().className() == "MainWindow":
                return cls(q_active_window)

    def __init__(self, q_main_window):
        self._q = _QObjectProxy(q_main_window)

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

    def openUrlDialog(self):
        """Opens the URL open dialog."""
        self._q.openUrlDialog()

    def save(self):
        """Saves the database."""
        self._q.saveDatabase()

    def saveAs(self):
        """Opens the binary contents save dialog."""
        self._q.saveAs()
