"use client";

import { useCallback, useEffect, useState } from "react";

export function useApiResource<T>(load: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    load().then(value => {
      if (active) setData(value);
    }).catch(cause => {
      if (active) setError(cause instanceof Error ? cause.message : "Không thể tải dữ liệu.");
    });
    return () => { active = false; };
  }, [load, attempt]);

  const retry = useCallback(() => {
    setData(null);
    setError("");
    setAttempt(value => value + 1);
  }, []);

  return { data, error, retry };
}
