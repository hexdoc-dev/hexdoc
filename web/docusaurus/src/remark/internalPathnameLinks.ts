import type { Transformer } from "unified";
import type { Parent } from "unist";
import type { Link } from "mdast";
import type {
  MdxJsxFlowElement,
  MdxjsEsm,
  MdxJsxAttributeValueExpression,
} from "mdast-util-mdx";
import { transformNode } from "@docusaurus/mdx-loader/src/remark/utils";
import escapeHtml from "escape-html";
import { visit } from "unist-util-visit";

// Transforms links starting with `static://` into <Link> elements with `pathname://` and `target={null}`.
// See: https://github.com/facebook/docusaurus/issues/3309#issuecomment-893839723
// Based on: https://github.com/facebook/docusaurus/blob/caa81e570afd/packages/docusaurus-mdx-loader/src/remark/transformLinks/index.ts

const URL_SCHEME = "static://";

/*
{
  type: 'link',
  title: null,
  url: '/docs/api/hexdoc/core/properties.html',
  children: [
    {
      type: 'text',
      value: 'hexdoc.core.properties',
      position: [Object]
    }
  ],
  position: {
    start: { line: 21, column: 1, offset: 935 },
    end: { line: 21, column: 64, offset: 998 }
  }
}

{
  type: 'link',
  title: null,
  url: 'pathname:///docs/api/hexdoc/core/properties.html',
  children: [
    {
      type: 'text',
      value: 'hexdoc.core.properties',
      position: [Object]
    }
  ],
  position: {
    start: { line: 23, column: 1, offset: 1002 },
    end: { line: 23, column: 75, offset: 1076 }
  }
}

{
  type: 'link',
  title: null,
  url: 'static:///docs/api/hexdoc/core/properties.html',
  children: [
    {
      type: 'text',
      value: 'hexdoc.core.properties',
      position: [Object]
    }
  ],
  position: {
    start: { line: 25, column: 1, offset: 1080 },
    end: { line: 25, column: 73, offset: 1152 }
  }
}

{
  type: 'mdxJsxFlowElement',
  name: 'Link',
  attributes: [
    {
      type: 'mdxJsxAttribute',
      name: 'to',
      value: 'pathname:///docs/api/hexdoc/core/properties.html',
      position: {
        start: { line: 27, column: 7, offset: 1162 },
        end: { line: 27, column: 60, offset: 1215 }
      }
    },
    {
      type: 'mdxJsxAttribute',
      name: 'target',
      value: {
        type: 'mdxJsxAttributeValueExpression',
        value: 'null',
        data: {
          estree: {
            type: 'Program',
            start: 1224,
            end: 1228,
            body: [
              {
                type: 'ExpressionStatement',
                expression: Node {
                  type: 'Literal',
                  start: 1224,
                  end: 1228,
                  loc: {
                    start: { line: 27, column: 68, offset: 1224 },
                    end: { line: 27, column: 72, offset: 1228 }
                  },
                  value: null,
                  raw: 'null',
                  range: [ 1224, 1228 ]
                },
                start: 1224,
                end: 1228,
                loc: {
                  start: { line: 27, column: 68, offset: 1224 },
                  end: { line: 27, column: 72, offset: 1228 }
                },
                range: [ 1224, 1228 ]
              }
            ],
            sourceType: 'module',
            comments: [],
            loc: {
              start: { line: 27, column: 68, offset: 1224 },
              end: { line: 27, column: 72, offset: 1228 }
            },
            range: [ 1224, 1228 ]
          }
        }
      },
      position: {
        start: { line: 27, column: 61, offset: 1216 },
        end: { line: 27, column: 74, offset: 1229 }
      }
    },
    {
      type: 'mdxJsxAttribute',
      name: 'rel',
      value: {
        type: 'mdxJsxAttributeValueExpression',
        value: 'null',
        data: {
          estree: {
            type: 'Program',
            start: 1235,
            end: 1239,
            body: [
              {
                type: 'ExpressionStatement',
                expression: Node {
                  type: 'Literal',
                  start: 1235,
                  end: 1239,
                  loc: {
                    start: { line: 27, column: 79, offset: 1235 },
                    end: { line: 27, column: 83, offset: 1239 }
                  },
                  value: null,
                  raw: 'null',
                  range: [ 1235, 1239 ]
                },
                start: 1235,
                end: 1239,
                loc: {
                  start: { line: 27, column: 79, offset: 1235 },
                  end: { line: 27, column: 83, offset: 1239 }
                },
                range: [ 1235, 1239 ]
              }
            ],
            sourceType: 'module',
            comments: [],
            loc: {
              start: { line: 27, column: 79, offset: 1235 },
              end: { line: 27, column: 83, offset: 1239 }
            },
            range: [ 1235, 1239 ]
          }
        }
      },
      position: {
        start: { line: 27, column: 75, offset: 1230 },
        end: { line: 27, column: 85, offset: 1240 }
      }
    }
  ],
  children: [
    {
      type: 'text',
      value: 'hexdoc.core.properties',
      position: {
        start: { line: 27, column: 86, offset: 1241 },
        end: { line: 27, column: 108, offset: 1263 }
      }
    }
  ],
  position: {
    start: { line: 27, column: 1, offset: 1156 },
    end: { line: 27, column: 115, offset: 1270 }
  },
  data: { _mdxExplicitJsx: true }
}
*/

