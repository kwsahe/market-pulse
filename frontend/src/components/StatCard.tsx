import styles from "./StatCard.module.css";

export interface Stat {
  label: string;
  value: string;
  color?: string;
  accent?: boolean;
}

export function StatCards({ stats }: { stats: Stat[] }) {
  return (
    <div className={styles.grid}>
      {stats.map((stat) => (
        <div
          key={stat.label}
          className={`${styles.card} ${stat.accent ? styles.accent : ""}`}
        >
          <div className={styles.label}>{stat.label}</div>
          <div className={styles.value} style={stat.color ? { color: stat.color } : undefined}>
            {stat.value}
          </div>
        </div>
      ))}
    </div>
  );
}
