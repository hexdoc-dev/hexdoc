# Config Flags

As of `v1!0.1.0a31`, hexdoc has full support for Patchouli's [config flag system](https://vazkiimods.github.io/Patchouli/docs/patchouli-basics/config-gating).

## Default flags

The following flags default to false:

- `debug`
- `advancements_disabled`
- All flags starting with `advancements_disabled_`
- `testing_mode`

Unlike Patchouli, **all other flags default to true** if not defined. This generally provides a more complete default state for the web book, ensuring that all optional content is enabled by default.

:::tip

This behaviour makes it easy to add content that's only visible in Patchouli or hexdoc, but not both. You can use the flag `mod:hexdoc:web_only` to hide content ingame, or `!mod:hexdoc:web_only` to hide content in the web book. This flag has no special meaning in hexdoc or Patchouli; rather, it exploits the fact that hexdoc and Patchouli have opposite defaults for unknown flags. The `mod:` prefix ensures that an "undefined flag" warning will not be logged, and the `:` in `hexdoc:web_only` ensures that this flag will never conflict with an actual modid.

:::

## Setting flags

There are two ways to override the default values of flags in hexdoc. The first method is to add them to `hexdoc.toml` as follows:

```toml title="doc/hexdoc.toml"
[flags]
"yourmod:foo" = false
```

Flags set in `hexdoc.toml` only apply to your own web book - they won't affect other mods that depend on your hexdoc plugin. Also, this can be used to **override** values from other sources. For example, if another mod sets flag `foo` to true, you can use `hexdoc.toml` to override it to false.

The second method is to implement [`ModPlugin.flags`](pathname:///docs/api/hexdoc/plugin/mod_plugin.html#ModPlugin.flags). Flags returned by this hook are available for use by mods that depend on your hexdoc plugin. If multiple mods define flags using this hooks, the values are combined using OR. For example, if one mod uses this hook to set flag `foo` to true, and another mod sets it to false, the final value will be true.
