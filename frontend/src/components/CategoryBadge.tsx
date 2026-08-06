import { categoryColor } from "../constants";

export function CategoryBadge({ category }: { category: string }) {
  const color = categoryColor(category);
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 10px",
        borderRadius: 999,
        fontSize: "0.75rem",
        fontWeight: 600,
        color,
        background: `${color}26`,
        border: `1px solid ${color}55`,
      }}
    >
      {category}
    </span>
  );
}
