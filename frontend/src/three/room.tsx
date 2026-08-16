// frontend/src/three/room.tsx
// 게임룸 배경/소품. 전부 장식이라 클릭 대상이 아니다.
//
// 지켜야 하는 규칙 3가지:
// 1) 벽·천장은 planeGeometry에 안쪽 법선(FrontSide). box로 만들면 궤도 회전할 때 바깥면이 씬을 통째로 가린다.
// 2) 장식에는 포인터 핸들러를 절대 붙이지 않고, 큰 판때기에는 raycast를 꺼서 부품 클릭 판정을 방해하지 않는다.
// 3) 새 광원을 늘리지 않는다. 발광은 emissive + 가산합성 글로우 판으로 위조한다
//    (후처리 블룸은 별도 의존성이 필요하고, 광원 수는 SwiftShader 헤드리스 렌더 비용에 직결된다).

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { AdditiveBlending, BackSide, type Group, type Mesh, type MeshStandardMaterial } from "three";
import { ROOM } from "./parts";

const WALL = "#161a23";
const WALL_SIDE = "#11141c";
const TRIM = "#232936";

/** 큰 장식 판은 레이캐스트 대상에서 아예 빼서 부품 선택을 방해하지 않게 한다. */
const noRaycast = () => null;

// ============================================================
// 방 구조
// ============================================================

export function RoomShell() {
  const width = ROOM.maxX - ROOM.minX;
  const centerX = (ROOM.minX + ROOM.maxX) / 2;

  return (
    <group>
      {/* 뒷벽 — 법선이 +z(카메라 쪽)를 보게 둔다 */}
      <mesh position={[centerX, ROOM.height / 2, ROOM.backZ]} receiveShadow raycast={noRaycast}>
        <planeGeometry args={[width, ROOM.height]} />
        <meshStandardMaterial color={WALL} roughness={0.96} metalness={0.04} />
      </mesh>

      {/* 좌벽 — 법선 +x */}
      <mesh
        position={[ROOM.minX, ROOM.height / 2, 0.6]}
        rotation={[0, Math.PI / 2, 0]}
        receiveShadow
        raycast={noRaycast}
      >
        <planeGeometry args={[4.8, ROOM.height]} />
        <meshStandardMaterial color={WALL_SIDE} roughness={0.96} metalness={0.04} />
      </mesh>

      {/* 우벽 — 법선 -x */}
      <mesh
        position={[ROOM.maxX, ROOM.height / 2, 0.6]}
        rotation={[0, -Math.PI / 2, 0]}
        receiveShadow
        raycast={noRaycast}
      >
        <planeGeometry args={[4.8, ROOM.height]} />
        <meshStandardMaterial color={WALL_SIDE} roughness={0.96} metalness={0.04} />
      </mesh>

      {/* 걸레받이 — 벽과 바닥 경계. 책상이 가리는 중앙 하단은 어차피 안 보이지만 좌우 끝에서 방을 닫아준다 */}
      <mesh position={[centerX, 0.055, ROOM.backZ + 0.016]} raycast={noRaycast}>
        <boxGeometry args={[width, 0.11, 0.03]} />
        <meshStandardMaterial color={TRIM} roughness={0.8} metalness={0.15} />
      </mesh>
      {[ROOM.minX + 0.016, ROOM.maxX - 0.016].map((x) => (
        <mesh key={x} position={[x, 0.055, 0.6]} raycast={noRaycast}>
          <boxGeometry args={[0.03, 0.11, 4.8]} />
          <meshStandardMaterial color={TRIM} roughness={0.8} metalness={0.15} />
        </mesh>
      ))}
    </group>
  );
}

/**
 * 가산합성 글로우 — 후처리 블룸 없이 발광 번짐을 흉내낸다.
 *
 * 한 장짜리 균일한 색 평면은 감쇠가 없어서 벽에 직사각형 자국으로 보인다.
 * 크기가 다른 판을 opacity를 낮춰가며 겹쳐야 가장자리로 갈수록 옅어지는 falloff가 생긴다.
 * 케이스 유리(투명)와 같은 시선에 겹치면 정렬이 깨지므로 반드시 벽면(z ≤ -1.6)에만 둔다.
 */
