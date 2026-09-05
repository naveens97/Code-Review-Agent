"""
C++ static analyzer.

Subclasses CAnalyzer and overrides:
  - COMPILER = "g++"
  - EXTRA_FLAGS = ["-std=c++17"]

All parsing and rating logic is inherited from CAnalyzer.
Additional C++-specific recommendations are layered on top.
"""

from .c_analyzer import CAnalyzer, _C_RECOMMENDATIONS

# ---------------------------------------------------------------------------
# C++-specific additions to the shared recommendation table.
# These are merged in at import time so the parent parser can use them too.
# ---------------------------------------------------------------------------
_CPP_EXTRA_RECOMMENDATIONS = {
    "no viable conversion": {
        "explanation": "There is no implicit conversion between these types. Use an explicit cast or constructor.",
    },
    "member access into incomplete type": {
        "explanation": "You're dereferencing a pointer to a type that hasn't been fully defined yet. Make sure the full class definition (not just a forward declaration) is visible at this point.",
    },
    "does not name a type": {
        "explanation": "The identifier isn't recognized as a type. Check for missing #include, missing namespace qualification (std::), or a typo.",
        "before": "vector<int> v;",
        "after": "#include <vector>\nstd::vector<int> v;",
    },
    "expected primary-expression": {
        "explanation": "The compiler expected a value or expression here but found something unexpected. Usually caused by an extra operator, a missing argument, or an unmatched bracket.",
    },
    "narrowing conversion": {
        "explanation": "C++ forbids implicit narrowing conversions (e.g. double→int) inside initializer lists. Use an explicit cast if the loss of precision is intentional.",
        "before": "int x{3.14};  // error in C++11+",
        "after": "int x{static_cast<int>(3.14)};",
    },
    "use of undeclared identifier": {
        "explanation": "This identifier hasn't been declared. Check spelling, scope, missing #include, or missing namespace prefix.",
    },
    "override": {
        "explanation": "A method marked `override` doesn't actually override any virtual method in the base class. Check the method signature matches exactly (name, const-ness, parameter types).",
    },
    "deleted function": {
        "explanation": "You're calling a function that has been explicitly deleted (= delete). This usually means the class is non-copyable or non-movable by design.",
    },
    "redefinition of": {
        "explanation": "This name is defined more than once. Use include guards (#pragma once or #ifndef) in headers to prevent multiple inclusion.",
        "before": "// header.h (included twice)\nstruct Foo {};",
        "after": "#pragma once\nstruct Foo {};",
    },
    "infinite recursion": {
        "explanation": "This function calls itself unconditionally, which will cause a stack overflow at runtime. Add a base case to stop the recursion.",
    },
}

# Merge C++ extras into the shared table so CAnalyzer's parser can use them.
_C_RECOMMENDATIONS.update(_CPP_EXTRA_RECOMMENDATIONS)


class CppAnalyzer(CAnalyzer):
    """C++ analyzer — inherits all of CAnalyzer's logic, just changes the
    compiler binary and adds the C++17 standard flag."""

    COMPILER = "g++"
    EXTRA_FLAGS = ["-std=c++17"]
