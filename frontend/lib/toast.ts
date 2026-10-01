"use client";

import { create } from "zustand";

interface ToastState {
  message: string | null;
  show: (m: string) => void;
}

let timer: ReturnType<typeof setTimeout> | undefined;

/** One toast at a time, bottom-right, 4 seconds (spec 4.2). */
export const useToast = create<ToastState>()((set) => ({
  message: null,
  show: (message) => {
    clearTimeout(timer);
    set({ message });
    timer = setTimeout(() => set({ message: null }), 4000);
  },
}));