export function GlowQuad({
  position,
  size,
  color,
  opacity = 0.16,
  layers = 3,
}: {
  position: [number, number, number];
  size: [number, number];
  color: string;
  opacity?: number;
  layers?: number;
}) {
  const [w, h] = size;
  return (
    <group position={position}>
      {Array.from({ length: layers }, (_, i) => {
        const grow = 1 + i * 0.55;
        return (
          <mesh key={i} position={[0, 0, i * 0.004]} raycast={noRaycast}>
            <planeGeometry args={[w * grow, h * grow]} />
            <meshBasicMaterial
              color={color}
              transparent
              opacity={opacity / (i + 1) ** 1.6}
              blending={AdditiveBlending}
              depthWrite={false}
              toneMapped={false}
            />
          </mesh>
        );
      })}
    </group>
  );
}

/** 책상 앞 바닥 러그. */
export function Rug() {
  return (
    <group position={[-0.7, 0, 1.2]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.006, 0]} receiveShadow raycast={noRaycast}>
        <planeGeometry args={[3.5, 1.8]} />
        <meshStandardMaterial color="#1b1f2a" roughness={0.99} metalness={0} />
      </mesh>
      {/* 테두리 두 줄 */}
      {[
        { s: [3.34, 1.64] as [number, number], c: "#2b3240" },
        { s: [3.2, 1.5] as [number, number], c: "#232936" },
      ].map((r) => (
        <mesh
          key={r.c}
          rotation={[-Math.PI / 2, 0, 0]}
          position={[0, 0.0065, 0]}
          raycast={noRaycast}
        >
          <planeGeometry args={r.s} />
          <meshStandardMaterial color={r.c} roughness={0.99} />
        </mesh>
      ))}
    </group>
  );
}

// ============================================================
// 벽 장식
// ============================================================

/** 흡음 폼 패널 존 — 스트리머 방의 1순위 시그널. 웨지를 사각뿔로 촘촘히 깐다. */
export function AcousticFoamWall({
  position,
  cols = 6,
  rows = 2,
}: {
  position: [number, number, number];
  cols?: number;
  rows?: number;
}) {
  const tile = 0.32;
  const wedgesPerSide = 3;
  const wedge = tile / wedgesPerSide;

  const wedges = useMemo(() => {
    const out: { x: number; y: number; flip: boolean }[] = [];
    for (let c = 0; c < cols; c++) {
      for (let r = 0; r < rows; r++) {
        const tileX = (c - (cols - 1) / 2) * (tile + 0.015);
        const tileY = (r - (rows - 1) / 2) * (tile + 0.015);
        for (let i = 0; i < wedgesPerSide; i++) {
          for (let j = 0; j < wedgesPerSide; j++) {
            out.push({
              x: tileX + (i - (wedgesPerSide - 1) / 2) * wedge,
              y: tileY + (j - (wedgesPerSide - 1) / 2) * wedge,
              // 타일마다 웨지 방향을 90도 교차시켜야 실제 흡음폼처럼 보인다
              flip: (c + r) % 2 === 0,
            });
          }
        }
      }
    }
    return out;
  }, [cols, rows, wedge]);

  const boardW = cols * (tile + 0.015);
  const boardH = rows * (tile + 0.015);

  return (
    <group position={position}>
      <mesh raycast={noRaycast}>
        <boxGeometry args={[boardW, boardH, 0.02]} />
        <meshStandardMaterial color="#14171f" roughness={1} />
      </mesh>
      {wedges.map((w, i) => (
        <mesh
          key={i}
          position={[w.x, w.y, 0.035]}
          rotation={[Math.PI / 2, 0, w.flip ? Math.PI / 4 : 0]}
          raycast={noRaycast}
        >
          <coneGeometry args={[wedge * 0.62, 0.05, 4]} />
          <meshStandardMaterial color="#1c202a" roughness={1} />
        </mesh>
      ))}
    </group>
  );
}

/** 육각 RGB 벽 패널 — 모니터 뒤 헤일로. 전부 최대 밝기면 납작해지므로 켜짐/소등을 섞는다. */
export function HexPanelCluster({
  position,
  colors = ["#22d3ee", "#8b5cf6", "#22d3ee", "#151a22", "#8b5cf6", "#22d3ee", "#151a22"],
}: {
  position: [number, number, number];
  colors?: string[];
}) {
  const radius = 0.125;
  const dx = radius * 1.732;
  const dy = radius * 1.5;
  // 허니컴 7타일 (중앙 + 6방향)
  const layout: [number, number][] = [
    [0, 0],
    [dx, 0],
    [-dx, 0],
    [dx / 2, dy],
    [-dx / 2, dy],
    [dx / 2, -dy],
    [-dx / 2, -dy],
  ];

  return (
    <group position={position}>
      {layout.map(([x, y], i) => {
        const color = colors[i % colors.length];
        const lit = color !== "#151a22";
        return (
          <mesh key={i} position={[x, y, 0]} rotation={[Math.PI / 2, 0, 0]} raycast={noRaycast}>
            <cylinderGeometry args={[radius, radius, 0.03, 6]} />
            <meshStandardMaterial
              color={color}
              emissive={color}
              emissiveIntensity={lit ? 0.8 : 0.05}
              roughness={0.5}
              toneMapped={!lit}
            />
          </mesh>
        );
      })}
    </group>
  );
}

