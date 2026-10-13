// frontend/src/hooks/useReadonly.ts
// 서버가 읽기전용으로 떠 있는지 알려준다.
//
// 공개 URL로 띄울 때는 워치리스트 쓰기 라우트를 등록하지 않는다(인증이 없어서다).
// 그 상태에서 편집 버튼을 그대로 두면 눌렀을 때만 실패하므로, 아예 감추는 게 낫다.
// 판단이 서기 전(로딩 중)에는 false 를 돌려준다 — 로컬 사용이 기본이고,
// 잘못 눌러도 위 sendJson 이 안내 메시지를 띄운다.

import { useEffect, useState } from "react";
import { getHealth } from "../api/client";

let cached: boolean | null = null;

export function useReadonly(): boolean {
  const [readonly, setReadonly] = useState(cached ?? false);

  useEffect(() => {
    if (cached !== null) return;
    let alive = true;
    getHealth()
      .then((h) => {
        cached = h.readonly;
        if (alive) setReadonly(h.readonly);
      })
      .catch(() => {
        /* health 를 못 읽으면 기본값(편집 가능)을 유지한다 */
      });
    return () => {
      alive = false;
    };
  }, []);

  return readonly;
}
