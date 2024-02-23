import { themes as prismThemes } from "prism-react-renderer";
import type { Config } from "@docusaurus/types";
import type * as Preset from "@docusaurus/preset-classic";

const config: Config = {
  title: "hexdoc",
  favicon: "favicon.ico",

  url: "https://hexdoc.hexxy.media",
  baseUrl: "/",

  organizationName: "hexdoc-dev",
  projectName: "hexdoc",

  onBrokenLinks: "throw",
  onBrokenMarkdownLinks: "warn",

  i18n: {
    defaultLocale: "en",
    locales: ["en"],
  },

  presets: [
    [
      "classic",
      {
        docs: {
          routeBasePath: "/",
          sidebarPath: "./sidebars.ts",
          editUrl:
            "https://github.com/hexdoc-dev/hexdoc/tree/main/docs/docusaurus/",
        },
        blog: false,
        theme: {
          customCss: "./src/css/custom.css",
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: "img/hexdoc.png",
    navbar: {
      title: "hexdoc",
      logo: {
        alt: "hexdoc logo",
        src: "img/hexdoc.svg",
      },
      items: [
        {
          type: "docSidebar",
          label: "Docs",
          sidebarId: "sidebar",
          position: "left",
        },
        {
          label: "API",
          to: "pathname:///api",
          position: "left",
        },
        {
          label: "PyPI",
          href: "https://pypi.org/project/hexdoc",
          position: "right",
        },
        {
          label: "GitHub",
          href: "https://github.com/hexdoc-dev/hexdoc",
          position: "right",
        },
      ],
    },
    footer: {
      style: "dark",
      copyright: `Copyright © ${new Date().getFullYear()} hexdoc-dev. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ["css", "toml"],
    },
    colorMode: {
      defaultMode: "dark",
    },
  } satisfies Preset.ThemeConfig,

  staticDirectories: ["static", "static-generated"],
};

export default config;