import ctypes
import json
import os
from pathlib import Path

# 指向正版游戏目录里的 lua51.dll，通过环境变量 BALATRO_LUA51 指定
DLL = Path(os.environ['BALATRO_LUA51']) if os.environ.get('BALATRO_LUA51') else None

class Lua:
    def __init__(self, dll=None):
        dll = dll or DLL
        if not dll:
            raise SystemExit('请设置环境变量 BALATRO_LUA51 指向游戏目录的 lua51.dll')
        self.dll = ctypes.CDLL(str(dll))
        d = self.dll
        d.luaL_newstate.restype = ctypes.c_void_p
        d.luaL_openlibs.argtypes = [ctypes.c_void_p]
        d.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        d.lua_pcall.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        d.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_size_t)]
        d.lua_tolstring.restype = ctypes.c_char_p
        d.lua_settop.argtypes = [ctypes.c_void_p, ctypes.c_int]
        d.lua_close.argtypes = [ctypes.c_void_p]
        self.state = d.luaL_newstate()
        d.luaL_openlibs(self.state)
        self.run('''
        function encode(x)
            if type(x) == 'number' then return string.format('%.17g',x) end
            if type(x) == 'boolean' then return tostring(x) end
            if type(x) == 'string' then return string.format('%q',x) end
            local parts = {}
            if #x > 0 then
                for i=1,#x do parts[i]=encode(x[i]) end
                return '[' .. table.concat(parts,',') .. ']'
            end
            for key,value in pairs(x) do parts[#parts+1]=encode(key)..':'..encode(value) end
            return '{' .. table.concat(parts,',') .. '}'
        end
        ''')

    def run(self, source):
        d, s = self.dll, self.state
        if d.luaL_loadstring(s, source.encode()) or d.lua_pcall(s, 0, 1, 0):
            raise AssertionError(d.lua_tolstring(s, -1, None).decode())
        result = d.lua_tolstring(s, -1, None)
        result = result.decode() if result else None
        d.lua_settop(s, 0)
        return result

    def close(self):
        self.dll.lua_close(self.state)


def lua_value(value):
    if isinstance(value, list):
        return '{' + ','.join(map(lua_value, value)) + '}'
    if isinstance(value, dict):
        return '{' + ','.join('['+json.dumps(key)+']='+lua_value(v) for key,v in value.items()) + '}'
    return json.dumps(value)


