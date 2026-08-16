// frontend/src/three/DeskScene.tsx
// 책상 + 오픈케이스 PC + 노트북 2대로 이루어진 3D 씬.
// 부품을 호버하면 라벨이 뜨고, 클릭하면 카메라가 그 부품 앞으로 날아가면서 상위 컴포넌트에 선택을 알린다.
// 실제 가격 데이터 렌더링은 DeskPage 쪽 패널이 담당하고, 여기서는 라벨용 요약 문자열만 받는다.

import { useEffect, useRef, useState } from "react";
import { Canvas, useFrame, type ThreeEvent } from "@react-three/fiber";
import { ContactShadows, Edges, Html, OrbitControls, useCursor } from "@react-three/drei";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { Vector3 } from "three";

import {
  CaseFan,
  CpuCooler,
  Desk,
  Floor,
  Gpu,
  Laptop,
  Monitor,
  Motherboard,
  Psu,
  RamSticks,
  Ssd,
  TowerShell,
} from "./models";
import {
  AcousticFoamWall,
  CableClutter,
  Ceiling,
  DeskMat,
  DustMotes,
  FloorLightBar,
  GamingChair,
  HeadsetStand,
  HexPanelCluster,
  Keyboard,
  MicBoomArm,
  Mouse,
  NeonPulseSign,
  GlowQuad,
  PottedPlant,
  RoomShell,
  Rug,
  ScreenBar,
  Speaker,
  WallShelf,
  BlindWindow,
} from "./room";
import {
  DESK_TOP_Y,
  MONITOR_POSITION,
  ROOM,
  MONITOR_ROTATION_Y,
  OVERVIEW_CAMERA,
  PARTS,
  TOWER_POSITION,
  TOWER_ROTATION_Y,
  TOWER_SCALE,
  findPart,
  partColor,
  type PartDef,
  type Vec3,
} from "./parts";

// ============================================================
// 카메라 이동
// ============================================================

