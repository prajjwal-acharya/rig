from __future__ import annotations

from rig.languages.model import Language
from rig.languages.registry import LanguageRegistry

DEFAULT_LANGUAGES: tuple[Language, ...] = (
    Language(id="python", display_name="Python", extensions=frozenset({"py", "pyw", "pyi"})),
    Language(id="go", display_name="Go", extensions=frozenset({"go"})),
    Language(
        id="javascript",
        display_name="JavaScript",
        extensions=frozenset({"js", "mjs", "cjs", "jsx"}),
    ),
    Language(id="typescript", display_name="TypeScript", extensions=frozenset({"ts", "tsx"})),
    Language(id="java", display_name="Java", extensions=frozenset({"java"})),
    Language(id="c", display_name="C", extensions=frozenset({"c", "h"})),
    Language(
        id="cpp",
        display_name="C++",
        extensions=frozenset({"cpp", "cc", "cxx", "hpp", "hh", "hxx"}),
    ),
    Language(id="csharp", display_name="C#", extensions=frozenset({"cs"})),
    Language(id="rust", display_name="Rust", extensions=frozenset({"rs"})),
    Language(id="ruby", display_name="Ruby", extensions=frozenset({"rb"})),
    Language(id="php", display_name="PHP", extensions=frozenset({"php"})),
    Language(id="shell", display_name="Shell", extensions=frozenset({"sh", "bash", "zsh"})),
    Language(id="yaml", display_name="YAML", extensions=frozenset({"yaml", "yml"})),
    Language(id="json", display_name="JSON", extensions=frozenset({"json"})),
    Language(id="toml", display_name="TOML", extensions=frozenset({"toml"})),
    Language(id="markdown", display_name="Markdown", extensions=frozenset({"md", "markdown"})),
    Language(id="html", display_name="HTML", extensions=frozenset({"html", "htm"})),
    Language(id="css", display_name="CSS", extensions=frozenset({"css"})),
    Language(id="scss", display_name="SCSS", extensions=frozenset({"scss"})),
    Language(id="sql", display_name="SQL", extensions=frozenset({"sql"})),
    Language(id="xml", display_name="XML", extensions=frozenset({"xml"})),
    Language(id="kotlin", display_name="Kotlin", extensions=frozenset({"kt", "kts"})),
    Language(id="swift", display_name="Swift", extensions=frozenset({"swift"})),
    Language(id="scala", display_name="Scala", extensions=frozenset({"scala"})),
    Language(id="perl", display_name="Perl", extensions=frozenset({"pl", "pm"})),
    Language(id="lua", display_name="Lua", extensions=frozenset({"lua"})),
    Language(id="r", display_name="R", extensions=frozenset({"r"})),
    Language(id="haskell", display_name="Haskell", extensions=frozenset({"hs"})),
    Language(id="elixir", display_name="Elixir", extensions=frozenset({"ex", "exs"})),
    Language(id="erlang", display_name="Erlang", extensions=frozenset({"erl"})),
    Language(id="clojure", display_name="Clojure", extensions=frozenset({"clj", "cljs"})),
    Language(id="dart", display_name="Dart", extensions=frozenset({"dart"})),
    Language(id="graphql", display_name="GraphQL", extensions=frozenset({"graphql", "gql"})),
    Language(id="protobuf", display_name="Protocol Buffers", extensions=frozenset({"proto"})),
    Language(id="ini", display_name="INI", extensions=frozenset({"ini", "cfg"})),
    Language(id="text", display_name="Text", extensions=frozenset({"txt"})),
    Language(
        id="dockerfile",
        display_name="Dockerfile",
        extensions=frozenset({"dockerfile"}),
        filenames=frozenset({"Dockerfile"}),
    ),
    Language(
        id="makefile",
        display_name="Makefile",
        filenames=frozenset({"Makefile", "makefile", "GNUmakefile"}),
    ),
)

DEFAULT_REGISTRY = LanguageRegistry(DEFAULT_LANGUAGES)
