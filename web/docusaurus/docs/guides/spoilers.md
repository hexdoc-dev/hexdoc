# Spoilers

Patchouli's [advancement locking system](https://vazkiimods.github.io/Patchouli/docs/patchouli-basics/advancement-locking) can be used with hexdoc to automatically add a spoiler blur to late-game categories and entries.

:::warning

[Spoilering individual pages](https://vazkiimods.github.io/Patchouli/docs/patchouli-basics/page-types#advancement-string) is **not yet supported** by hexdoc. The `advancement` field is allowed, but the value will be ignored.

:::

## Marking advancements as spoilers

hexdoc checks a [custom tag](https://minecraft.wiki/w/Tag) in the `advancements` registry (`#hexdoc:spoilered`) to figure out which advancements are considered spoilers. This tag is empty by default.

To mark an advancement as spoilered, add it to a JSON tag file in the correct location. This tag is not used ingame, so it will work fine if created in a hexdoc-only resources directory.

```json title="doc/resources/data/hexdoc/tags/advancements/spoilered.json"
{
    "replace": false,
    "values": [
        "minecraft:nether/all_effects"
    ]
}
```

:::tip

Because [`fnmatch.fnmatch`](https://docs.python.org/3/library/fnmatch.html#fnmatch.fnmatch) is used for comparisons, resource locations in this file can include wildcards (eg. `hexcasting:lore/*`).

:::

## Example

![A screenshot of a spoilered entry in the Hex Casting web book](/img/spoilers.png)

:::hex-casting

As seen in this screenshot, Hex Casting's hexdoc plugin [adds several advancements](https://github.com/object-Object/HexMod/blob/3c7d0e88707a13a6e2c7d4cc75472a8763e6253c/doc/resources/data/hexdoc/tags/advancements/spoilered.json) to `#hexdoc:spoilered` which can be used by addons.

:::
