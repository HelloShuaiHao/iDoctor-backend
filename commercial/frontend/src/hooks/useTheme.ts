import { useEffect, useState } from 'react';

type Theme = 'light' | 'dark';

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => {
    // 从 localStorage 读取主题，或使用系统偏好
    const stored = localStorage.getItem('theme') as Theme | null;
    if (stored) return stored;

    // 检查系统偏好
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }

    return 'light';
  });

  useEffect(() => {
    const root = document.documentElement;

    // 移除旧的主题类
    root.classList.remove('light', 'dark');

    // 添加新的主题类
    root.classList.add(theme);

    // 保存到 localStorage
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  return { theme, toggleTheme };
}
