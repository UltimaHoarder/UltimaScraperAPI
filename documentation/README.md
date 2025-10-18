# UltimaScraperAPI Documentation

This directory contains the MkDocs-based documentation for UltimaScraperAPI.

## Quick Start

### View Documentation Locally

To build and serve the documentation locally:

```bash
# Using uv (recommended)
uv run mkdocs serve

# Or using pip
pip install mkdocs-material
mkdocs serve
```

Then open http://localhost:8000 in your browser.

### Build Static Site

To build the static HTML documentation:

```bash
# Using uv
uv run mkdocs build

# Or using pip
mkdocs build
```

The built site will be in the `site/` directory.

## Documentation Structure

```
documentation/
├── docs/                      # Documentation source files (Markdown)
│   ├── index.md              # Homepage
│   ├── getting-started/      # Getting started guides
│   │   ├── installation.md
│   │   ├── quick-start.md
│   │   └── configuration.md
│   ├── user-guide/           # User guides
│   │   ├── authentication.md
│   │   ├── working-with-apis.md
│   │   ├── session-management.md
│   │   └── proxy-support.md
│   ├── api-reference/        # API documentation
│   │   ├── onlyfans.md
│   │   ├── fansly.md
│   │   ├── loyalfans.md
│   │   └── helpers.md
│   ├── development/          # Development docs
│   │   ├── contributing.md
│   │   ├── architecture.md
│   │   └── testing.md
│   └── about/               # About pages
│       ├── license.md
│       └── changelog.md
└── README.md                # This file
```

## Writing Documentation

### Markdown Files

Documentation is written in Markdown with MkDocs Material extensions:

- **Code blocks with syntax highlighting**
  ````markdown
  ```python
  def example():
      pass
  ```
  ````

- **Admonitions (notes, warnings, tips)**
  ```markdown
  !!! note "Title"
      Content here
  
  !!! warning
      Warning content
  
  !!! tip
      Tip content
  ```

- **Tabs**
  ```markdown
  === "Tab 1"
      Content 1
  
  === "Tab 2"
      Content 2
  ```

### Adding New Pages

1. Create a new `.md` file in the appropriate directory
2. Add it to the `nav` section in `mkdocs.yml`
3. Write your content using Markdown
4. Preview with `mkdocs serve`

Example:
```yaml
nav:
  - Home: index.md
  - New Section:
      - New Page: section/new-page.md
```

## Configuration

The documentation is configured in `mkdocs.yml` at the project root.

Key configuration sections:
- **site_name**: Site title
- **theme**: Material theme configuration
- **nav**: Navigation structure
- **markdown_extensions**: Enabled Markdown extensions
- **plugins**: MkDocs plugins

## Deployment

### GitHub Pages

To deploy to GitHub Pages:

```bash
mkdocs gh-deploy
```

This will build the documentation and push it to the `gh-pages` branch.

### Custom Hosting

Build the static site and upload the `site/` directory to your web server:

```bash
mkdocs build
# Upload site/ directory to your server
```

## MkDocs Material Theme

We use the [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) theme.

Features enabled:
- Light/dark mode toggle
- Search functionality
- Navigation tabs
- Code copy button
- Syntax highlighting
- Emoji support
- Table of contents

## Maintenance

### Updating Documentation

1. Edit the relevant `.md` file
2. Preview changes with `mkdocs serve`
3. Commit and push changes
4. Documentation will auto-update on deployment

### Adding Dependencies

If you need additional MkDocs plugins:

1. Add to `pyproject.toml` dependencies
2. Update this README
3. Add plugin configuration to `mkdocs.yml`

## Resources

- [MkDocs Documentation](https://www.mkdocs.org/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- [Markdown Guide](https://www.markdownguide.org/)
- [Python Markdown Extensions](https://python-markdown.github.io/extensions/)

## Getting Help

For documentation issues:
- Open an issue on GitHub
- Check MkDocs Material documentation
- Review existing documentation pages for examples
