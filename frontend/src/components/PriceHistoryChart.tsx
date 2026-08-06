import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PricePoint } from "../types/api";

export function PriceHistoryChart({ history, color }: { history: PricePoint[]; color: string }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={history} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--mp-border)" vertical={false} />
        <XAxis dataKey="date" stroke="var(--mp-muted)" fontSize={12} tickLine={false} />
        <YAxis
          stroke="var(--mp-muted)"
          fontSize={12}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: number) => `${(v / 10000).toFixed(0)}만`}
        />
        <Tooltip
          contentStyle={{
            background: "var(--mp-surface-raised)",
            border: "1px solid var(--mp-border)",
            borderRadius: 10,
            color: "var(--mp-text)",
          }}
          formatter={(value) => [`${Number(value).toLocaleString()}원`, "가격"]}
        />
        <Line type="monotone" dataKey="price" stroke={color} strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
