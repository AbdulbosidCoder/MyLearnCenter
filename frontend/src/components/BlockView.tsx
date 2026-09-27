import type { Block } from "../api";
import { WidgetView } from "../widgets";
import { Markdown } from "./Markdown";

export function BlockView({ block }: { block: Block }) {
  switch (block.type) {
    case "text":
      return (
        <div className="theory">
          <Markdown>{block.content}</Markdown>
        </div>
      );
    case "gif":
    case "image":
      return (
        <figure>
          <img src={block.content} alt={block.caption} loading="lazy" />
          {block.caption && <figcaption>{block.caption}</figcaption>}
        </figure>
      );
    case "viz":
      return (
        <figure>
          <WidgetView content={block.content} />
          {block.caption && <figcaption>{block.caption}</figcaption>}
        </figure>
      );
    case "video":
      return (
        <figure>
          <video src={block.content} controls playsInline />
          {block.caption && <figcaption>{block.caption}</figcaption>}
        </figure>
      );
  }
}
