// frontend/src/three/models.tsx
// 3D 데스크를 이루는 순수 지오메트리들. 데이터/상호작용은 전혀 모르고 모양만 담당한다.
// 상호작용(호버·선택·카메라 이동)은 DeskScene.tsx가 Hotspot으로 감싸서 붙인다.

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import type { Group, Mesh } from "three";
import { DESK_TOP_Y } from "./parts";

const CASE_METAL = "#1a1e26";
const CASE_EDGE = "#2b313d";
const PCB = "#14202b";

// ============================================================
// 바닥 / 책상
// ============================================================

export function Floor() {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]} receiveShadow>
      <planeGeometry args={[26, 26]} />
      <meshStandardMaterial color="#0b0d12" roughness={0.85} metalness={0.1} />
    </mesh>
  );
}

export function Desk() {
  const topThickness = 0.05;
  const width = 3.0;
  const depth = 1.2;
  const centerX = -0.6;
  const legInset = 0.12;
  const legHeight = DESK_TOP_Y - topThickness;

  const legPositions: [number, number][] = [
    [centerX - width / 2 + legInset, -depth / 2 + legInset],
    [centerX + width / 2 - legInset, -depth / 2 + legInset],
    [centerX - width / 2 + legInset, depth / 2 - legInset],
    [centerX + width / 2 - legInset, depth / 2 - legInset],
  ];

  return (
    <group>
      <mesh position={[centerX, DESK_TOP_Y - topThickness / 2, 0]} castShadow receiveShadow>
        <boxGeometry args={[width, topThickness, depth]} />
        <meshStandardMaterial color="#6b5340" roughness={0.62} metalness={0.05} />
      </mesh>
      {/* 상판 앞쪽 엣지 라인 — 어두운 배경에서 책상 윤곽이 살도록 */}
      <mesh position={[centerX, DESK_TOP_Y - topThickness, depth / 2]}>
        <boxGeometry args={[width, 0.006, 0.006]} />
        <meshStandardMaterial color="#6f5a45" emissive="#3a2c20" emissiveIntensity={0.4} />
      </mesh>
      {/* 상판 밑 LED 스트립 — 책상이 바닥에서 떠 보이지 않게 아래를 받쳐 준다 */}
      <mesh position={[centerX, DESK_TOP_Y - topThickness - 0.012, depth / 2 - 0.03]}>
        <boxGeometry args={[width - 0.2, 0.012, 0.012]} />
        <meshStandardMaterial color="#8b5cf6" emissive="#8b5cf6" emissiveIntensity={1.5} toneMapped={false} />
      </mesh>
      {legPositions.map(([x, z]) => (
        <mesh key={`${x}-${z}`} position={[x, legHeight / 2, z]} castShadow>
          <boxGeometry args={[0.06, legHeight, 0.06]} />
          <meshStandardMaterial color="#23262e" roughness={0.4} metalness={0.6} />
        </mesh>
      ))}
    </group>
  );
}

// ============================================================
// 케이스 (내부 부품은 DeskScene에서 Hotspot으로 감싸 배치)
// ============================================================