/** 선택이 바뀔 때마다 카메라를 프리셋으로 부드럽게 이동시킨다. 사용자가 드래그를 시작하면 즉시 손을 뗀다. */
function CameraRig({
  controlsRef,
  goalKey,
  position,
  target,
}: {
  controlsRef: React.RefObject<OrbitControlsImpl | null>;
  goalKey: string;
  position: Vec3;
  target: Vec3;
}) {
  const traveling = useRef(true);
  const goalPosition = useRef(new Vector3(...position));
  const goalTarget = useRef(new Vector3(...target));

  useEffect(() => {
    goalPosition.current.set(...position);
    goalTarget.current.set(...target);
    traveling.current = true;
    // goalKey가 바뀔 때만 새 여행을 시작한다 (position/target 배열은 매 렌더 새 참조라 deps에서 뺀다)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [goalKey]);

  useEffect(() => {
    const controls = controlsRef.current;
    if (!controls) return;
    const stop = () => {
      traveling.current = false;
    };
    controls.addEventListener("start", stop);
    return () => controls.removeEventListener("start", stop);
  }, [controlsRef]);

  useFrame((state, delta) => {
    const controls = controlsRef.current;
    if (!controls || !traveling.current) return;

    // 프레임레이트와 무관하게 같은 속도로 수렴하는 지수 보간
    const t = 1 - Math.pow(0.0015, delta);
    state.camera.position.lerp(goalPosition.current, t);
    controls.target.lerp(goalTarget.current, t);
    controls.update();

    if (
      state.camera.position.distanceTo(goalPosition.current) < 0.01 &&
      controls.target.distanceTo(goalTarget.current) < 0.01
    ) {
      traveling.current = false;
    }
  });

  return null;
}

// ============================================================
// 부품 핫스팟
// ============================================================

interface HotspotProps {
  part: PartDef;
  /** 클릭 판정 + 선택 테두리를 그릴 박스. 부모 그룹 로컬 좌표 기준. */
  center: Vec3;
  size: Vec3;
  selected: boolean;
  /** 데이터가 없는 카테고리는 라벨만 흐리게 표시한다. */
  available: boolean;
  summary: string;
  onSelect: (id: string) => void;
  children: React.ReactNode;
}

function Hotspot({
  part,
  center,
  size,
  selected,
  available,
  summary,
  onSelect,
  children,
}: HotspotProps) {
  const [hovered, setHovered] = useState(false);
  useCursor(hovered);
  const accent = partColor(part);
  const active = hovered || selected;

  const handleOver = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation();
    setHovered(true);
  };
  const handleOut = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation();
    setHovered(false);
  };
  const handleClick = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    onSelect(part.id);
  };

  return (
    <group>
      {children}

      {/* 클릭/호버 판정용 투명 박스 — 얇은 부품도 넉넉하게 집히도록 */}
      <mesh
        position={center}
        onPointerOver={handleOver}
        onPointerOut={handleOut}
        onClick={handleClick}
      >
        <boxGeometry args={size} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
        {active && <Edges color={accent} lineWidth={selected ? 2.5 : 1.5} scale={1.06} />}
      </mesh>

      {selected && <pointLight position={center} color={accent} intensity={0.3} distance={0.9} />}

      {active && (
        <Html position={[center[0], center[1] + size[1] / 2 + 0.06, center[2]]} center zIndexRange={[20, 0]}>
          <div
            style={{
              pointerEvents: "none",
              whiteSpace: "nowrap",
              transform: "translateY(-50%)",
              padding: "5px 10px",
              borderRadius: 999,
              border: `1px solid ${accent}`,
              background: "rgba(13, 15, 20, 0.88)",
              color: "#f3f4f6",
              fontFamily: "Inter, sans-serif",
              fontSize: 12,
              fontWeight: 600,
              boxShadow: `0 0 14px ${accent}55`,
              opacity: available ? 1 : 0.55,
            }}
          >
            <span style={{ color: accent }}>{part.icon} {part.label}</span>
            <span style={{ color: "#8b93a7", marginLeft: 8, fontWeight: 500 }}>{summary}</span>
          </div>
        </Html>
      )}
    </group>
  );
}

// ============================================================
// 씬 구성
// ============================================================

export interface DeskSceneProps {
  selectedId: string | null;
  onSelect: (id: string) => void;
  /** 부품 id → 라벨에 띄울 짧은 요약 (예: "평균 62.4만원 · 128개"). */
  summaries: Record<string, string>;
  availableCategories: Set<string>;
}

