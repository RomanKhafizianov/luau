#!/usr/bin/python3
# This file is part of the Luau programming language and is licensed under MIT License; see LICENSE.txt for details

# This code can be used to split lvmexecute.cpp VM switch into separate functions for use as native code generation fallbacks
import sys
import re

input = sys.stdin.readlines()

inst = ""

header = """// This file is part of the Luau programming language and is licensed under MIT License; see LICENSE.txt for details
// This file was generated by 'tools/lvmexecute_split.py' script, do not modify it by hand
#pragma once

#include <stdint.h>

struct lua_State;
struct Closure;
typedef uint32_t Instruction;
typedef struct lua_TValue TValue;
typedef TValue* StkId;

"""

source = """// This file is part of the Luau programming language and is licensed under MIT License; see LICENSE.txt for details
// This code is based on Lua 5.x implementation licensed under MIT License; see lua_LICENSE.txt for details
// This file was generated by 'tools/lvmexecute_split.py' script, do not modify it by hand
#include "Fallbacks.h"
#include "FallbacksProlog.h"

"""

function = ""
signature = ""

includeInsts = ["LOP_NEWCLOSURE", "LOP_NAMECALL", "LOP_FORGPREP", "LOP_GETVARARGS", "LOP_DUPCLOSURE", "LOP_PREPVARARGS", "LOP_BREAK", "LOP_GETGLOBAL", "LOP_SETGLOBAL", "LOP_GETTABLEKS", "LOP_SETTABLEKS", "LOP_SETLIST"]

state = 0

# parse with the state machine
for line in input:
    # find the start of an instruction
    if state == 0:
        match = re.match("\s+VM_CASE\((LOP_[A-Z_0-9]+)\)", line)

        if match:
            inst = match[1]
            signature = "const Instruction* execute_" + inst + "(lua_State* L, const Instruction* pc, StkId base, TValue* k)"
            function = signature + "\n"
            function += "{\n"
            function += "    [[maybe_unused]] Closure* cl = clvalue(L->ci->func);\n"
            state = 1

    # first line of the instruction which is "{"
    elif state == 1:
        assert(line == "            {\n")
        state = 2

    # find the end of an instruction
    elif state == 2:
        # remove jumps back into the native code
        if line == "#if LUA_CUSTOM_EXECUTION\n":
            state = 3
            continue

        if line[0] == ' ':
            finalline = line[12:-1] + "\n"
        else:
            finalline = line

        finalline = finalline.replace("VM_NEXT();", "return pc;");
        finalline = finalline.replace("goto exit;", "return NULL;");
        finalline = finalline.replace("return;", "return NULL;");

        function += finalline
        match = re.match("            }", line)

        if match:
            # break is not supported
            if inst == "LOP_BREAK":
                function = "const Instruction* execute_" + inst + "(lua_State* L, const Instruction* pc, StkId base, TValue* k)\n"
                function += "{\n    LUAU_ASSERT(!\"Unsupported deprecated opcode\");\n    LUAU_UNREACHABLE();\n}\n"
            # handle fallthrough
            elif inst == "LOP_NAMECALL":
                function = function[:-len(finalline)]
                function += "    return pc;\n}\n"

            if inst in includeInsts:
                header += signature + ";\n"
                source += function + "\n"

            state = 0

    # skip LUA_CUSTOM_EXECUTION code blocks
    elif state == 3:
        if line == "#endif\n":
            state = 4
            continue

    # skip extra line
    elif state == 4:
        state = 2

# make sure we found the ending
assert(state == 0)

with open("Fallbacks.h", "w") as fp:
    fp.writelines(header)

with open("Fallbacks.cpp", "w") as fp:
    fp.writelines(source)
