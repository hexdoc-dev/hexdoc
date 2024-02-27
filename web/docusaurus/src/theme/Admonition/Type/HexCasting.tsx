import React from "react";
import clsx from "clsx";
import AdmonitionLayout from "@theme/Admonition/Layout";
import IconHexCasting from "@site/static/img/hexxy.svg";
import type { Props } from "@theme/Admonition";

const infimaClassName = "alert alert--secondary";

const defaultProps = {
  icon: <IconHexCasting />,
  title: "Hex Addons",
};

export default function AdmonitionTypeHexCasting(props: Props) {
  return (
    <AdmonitionLayout
      {...defaultProps}
      {...props}
      className={clsx(infimaClassName, props.className)}
    >
      {props.children}
    </AdmonitionLayout>
  );
}