const nullExpression: MdxJsxAttributeValueExpression = {
  type: "mdxJsxAttributeValueExpression",
  value: "null",
  data: {
    estree: {
      type: "Program",
      sourceType: "module",
      body: [
        {
          type: "ExpressionStatement",
          expression: {
            type: "Literal",
            value: null,
            raw: "null",
          },
        },
      ],
    },
  },
};

// import foo from "bar";
function defaultImportNode({
  name,
  source,
}: {
  name: string;
  source: string;
}): MdxjsEsm {
  return {
    type: "mdxjsEsm",
    value: `import ${name} from '${source}';`,
    data: {
      estree: {
        type: "Program",
        sourceType: "module",
        body: [
          {
            type: "ImportDeclaration",
            specifiers: [
              {
                type: "ImportDefaultSpecifier",
                local: { type: "Identifier", name },
              },
            ],
            source: {
              type: "Literal",
              value: source,
              raw: `'${source}'`,
            },
          },
        ],
      },
    },
  };
}

function processLinkNode(node: Link) {
  if (!node.url.startsWith(URL_SCHEME)) return;

  const strippedUrl = node.url.slice(URL_SCHEME.length);
  const newUrl = `pathname://${strippedUrl}`;

  const attributes: MdxJsxFlowElement["attributes"] = [];

  // to=newUrl target={null} rel={null}
  attributes.push(
    {
      type: "mdxJsxAttribute",
      name: "to",
      value: newUrl,
    },
    {
      type: "mdxJsxAttribute",
      name: "target",
      value: nullExpression,
    },
    {
      type: "mdxJsxAttribute",
      name: "rel",
      value: nullExpression,
    }
  );

  if (node.title) {
    attributes.push({
      type: "mdxJsxAttribute",
      name: "title",
      value: escapeHtml(node.title),
    });
  }

  const children = node.children;

  transformNode(node, {
    type: "mdxJsxFlowElement",
    name: "Link",
    attributes,
    children,
  });
}

export default function plugin(): Transformer {
  return (tree: Parent) => {
    visit(tree, "link", processLinkNode);

    // https://github.com/mrazauskas/docusaurus-remark-plugin-tab-blocks/blob/fb535617b7a3/index.js#L146
    let includesImportLink = false;

    visit(tree, "mdxjsEsm", (node: MdxjsEsm, index, parent) => {
      if (node.value.includes("@docusaurus/Link")) {
        includesImportLink = true;
      }
    });

    if (!includesImportLink) {
      tree.children.unshift(
        defaultImportNode({ name: "Link", source: "@docusaurus/Link" })
      );
    }
  };
}
