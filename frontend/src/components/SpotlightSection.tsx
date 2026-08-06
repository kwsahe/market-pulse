import { getSpotlights } from "../api/client";
import { useFetch } from "../hooks/useFetch";
import { SectionHeader } from "./SectionHeader";
import { Carousel } from "./Carousel";
import { SpotlightCard } from "./SpotlightCard";
import cardStyles from "./SpotlightCard.module.css";

export function SpotlightSection() {
  const { data } = useFetch(() => getSpotlights(), []);
  if (!data) return null;

  const moverSlides = data.top_movers.map((item) => {
    const isUp = item.change > 0;
    return (
      <SpotlightCard
        key={item.code || item.product}
        code={item.code}
        product={item.product}
        category={item.category}
        imageUrl={item.image_url}
        priceLine={`${item.prev_price.toLocaleString()}원 → ${item.current_price.toLocaleString()}원`}
        badge={`${isUp ? "📈" : "📉"} ${isUp ? "+" : ""}${item.change.toLocaleString()}원 (${isUp ? "+" : ""}${item.change_pct}%)`}
        badgeClassName={isUp ? cardStyles.badgeUp : cardStyles.badgeDown}
      />
    );
  });

  const notableSlides = data.notable.map((item) => (
    <SpotlightCard
      key={item.code || item.product}
      code={item.code}
      product={item.product}
      category={item.category}
      imageUrl={item.image_url}
      priceLine={`${item.price.toLocaleString()}원`}
      badge={
        item.kind === "new"
          ? "🆕 NEW"
          : `${item.z_score != null && item.z_score > 0 ? "📈 고가 이상치" : "📉 저가 이상치"} Z=${item.z_score?.toFixed(2)}`
      }
      badgeClassName={item.kind === "new" ? cardStyles.badge : cardStyles.badgeAmber}
    />
  ));

  return (
    <>
      {moverSlides.length > 0 && (
        <section>
          <SectionHeader icon="🔥" title="오늘의 변동폭 TOP" subtitle="가격이 가장 많이 움직인 상품이 순서대로 나타나요" />
          <Carousel slides={moverSlides} />
        </section>
      )}
      {notableSlides.length > 0 && (
        <section>
          <SectionHeader icon="✨" title="주목할 만한 상품" subtitle="이상치·신제품이 순서대로 나타나요" />
          <Carousel slides={notableSlides} />
        </section>
      )}
    </>
  );
}
