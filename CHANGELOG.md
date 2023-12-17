# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Pydantic's HISTORY.md](https://github.com/pydantic/pydantic/blob/main/HISTORY.md), and this project *mostly* adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1!0.1.0a6]

### New Features

- `hexdoc.toml`: Added `textures.enabled`. Set to `false` to disable texture rendering.
- Added `props` to the instance attributes of `ModPlugin`. Implement `ModPluginImplWithProps` to get the props object when constructing your plugin.
- Added `ModPlugin.update_jinja_env`.

### Changes

- `hexdoc.toml`: Made `template.icon` optional.
- `hexdoc.toml`: Allowed setting `template.redirect={'!None'=true}` to disable generating redirects in `hexdoc build`.
- `ModPlugin.update_jinja_env` (previously `hexdoc_update_jinja_env`) is now only called if the plugin's modid is in `template.include`.

### Removals

- ⚠️ BREAKING: Removed the `hexdoc_update_jinja_env` hook.

## [1!0.1.0a5]

### New Features

- Added `link_overrides` field to `hexdoc.toml`, for patching broken inter-mod links.
- Created a couple of [Shields.io](https://shields.io) badges for hexdoc.
- Started keeping a changelog!

### Changes

- ⚠️ BREAKING: Completely reworked the validation context system. Context is now a dict (returning to the Pydantic standard), and classes can now inherit from `hexdoc.utils.ValidationContext` to get the methods `.of()` and `.add_to_context()`. `BookContext` is no longer the god object for all validation context.
- Moved Hatch to a required dependency, from `[pdoc]`.
- Slightly tweaked the page footer text.

### Fixes

- Fixed an issue that was preventing CI plugin builds from being copied to the Pages branch.
- Fixed category spoilers not taking external entries into account.
