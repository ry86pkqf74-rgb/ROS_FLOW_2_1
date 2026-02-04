/**
 * Favorites API Client
 *
 * List, add, and remove user favorites (starred resources).
 */

import { api } from './client';

export interface Favorite {
  id: string;
  userId?: string;
  resourceType: string;
  resourceId: string;
  createdAt?: string;
}

export interface FavoritesListResponse {
  favorites: Favorite[];
}

function unwrap<T>(result: { data: T | null; error: { error: string } | null }): T {
  if (result.error) {
    throw new Error(result.error.error || 'Request failed');
  }
  if (result.data == null) {
    throw new Error('No data');
  }
  return result.data;
}

export const favoritesApi = {
  list: () =>
    api.get<FavoritesListResponse>('/api/favorites').then((res) => unwrap(res)),

  add: (data: { resourceType: string; resourceId: string }) =>
    api.post<Favorite>('/api/favorites', data).then((res) => unwrap(res)),

  remove: (favoriteId: string) =>
    api.delete<unknown>(`/api/favorites/${favoriteId}`).then((res) => {
      if (res.error) throw new Error(res.error.error || 'Request failed');
      return undefined;
    }),
};

export default favoritesApi;
