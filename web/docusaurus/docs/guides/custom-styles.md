# Custom Styles

The easiest way to customize the appearance of your web book is by adding styles to `index.css`.

## Using [`template.extend_render`](pathname:///docs/api/hexdoc/core/properties.html#TemplateProps.extend_render) to overwrite `index.css`

Create a template called `yourmodid.css.jinja`:

```css title="doc/src/hexdoc_yourmodid/_templates/yourmodid.css.jinja"
{% include "index.css.jinja" %}

body {
  background-color: red;
}
```

The `include` tag ([Jinja docs](https://jinja.palletsprojects.com/en/3.0.x/templates/#include)) inserts the contents of the template `index.css.jinja` from the plugin `hexdoc`. This is important if you want to keep the default hexdoc CSS styles.

:::tip

Any filename can be used here, but we recommend using your modid to help avoid conflicts with other plugins.

:::

Then, add the following to your `hexdoc.toml` file:

```toml title="doc/hexdoc.toml"
[template.extend_render]
"index.css" = "yourmodid:yourmodid.css.jinja"
```

This tells hexdoc to create a file called `index.css` using the template `yourmodid.css.jinja` from the plugin `yourmodid`.

:::note

This section of the `hexdoc.toml` file is not exported, so it won't affect any other plugins that depend on your book.

:::

## Directly extending `index.css.jinja`

Create a template called `index.css.jinja`:

```css title="doc/src/hexdoc_yourmodid/_templates/index.css.jinja"
{% include "hexdoc:index.css.jinja" %}

body {
  background-color: red;
}
```

:::note

If you're creating a book for a Hex Casting addon, use `hexcasting:index.css.jinja` instead of `hexdoc:index.css.jinja`.

:::

:::warning

There are two problems with this approach:

* You must specify a namespace (the `hexdoc:` part) to prevent the template from recursively rendering itself. This can be error-prone if you pick the wrong namespace.
  * For example, [hexdoc-hexcasting](https://github.com/object-Object/HexMod/blob/7edab68db2bee50285e354f7c9b935b512ebc4bd/doc/src/hexdoc_hexcasting/_templates/index.css.jinja) adds styles to `index.css`, which is why the above note is necessary.
* Your custom styles might interfere with other hexdoc plugins if they add your modid to [`template.include`](pathname:///docs/api/hexdoc/core/properties.html#TemplateProps.include).

Both of these problems can be avoided by using the `template.extend_render` approach.

:::
