/**
 * Axios 实例 + ApiResponse 信封解包 + ApiError
 *
 * Reference: docs/tech-spec.md §4.1, docs/contracts/error-handling.md
 * 唯一后端访问点，业务代码禁止直接 import axios。
 */
import axios, { AxiosError } from 'axios';

/** 后端统一响应信封（api-contract §1.1） */
export interface ApiEnvelope<T> {
  code: number;
  message: string;
  data: T;
  request_id: string | null;
}

/** 统一 API 错误（error-handling 契约 §1） */
export class ApiError extends Error {
  code: number;
  httpStatus: number;
  requestId: string | null;

  constructor(code: number, message: string, httpStatus: number, requestId: string | null) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.httpStatus = httpStatus;
    this.requestId = requestId;
  }
}

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 30_000,
});

http.interceptors.response.use(
  (response) => {
    const body = response.data as ApiEnvelope<unknown>;
    // 成功判定：code === 0（已实测，message 文案不稳定不可依赖）
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code === 0) {
        response.data = body.data;
        return response;
      }
      throw new ApiError(body.code, body.message, response.status, body.request_id ?? null);
    }
    // 无信封端点（如 /health）直接透传
    return response;
  },
  (error: AxiosError) => {
    const body = error.response?.data as ApiEnvelope<unknown> | undefined;
    if (body && typeof body === 'object' && 'code' in body) {
      throw new ApiError(
        body.code,
        body.message,
        error.response?.status ?? 0,
        body.request_id ?? null,
      );
    }
    // FastAPI 422 校验错误：{ detail: [...] }
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail;
    if (error.response?.status === 422 && detail) {
      throw new ApiError(422, JSON.stringify(detail), 422, null);
    }
    // 网络错误
    throw new ApiError(0, error.message || 'Network Error', error.response?.status ?? 0, null);
  },
);

export default http;
