import io
from collections import OrderedDict
from dataclasses import field
from typing import Any, Dict, Iterable, Optional, Union

from pheasant.core.base import Base
from pheasant.core.decorator import Decorator
from pheasant.core.page import Page
from pheasant.core.parser import Parser
from pheasant.core.renderer import Renderer
from pheasant.core.renderers import Renderers


class Converter(Base):
    parsers: Dict[str, Parser] = field(default_factory=OrderedDict)
    renderers: Renderers = field(default_factory=Renderers)
    pages: Dict[str, Page] = field(default_factory=dict)

    def __post_repr__(self):
        return ", ".join(f"'{name}'" for name in self.parsers)

    def __getitem__(self, item):
        if isinstance(item, str):
            return self.parsers[item]
        elif isinstance(item, tuple):
            return self.renderers[item]

    def update_config(self, config: Dict[str, Any]):
        for renderer in self.renderers:
            if renderer.name in config:
                renderer._update("config", config[renderer.name])

    def setup(self):
        for renderer in self.renderers:
            renderer.setup()

    def reset(self):
        for renderer in self.renderers:
            renderer.reset()
        self.pages = {}

    def register(
        self,
        name: str,
        renderers: Union[Renderer, Iterable[Renderer]],
        decorator: Optional[Decorator] = None,
    ):
        """Register renderer's processes

        Parameters
        ----------
        name
            The name of Parser
        renderers
            List of Renderer's instance or name of Renderer
        """
        if name in self.parsers:
            raise ValueError(f"Duplicated parser name '{name}'")
        parser = Parser(name)  # type:ignore
        if decorator:
            parser.decorator = decorator
        self.parsers[name] = parser
        if isinstance(renderers, Renderer):
            renderers = [renderers]
        self.renderers.register(name, renderers)
        for renderer in self.renderers[name]:  # type: ignore
            for pattern, render in renderer.renders.items():
                parser.register(pattern, render)

    def convert(
        self, source: str, names: Optional[Union[str, Iterable[str]]] = None
    ) -> str:
        """Convert source text.

        Parameters
        ----------
        source
            The text string to be converted.
        names
            Parser names to be used. If not specified. all of the registered
            parsers will be used.

        Returns
        -------
        Converted source text.
        """
        if isinstance(names, str):
            names = [names]
        names = names or self.parsers
        for name in names:
            parser = self.parsers[name]
            source = "".join(parser.parse(source))

        return source

    def convert_from_file(
        self, path: str, names: Optional[Union[str, Iterable[str]]] = None
    ) -> str:
        with io.open(path, "r", encoding="utf-8-sig", errors="strict") as f:
            source = f.read()

        break_str = "<!-- break -->"
        if break_str in source:
            source = source.split(break_str)[0]

        page = Page(path, source=source)  # type: ignore
        self.pages[path] = page
        page.output = self.convert(source, names)
        return page.output

    def convert_from_output(
        self, path: str, names: Optional[Union[str, Iterable[str]]] = None
    ) -> str:
        page = self.pages[path]
        page.output = self.convert(page.output, names)
        return page.output