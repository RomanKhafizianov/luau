// This file is part of the Luau programming language and is licensed under MIT License; see LICENSE.txt for details
// This code is based on Lua 5.x implementation licensed under MIT License; see lua_LICENSE.txt for details
#include "ludata.h"

#include "lgc.h"
#include "lmem.h"

#include <string.h>

Udata* luaU_newudata(lua_State* L, size_t s, int tag)
{
    if (s > INT_MAX - sizeof(Udata))
        luaM_toobig(L);
    Udata* u = luaM_newgco(L, Udata, sizeudata(s), L->activememcat);
    luaC_init(L, u, LUA_TUSERDATA);
    u->len = int(s);
    u->metatable = NULL;
    LUAU_ASSERT(tag >= 0 && tag <= 255);
    u->tag = uint8_t(tag);
    return u;
}

void luaU_freeudata(lua_State* L, Udata* u, lua_Page* page)
{
    void (*dtor)(void*) = nullptr;
    if (u->tag < LUA_UTAG_LIMIT)
        dtor = L->global->udatagc[u->tag];
    else if (u->tag == UTAG_IDTOR)
        memcpy(&dtor, &u->data + u->len - sizeof(dtor), sizeof(dtor));

    if (dtor)
        dtor(u->data);

    luaM_freegco(L, u, sizeudata(u->len), u->memcat, page);
}
