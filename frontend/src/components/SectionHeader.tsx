import styles from "./SectionHeader.module.css";

export function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className={styles.row}>
      <div>
        <h2 className={styles.title}>{title}</h2>
        {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
      </div>
    </div>
  );
}
