# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Pydantic's HISTORY.md](https://github.com/pydantic/pydantic/blob/main/HISTORY.md), and this project *mostly* adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### New Features

* `hexdoc_item`, a Jinja filter that looks up an `ItemWithTexture` from the item id.
  * Syntax: `{{ texture_macros.render_item("minecraft:stone"|hexdoc_item) }}`

### Changed

* `ModPlugin.jinja_template_root` can now return a list of tuples, to expose multiple template roots from a single plugin.

### Fixed

* `AttributeError` when generating error message for a nonexistent resource dir.

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
