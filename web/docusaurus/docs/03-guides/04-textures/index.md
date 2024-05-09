import Tabs from "@theme/Tabs";
import TabItem from "@theme/TabItem";
import ModelPrecedence from "./_model_precedence.md";

# Textures

## Model precedence

When loading or rendering a model `namespace:path` (eg. `minecraft:item/stick`), the following options will be attempted in this order; the first to successfully load will be used.

<Tabs>
  {
    [
      { namespace: "{namespace}", path: "{path}" },
      { namespace: "minecraft", path: "item/stick" },
    ].map((props, i) => {
      const { namespace, path } = props;
      const key = i == 0 ? "generic" : `example${i}`;
      return (
        <TabItem
          key={key}
          value={key}
          label={i == 0 ? "Generic" : <code>{namespace}:{path}</code>}
        >
          <ModelPrecedence {...props} />
        </TabItem>
      );
    })
  }
</Tabs>

:::note

In hexdoc.toml, if `textures.strict` is `True` (the default) and none of the above options are successfully loaded, the build will fail.

:::
