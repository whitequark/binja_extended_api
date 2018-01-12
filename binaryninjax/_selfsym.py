import sys
import ctypes
import binaryninja

if 'linux' in sys.platform:
    from elftools.elf.elffile import ELFFile

    class _SymbolResolver(object):
        def __init__(self, stream):
            self._elf = ELFFile(stream)
            self._symtab = self._elf.get_section_by_name('.symtab')

        # In case we're a PIE.
        def set_offset(self, symbol_name, actual_addr):
            symbol = self._symtab.get_symbol_by_name(symbol_name)[0]
            self._offset = actual_addr - symbol.entry.st_value

        def lookup(self, name):
            symbols = self._symtab.get_symbol_by_name(name)
            if symbols:
                return self._offset + symbols[0].entry.st_value
            else:
                return None

    _self_dll = ctypes.CDLL("binaryninja", handle=0)

    _resolver = _SymbolResolver(open(binaryninja.get_install_directory() + '/binaryninja'))
    _resolver.set_offset('_end', _self_dll.dlsym(0, '_end'))

    def resolve_symbol(symbol_name):
        symbol_addr = _self_dll.dlsym(0, symbol_name)
        if symbol_addr:
            return symbol_addr
        return _resolver.lookup(symbol_name)

else:
    raise NotImplementedError("Sorry, your platform is not supported")
