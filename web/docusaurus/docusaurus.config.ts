import { themes as prismThemes } from "prism-react-renderer";
import type { Config } from "@docusaurus/types";
import type * as Preset from "@docusaurus/preset-classic";
import internalPathnameLinks from "./src/remark/internalPathnameLinks";

const SITE_URL = "https://hexdoc.hexxy.media";

const GITHUB_ORG = "hexdoc-dev";
const GITHUB_REPO = "hexdoc";
const GITHUB_ORG_URL = `https://github.com/${GITHUB_ORG}`;
const GITHUB_REPO_URL = `${GITHUB_ORG_URL}/${GITHUB_REPO}`;

const config: Config = {
  title: "hexdoc",
  favicon: "favicon.ico",

  url: SITE_URL,
  baseUrl: "/",

  organizationName: GITHUB_ORG,
  projectName: GITHUB_REPO,

  onBrokenLinks: "throw",
  onBrokenMarkdownLinks: "warn",

  i18n: {
    defaultLocale: "en",
    locales: ["en"],
  },

  staticDirectories: ["static", "static-generated"],

  presets: [
    [
      "classic",
      {
        docs: {
          sidebarPath: "./sidebars.ts",
          editUrl: `${GITHUB_REPO_URL}/tree/main/web/docusaurus/`,
          admonitions: {
            keywords: ["hex-casting"],
            extendDefaults: true,
          },
          beforeDefaultRemarkPlugins: [internalPathnameLinks],
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
      logo: { alt: "hexdoc logo", src: "img/hexdoc.svg" },
      items: [
        // left
        {
          label: "Docs",
          type: "docSidebar",
          sidebarId: "sidebar",
          position: "left",
        },
        {
          label: "API",
          to: "pathname:///docs/api/",
          target: null, // disable opening in a new tab by default
          rel: null,
          position: "left",
        },

        // right
        {
          label: "PyPI",
          href: "https://pypi.org/project/hexdoc",
          position: "right",
        },
        {
          label: "GitHub",
          href: GITHUB_REPO_URL,
          position: "right",
        },
      ],
    },

    footer: {
      style: "dark",
      // TODO: target blank etc etc (Link no worky)
      copyright: `Copyright © ${new Date().getFullYear()} <a href="${GITHUB_ORG_URL}" target="_blank">hexdoc-dev</a>. Built with <a href="https://docusaurus.io" target="_blank">Docusaurus</a>.`,
    },

    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ["css", "toml", "json", "bash"],
    },

    colorMode: {
      defaultMode: "dark",
    },

    metadata: [
      {
        name: "twitter:card",
        content: "summary",
      },
    ],

    algolia: {
      appId: "80YMFEUQR0",
      apiKey: "e343669523bbc4dff590247b05498ff2",
      indexName: "hexdoc",
      contextualSearch: true,
      searchPagePath: "search",
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
