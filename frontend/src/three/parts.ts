// frontend/src/three/parts.ts
// 3D 데스크의 부품 6개 ↔ 가격 카테고리 매핑, 그리고 부품을 "방문"할 때 쓰는 카메라 프리셋.
//
// 좌표계: Y-up, 바닥 y=0, 책상 상판 y=0.74.
// 케이스 내부 부품(CPU/GPU/RAM/SSD)의 좌표는 케이스 로컬 기준이라 towerToWorld()로 변환해서 쓴다.

import { CATEGORY_COLORS } from "../constants";

export type Vec3 = [number, number, number];

// ---- 씬 배치 상수 (DeskScene.tsx와 공유) ----
/** 방 크기. 벽·천장은 안쪽 법선 평면이라 카메라가 있는 +z 쪽은 열어 둔다. */
export const ROOM = {
  minX: -3.2,
  maxX: 3.0,
  backZ: -1.7,
  height: 2.8,
};

export const DESK_TOP_Y = 0.74;
export const MONITOR_POSITION: Vec3 = [0.5, DESK_TOP_Y, -0.32];
export const MONITOR_ROTATION_Y = -0.34;
export const TOWER_POSITION: Vec3 = [1.5, 0, 0.12];
export const TOWER_ROTATION_Y = -0.35;
/** 케이스 원본 높이가 0.96이라 그대로 두면 책상보다 커진다. 상판과 비슷한 높이로 줄인다. */
export const TOWER_SCALE = 0.8;

/** 케이스 로컬 좌표 → 월드 좌표 (스케일 + Y축 회전 + 평행이동). */
export function towerToWorld([x, y, z]: Vec3): Vec3 {
  const cos = Math.cos(TOWER_ROTATION_Y);
  const sin = Math.sin(TOWER_ROTATION_Y);
  const [sx, sy, sz] = [x * TOWER_SCALE, y * TOWER_SCALE, z * TOWER_SCALE];
  return [
    TOWER_POSITION[0] + sx * cos + sz * sin,
    TOWER_POSITION[1] + sy,
    TOWER_POSITION[2] - sx * sin + sz * cos,
  ];
}

export interface PartDef {
  id: string;
  /** DB의 카테고리명과 정확히 일치해야 한다 (api/categories의 응답 키). */
  category: string;
  label: string;
  icon: string;
  hint: string;
  /** 부품을 방문했을 때의 카메라 위치와 바라볼 지점. */
  camera: { position: Vec3; target: Vec3 };
}

export const OVERVIEW_CAMERA: { position: Vec3; target: Vec3 } = {
  position: [0.35, 1.5, 4.55],
  target: [-0.3, 0.64, 0],
};

export const PARTS: PartDef[] = [
  {
    id: "cpu",
    category: "CPU",
    label: "CPU",
    icon: "🧠",
    hint: "메인보드 소켓 위 쿨러",
    camera: { position: towerToWorld([-0.06, 0.86, 0.76]), target: towerToWorld([0, 0.7, -0.1]) },
  },
  {
    id: "gpu",
    category: "그래픽카드",
    label: "그래픽카드",
    icon: "🎮",
    hint: "PCIe 슬롯의 대형 카드",
    camera: { position: towerToWorld([0.02, 0.6, 1.05]), target: towerToWorld([0.02, 0.44, -0.13]) },
  },
  {
    id: "ram",
    category: "DDR5 RAM",
    label: "DDR5 RAM",
    icon: "🧩",
    hint: "CPU 오른쪽 메모리 슬롯",
    camera: { position: towerToWorld([0.28, 0.8, 0.42]), target: towerToWorld([0.268, 0.72, -0.14]) },
  },
  {
    id: "ssd",
    category: "NVMe SSD",
    label: "NVMe SSD",
    icon: "💾",
    hint: "그래픽카드 아래 M.2 슬롯",
    camera: { position: towerToWorld([0.14, 0.22, 0.88]), target: towerToWorld([0.1, 0.34, -0.185]) },
  },
  {
    id: "gaming-laptop",
    category: "게이밍 노트북",
    label: "게이밍 노트북",
    icon: "💻",
    hint: "책상 왼쪽, RTX 게이밍 모델",
    camera: { position: [-1.5, 1.32, 1.15], target: [-1.5, 0.87, 0.05] },
  },
  {
    id: "ai-laptop",
    category: "AI 노트북",
    label: "AI 노트북",
    icon: "🤖",
    hint: "책상 가운데, NPU 탑재 모델",
    camera: { position: [-0.35, 1.3, 1.1], target: [-0.35, 0.85, 0.02] },
  },
  // PARTS는 DeskScene.tsx에서 인덱스로 꺼내 쓴다 — 새 부품은 반드시 끝에 추가할 것
  {
    id: "monitor",
    category: "게이밍 모니터",
    label: "게이밍 모니터",
    icon: "🖥️",
    hint: "책상 오른쪽, 고주사율 패널",
    camera: { position: [0.18, 1.24, 0.59], target: [0.5, 1.14, -0.31] },
  },
];

export function partColor(part: PartDef): string {
  return CATEGORY_COLORS[part.category] ?? "#8b93a7";
}

export function findPart(id: string | null): PartDef | undefined {
  return PARTS.find((p) => p.id === id);
}
