/**
 * React Query hooks for user favorites
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { favoritesApi } from '@/api/favorites';

export function useFavorites() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['favorites'],
    queryFn: () => favoritesApi.list(),
  });

  const addFavorite = useMutation({
    mutationFn: (payload: { resourceType: string; resourceId: string }) =>
      favoritesApi.add(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['favorites'] });
    },
  });

  const removeFavorite = useMutation({
    mutationFn: (favoriteId: string) => favoritesApi.remove(favoriteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['favorites'] });
    },
  });

  return {
    favorites: data?.favorites ?? [],
    isLoading,
    addFavorite,
    removeFavorite,
  };
}
