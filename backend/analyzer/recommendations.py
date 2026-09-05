"""
Human-readable explanations and fixes for specific analyzer findings.

Every key in PYLINT_RECOMMENDATIONS and BANDIT_RECOMMENDATIONS below was
checked against real output from the installed pylint/bandit versions
(see the project's dev notes) rather than assumed from memory, since rule
symbols occasionally change between tool versions.

Anything the analyzer finds that ISN'T in these dictionaries still gets
reported to the user -- it just falls back to the tool's own message
instead of our curated explanation. Nothing is ever silently dropped.
"""

# Each entry: explanation (the "why"), and optionally before/after snippets
# demonstrating the "optimal solution" for the most teachable issues.
PYLINT_RECOMMENDATIONS = {
    "dangerous-default-value": {
        "explanation": (
            "Mutable default arguments (like [] or {}) are created ONCE when the "
            "function is defined, not each time it's called. Every call that "
            "relies on the default shares and mutates the same object, which "
            "causes hard-to-trace bugs."
        ),
        "before": "def add_item(item, bucket=[]):\n    bucket.append(item)\n    return bucket",
        "after": "def add_item(item, bucket=None):\n    if bucket is None:\n        bucket = []\n    bucket.append(item)\n    return bucket",
    },
    "bare-except": {
        "explanation": (
            "A bare `except:` catches everything, including KeyboardInterrupt and "
            "SystemExit, and hides the real cause of failures. Catch the specific "
            "exception(s) you actually expect."
        ),
        "before": "try:\n    value = int(user_input)\nexcept:\n    value = 0",
        "after": "try:\n    value = int(user_input)\nexcept ValueError:\n    value = 0",
    },
    "broad-exception-caught": {
        "explanation": (
            "Catching the base `Exception` class swallows errors you didn't "
            "anticipate (typos, wrong types, logic bugs) alongside the one you "
            "meant to handle. Narrow it to the specific exception type."
        ),
    },
    "eval-used": {
        "explanation": (
            "eval() executes arbitrary strings as Python code, which is a "
            "serious security risk if the string ever contains user input. For "
            "parsing literals (numbers, lists, dicts) use ast.literal_eval, "
            "which cannot execute arbitrary code."
        ),
        "before": "value = eval(user_input)",
        "after": "import ast\nvalue = ast.literal_eval(user_input)",
    },
    "consider-using-enumerate": {
        "explanation": (
            "Indexing with range(len(...)) is slower and less readable than "
            "iterating directly. enumerate() gives you the index and value "
            "together."
        ),
        "before": "for i in range(len(items)):\n    print(i, items[i])",
        "after": "for i, item in enumerate(items):\n    print(i, item)",
    },
    "consider-using-with": {
        "explanation": (
            "Resources opened without a `with` block (files, sockets, locks) "
            "can leak if an exception happens before you close them. `with` "
            "guarantees cleanup."
        ),
        "before": "f = open('data.txt')\ndata = f.read()\nf.close()",
        "after": "with open('data.txt', encoding='utf-8') as f:\n    data = f.read()",
    },
    "unspecified-encoding": {
        "explanation": (
            "open() without an explicit encoding uses whatever the OS default "
            "is, which differs across machines and can silently corrupt text. "
            "Always pass encoding='utf-8' (or whatever the file actually uses)."
        ),
        "before": "with open('data.txt') as f:\n    text = f.read()",
        "after": "with open('data.txt', encoding='utf-8') as f:\n    text = f.read()",
    },
    "no-else-return": {
        "explanation": (
            "Once a branch returns, the `else` is redundant -- code after the "
            "if-block only runs when the if didn't return anyway. Removing it "
            "reduces nesting."
        ),
        "before": "if x > 0:\n    return 'positive'\nelse:\n    return 'non-positive'",
        "after": "if x > 0:\n    return 'positive'\nreturn 'non-positive'",
    },
    "inconsistent-return-statements": {
        "explanation": (
            "Some paths through this function return a value and others fall "
            "off the end (returning None implicitly). Callers can't rely on a "
            "consistent return type. Make every path return explicitly."
        ),
    },
    "singleton-comparison": {
        "explanation": (
            "Singletons like None, True, and False should be compared with "
            "`is`, not `==`. `is` checks identity, which is what you actually "
            "want and can't be fooled by custom __eq__ implementations."
        ),
        "before": "if value == None:\n    ...",
        "after": "if value is None:\n    ...",
    },
    "simplifiable-if-statement": {
        "explanation": (
            "An if/else that only returns True or False can be replaced with "
            "the condition itself (wrapped in bool() if needed)."
        ),
        "before": "if condition:\n    return True\nelse:\n    return False",
        "after": "return bool(condition)",
    },
    "unused-import": {
        "explanation": "This import is never referenced. Remove it to keep the module's dependencies honest and imports fast.",
    },
    "unused-variable": {
        "explanation": "This variable is assigned but never used. If it's genuinely unneeded, remove it; if it's a placeholder, prefix it with an underscore (e.g. _unused) to signal intent.",
    },
    "redefined-outer-name": {
        "explanation": "This name shadows a variable or function already defined in an outer scope, which makes both harder to reason about. Rename one of them.",
    },
    "missing-function-docstring": {
        "explanation": "A short docstring describing what this function does, its parameters, and its return value makes it usable without reading the implementation.",
    },
    "missing-class-docstring": {
        "explanation": "A short docstring describing this class's responsibility helps callers understand its purpose at a glance.",
    },
    "missing-module-docstring": {
        "explanation": "A one-line module docstring at the top of the file describing what it contains is standard practice for anything meant to be imported or reused.",
    },
    "invalid-name": {
        "explanation": "This name doesn't follow PEP 8 naming conventions (snake_case for variables/functions, PascalCase for classes, UPPER_CASE for constants). Consistent naming makes code predictable to navigate.",
    },
    "too-complex": {
        "explanation": (
            "This function's cyclomatic complexity is high -- there are many "
            "independent paths through it, which makes it hard to test and "
            "reason about. Consider splitting it into smaller helper functions, "
            "each handling one responsibility."
        ),
    },
    "too-many-arguments": {
        "explanation": "This function takes a lot of parameters, which makes call sites hard to read and easy to misuse. Consider grouping related parameters into a dataclass or config object.",
    },
    "too-many-positional-arguments": {
        "explanation": "This function accepts a lot of positional parameters. Consider keyword-only arguments or a config object so call sites stay readable.",
    },
    "too-many-branches": {
        "explanation": "This function has a lot of branches (if/elif/for/while), which increases the number of paths a reader has to hold in their head at once. Consider extracting some branches into named helper functions.",
    },
    "too-many-locals": {
        "explanation": "This function tracks a lot of local variables at once, which is a common sign it's doing more than one job. Splitting it up usually also shortens the variable list naturally.",
    },
    "consider-using-f-string": {
        "explanation": "f-strings are faster and more readable than % formatting or .format() for building strings from variables.",
        "before": "message = 'Hello, %s! You are %d.' % (name, age)",
        "after": "message = f'Hello, {name}! You are {age}.'",
    },
}