/** 케이스 로컬 좌표: x = 앞(-)/뒤(+) 0.9, y = 0~0.96, z = 메인보드 트레이(-0.24)/유리 패널(+0.24) */
export function TowerShell() {
  const panel = (
    key: string,
    position: [number, number, number],
    size: [number, number, number],
  ) => (
    // 내부 조명이 금속 패널에 흰 반사 얼룩을 남기지 않도록 거칠기를 높이고 금속성은 낮춘다
    <mesh key={key} position={position} castShadow receiveShadow>
      <boxGeometry args={size} />
      <meshStandardMaterial color={CASE_METAL} roughness={0.72} metalness={0.35} />
    </mesh>
  );

  return (
    <group>
      {panel("bottom", [0, -0.01, 0], [0.9, 0.02, 0.5])}
      {panel("top", [0, 0.97, 0], [0.9, 0.02, 0.5])}
      {panel("back", [0.44, 0.48, 0], [0.02, 0.96, 0.5])}
      {panel("front", [-0.44, 0.48, 0], [0.02, 0.96, 0.5])}
      {panel("tray", [0, 0.48, -0.24], [0.9, 0.96, 0.02])}

      {/* 유리 사이드 패널 — 부품을 확대해서 볼 때 뿌옇게 덮지 않도록 아주 옅게만 남긴다 */}
      <mesh position={[0, 0.48, 0.245]}>
        <boxGeometry args={[0.88, 0.94, 0.006]} />
        <meshStandardMaterial
          color="#8fd3e8"
          transparent
          opacity={0.06}
          roughness={0.1}
          metalness={0.1}
          depthWrite={false}
        />
      </mesh>
      {/* 유리 테두리 프레임 (네 변만 — wireframe을 쓰면 삼각형 대각선이 유리에 X자로 비친다) */}
      {[
        { p: [0, 0.955, 0.245], s: [0.9, 0.02, 0.014] },
        { p: [0, 0.005, 0.245], s: [0.9, 0.02, 0.014] },
        { p: [-0.44, 0.48, 0.245], s: [0.02, 0.96, 0.014] },
        { p: [0.44, 0.48, 0.245], s: [0.02, 0.96, 0.014] },
      ].map(({ p, s }) => (
        <mesh key={`${p[0]}-${p[1]}`} position={p as [number, number, number]}>
          <boxGeometry args={s as [number, number, number]} />
          <meshStandardMaterial color={CASE_EDGE} roughness={0.4} metalness={0.8} />
        </mesh>
      ))}

      {/* 내부 조명 — 유리 너머 부품이 검게 뭉치지 않도록 케이스 안쪽을 직접 밝힌다 */}
      <pointLight position={[-0.1, 0.82, 0.16]} color="#cfe4ff" intensity={0.2} distance={1.6} />
      <pointLight position={[0.2, 0.34, 0.18]} color="#ffffff" intensity={0.14} distance={1.4} />

      {/* 전면 상단 전원 LED */}
      <mesh position={[-0.451, 0.9, 0]}>
        <boxGeometry args={[0.006, 0.012, 0.06]} />
        <meshStandardMaterial color="#22d3ee" emissive="#22d3ee" emissiveIntensity={2.4} />
      </mesh>
    </group>
  );
}

export function Motherboard() {
  return (
    <group>
      <mesh position={[0.06, 0.58, -0.21]} receiveShadow>
        <boxGeometry args={[0.62, 0.56, 0.014]} />
        <meshStandardMaterial color={PCB} roughness={0.75} metalness={0.25} />
      </mesh>
      {/* 칩셋 방열판 */}
      <mesh position={[0.06, 0.36, -0.19]}>
        <boxGeometry args={[0.12, 0.1, 0.022]} />
        <meshStandardMaterial color="#2b3340" roughness={0.35} metalness={0.8} />
      </mesh>
      {/* I/O 실드 */}
      <mesh position={[0.33, 0.78, -0.18]}>
        <boxGeometry args={[0.06, 0.14, 0.04]} />
        <meshStandardMaterial color="#333a47" roughness={0.3} metalness={0.85} />
      </mesh>
      {/* PCIe 슬롯 라인 */}
      {[0.5, 0.44].map((y) => (
        <mesh key={y} position={[0.0, y, -0.195]}>
          <boxGeometry args={[0.4, 0.012, 0.016]} />
          <meshStandardMaterial color="#4d3565" roughness={0.5} metalness={0.4} />
        </mesh>
      ))}
    </group>
  );
}

