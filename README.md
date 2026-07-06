# fcp-python

Python Code Intelligence FCP — an MCP server for querying Python codebases and performing cross-file symbol rename through intent-level commands.

Wraps [pylsp](https://github.com/python-lsp/python-lsp-server) (python-lsp-server), backed by jedi for navigation/queries and rope for rename. The mutation surface is intentionally narrow: `rename` is the only mutation verb. Everything else (extracting functions, adding imports, etc.) is something the calling LLM should do directly with a normal file edit — routing single-line changes through MCP→DSL→LSP adds ceremony without adding value.

## Install

```bash
uvx fcp-python
```

## Usage

```
python_session  ->  open /path/to/project
python_query    ->  find MyClass
python_query    ->  def my_function @file:main.py
python_query    ->  refs MyClass @file:models.py
python_query    ->  symbols src/main.py
python_query    ->  diagnose
python_query    ->  inspect MyClass
python_query    ->  callers process_data
python_query    ->  map
python_query    ->  unused
python          ->  rename Config Settings
python_help     ->  (shows reference card)
```

## License

MIT