/**
 * 벽걸이 네온 사인 — Market Pulse 로고의 심박 파형.
 * 글자를 쓰려면 폰트 로더(troika/Text)가 필요한데 CDN에서 폰트를 받아오려 해서
 * 오프라인/CSP 환경에서 못 쓴다. 그래서 브랜드 파형으로 대체했다.
 */
export function NeonPulseSign({
  position,
  color = "#22d3ee",
  scale = 1,
}: {
  position: [number, number, number];
  color?: string;
  scale?: number;
}) {
  const points: [number, number][] = [
    [-0.66, 0],
    [-0.36, 0],
    [-0.25, 0.22],
    [-0.13, -0.28],
    [0.0, 0.36],
    [0.13, -0.18],
    [0.24, 0],
    [0.66, 0],
  ];

  const segments = points.slice(0, -1).map((start, i) => {
    const end = points[i + 1];
    const dx = end[0] - start[0];
    const dy = end[1] - start[1];
    return {
      key: i,
      length: Math.hypot(dx, dy),
      angle: Math.atan2(dy, dx),
      mid: [(start[0] + end[0]) / 2, (start[1] + end[1]) / 2] as [number, number],
    };
  });

  return (
    <group position={position} scale={scale}>
      {segments.map((s) => (
        <mesh
          key={s.key}
          position={[s.mid[0], s.mid[1], 0]}
          rotation={[0, 0, s.angle]}
          raycast={noRaycast}
        >
          <boxGeometry args={[s.length + 0.02, 0.034, 0.03]} />
          <meshStandardMaterial
            color={color}
            emissive={color}
            emissiveIntensity={1.9}
            toneMapped={false}
          />
        </mesh>
      ))}
    </group>
  );
}

/** 벽 선반 + 트로피/피규어/화분. */
export function WallShelf({ position }: { position: [number, number, number] }) {
  return (
    <group position={position}>
      <mesh castShadow raycast={noRaycast}>
        <boxGeometry args={[0.95, 0.035, 0.2]} />
        <meshStandardMaterial color="#33271c" roughness={0.8} metalness={0.05} />
      </mesh>
      {[-0.36, 0.36].map((x) => (
        <mesh key={x} position={[x, -0.055, -0.055]} raycast={noRaycast}>
          <boxGeometry args={[0.028, 0.08, 0.085]} />
          <meshStandardMaterial color="#1d222c" roughness={0.5} metalness={0.6} />
        </mesh>
      ))}
      {/* 트로피 */}
      <group position={[-0.31, 0.018, 0]}>
        <mesh position={[0, 0.018, 0]} raycast={noRaycast}>
          <boxGeometry args={[0.075, 0.03, 0.075]} />
          <meshStandardMaterial color="#20242e" roughness={0.4} metalness={0.6} />
        </mesh>
        <mesh position={[0, 0.085, 0]} raycast={noRaycast}>
          <cylinderGeometry args={[0.042, 0.018, 0.1, 12]} />
          <meshStandardMaterial color="#c9a227" roughness={0.25} metalness={0.95} />
        </mesh>
      </group>
      {/* 피규어 */}
      {[-0.05, 0.1].map((x, i) => (
        <mesh key={x} position={[x, 0.08, 0.01]} raycast={noRaycast}>
          <capsuleGeometry args={[0.022, 0.055, 4, 8]} />
          <meshStandardMaterial
            color={i === 0 ? "#3987e5" : "#d55181"}
            emissive={i === 0 ? "#3987e5" : "#d55181"}
            emissiveIntensity={0.25}
            roughness={0.55}
          />
        </mesh>
      ))}
      {/* 화분 */}
      <group position={[0.34, 0.018, 0]}>
        <mesh position={[0, 0.035, 0]} raycast={noRaycast}>
          <cylinderGeometry args={[0.045, 0.034, 0.07, 10]} />
          <meshStandardMaterial color="#4a3a2c" roughness={0.9} />
        </mesh>
        {[0, 1, 2, 3, 4].map((i) => {
          const a = (i / 5) * Math.PI * 2;
          return (
            <mesh
              key={i}
              position={[Math.cos(a) * 0.028, 0.11, Math.sin(a) * 0.028]}
              rotation={[Math.sin(a) * 0.6, 0, -Math.cos(a) * 0.6]}
              raycast={noRaycast}
            >
              <boxGeometry args={[0.022, 0.095, 0.006]} />
              <meshStandardMaterial color="#2f6b3a" roughness={0.95} />
            </mesh>
          );
        })}
      </group>
    </group>
  );
}

