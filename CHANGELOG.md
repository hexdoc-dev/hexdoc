# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Pydantic's HISTORY.md](https://github.com/pydantic/pydantic/blob/main/HISTORY.md), and this project *mostly* adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
