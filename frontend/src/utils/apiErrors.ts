import { AxiosError } from 'axios';

export function getApiErrorMessage(err: unknown, fallbackMessage: string): string {
  if (!(err instanceof AxiosError)) {
    return fallbackMessage;
  }

  const responseData = err.response?.data;
  if (typeof responseData === 'string') {
    return responseData;
  }

  if (responseData?.detail && typeof responseData.detail === 'string') {
    return responseData.detail;
  }

  if (responseData && typeof responseData === 'object') {
    for (const value of Object.values(responseData as Record<string, unknown>)) {
      if (Array.isArray(value) && value.length > 0 && typeof value[0] === 'string') {
        return value[0];
      }
      if (typeof value === 'string') {
        return value;
      }
    }
  }

  return fallbackMessage;
}