/** 창문 + 블라인드 — 좌벽에 걸어 방 바깥을 암시한다(궤도 회전 보상 요소). */
export function BlindWindow({ position }: { position: [number, number, number] }) {
  const slats = 13;
  return (
    <group position={position} rotation={[0, Math.PI / 2, 0]}>
      <mesh raycast={noRaycast}>
        <planeGeometry args={[1.05, 1.2]} />
        <meshStandardMaterial color="#0f1a2b" emissive="#24406e" emissiveIntensity={0.75} />
      </mesh>
      {Array.from({ length: slats }, (_, i) => (
        <mesh
          key={i}
          position={[0, 0.55 - (i * 1.1) / (slats - 1), 0.02]}
          rotation={[0.42, 0, 0]}
          raycast={noRaycast}
        >
          <boxGeometry args={[1.03, 0.055, 0.008]} />
          <meshStandardMaterial color="#232936" roughness={0.9} />
        </mesh>
      ))}
      {/* 창틀 */}
      {[
        { p: [0, 0.62, 0.03], s: [1.14, 0.04, 0.05] },
        { p: [0, -0.62, 0.03], s: [1.14, 0.04, 0.05] },
        { p: [-0.55, 0, 0.03], s: [0.04, 1.28, 0.05] },
        { p: [0.55, 0, 0.03], s: [0.04, 1.28, 0.05] },
      ].map(({ p, s }) => (
        <mesh key={`${p[0]}-${p[1]}`} position={p as [number, number, number]} raycast={noRaycast}>
          <boxGeometry args={s as [number, number, number]} />
          <meshStandardMaterial color="#1a1e27" roughness={0.6} metalness={0.3} />
        </mesh>
      ))}
    </group>
  );
}

// ============================================================
// 가구 / 바닥 소품
// ============================================================

/** 게이밍 체어. 노트북 클로즈업 카메라 경로(x≈-1.2, y≈1.33, z≈1.6)를 피해 왼쪽으로 물려 놓는다. */
export function GamingChair({
  position,
  rotationY = 0,
  accent = "#d03b3b",
}: {
  position: [number, number, number];
  rotationY?: number;
  accent?: string;
}) {
  const body = "#15181f";

  return (
    <group position={position} rotation={[0, rotationY, 0]}>
      {[0, 1, 2, 3, 4].map((i) => (
        <group key={i} rotation={[0, (i / 5) * Math.PI * 2, 0]}>
          <mesh position={[0.16, 0.055, 0]} castShadow raycast={noRaycast}>
            <boxGeometry args={[0.32, 0.03, 0.05]} />
            <meshStandardMaterial color="#22262f" roughness={0.4} metalness={0.7} />
          </mesh>
          <mesh position={[0.31, 0.03, 0]} raycast={noRaycast}>
            <cylinderGeometry args={[0.03, 0.03, 0.025, 10]} />
            <meshStandardMaterial color="#0f1116" roughness={0.6} />
          </mesh>
        </group>
      ))}
      <mesh position={[0, 0.2, 0]} raycast={noRaycast}>
        <cylinderGeometry args={[0.035, 0.045, 0.28, 12]} />
        <meshStandardMaterial color="#2b3039" roughness={0.35} metalness={0.8} />
      </mesh>
      <mesh position={[0, 0.37, 0]} castShadow raycast={noRaycast}>
        <boxGeometry args={[0.46, 0.09, 0.44]} />
        <meshStandardMaterial color={body} roughness={0.78} metalness={0.08} />
      </mesh>
      {[-0.2, 0.2].map((x) => (
        <mesh key={x} position={[x, 0.41, 0.02]} castShadow raycast={noRaycast}>
          <boxGeometry args={[0.07, 0.08, 0.4]} />
          <meshStandardMaterial color={accent} roughness={0.72} />
        </mesh>
      ))}
      <group position={[0, 0.41, -0.19]} rotation={[-0.17, 0, 0]}>
        <mesh position={[0, 0.33, 0]} castShadow raycast={noRaycast}>
          <boxGeometry args={[0.44, 0.64, 0.09]} />
          <meshStandardMaterial color={body} roughness={0.78} metalness={0.08} />
        </mesh>
        {[-0.19, 0.19].map((x) => (
          <mesh key={x} position={[x, 0.33, 0.035]} raycast={noRaycast}>
            <boxGeometry args={[0.07, 0.6, 0.06]} />
            <meshStandardMaterial color={accent} roughness={0.72} />
          </mesh>
        ))}
        <mesh position={[0, 0.72, 0.01]} castShadow raycast={noRaycast}>
          <boxGeometry args={[0.3, 0.13, 0.1]} />
          <meshStandardMaterial color={accent} roughness={0.72} />
        </mesh>
      </group>
      {[-0.27, 0.27].map((x) => (
        <group key={x} position={[x, 0.43, 0.02]}>
          <mesh position={[0, 0.07, 0]} raycast={noRaycast}>
            <boxGeometry args={[0.05, 0.14, 0.05]} />
            <meshStandardMaterial color="#22262f" roughness={0.5} metalness={0.5} />
          </mesh>
          <mesh position={[0, 0.15, 0.02]} raycast={noRaycast}>
            <boxGeometry args={[0.07, 0.03, 0.22]} />
            <meshStandardMaterial color={body} roughness={0.7} />
          </mesh>
        </group>
      ))}
    </group>
  );
}

