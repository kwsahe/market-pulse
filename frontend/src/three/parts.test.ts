import { describe, expect, it } from "vitest";
import { CATEGORY_COLORS } from "../constants";
import { PARTS, TOWER_POSITION, findPart, partColor, towerToWorld } from "./parts";

describe("PARTS", () => {
  it("maps every 3D part to a real price category", () => {
    // 오타 하나로 부품 패널이 통째로 404가 되므로 카테고리 이름을 색상 테이블과 대조한다
    for (const part of PARTS) {
      expect(Object.keys(CATEGORY_COLORS)).toContain(part.category);
    }
  });

  it("covers every category exactly once", () => {
    const categories = PARTS.map((p) => p.category);
    expect(new Set(categories).size).toBe(categories.length);
    expect(categories.sort()).toEqual(Object.keys(CATEGORY_COLORS).sort());
  });

  it("uses unique part ids", () => {
    const ids = PARTS.map((p) => p.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("gives each part its category color", () => {
    const cpu = findPart("cpu")!;
    expect(partColor(cpu)).toBe(CATEGORY_COLORS.CPU);
  });

  it("returns undefined for an unknown part id", () => {
    expect(findPart("없는부품")).toBeUndefined();
    expect(findPart(null)).toBeUndefined();
  });
});

describe("towerToWorld", () => {
  it("maps the case origin to the case position", () => {
    const [x, y, z] = towerToWorld([0, 0, 0]);
    expect([x, y, z]).toEqual(TOWER_POSITION);
  });

  it("keeps height on the world Y axis", () => {
    const [, y] = towerToWorld([0, 0.5, 0]);
    expect(y).toBeGreaterThan(TOWER_POSITION[1]);
  });

  it("puts every part camera outside its focus point", () => {
    for (const part of PARTS) {
      const { position, target } = part.camera;
      const distance = Math.hypot(
        position[0] - target[0],
        position[1] - target[1],
        position[2] - target[2],
      );
      // OrbitControls의 minDistance(0.25)보다 가까우면 카메라가 밀려나 프리셋이 깨진다
      expect(distance).toBeGreaterThan(0.25);
    }
  });
});
