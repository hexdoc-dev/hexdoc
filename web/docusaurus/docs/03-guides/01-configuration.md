import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Configuration

Most configuration for hexdoc can be done in the `hexdoc.toml` (or `doc/hexdoc.toml`) file.

## File paths

Most file paths in the `hexdoc.toml` file are resolved relative to the location of the config file, *not* the working directory of the `hexdoc` command or the root of the Git repository.

For example, in the below file structure, the following `hexdoc.toml` file would correctly reference the `src/main/resources` directory, regardless of where the `hexdoc` command is executed from:

```
.
├── doc/
│   └── hexdoc.toml
└── src/
    └── main/
        └── resources/
```

```toml title="doc/hexdoc.toml"
resource_dirs = [
    "../src/main/resources",
]
```

## TOML placeholders

The `hexdoc.toml` parser includes a custom placeholder interpolation system, similar to [JSONPath](https://github.com/json-path/JsonPath), that allows referencing other values in the config file (eg. for reusing common values).

Placeholders are added to strings in the format `{key}`, similar to Python's [f-strings](https://docs.python.org/3/tutorial/inputoutput.html#tut-f-strings). The string may also contain other text outside of the placeholder. By default, placeholder keys are resolved relative to the table containing the placeholder.

export const parserTabValues = [
  {value: "input", label: "Before parsing"},
  {value: "output", label: "After parsing"},
];

<Tabs groupId="parser" values={parserTabValues}>
  <TabItem value="input">
    ```toml
    key = "foo {var} baz"
    var = "bar"
    ```
  </TabItem>
  <TabItem value="output">
    ```toml
    key = "foo bar baz"
    var = "bar"
    ```
  </TabItem>
</Tabs>

Placeholders must reference keys containing string values; the following example is invalid and would raise an error.

<Tabs groupId="parser" values={parserTabValues}>
  <TabItem value="input">
    ```toml
    key = "{var}"
    var = 0
    ```
  </TabItem>
  <TabItem value="output">
    ```toml
    key = <INVALID>
    var = 0
    ```
  </TabItem>
</Tabs>

### Parent references

The key `^` may be used to reference the table containing the current table (ie. the parent table). It can be used multiple times to reference grandparents, great-grandparents, and so on. Parent references may optionally be separated by `.` characters.

<Tabs groupId="parser" values={parserTabValues}>
  <TabItem value="input">
    ```toml
    [foo.bar]
    key1 = "{^^baz.var}"
    key2 = "{^.^.baz.var}"

    [baz]
    var = "value"
    ```
  </TabItem>
  <TabItem value="output">
    ```toml
    [foo.bar]
    key1 = "value"
    key2 = "value"

    [baz]
    var = "value"
    ```
  </TabItem>
</Tabs>

### Root references

The key `$` may be used at the start of a placeholder key to reference the root table of the TOML file. It may optionally be followed by a `.` character.

<Tabs groupId="parser" values={parserTabValues}>
  <TabItem value="input">
    ```toml
    [foo]
    key1 = "{$var}"

    [foo.bar]
    key2 = "$.var"

    var = "value"
    ```
  </TabItem>
  <TabItem value="output">
    ```toml
    [foo]
    key1 = "value"

    [foo.bar]
    key2 = "value"

    var = "value"
    ```
  </TabItem>
</Tabs>

### Arrays

Placeholders in arrays are resolved relative to the table containing the array. However, placeholders in tables within arrays are resolved relative to the table in the array.

<Tabs groupId="parser" values={parserTabValues}>
  <TabItem value="input">
    ```toml
    key1 = [
        "{var}",
        { key2="{^var}" }
    ]

    var = "value"
    ```
  </TabItem>
  <TabItem value="output">
    ```toml
    key1 = [
        "value",
        { key2="value" }
    ]

    var = "value"
    ```
  </TabItem>
</Tabs>

For this reason, it is usually more readable to use root references within arrays.

<Tabs groupId="parser" values={parserTabValues}>
  <TabItem value="input">
    ```toml
    key1 = [
        "{$var}",
        { key2="{$var}" }
    ]

    var = "value"
    ```
  </TabItem>
  <TabItem value="output">
    ```toml
    key1 = [
        "value",
        { key2="value" }
    ]

    var = "value"
    ```
  </TabItem>
</Tabs>

## Custom fields

To make your `hexdoc.toml` file easier to maintain, you can add custom fields starting with the prefix `_`. All fields starting with `_` will be silently ignored by hexdoc (instead of raising a validation error for unrecognized fields).

For example, custom fields and placeholders are used by the [hexdoc project templates](./template) to define common paths that are used in multiple places:

<Tabs groupId="parser" values={parserTabValues}>
  <TabItem value="input">
    ```toml title="doc/hexdoc.toml"
    resource_dirs = [
        "{$_common.src}/main/resources",
        { path="{$_common.src}/generated/resources", required=false },
    ]

    [[extra.hexcasting.pattern_stubs]]
    path = "{$_common.package}/Patterns.java"

    [_common]
    src = "../common/src"
    package = "{src}/main/java/com/example"
    ```
  </TabItem>
  <TabItem value="output">
    ```toml title="doc/hexdoc.toml"
    resource_dirs = [
        "../common/src/main/resources",
        { path="../common/src/generated/resources", required=false },
    ]

    [[extra.hexcasting.pattern_stubs]]
    path = "../common/src/main/java/com/example/Patterns.java"
    ```
  </TabItem>
</Tabs>

Note that since the `_common` table starts with `_`, the fields within that table (eg. `_common.src`) are not parsed by hexdoc, so they don't need to start with `_`.

:::note

This is similar to Docker Compose's [Extensions](https://docs.docker.com/compose/compose-file/11-extension/) feature.

:::

## Intrinsic functions

Intrinsic functions are tables with a key starting with the prefix `!` that are handled specially by the TOML parser.

To use an intrinsic function, create a table with a single entry, where the key is the name of the function, and the value is the input to the function. For example:

<Tabs groupId="parser" values={parserTabValues}>
  <TabItem value="input">
    ```toml
    key1 = "value"             # normal value
    key2."!Raw" = "value"      # !Raw function (option 1)
    key3 = { "!Raw"="value" }  # !Raw function (option 2)
    ```
  </TabItem>
  <TabItem value="output">
    ```toml
    key1 = "value"             # normal value
    key2 = "value"             # !Raw function (option 1)
    key3 = "value"             # !Raw function (option 2)
    ```
  </TabItem>
</Tabs>

:::note

The last two examples above are logically equivalent in TOML, and are both equivalent to the following JSON value before being parsed by hexdoc.

```json
{
    "key": {
        "!Raw": "value"
    }
}
```

:::

### `!Raw`

Outputs the value passed to this function as-is, without any further processing (eg. string placeholders and intrinsic functions will not be expanded). Useful for defining regular expressions.

<Tabs groupId="parser" values={parserTabValues}>
  <TabItem value="input">
    ```toml
    pattern1."!Raw" = "^{.+}$"
    pattern2 = { "!Raw"="^{.+}$" }
    ```
  </TabItem>
  <TabItem value="output">
    ```toml
    pattern1 = "^{.+}$"
    pattern2 = "^{.+}$"
    ```
  </TabItem>
</Tabs>

### `!None`

Outputs `None`. The input value is ignored. This function is necessary because TOML [does not have a `null` keyword](https://github.com/toml-lang/toml/issues/30).

<Tabs groupId="parser" values={parserTabValues}>
  <TabItem value="input">
    ```toml
    null1."!None" = ""
    null2 = { "!None"="" }
    ```
  </TabItem>
  <TabItem value="output">
    ```toml
    null1 = None
    null2 = None
    ```
  </TabItem>
</Tabs>

## JSON Schema

If you use a TOML validator with JSON Schema support (eg. the [Even Better TOML](https://marketplace.visualstudio.com/items?itemName=tamasfe.even-better-toml) VSCode extension), you can get autocomplete and validation for `hexdoc.toml` files by using the [autogenerated JSON Schema definition](https://hexdoc.hexxy.media/schema/core/Properties.json).

With Taplo-based tools like Even Better TOML, you can enable the schema by adding the following comment to the top of `hexdoc.toml` ([docs](https://taplo.tamasfe.dev/configuration/directives.html#the-schema-directive)):

```toml
#:schema https://hexdoc.hexxy.media/schema/core/Properties.json
```