/** 축을 x로 눕힌 케이스 팬 (전/후면 흡배기). */
export function CaseFan({
  position,
  radius = 0.075,
  speed = 2.4,
  color = "#3b4250",
}: {
  position: [number, number, number];
  radius?: number;
  speed?: number;
  color?: string;
}) {
  const blades = useRef<Group>(null);
  useFrame((_, delta) => {
    if (blades.current) blades.current.rotation.x += delta * speed;
  });

  return (
    <group position={position} rotation={[0, 0, Math.PI / 2]}>
      <mesh>
        <boxGeometry args={[0.024, radius * 2.05, radius * 2.05]} />
        <meshStandardMaterial color="#252a34" roughness={0.6} metalness={0.4} />
      </mesh>
      <group ref={blades}>
        {[0, 1, 2, 3, 4].map((i) => (
          <mesh key={i} rotation={[(i * Math.PI * 2) / 5, 0, 0]} position={[0.014, 0, 0]}>
            <boxGeometry args={[0.008, radius * 1.7, 0.026]} />
            <meshStandardMaterial color={color} roughness={0.5} metalness={0.3} />
          </mesh>
        ))}
      </group>
      <mesh position={[0.016, 0, 0]}>
        <cylinderGeometry args={[0.018, 0.018, 0.012, 16]} />
        <meshStandardMaterial color="#161a21" roughness={0.4} metalness={0.6} />
      </mesh>
    </group>
  );
}

export function CpuCooler({ accent }: { accent: string }) {
  const fan = useRef<Mesh>(null);
  useFrame((_, delta) => {
    if (fan.current) fan.current.rotation.z += delta * 4;
  });

  return (
    <group position={[0, 0.7, -0.1]}>
      {/* 방열 핀 스택 */}
      {Array.from({ length: 9 }, (_, i) => (
        <mesh key={i} position={[-0.06 + i * 0.015, 0, 0]}>
          <boxGeometry args={[0.006, 0.15, 0.135]} />
          <meshStandardMaterial color="#9aa3b2" roughness={0.28} metalness={0.92} />
        </mesh>
      ))}
      {/* 상단 커버 */}
      <mesh position={[0, 0.085, 0]}>
        <boxGeometry args={[0.155, 0.022, 0.145]} />
        <meshStandardMaterial
          color="#20242d"
          emissive={accent}
          emissiveIntensity={0.35}
          roughness={0.35}
          metalness={0.7}
        />
      </mesh>
      {/* 쿨러 팬 (유리 쪽을 향해 회전) */}
      <mesh ref={fan} position={[0, 0, 0.082]}>
        <cylinderGeometry args={[0.062, 0.062, 0.012, 6]} />
        <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={0.55} roughness={0.4} />
      </mesh>
    </group>
  );
}

export function RamSticks({ accent }: { accent: string }) {
  return (
    <group>
      {[0.245, 0.29].map((x) => (
        <group key={x} position={[x, 0.72, -0.145]}>
          <mesh castShadow>
            <boxGeometry args={[0.018, 0.17, 0.095]} />
            <meshStandardMaterial color="#242a35" roughness={0.35} metalness={0.75} />
          </mesh>
          {/* 상단 RGB 디퓨저 */}
          <mesh position={[0, 0.093, 0]}>
            <boxGeometry args={[0.02, 0.016, 0.09]} />
            <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={1.5} />
          </mesh>
          {/* 슬롯 래치 */}
          <mesh position={[0, -0.093, 0]}>
            <boxGeometry args={[0.026, 0.016, 0.1]} />
            <meshStandardMaterial color="#4b3a5c" roughness={0.5} metalness={0.3} />
          </mesh>
        </group>
      ))}
    </group>
  );
}

export function Gpu({ accent }: { accent: string }) {
  const fanA = useRef<Mesh>(null);
  const fanB = useRef<Mesh>(null);
  useFrame((_, delta) => {
    if (fanA.current) fanA.current.rotation.y += delta * 3.2;
    if (fanB.current) fanB.current.rotation.y += delta * 3.2;
  });

  return (
    <group position={[0.02, 0.44, -0.13]}>
      {/* 쿨러 슈라우드 */}
      <mesh castShadow>
        <boxGeometry args={[0.6, 0.095, 0.17]} />
        <meshStandardMaterial color="#22262e" roughness={0.4} metalness={0.7} />
      </mesh>
      {/* PCB 꼬리 */}
      <mesh position={[0, -0.055, -0.03]}>
        <boxGeometry args={[0.62, 0.02, 0.12]} />
        <meshStandardMaterial color={PCB} roughness={0.8} metalness={0.2} />
      </mesh>
      {/* 하단 팬 2개 */}
      {[-0.13, 0.13].map((x, i) => (
        <mesh
          key={x}
          ref={i === 0 ? fanA : fanB}
          position={[x, -0.049, 0]}
          rotation={[Math.PI / 2, 0, 0]}
        >
          <cylinderGeometry args={[0.055, 0.055, 0.01, 7]} />
          <meshStandardMaterial color="#2f3542" roughness={0.5} metalness={0.4} />
        </mesh>
      ))}
      {/* 유리 쪽에서 보이는 RGB 로고 스트립 */}
      <mesh position={[0, 0.0, 0.088]}>
        <boxGeometry args={[0.44, 0.018, 0.004]} />
        <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={1.3} />
      </mesh>
      {/* 브래킷 */}
      <mesh position={[-0.315, -0.02, -0.02]}>
        <boxGeometry args={[0.014, 0.11, 0.14]} />
        <meshStandardMaterial color="#8f97a6" roughness={0.3} metalness={0.9} />
      </mesh>
    </group>
  );
}

