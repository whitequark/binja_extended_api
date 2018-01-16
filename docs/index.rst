Binary Ninja Extended API Documentation
=======================================

.. currentmodule:: binaryninjax

.. toctree::
   :maxdepth: 2

.. autosummary::
   :template: class.rst
   :toctree:
   :nosignatures:

   MainWindow
   ViewFrame
   InfoPanel
   HexEditor
   DisassemblyView
   StringsView
   LinearView
   TypeView
   CrossReferenceItemDelegate

The :mod:`binaryninjax` module provides additional bindings to the C++ API not normally exposed by Binary Ninja. These bindings provide a more extensive programmatic access to its GUI.

.. attention::
  Remember that the Python code normally executes on a non-UI thread. While Qt takes care of synchronization for most operations, any new objects (widgets, timers, etc) must be created on the main thread or they will not function correctly.
