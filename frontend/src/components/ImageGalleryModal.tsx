import type { LaptopImage } from "../types/api";
import styles from "./ImageGalleryModal.module.css";

export function ImageGalleryModal({
  product,
  images,
  onClose,
}: {
  product: string;
  images: LaptopImage[];
  onClose: () => void;
}) {
  const main = images.filter((i) => i.image_type === "main");
  const detail = images.filter((i) => i.image_type === "detail");

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <strong>{product}</strong>
          <button className={styles.closeBtn} onClick={onClose}>
            ✕
          </button>
        </div>
        {images.length === 0 ? (
          <p className={styles.empty}>이미지 없음</p>
        ) : (
          <div className={styles.images}>
            {[...main, ...detail].map((img, i) => (
              <img key={`${img.image_url}-${i}`} src={img.image_url} alt="" className={styles.image} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