export function Ssd({ accent }: { accent: string }) {
  return (
    <group position={[0.1, 0.34, -0.185]}>
      {/* M.2 기판 */}
      <mesh>
        <boxGeometry args={[0.22, 0.036, 0.014]} />
        <meshStandardMaterial color="#1c2b24" roughness={0.75} metalness={0.25} />
      </mesh>
      {/* 방열판 */}
      <mesh position={[0, 0, 0.016]}>
        <boxGeometry args={[0.2, 0.042, 0.02]} />
        <meshStandardMaterial
          color="#2a3a34"
          emissive={accent}
          emissiveIntensity={0.5}
          roughness={0.35}
          metalness={0.8}
        />
      </mesh>
      {/* 방열판 홈 */}
      {[-0.06, -0.02, 0.02, 0.06].map((x) => (
        <mesh key={x} position={[x, 0, 0.027]}>
          <boxGeometry args={[0.008, 0.03, 0.004]} />
          <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={1.4} />
        </mesh>
      ))}
    </group>
  );
}

export function Psu() {
  return (
    <group>
      <mesh position={[0.02, 0.09, -0.02]} castShadow>
        <boxGeometry args={[0.62, 0.18, 0.44]} />
        <meshStandardMaterial color="#1e222b" roughness={0.5} metalness={0.7} />
      </mesh>
      <mesh position={[0.02, 0.185, -0.02]}>
        <boxGeometry args={[0.6, 0.006, 0.42]} />
        <meshStandardMaterial color="#2b313d" roughness={0.4} metalness={0.8} />
      </mesh>
    </group>
  );
}

// ============================================================
// 책상 위 장비
// ============================================================

