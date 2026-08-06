import { useEffect, useState, type ReactNode } from "react";
import styles from "./Carousel.module.css";

export function Carousel({ slides, seconds = 4 }: { slides: ReactNode[]; seconds?: number }) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    setIndex(0);
    if (slides.length <= 1) return;
    const id = setInterval(() => setIndex((i) => (i + 1) % slides.length), seconds * 1000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slides.length, seconds]);

  if (slides.length === 0) return null;

  return (
    <div className={styles.wrap}>
      <div key={index} className={styles.slide}>
        {slides[index]}
      </div>
      {slides.length > 1 && (
        <div className={styles.dots}>
          {slides.map((_, i) => (
            <span key={i} className={i === index ? styles.dotActive : styles.dot} />
          ))}
        </div>
      )}
    </div>
  );
}
