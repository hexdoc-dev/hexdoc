# GitHub Pages

[GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages) is the default and most supported method of serving a hexdoc book as a website.

## Setup

1. In your local Git repo, run these commands to create an empty branch for GitHub Pages:
   ```sh
   git switch --orphan gh-pages
   git commit --allow-empty -m "Initial commit"
   git push -u origin gh-pages
   git switch -  # optional: switch back to the previous branch
   ```
2. In your GitHub repo, go to `Settings > Pages`.
3. In the `Build and deployment` section, set the following values:
   * Source: `Deploy from a branch`
   * Branch: `gh-pages`
   * Folder: `/docs`
4. Save your changes.

:::note

Making changes to these settings will immediately trigger the built-in `pages-build-deployment` workflow. If you haven't yet deployed your book to the `gh-pages` branch, this workflow will fail since the `docs/` folder does not exist. This failure is expected at this point - you can safely ignore it.

:::

## Deploying with GitHub Actions

You can use the [`hexdoc-dev/hexdoc/.github/workflows/hexdoc.yml`](https://github.com/hexdoc-dev/hexdoc/blob/main/.github/workflows/hexdoc.yml) reusable workflow to build and deploy a hexdoc book using [GitHub Actions](https://docs.github.com/en/actions).

Try using [hexdoc-mod-template](https://github.com/hexdoc-dev/hexdoc-mod-template) to generate a sample project, or see [Hex Casting](https://github.com/FallingColors/HexMod/blob/efc889998ff54c13c08d40bcf07c2069c4cae6ee/.github/workflows/build_docs.yml#L26) for a real-world example.

:::hex-casting

[hexdoc-hexcasting-template](https://github.com/hexdoc-dev/hexdoc-hexcasting-template) is a version of hexdoc-mod-template designed specifically for creating new Hex Casting addons. It's also compatible with [hexdummy](https://github.com/FallingColors/hexdummy).

:::