BANDIT_RECOMMENDATIONS = {
    "B307": {
        "explanation": (
            "eval() executes arbitrary strings as Python code. If any part of "
            "that string can be influenced by user input, this is a remote "
            "code execution vulnerability. Use ast.literal_eval() for parsing "
            "literals, or a proper parser for anything more complex."
        ),
        "before": "value = eval(user_input)",
        "after": "import ast\nvalue = ast.literal_eval(user_input)",
    },
    "B102": {
        "explanation": "exec() runs arbitrary strings as Python code, same risk profile as eval(). Avoid it, especially with any input that isn't fully trusted.",
    },
    "B110": {
        "explanation": "Silently swallowing every exception with `except: pass` hides real bugs and makes failures invisible. At minimum, log the exception; better, catch only the specific exception you expect.",
    },
    "B105": {
        "explanation": "This looks like a hardcoded credential. Secrets in source code end up in version control history and are visible to anyone with repo access. Load them from environment variables or a secrets manager instead.",
        "before": "password = 'admin123'",
        "after": "import os\npassword = os.environ['APP_PASSWORD']",
    },
    "B106": {
        "explanation": "This looks like a hardcoded credential passed as a function argument. Load it from environment variables or a secrets manager instead of committing it to source.",
    },
    "B107": {
        "explanation": "This looks like a hardcoded credential used as a default argument value, which means it ships with the code itself. Load it from environment variables or a secrets manager instead.",
    },
    "B605": {
        "explanation": (
            "Building a shell command by concatenating strings (including user "
            "input) is a classic command-injection vector. Pass arguments as a "
            "list to subprocess.run() instead of building a shell string."
        ),
        "before": "os.system('echo ' + user_input)",
        "after": "import subprocess\nsubprocess.run(['echo', user_input], check=True)",
    },
    "B602": {
        "explanation": "subprocess called with shell=True passes the command through a shell, which is a command-injection risk if any part of it comes from user input. Pass the command as a list and drop shell=True.",
        "before": "subprocess.call(cmd, shell=True)",
        "after": "subprocess.call(cmd_list, shell=False)",
    },
    "B603": {
        "explanation": "subprocess called without shell=True is safer, but double-check that every argument in the list is trusted or validated -- untrusted paths/flags can still change program behavior.",
    },
    "B301": {
        "explanation": (
            "pickle.load/loads can execute arbitrary code while deserializing "
            "data it doesn't trust. Never unpickle data from an untrusted "
            "source. If you need a safe interchange format, use json instead."
        ),
    },
    "B403": {
        "explanation": "Importing pickle is fine on its own, but flags that this module deserializes data somewhere -- make sure that data always comes from a source you trust.",
    },
    "B404": {
        "explanation": "Importing subprocess is fine on its own, but flags that this module shells out somewhere -- make sure arguments passed to it are never built from unsanitized user input.",
    },
    "B324": {
        "explanation": "MD5/SHA1 are cryptographically broken and shouldn't be used for security purposes (password hashing, signatures). For passwords use a purpose-built KDF like bcrypt/scrypt/argon2; for general hashing where security matters, use SHA-256 or better.",
        "before": "hashlib.md5(password.encode()).hexdigest()",
        "after": "import bcrypt\nbcrypt.hashpw(password.encode(), bcrypt.gensalt())",
    },
    "B101": {
        "explanation": "assert statements are stripped out when Python runs with optimizations (-O), so they're unreliable for anything that must always be checked (input validation, security checks). Use an explicit if/raise instead.",
        "before": "assert user.is_admin",
        "after": "if not user.is_admin:\n    raise PermissionError('Admin access required')",
    },
    "B608": {
        "explanation": (
            "Building SQL by formatting strings (%, +, f-strings) lets an "
            "attacker change the query's meaning by controlling its content -- "
            "classic SQL injection. Use parameterized queries instead, which "
            "keep data separate from the query structure."
        ),
        "before": "cursor.execute(\"SELECT * FROM users WHERE name = '%s'\" % username)",
        "after": "cursor.execute('SELECT * FROM users WHERE name = ?', (username,))",
    },
    "B201": {
        "explanation": "Running a Flask app with debug=True in production exposes an interactive debugger that can execute arbitrary code. Only enable debug mode locally, driven by an environment variable that defaults to off.",
    },
}


def get_pylint_recommendation(symbol: str, fallback_message: str) -> dict:
    entry = PYLINT_RECOMMENDATIONS.get(symbol)
    if entry:
        return {
            "recommendation": entry["explanation"],
            "before": entry.get("before"),
            "after": entry.get("after"),
        }
    return {"recommendation": fallback_message, "before": None, "after": None}


def get_bandit_recommendation(test_id: str, fallback_message: str) -> dict:
    entry = BANDIT_RECOMMENDATIONS.get(test_id)
    if entry:
        return {
            "recommendation": entry["explanation"],
            "before": entry.get("before"),
            "after": entry.get("after"),
        }
    return {"recommendation": fallback_message, "before": None, "after": None}
