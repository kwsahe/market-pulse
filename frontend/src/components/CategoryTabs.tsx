import styles from "./CategoryTabs.module.css";

export function CategoryTabs({
  categories,
  active,
  onChange,
}: {
  categories: string[];
  active: string;
  onChange: (category: string) => void;
}) {
  return (
    <div className={styles.tabs}>
      <button
        className={active === "" ? styles.tabActive : styles.tab}
        onClick={() => onChange("")}
      >
        전체
      </button>
      {categories.map((cat) => (
        <button
          key={cat}
          className={active === cat ? styles.tabActive : styles.tab}
          onClick={() => onChange(cat)}
        >
          {cat}
        </button>
      ))}
    </div>
  );
}
