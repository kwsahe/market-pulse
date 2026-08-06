import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { CategoryStat } from "../types/api";
import { categoryColor } from "../constants";

export function CategoryBarChart({
  data,
  valueKey,
  valueLabel,
  formatValue,
}: {
  data: CategoryStat[];
  valueKey: "avg_price" | "count";
  valueLabel: string;
  formatValue: (value: number) => string;
}) {
  const sorted = [...data].sort((a, b) => b[valueKey] - a[valueKey]);

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={sorted} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--mp-border)" vertical={false} />
        <XAxis dataKey="category" stroke="var(--mp-muted)" fontSize={12} tickLine={false} />
        <YAxis
          stroke="var(--mp-muted)"
          fontSize={12}
          tickLine={false}
          axisLine={false}
          tickFormatter={formatValue}
        />
        <Tooltip
          contentStyle={{
            background: "var(--mp-surface-raised)",
            border: "1px solid var(--mp-border)",
            borderRadius: 10,
            color: "var(--mp-text)",
          }}
          formatter={(value) => [formatValue(Number(value)), valueLabel]}
        />
        <Bar dataKey={valueKey} radius={[6, 6, 0, 0]}>
          {sorted.map((entry) => (
            <Cell key={entry.category} fill={categoryColor(entry.category)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