/** 코너 RGB 플로어 라이트바. 실제 광원은 씬의 기존 pointLight를 여기 붙여서 쓴다. */
export function FloorLightBar({
  position,
  color = "#8b5cf6",
  height = 1.7,
}: {
  position: [number, number, number];
  color?: string;
  height?: number;
}) {
  const tube = useRef<Mesh>(null);
  useFrame((state) => {
    if (!tube.current) return;
    const m = tube.current.material as MeshStandardMaterial;
    // 아주 느린 숨쉬기 — 정지 이미지처럼 보이지 않게 하는 최소 장치
    m.emissiveIntensity = 1.7 + Math.sin(state.clock.elapsedTime * 0.7) * 0.4;
  });

  return (
    <group position={position}>
      <mesh position={[0, 0.015, 0]} raycast={noRaycast}>
        <cylinderGeometry args={[0.1, 0.12, 0.03, 14]} />
        <meshStandardMaterial color="#1b1f28" roughness={0.5} metalness={0.6} />
      </mesh>
      <mesh ref={tube} position={[0, height / 2 + 0.03, 0]} raycast={noRaycast}>
        <cylinderGeometry args={[0.026, 0.026, height, 10]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={1.7}
          toneMapped={false}
        />
      </mesh>
    </group>
  );
}

/** 코너 관엽식물. */
export function PottedPlant({ position }: { position: [number, number, number] }) {
  const leaves = useMemo(
    () =>
      Array.from({ length: 11 }, (_, i) => {
        const a = (i / 11) * Math.PI * 2 + i * 0.37;
        const lean = 0.35 + (i % 3) * 0.16;
        const h = 0.42 + ((i * 7) % 5) * 0.07;
        return { a, lean, h, y: 0.3 + ((i * 3) % 4) * 0.06 };
      }),
    [],
  );

  return (
    <group position={position}>
      <mesh position={[0, 0.13, 0]} castShadow raycast={noRaycast}>
        <cylinderGeometry args={[0.15, 0.11, 0.26, 14]} />
        <meshStandardMaterial color="#3b3128" roughness={0.92} />
      </mesh>
      <mesh position={[0, 0.26, 0]} raycast={noRaycast}>
        <cylinderGeometry args={[0.155, 0.155, 0.03, 14]} />
        <meshStandardMaterial color="#2a2119" roughness={0.9} />
      </mesh>
      {leaves.map((l, i) => (
        <group key={i} rotation={[0, l.a, 0]}>
          <mesh
            position={[Math.sin(l.lean) * l.h * 0.5, l.y + Math.cos(l.lean) * l.h * 0.5, 0]}
            rotation={[0, 0, -l.lean]}
            raycast={noRaycast}
          >
            <boxGeometry args={[0.075, l.h, 0.008]} />
            <meshStandardMaterial color={i % 2 ? "#2f6b3a" : "#275c32"} roughness={0.95} />
          </mesh>
        </group>
      ))}
    </group>
  );
}

/** 책상 밑 케이블 + 멀티탭 — 약간의 지저분함이 있어야 실제 방처럼 읽힌다. */
export function CableClutter({ position }: { position: [number, number, number] }) {
  return (
    <group position={position}>
      <mesh position={[0, 0.018, 0]} rotation={[0, 0.35, 0]} castShadow raycast={noRaycast}>
        <boxGeometry args={[0.28, 0.035, 0.075]} />
        <meshStandardMaterial color="#20242c" roughness={0.65} metalness={0.2} />
      </mesh>
      {[-0.08, 0, 0.08].map((t) => (
        <mesh key={t} position={[t * 0.94, 0.037, t * 0.34]} rotation={[0, 0.35, 0]} raycast={noRaycast}>
          <boxGeometry args={[0.03, 0.004, 0.028]} />
          <meshStandardMaterial color="#0ca30c" emissive="#0ca30c" emissiveIntensity={1.1} />
        </mesh>
      ))}
      {[
        { x: 0.02, z: 0.14, len: 0.55, rot: 0.35 },
        { x: 0.2, z: -0.06, len: 0.42, rot: -0.7 },
        { x: -0.18, z: 0.06, len: 0.5, rot: 1.15 },
      ].map((c, i) => (
        <mesh
          key={i}
          position={[c.x, 0.008, c.z]}
          rotation={[0, c.rot, Math.PI / 2]}
          raycast={noRaycast}
        >
          <cylinderGeometry args={[0.008, 0.008, c.len, 6]} />
          <meshStandardMaterial color="#14171d" roughness={0.95} />
        </mesh>
      ))}
    </group>
  );
}

// ============================================================
// 책상 위 소품
// ============================================================

/** RGB 데스크 매트. */
export function DeskMat({
  position,
  rotationY = 0,
  size = [0.92, 0.5],
  accent = "#8b5cf6",
}: {
  position: [number, number, number];
  rotationY?: number;
  size?: [number, number];
  accent?: string;
}) {
  const [w, d] = size;
  return (
    <group position={position} rotation={[0, rotationY, 0]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow raycast={noRaycast}>
        <planeGeometry args={[w, d]} />
        <meshStandardMaterial color="#0f1219" roughness={0.98} metalness={0} />
      </mesh>
      {[d / 2, -d / 2].map((z) => (
        <mesh key={z} position={[0, 0.001, z]} raycast={noRaycast}>
          <boxGeometry args={[w, 0.003, 0.008]} />
          <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={1.3} />
        </mesh>
      ))}
    </group>
  );
}

/** 기계식 키보드 — 키캡 격자가 있어야 키보드로 읽힌다. */
export function Keyboard({
  position,
  rotationY = 0,
  accent = "#22d3ee",
}: {
  position: [number, number, number];
  rotationY?: number;
  accent?: string;
}) {
  const cols = 15;
  const rows = 5;
  const keyW = 0.021;
  const w = cols * keyW + 0.018;
  const d = rows * keyW + 0.016;

  const keys = useMemo(
    () =>
      Array.from({ length: rows }, (_, r) =>
        Array.from({ length: cols }, (_, c) => ({
          key: `${r}-${c}`,
          x: (c - (cols - 1) / 2) * keyW,
          z: (r - (rows - 1) / 2) * keyW,
        })),
      ).flat(),
    [],
  );

  return (
    <group position={position} rotation={[0, rotationY, 0]}>
      <mesh position={[0, 0.008, 0]} castShadow raycast={noRaycast}>
        <boxGeometry args={[w, 0.016, d]} />
        <meshStandardMaterial color="#191d25" roughness={0.5} metalness={0.4} />
      </mesh>
      {/* 키 사이로 새어나오는 백라이트 */}
      <mesh position={[0, 0.0155, 0]} raycast={noRaycast}>
        <boxGeometry args={[w - 0.008, 0.003, d - 0.008]} />
        <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={1.5} />
      </mesh>
      {keys.map((k) => (
        <mesh key={k.key} position={[k.x, 0.0195, k.z]} raycast={noRaycast}>
          <boxGeometry args={[keyW * 0.76, 0.005, keyW * 0.76]} />
          <meshStandardMaterial color="#2a3038" roughness={0.85} />
        </mesh>
      ))}
    </group>
  );
}

/** 게이밍 마우스. */
export function Mouse({
  position,
  rotationY = 0,
  accent = "#22d3ee",
}: {
  position: [number, number, number];
  rotationY?: number;
  accent?: string;
}) {
  return (
    <group position={position} rotation={[0, rotationY, 0]}>
      <mesh position={[0, 0.016, 0]} rotation={[Math.PI / 2, 0, 0]} castShadow raycast={noRaycast}>
        <capsuleGeometry args={[0.021, 0.032, 4, 10]} />
        <meshStandardMaterial color="#1b1f28" roughness={0.45} metalness={0.4} />
      </mesh>
      <mesh position={[0, 0.033, 0.008]} raycast={noRaycast}>
        <boxGeometry args={[0.007, 0.004, 0.016]} />
        <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={2} />
      </mesh>
    </group>
  );
}

/** 헤드셋 스탠드. */
export function HeadsetStand({
  position,
  accent = "#8b5cf6",
}: {
  position: [number, number, number];
  accent?: string;
}) {
  return (
    <group position={position}>
      <mesh position={[0, 0.008, 0]} raycast={noRaycast}>
        <cylinderGeometry args={[0.07, 0.075, 0.016, 14]} />
        <meshStandardMaterial color="#1b1f28" roughness={0.4} metalness={0.6} />
      </mesh>
      <mesh position={[0, 0.12, 0]} raycast={noRaycast}>
        <cylinderGeometry args={[0.011, 0.011, 0.22, 10]} />
        <meshStandardMaterial color="#262b35" roughness={0.35} metalness={0.75} />
      </mesh>
      <mesh position={[0, 0.235, 0]} raycast={noRaycast}>
        <torusGeometry args={[0.068, 0.013, 8, 18, Math.PI]} />
        <meshStandardMaterial color="#1d212a" roughness={0.6} />
      </mesh>
      {[-0.068, 0.068].map((x) => (
        <mesh key={x} position={[x, 0.222, 0]} rotation={[0, 0, Math.PI / 2]} raycast={noRaycast}>
          <cylinderGeometry args={[0.038, 0.038, 0.03, 14]} />
          <meshStandardMaterial
            color="#20242e"
            emissive={accent}
            emissiveIntensity={0.8}
            roughness={0.5}
          />
        </mesh>
      ))}
    </group>
  );
}

/** 데스크 스피커. */
export function Speaker({
  position,
  rotationY = 0,
  accent = "#22d3ee",
}: {
  position: [number, number, number];
  rotationY?: number;
  accent?: string;
}) {
  return (
    <group position={position} rotation={[0, rotationY, 0]}>
      <mesh position={[0, 0.1, 0]} castShadow raycast={noRaycast}>
        <boxGeometry args={[0.095, 0.2, 0.1]} />
        <meshStandardMaterial color="#171b23" roughness={0.7} metalness={0.15} />
      </mesh>
      <mesh position={[0, 0.07, 0.051]} rotation={[Math.PI / 2, 0, 0]} raycast={noRaycast}>
        <cylinderGeometry args={[0.03, 0.03, 0.008, 14]} />
        <meshStandardMaterial color="#0d1015" roughness={0.95} />
      </mesh>
      <mesh position={[0, 0.148, 0.051]} rotation={[Math.PI / 2, 0, 0]} raycast={noRaycast}>
        <cylinderGeometry args={[0.014, 0.014, 0.008, 10]} />
        <meshStandardMaterial color="#0d1015" roughness={0.95} />
      </mesh>
      <mesh position={[0, 0.006, 0]} rotation={[-Math.PI / 2, 0, 0]} raycast={noRaycast}>
        <ringGeometry args={[0.042, 0.056, 14]} />
        <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={1.6} />
      </mesh>
    </group>
  );
}

/** 마이크 붐암 + 콘덴서 마이크 — 스트리머 방의 시그니처. 모니터 화면 앞을 가리지 않게 뒤쪽에 세운다. */
export function MicBoomArm({
  position,
  accent = "#22d3ee",
}: {
  position: [number, number, number];
  accent?: string;
}) {
  return (
    <group position={position}>
      {/* 데스크 클램프 + 지주 */}
      <mesh position={[0, 0.03, 0]} raycast={noRaycast}>
        <boxGeometry args={[0.06, 0.06, 0.07]} />
        <meshStandardMaterial color="#1b1f28" roughness={0.5} metalness={0.6} />
      </mesh>
      <mesh position={[0, 0.34, 0]} raycast={noRaycast}>
        <cylinderGeometry args={[0.012, 0.012, 0.6, 8]} />
        <meshStandardMaterial color="#22262f" roughness={0.4} metalness={0.75} />
      </mesh>
      {/* 붐 1단 (위로 비스듬히) */}
      <group position={[0, 0.62, 0]} rotation={[0, 0, -0.85]}>
        <mesh position={[0, 0.19, 0]} raycast={noRaycast}>
          <cylinderGeometry args={[0.011, 0.011, 0.38, 8]} />
          <meshStandardMaterial color="#22262f" roughness={0.4} metalness={0.75} />
        </mesh>
      </group>
      {/* 붐 2단 (아래로 꺾여 마이크로) */}
      <group position={[-0.29, 0.87, 0]} rotation={[0, 0, -2.05]}>
        <mesh position={[0, 0.17, 0]} raycast={noRaycast}>
          <cylinderGeometry args={[0.011, 0.011, 0.34, 8]} />
          <meshStandardMaterial color="#22262f" roughness={0.4} metalness={0.75} />
        </mesh>
      </group>
      {/* 마이크 본체 */}
      <group position={[-0.0, 0.99, 0]} rotation={[0, 0, 0.35]}>
        <mesh raycast={noRaycast}>
          <cylinderGeometry args={[0.032, 0.032, 0.15, 14]} />
          <meshStandardMaterial color="#20242e" roughness={0.35} metalness={0.8} />
        </mesh>
        <mesh position={[0, 0.055, 0]} raycast={noRaycast}>
          <cylinderGeometry args={[0.034, 0.034, 0.045, 14]} />
          <meshStandardMaterial color="#3a4150" roughness={0.55} metalness={0.7} wireframe />
        </mesh>
        <mesh position={[0, -0.065, 0.03]} raycast={noRaycast}>
          <boxGeometry args={[0.016, 0.005, 0.005]} />
          <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={2.2} />
        </mesh>
      </group>
    </group>
  );
}

/** 모니터 상단 스크린바 — 책상을 비추는 웜 라이트를 실체와 함께 둔다. */
export function ScreenBar({
  position,
  rotationY = 0,
  color = "#ffd9a8",
}: {
  position: [number, number, number];
  rotationY?: number;
  color?: string;
}) {
  return (
    <group position={position} rotation={[0, rotationY, 0]}>
      <mesh raycast={noRaycast}>
        <boxGeometry args={[0.44, 0.032, 0.05]} />
        <meshStandardMaterial color="#1b1f28" roughness={0.5} metalness={0.6} />
      </mesh>
      <mesh position={[0, -0.018, 0.012]} rotation={[0.5, 0, 0]} raycast={noRaycast}>
        <boxGeometry args={[0.4, 0.008, 0.02]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={2.2} toneMapped={false} />
      </mesh>
      {/* 스크린바는 화면이 아니라 책상을 비춰야 한다 — 앞·아래로 충분히 빼서 화면 정반사를 피한다 */}
      <pointLight position={[0, -0.22, 0.5]} color={color} intensity={1.3} distance={1.4} />
    </group>
  );
}

/** 아주 느리게 떠다니는 먼지 — 공기감. 개수는 적게, 크기로 승부한다. */
export function DustMotes({ count = 46 }: { count?: number }) {
  const group = useRef<Group>(null);
  const seeds = useMemo(
    () =>
      Array.from({ length: count }, (_, i) => ({
        x: -2.9 + ((i * 37) % 57) / 10,
        y: 0.35 + ((i * 53) % 20) / 10,
        z: -1.5 + ((i * 29) % 33) / 10,
        speed: 0.05 + ((i * 17) % 10) / 180,
        phase: (i * 0.7) % (Math.PI * 2),
      })),
    [count],
  );

  useFrame((state) => {
    if (!group.current) return;
    const t = state.clock.elapsedTime;
    group.current.children.forEach((child, i) => {
      const s = seeds[i];
      child.position.y = s.y + Math.sin(t * s.speed * 6 + s.phase) * 0.13;
      child.position.x = s.x + Math.cos(t * s.speed * 4 + s.phase) * 0.09;
    });
  });

  return (
    <group ref={group}>
      {seeds.map((s, i) => (
        <mesh key={i} position={[s.x, s.y, s.z]} raycast={noRaycast}>
          <sphereGeometry args={[0.0055, 5, 4]} />
          <meshBasicMaterial color="#9fd8e8" transparent opacity={0.3} depthWrite={false} />
        </mesh>
      ))}
    </group>
  );
}

/** 천장 — 위에서 내려다보는 각도에서만 보인다. 안쪽 법선이라 궤도 회전을 막지 않는다. */
export function Ceiling() {
  return (
    <mesh
      position={[(ROOM.minX + ROOM.maxX) / 2, ROOM.height, 0.6]}
      rotation={[Math.PI / 2, 0, 0]}
      raycast={noRaycast}
    >
      <planeGeometry args={[ROOM.maxX - ROOM.minX, 4.8]} />
      <meshStandardMaterial color="#0e1119" roughness={1} side={BackSide} />
    </mesh>
  );
}
