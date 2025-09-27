# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Pydantic's HISTORY.md](https://github.com/pydantic/pydantic/blob/main/HISTORY.md), and this project *mostly* adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## `1!0.1.0a30`

### Fixed

* Fixed Markdown newlines being incorrectly escaped in some cases.

## `1!0.1.0a29`

### Fixed

* Fixed incorrect Markdown escaping in `macros/styles.md.jinja`.

## `1!0.1.0a28`

### Added

* Added a page template for `patchouli:entity` pages, by penguinencounter in [#93](https://github.com/hexdoc-dev/hexdoc/pull/93).

## `1!0.1.0a27`

### Added

* Added a page template for `patchouli:relations` pages, by penguinencounter in [#92](https://github.com/hexdoc-dev/hexdoc/pull/92).

### Fixed

* Changed animated texture type from linear to steps to fix glitched animations on page load, by penguinencounter in [#89](https://github.com/hexdoc-dev/hexdoc/pull/89).

## `1!0.1.0a26`

### Fixed

* Hotfix: Require `click<8.2.0` to work around issue where `HEXDOC_RELEASE` always parses as True ([#88](https://github.com/hexdoc-dev/hexdoc/issues/88)).

## `1!0.1.0a25`

### Contributions

* Add ru_ru localization for main hexdoc lang, by JustS-js in [#87](https://github.com/hexdoc-dev/hexdoc/pull/87).

## `1!0.1.0a24`

### Fixed

* Fix incorrect tag serialization caused by PydanticOrderedSet, which resulted in tags with optional entries failing to load in certain cases.

## `1!0.1.0a23`

### Fixed

* Hotfix: Log a warning instead of failing the build when item NBT parsing fails.

## `1!0.1.0a22`

### Changed

* Update Pillow to 11.0, which should hopefully allow hexdoc to be used with Python 3.12+.
* ItemStack now uses [nbtlib](https://pypi.org/project/nbtlib/) to parse NBT tags.
* Spotlight pages now use item names from NBT tags if set.

### Fixed

* Avoid adding a double title to spotlight pages with a title field.

## `1!0.1.0a21`

### Fixed

* Fix broken environment variable loading by adding a dependency exclusion for Pydantic Settings v2.6.0 (see [pydantic/pydantic-settings#445](https://github.com/pydantic/pydantic-settings/issues/445)).

## `1!0.1.0a20`

### Added

* New Jinja template filter: `hexdoc_smart_var`
  * Can be used to allow runtime variable lookups based on values in `props.template.args`. This is currently used by the [custom navbar links](https://hexdoc.hexxy.media/docs/guides/template/#navbar) feature.

### Changed

* A GitHub link is now added to the navbar by default (fixes [#26](https://github.com/hexdoc-dev/hexdoc/issues/26)). See the [docs](https://hexdoc.hexxy.media/docs/guides/template/#navbar) for more info.

### Fixed

* Fix the root-level redirect not being generated in cases where there are no versioned books and no book exists for the default branch.
* Fix crash on startup by adding a dependency exclusion for Pydantic v2.9.0 (see [pydantic/pydantic#10345](https://github.com/pydantic/pydantic/issues/10345)).

## `1!0.1.0a19`

### Added

* Allow adding custom links to the web book navbar ([docs](https://hexdoc.hexxy.media/docs/guides/template)).

## `1!0.1.0a18`

### Fixed

* Add missing handler for nested list styles (`$(li2)`, `$(li3)`, etc).
* Fix book links to other extension books on 1.19 and below (also fixes [#75](https://github.com/hexdoc-dev/hexdoc/issues/75))

## `1!0.1.0a17`

### Fixed

* Localize the "please don't sue us Microsoft" page footer (previously was hardcoded).
* Disable showing local variables in Typer pretty exceptions, since it produces a really absurd amount of output. Set a non-empty value for the environment variable `HEXDOC_TYPER_EXCEPTION_LOCALS` to reenable it if you really want to.

### Contributions

* Update `zh_cn` translations, by @ChuijkYahus in [#74](https://github.com/hexdoc-dev/hexdoc/pull/74).

## `1!0.1.0a16`

### Added

* The internal hexdoc CI now automatically generates and deploys JSON Schema definitions for several Patchouli file types. See the [documentation](https://hexdoc.hexxy.media/docs/guides/standalone/patchouli-schemas) for more details.

### Changed

* The `hexdoc.toml` field `textures.missing` can now be set to `missing = "*"`, allowing all textures to be missing. No other string values are currently supported.
* The command `hexdoc merge` now creates an empty `.nojekyll` file in the site root to disable Jekyll on GitHub Pages (since it's not necessary for hexdoc). Fixes [#68](https://github.com/hexdoc-dev/hexdoc/issues/68).
* Tentatively reenable Typer's [pretty exceptions](https://typer.tiangolo.com/tutorial/exceptions/). Please open an issue if you notice any weird behaviour.
* Change the JSON Schema output path from `/schema/hexdoc` to `/schema`.
* Several documentation improvements/fixes.

### Fixed

* The command `hexdoc render-models` was accidentally configured to take a list of models as an option instead of an argument.

## `1!0.1.0a15`

### Added

* Path resource dirs now support reading `.jar` and `.zip` files.
  * Note: The resource folders (eg. `assets/`) currently must be at the root of the archive.
* New glob resource dir type: `{ glob="mods/*.jar", exclude=["**/some_broken_mod.jar"] }`
* New texture config to print some errors instead of failing the build: `textures.strict`
* New command: `hexdoc render-models`
* Placeholders in `hexdoc.toml` may now start with `$` to reference the root table (eg. `{$modid}` and `{$.modid}` are both valid).

### Changed

* In `hexdoc.toml`, `default_lang` and `default_branch` are now optional, defaulting to `en_us` and `main` respectively.
* Update minimum Pydantic version to `2.7.1`.
* Update Pyright version to `1.1.361`.

### Fixed

* Add missing default values for some fields in `*.png.mcmeta`.

## `1!0.1.0a14`

### Added

* The internal hexdoc CI now automatically generates and deploys a JSON Schema definition for `hexdoc.toml`. See the [documentation](https://hexdoc.hexxy.media/docs/guides/configuration/) for more details.

### Changed

* `hexdoc serve` will now fail immediately instead of retrying the build in non-release mode if an error occurs.
* Update minimum Typer version to `0.12`.

### Fixed

* Fix incorrect texture array size calculation when non-square images are used for block textures.

## `1!0.1.0a13`

### Changed

* Print stdout and stderr when shell commands fail (fixes [#63](https://github.com/hexdoc-dev/hexdoc/issues/63)).
* Improve the error message when GitHub Pages is not enabled.
* Support `.json5` files in places other than I18n. Note that `.flatten.json5` is still only supported for I18n.

## `1!0.1.0a12`

### Added

* New block rendering system, implemented entirely in Python! This replaces [minecraft-render-py](https://github.com/hexdoc-dev/minecraft-render-py) and removes hexdoc's Node.js dependency. Block renders should now be much closer to how items look in inventories ingame.
  * Note: Animated models currently only render the first frame of the animation.
  * Note: `minecraft-render` is still included as a dependency for backwards compatibility reasons. This will be removed in a future release.
* New command: `hexdoc render-model`
* New dependencies: `frozendict`, `moderngl[headless]`, `moderngl-window`
* New `hexdoc.toml` field `lang.{lang}` for per-language configuration. Currently supported options include `quiet` and `ignore_errors`.

### Changed

* Update `zh_cn` translations, by @ChuijkYahus in [#69](https://github.com/hexdoc-dev/hexdoc/pull/69).
* Blockstates are no longer taken into account when selecting block models to render.
* Deprecated the `--quiet-lang` CLI option.
* Errors will now always be raised for all languages unless explicitly disabled in `hexdoc.toml`. Previously, errors when rendering non-default languages would only fail the overall command in release mode.

### Removed

* ⚠️ BREAKING: Removed `HexdocPythonResourceLoader`, as it was only needed for the old rendering system.
* ⚠️ BREAKING: Removed `HexdocAssetLoader.load_blockstates` and `HexdocAssetLoader.renderer_loader`. Several argument/return types have been changed from `IRenderClass` to `BlockRenderer`.
* Removed `hexdoc render-block` subcommands.

## `1!0.1.0a11`

### Added

* hexdoc now uses a custom `sys.excepthook` to hide unnecessary traceback frames, except in verbose mode.
* New reusable workflow input `site-url` to help support non-Pages deployments.

### Changed

* Adding spoilers to individual pages with the `advancement` field is now supported.
* Use [`uv`](https://github.com/astral-sh/uv) instead of `pip` for all reusable workflows.
* `hexdoc ci build` now attempts to read the site url from `HEXDOC_SITE_URL` and `GITHUB_PAGES_URL` environment variables before querying the GitHub API.
* "No translation in {lang} for key {key}" warnings are now only printed once per key for each language to reduce log spam.

## `1!0.1.0a10`

### Added

* Web books will now generate a tree of redirects for categories, entries, and pages with anchors. These redirects include OpenGraph tags for generating Discord embeds.
  * For example, https://hexcasting.hexxy.media/v/latest/main/1.19/en_us/basics now redirects to https://hexcasting.hexxy.media/v/latest/main/1.19/en_us#basics, and the Discord embed for the first link includes the category title "Getting Started".
* Added template variable `relative_site_url`, which is a relative path to the root of the website from the current page.
  * For example, on the page `/v/latest/main/en_us`, `relative_site_url` would be `../../../..` .
* Added `HEXDOC_SUBDIRECTORY` environment variable and `subdirectory` GitHub Actions option, for deploying a hexdoc book alongside other sites/pages.
* Added the ability to print the installed hexdoc version with `hexdoc --version`.

### Changed

* ⚠️ BREAKING: Replaced the `link_bases` system with `book_links` to simplify/improve the link system.
  * This is what we use for constructing hrefs to internal and external categories/entries/pages. It's mostly only used internally, so this change hopefully won't have a big impact.
* Changed the Minecraft version in the dropdown to look like `Minecraft 1.19.2` instead of just `1.19.2`.
* Added more information to the hexdoc startup message, similar to what pytest prints.
* Updated minimum Pydantic version to `2.6.1`.
* Updated internal Pyright version from `1.1.343` to `1.1.345`.
  * We have not updated to `1.1.346` or higher because that version and `1.1.350` both introduce some type errors related to the lack of a `TypeForm` type in Python. The new versions enforce that types like `Union` and `Annotated` should not count as `type`, which is something that Pydantic and hexdoc are currently doing.

### Fixed

* [#47](https://github.com/hexdoc-dev/hexdoc/issues/47): Concurrent builds overwrite each other because merge happens outside of the sequential part

### Removed

* ⚠️ BREAKING: Removed `HexdocTypeAdapter` because `TypeAdapter` is now marked as final (and it never really worked properly anyway).

## `1!0.1.0a9`

### New Features

* Support for the rest of the default Patchouli page types, implemented by [@SamsTheNerd](https://github.com/SamsTheNerd) in [#53](https://github.com/hexdoc-dev/hexdoc/pull/53)!
* Refactored recipe rendering for better reusability - see the default recipe page types for more details.
* Added `ModPlugin.default_rendered_templates_v2`, which works the same as `default_rendered_templates` but gets the book and context as arguments.
  * This is meant to allow generating multi-file book structures instead of a single HTML document.
* `hexdoc.toml`: Added `template.render_from`, which is a list of modids to include default rendered templates from, defaulting to `template.include`.
  * This can be used in conjunction with `template.include` to add a plugin's templates to the environment without rendering its default templates.

### Changed

* The new version dropdown now only uses a submenu if there are at least 2 branches in a given version.
* Refactored `render` and `sitemap` out of `hexdoc.cli.utils` to more appropriate places.
* `ModPlugin.default_rendered_templates` (and `_v2`) may now return `tuple[str, dict[str, Any]]` as the dict value, where the string is the template to render and the dict contains extra arguments to pass to that template.

### Removed

* Removed separators between versions in the new version dropdown to reduce visual clutter.

### Fixed

* Overflowing text with long item names in the new dropdown submenus.
* Incorrect logic for deciding which dropdown items to disable (ie. the current book version being viewed).
* "Unhandled tag" error for page types without a namespace (Patchouli adds `patchouli:` if unspecified, but hexdoc didn't).

## `1!0.1.0a8`

### New Features

* Added `hexdoc_item`, a Jinja filter that looks up an `ItemWithTexture` from the item id.
  * Syntax: `{{ texture_macros.render_item("minecraft:stone"|hexdoc_item) }}`
* Updated the version dropdown! Versions are now grouped by Minecraft version, and branches are hidden behind a submenu to reduce clutter.
  * This allows you to use the same mod version for different Minecraft versions, as long as the plugin version is different.
  * To switch back to the old style, add `hide_dropdown_minecraft_version = true` to the `[template.args]` section of your `hexdoc.toml` file.
* Added `BookPlugin`, a base class for implementing alternative book systems. This is still heavily WIP, and there **will** be more breaking changes. We're planning to use this to implement Modonomicon support.
* Internal: Added a Nox session to generate a dummy book for testing templates locally.

### Changed

* ⚠️ BREAKING: Reworked book loading to support the new `BookPlugin` system. This *probably* won't affect most users, but it is a breaking change.
* `ModPlugin.jinja_template_root` may now return a list of template roots.
* `hexdoc_mod_plugin` may now return a list of plugins.
* `hexdoc merge` and `hexdoc ci merge` will now raise an error if trying to overwrite an existing version in release mode.
  * If you need to bypass this, either pass `--no-release` to `hexdoc [ci] merge`, or delete the `.sitemap-marker.json` file(s) in the merge destination.
* The dropdown item for the current version is now disabled to give better feedback.
* Replaced our `JSONValue` type with an alias for Pydantic's `JsonValue` type.

### Removed

* ⚠️ BREAKING: Removed reexports from `hexdoc.core` for `After_1_20`, `Before_1_19`, etc. They can still be imported from `hexdoc.core.compat` if needed, but this makes the namespace a bit cleaner.

### Fixed

* `AttributeError` when generating error message for a nonexistent resource dir.
* Deserializing the union type `ItemWithTexture | TagWithTexture` sometimes returned `TagWithTexture` for non-tag inputs.

## `1!0.1.0a7`

### New Features

* Implemented Pydantic models for all remaining vanilla recipes (other than `minecraft:special_*`) and page types.
  * Templates for the new page models are still WIP, but the models should now expose all necessary data.
* `hexdoc.toml`: Added support for directly specifying `patchouli_books` directories in `resource_dirs`.
  * This is intended to support the [modpack book layout](https://vazkiimods.github.io/Patchouli/docs/patchouli-basics/getting-started#1-locate-patchouli_books), so the modid for this type of resource dir is always `patchouli`.
  * Syntax:
    ```toml
    resource_dirs = [
        { patchouli_books="path/to/patchouli_books" },
    ]
    ```

### Changed

* The `I18n` missing translation log level is now `DEBUG` when `book.i18n` is `False`.

### Fixed

* Exception classname was not displayed in tagged union validation errors.

## `1!0.1.0a6`

### New Features

* `hexdoc.toml`: Added `textures.enabled`. Set to `false` to disable texture rendering.
* `hexdoc.toml`: Added `macros` for adding local macro overrides, with the same structure as the `book.json` field.
* Added an optional `props` field to `ModPlugin`. Implement `ModPluginImplWithProps` instead of `ModPluginImpl` to get the props object when constructing your plugin.
* Added `ModPlugin.update_jinja_env`.

### Changes

* `hexdoc.toml`: Made `template.icon` optional.
* `hexdoc.toml`: Allowed setting `template.redirect={'!None'=true}` to disable generating redirects in `hexdoc build`.
* `ModPlugin.update_jinja_env` (previously `hexdoc_update_jinja_env`) is now only called if the plugin's modid is in `template.include`.

### Removals

* ⚠️ BREAKING: Removed the `hexdoc_update_jinja_env` hook.

## `1!0.1.0a5`

### New Features

* Added `link_overrides` field to `hexdoc.toml`, for patching broken inter-mod links.
* Created a couple of [Shields.io](https://shields.io) badges for hexdoc.
* Started keeping a changelog!

### Changes

* ⚠️ BREAKING: Completely reworked the validation context system. Context is now a dict (returning to the Pydantic standard), and classes can now inherit from `hexdoc.utils.ValidationContext` to get the methods `.of()` and `.add_to_context()`. `BookContext` is no longer the god object for all validation context.
* Moved Hatch to a required dependency, from `[pdoc]`.
* Slightly tweaked the page footer text.

### Fixes

* Fixed an issue that was preventing CI plugin builds from being copied to the Pages branch.
* Fixed category spoilers not taking external entries into account.
