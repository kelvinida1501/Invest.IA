import { describe, expect, it, beforeEach, vi } from 'vitest';

const { axiosInstance } = vi.hoisted(() => ({
  axiosInstance: {
    defaults: { headers: {} as Record<string, string> },
    interceptors: { request: { use: vi.fn() } },
  },
}));

vi.mock('axios', () => ({
  __esModule: true,
  default: {
    create: vi.fn(() => axiosInstance),
  },
}));

import api, { setAuthToken } from './ApiClient';

describe('ApiClient', () => {
  beforeEach(() => {
    localStorage.clear();
    axiosInstance.defaults.headers = {};
  });

  it('sets auth token in localStorage and axios defaults', () => {
    setAuthToken('abc');
    expect(localStorage.getItem('token')).toBe('abc');
    expect((api.defaults.headers as any).Authorization).toBe('Bearer abc');
  });

  it('clears auth token when undefined', () => {
    localStorage.setItem('token', 'old');
    (api.defaults.headers as any).Authorization = 'Bearer old';

    setAuthToken(undefined);

    expect(localStorage.getItem('token')).toBeNull();
    expect((api.defaults.headers as any).Authorization).toBeUndefined();
  });
});