function SceneContent({ selectedId, onSelect, summaries, availableCategories }: DeskSceneProps) {
  const controlsRef = useRef<OrbitControlsImpl | null>(null);
  const selectedPart = findPart(selectedId);
  const goal = selectedPart?.camera ?? OVERVIEW_CAMERA;

  const hotspotProps = (part: PartDef) => ({
    part,
    selected: selectedId === part.id,
    available: availableCategories.has(part.category),
    summary: summaries[part.id] ?? "데이터 없음",
    onSelect,
  });

  const cpu = PARTS[0];
  const gpu = PARTS[1];
  const ram = PARTS[2];
  const ssd = PARTS[3];
  const gamingLaptop = PARTS[4];
  const aiLaptop = PARTS[5];
  const monitor = PARTS[6];

  return (
    <>
      <color attach="background" args={["#0b0e15"]} />
      {/* 방이 닫히면서 뒷벽 구석에 페이드가 걸리도록 안개를 앞으로 당긴다 */}
      <fog attach="fog" args={["#0b0e15", 5, 14]} />

      {/*
        벽이 생기면 전역광을 그대로 두는 순간 방 전체가 균일하게 떠서 무드가 사라진다.
        대신 케이스 내부/정면 필을 올려서 부품이 검게 뭉치지 않게 보정한다 — 무드보다 부품 가독성이 우선.
      */}
      <ambientLight intensity={0.34} />
      <hemisphereLight args={["#5c6f94", "#0a0d13", 0.42]} />
      <directionalLight
        position={[3.5, 5.5, 4]}
        intensity={1.5}
        castShadow
        shadow-mapSize={[1024, 1024]}
        shadow-camera-left={-5}
        shadow-camera-right={5}
        shadow-camera-top={5}
        shadow-camera-bottom={-5}
      />
      {/* 아래 두 광원은 각각 코너 라이트바와 육각 패널에 붙어 있다 — 광원에 실체를 준다 */}
      <pointLight position={[-2.85, 1.35, 1.55]} color="#22d3ee" intensity={6} distance={6.5} />
      <pointLight position={[2.15, 1.5, -1.05]} color="#8b5cf6" intensity={5.5} distance={5.5} />
      {/* 케이스 유리면 정면 필 라이트 — 기본 시점에서 내부 부품이 검게 뭉치지 않도록 */}
      <pointLight position={[1.14, 0.9, 1.18]} color="#dbe7ff" intensity={7} distance={3.2} />

      <Floor />
      <RoomShell />
      <Ceiling />
      <Rug />
      <Desk />
      <ContactShadows position={[0, 0.014, 0]} opacity={0.52} scale={11} blur={2.4} far={2.2} />

      {/* ---- 벽면 ---- */}
      <AcousticFoamWall position={[-1.95, 1.28, ROOM.backZ + 0.03]} cols={6} rows={2} />
      <GlowQuad position={[-1.95, 1.98, ROOM.backZ + 0.02]} size={[1.5, 0.5]} color="#22d3ee" opacity={0.2} />
      <NeonPulseSign position={[-1.95, 1.98, ROOM.backZ + 0.05]} color="#22d3ee" scale={0.95} />
      <WallShelf position={[-0.3, 1.62, ROOM.backZ + 0.13]} />
      <GlowQuad position={[0.66, 1.86, ROOM.backZ + 0.02]} size={[0.85, 0.75]} color="#8b5cf6" opacity={0.16} />
      <HexPanelCluster position={[0.66, 1.86, ROOM.backZ + 0.04]} />
      <BlindWindow position={[ROOM.minX + 0.05, 1.55, -0.35]} />

      {/* ---- 바닥 ---- */}
      <GamingChair position={[-2.18, 0, 1.05]} rotationY={0.72} accent="#8f3030" />
      <FloorLightBar position={[-2.85, 0, 1.55]} color="#22d3ee" height={1.75} />
      <FloorLightBar position={[2.15, 0, -1.15]} color="#8b5cf6" height={1.6} />
      <PottedPlant position={[2.72, 0, -0.35]} />
      <CableClutter position={[0.55, 0, -0.5]} />
      <DustMotes count={46} />

      {/* ---- 책상 위: 노트북 2대 + 모니터 ---- */}
      <group position={[-1.5, DESK_TOP_Y, 0.05]} rotation={[0, 0.3, 0]}>
        <Hotspot
          {...hotspotProps(gamingLaptop)}
          center={[0, 0.14, -0.06]}
          size={[0.46, 0.3, 0.36]}
        >
          <Laptop accent={partColor(gamingLaptop)} bodyColor="#1c2029" />
        </Hotspot>
      </group>

      <group position={[-0.35, DESK_TOP_Y, 0.02]} rotation={[0, -0.16, 0]}>
        <Hotspot {...hotspotProps(aiLaptop)} center={[0, 0.14, -0.06]} size={[0.46, 0.3, 0.36]}>
          <Laptop accent={partColor(aiLaptop)} bodyColor="#2a2d38" screenTint="#131024" />
        </Hotspot>
      </group>

      <group position={MONITOR_POSITION} rotation={[0, MONITOR_ROTATION_Y, 0]}>
        {/* Hotspot 박스는 패널만 감싼다 — 스크린바/바이어스 스트립까지 넣으면 선택 테두리가 장식을 감싼다 */}
        <Hotspot {...hotspotProps(monitor)} center={[0, 0.4, 0.01]} size={[0.72, 0.42, 0.09]}>
          <Monitor accent={partColor(monitor)} />
        </Hotspot>
        <ScreenBar position={[0, 0.63, 0.03]} />
        {/* 모니터 뒷면 바이어스 라이팅 — 벽에 색이 번지게 한다 */}
        <mesh position={[0, 0.4, -0.02]}>
          <boxGeometry args={[0.62, 0.36, 0.006]} />
          <meshStandardMaterial
            color={partColor(monitor)}
            emissive={partColor(monitor)}
            emissiveIntensity={1.8}
            toneMapped={false}
          />
        </mesh>
      </group>

      {/* ---- 책상 위 게이밍 소품 ---- */}
      <group position={[0.42, DESK_TOP_Y, 0.2]} rotation={[0, MONITOR_ROTATION_Y, 0]}>
        <DeskMat position={[0, 0.001, 0]} size={[0.94, 0.5]} accent="#8b5cf6" />
        <Keyboard position={[-0.04, 0.002, -0.02]} accent="#22d3ee" />
        <Mouse position={[0.32, 0.002, 0.06]} accent="#22d3ee" />
      </group>
      <Speaker position={[0.06, DESK_TOP_Y, -0.46]} rotationY={-0.5} accent="#22d3ee" />
      <Speaker position={[0.86, DESK_TOP_Y, -0.38]} rotationY={-0.18} accent="#22d3ee" />
      <HeadsetStand position={[-2.0, DESK_TOP_Y, -0.38]} accent="#8b5cf6" />
      <MicBoomArm position={[0.84, DESK_TOP_Y, -0.55]} accent="#22d3ee" />

      {/* ---- 바닥: 오픈케이스 데스크톱 ---- */}
      <group position={TOWER_POSITION} rotation={[0, TOWER_ROTATION_Y, 0]} scale={TOWER_SCALE}>
        <TowerShell />
        <Motherboard />
        <Psu />
        <CaseFan position={[-0.4, 0.32, 0]} />
        <CaseFan position={[-0.4, 0.62, 0]} />
        <CaseFan position={[0.4, 0.78, 0]} radius={0.06} speed={-2.8} />

        <Hotspot {...hotspotProps(cpu)} center={[0, 0.7, -0.09]} size={[0.19, 0.21, 0.23]}>
          <CpuCooler accent={partColor(cpu)} />
        </Hotspot>

        <Hotspot {...hotspotProps(gpu)} center={[0.02, 0.43, -0.13]} size={[0.64, 0.17, 0.22]}>
          <Gpu accent={partColor(gpu)} />
        </Hotspot>

        <Hotspot {...hotspotProps(ram)} center={[0.268, 0.72, -0.145]} size={[0.1, 0.22, 0.13]}>
          <RamSticks accent={partColor(ram)} />
        </Hotspot>

        <Hotspot {...hotspotProps(ssd)} center={[0.1, 0.34, -0.175]} size={[0.24, 0.08, 0.07]}>
          <Ssd accent={partColor(ssd)} />
        </Hotspot>
      </group>

      <OrbitControls
        ref={controlsRef}
        makeDefault
        enablePan={false}
        minDistance={0.25}
        maxDistance={7}
        minPolarAngle={0.15}
        maxPolarAngle={Math.PI / 2 - 0.04}
        enableDamping
        dampingFactor={0.08}
      />
      <CameraRig
        controlsRef={controlsRef}
        goalKey={selectedId ?? "overview"}
        position={goal.position}
        target={goal.target}
      />
    </>
  );
}

export function DeskScene(props: DeskSceneProps) {
  return (
    <Canvas
      shadows
      dpr={[1, 2]}
      camera={{ position: OVERVIEW_CAMERA.position, fov: 42, near: 0.05, far: 40 }}
    >
      <SceneContent {...props} />
    </Canvas>
  );
}

export default DeskScene;
