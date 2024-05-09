# Patchouli JSON Schemas

hexdoc automatically generates [JSON Schema](https://json-schema.org/) definitions for several Patchouli file types.

## Types

|Type|Schema|
|----|------|
|[Book](https://vazkiimods.github.io/Patchouli/docs/reference/book-json)|[/schema/patchouli/Book.json](pathname:///schema/patchouli/Book.json)|
|[Category](https://vazkiimods.github.io/Patchouli/docs/reference/category-json)|[/schema/patchouli/Category.json](pathname:///schema/patchouli/Category.json)|
|[Entry](https://vazkiimods.github.io/Patchouli/docs/reference/entry-json)|[/schema/patchouli/Entry.json](pathname:///schema/patchouli/Entry.json)|

## VSCode configuration

To use these schemas in VSCode, add the following content to your `settings.json` file:

```json
{
    "json.schemas": [
        {
            "fileMatch": ["**/patchouli_books/*/book.json"],
            "url": "https://hexdoc.hexxy.media/schema/patchouli/Book.json",
        },
        {
            "fileMatch": ["**/patchouli_books/*/*/categories/**/*.json"],
            "url": "https://hexdoc.hexxy.media/schema/patchouli/Category.json",
        },
        {
            "fileMatch": ["**/patchouli_books/*/*/entries/**/*.json"],
            "url": "https://hexdoc.hexxy.media/schema/patchouli/Entry.json",
        },
    ],
}
```