export function Laptop({
  accent,
  bodyColor = "#20242c",
  screenTint = "#0e1620",
  lidAngle = -0.26,
}: {
  accent: string;
  bodyColor?: string;
  screenTint?: string;
  lidAngle?: number;
}) {
  const width = 0.42;
  const depth = 0.29;

  return (
    <group>
      {/* 하판 (키보드 데크) */}
      <mesh position={[0, 0.008, 0]} castShadow receiveShadow>
        <boxGeometry args={[width, 0.016, depth]} />
        <meshStandardMaterial color={bodyColor} roughness={0.42} metalness={0.65} />
      </mesh>
      {/* 키보드 패널 */}
      <mesh position={[0, 0.017, -0.02]}>
        <boxGeometry args={[width - 0.05, 0.002, depth - 0.15]} />
        <meshStandardMaterial color="#0f1218" roughness={0.85} />
      </mesh>
      {/* 키 열 — 백라이트가 은은하게 도는 느낌만 */}
      {[-0.052, -0.026, 0, 0.026, 0.052].map((z) => (
        <mesh key={z} position={[0, 0.019, z - 0.02]}>
          <boxGeometry args={[width - 0.075, 0.003, 0.016]} />
          <meshStandardMaterial
            color="#191d26"
            emissive={accent}
            emissiveIntensity={0.35}
            roughness={0.8}
          />
        </mesh>
      ))}
      {/* 트랙패드 */}
      <mesh position={[0, 0.018, depth / 2 - 0.05]}>
        <boxGeometry args={[0.1, 0.002, 0.062]} />
        <meshStandardMaterial color="#252a34" roughness={0.35} metalness={0.4} />
      </mesh>
      {/* 전면 RGB 라이트바 */}
      <mesh position={[0, 0.004, depth / 2 + 0.001]}>
        <boxGeometry args={[width - 0.06, 0.004, 0.004]} />
        <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={2.4} />
      </mesh>

      {/* 상판 (힌지 기준 회전) */}
      <group position={[0, 0.016, -depth / 2]} rotation={[lidAngle, 0, 0]}>
        <mesh position={[0, 0.135, -0.006]} castShadow>
          <boxGeometry args={[width, 0.27, 0.012]} />
          <meshStandardMaterial color={bodyColor} roughness={0.42} metalness={0.65} />
        </mesh>
        {/* 화면 — 정반사 하이라이트가 흰 점으로 뜨지 않게 거칠기를 높인다 */}
        <mesh position={[0, 0.135, 0.001]}>
          <boxGeometry args={[width - 0.026, 0.245, 0.002]} />
          <meshStandardMaterial
            color={screenTint}
            emissive={accent}
            emissiveIntensity={0.5}
            roughness={0.9}
            metalness={0}
          />
        </mesh>
        {/* 화면 안 대시보드 느낌의 막대 그래프 */}
        {[
          { x: -0.12, h: 0.06 },
          { x: -0.05, h: 0.11 },
          { x: 0.02, h: 0.08 },
          { x: 0.09, h: 0.14 },
        ].map(({ x, h }) => (
          <mesh key={x} position={[x, 0.08 + h / 2, 0.003]}>
            <boxGeometry args={[0.035, h, 0.001]} />
            <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={1.1} />
          </mesh>
        ))}
        {/* 뚜껑 로고 */}
        <mesh position={[0, 0.135, -0.014]}>
          <boxGeometry args={[0.05, 0.05, 0.003]} />
          <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={2} />
        </mesh>
      </group>
    </group>
  );
}

export function Monitor({
  accent,
  screenAccent = "#22d3ee",
}: {
  accent: string;
  /** 화면 발광색. 카테고리색이 어두울 때 화면까지 어두워지지 않도록 분리한다. */
  screenAccent?: string;
}) {
  return (
    <group>
      <mesh position={[0, 0.012, 0]} castShadow>
        <boxGeometry args={[0.3, 0.024, 0.16]} />
        <meshStandardMaterial color="#1b1f27" roughness={0.4} metalness={0.7} />
      </mesh>
      <mesh position={[0, 0.14, 0]}>
        <boxGeometry args={[0.04, 0.26, 0.03]} />
        <meshStandardMaterial color="#23272f" roughness={0.4} metalness={0.7} />
      </mesh>
      <group position={[0, 0.4, 0.01]} rotation={[-0.08, 0, 0]}>
        <mesh castShadow>
          <boxGeometry args={[0.68, 0.4, 0.018]} />
          <meshStandardMaterial color="#181c23" roughness={0.45} metalness={0.6} />
        </mesh>
        <mesh position={[0, 0, 0.011]}>
          <boxGeometry args={[0.65, 0.37, 0.004]} />
          <meshStandardMaterial
            color="#101a28"
            emissive={screenAccent}
            emissiveIntensity={0.5}
            roughness={0.8}
            metalness={0}
          />
        </mesh>
        {/* 화면 안 대시보드 — 모니터가 켜져 있다는 신호 */}
        {[
          { x: -0.21, h: 0.1 },
          { x: -0.08, h: 0.18 },
          { x: 0.05, h: 0.13 },
          { x: 0.18, h: 0.24 },
        ].map(({ x, h }) => (
          <mesh key={x} position={[x, -0.09 + h / 2, 0.014]}>
            <boxGeometry args={[0.07, h, 0.002]} />
            <meshStandardMaterial color={screenAccent} emissive={screenAccent} emissiveIntensity={1.5} />
          </mesh>
        ))}
        {/* 하단 카테고리색 액센트 바 */}
        <mesh position={[0, -0.175, 0.014]}>
          <boxGeometry args={[0.6, 0.012, 0.002]} />
          <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={2.2} />
        </mesh>
      </group>
    </group>
  );
}
