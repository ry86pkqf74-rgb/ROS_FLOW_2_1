/**
 * Favorites sidebar panel and star button
 *
 * Sheet (right) with list of favorites; star/unstar for resources.
 */

import React from 'react';
import { Link } from 'wouter';
import { Star, StarOff } from 'lucide-react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { useFavorites } from '@/hooks/use-favorites';
import type { Favorite } from '@/api/favorites';
import { cn } from '@/lib/utils';

export interface FavoritesPanelProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function getResourceHref(fav: Favorite): string | null {
  if (fav.resourceType === 'project') return `/projects/${fav.resourceId}`;
  return null;
}

function getResourceLabel(fav: Favorite): string {
  return `${fav.resourceType}: ${fav.resourceId}`;
}

export function FavoritesPanel({ open, onOpenChange }: FavoritesPanelProps) {
  const { favorites, isLoading, removeFavorite } = useFavorites();

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="flex flex-col w-full sm:max-w-sm">
        <SheetHeader>
          <SheetTitle>Favorites</SheetTitle>
          <SheetDescription>Quick access to starred resources</SheetDescription>
        </SheetHeader>
        <ScrollArea className="flex-1 mt-4 -mx-6 px-6">
          {isLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : favorites.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Star className="h-12 w-12 text-muted-foreground opacity-50 mb-3" />
              <p className="text-sm font-medium">No favorites yet</p>
              <p className="text-xs text-muted-foreground mt-1">
                Star projects or other resources to see them here
              </p>
            </div>
          ) : (
            <ul className="space-y-1">
              {favorites.map((fav) => {
                const href = getResourceHref(fav);
                const label = getResourceLabel(fav);
                return (
                  <li
                    key={fav.id}
                    className="flex items-center gap-2 rounded-md border bg-card px-3 py-2 text-sm"
                  >
                    <span className="flex-1 min-w-0 truncate">
                      {href ? (
                        <Link href={href} className="text-primary hover:underline truncate block">
                          {label}
                        </Link>
                      ) : (
                        <span className="text-muted-foreground">{label}</span>
                      )}
                    </span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="shrink-0 h-8 w-8"
                      onClick={() => removeFavorite.mutate(fav.id)}
                      disabled={removeFavorite.isPending}
                      aria-label="Remove from favorites"
                    >
                      <StarOff className="h-4 w-4" />
                    </Button>
                  </li>
                );
              })}
            </ul>
          )}
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}

export interface FavoriteStarButtonProps {
  resourceType: string;
  resourceId: string;
  favoriteId?: string | null;
  className?: string;
  size?: 'default' | 'sm' | 'icon' | 'lg';
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
}

export function FavoriteStarButton({
  resourceType,
  resourceId,
  favoriteId,
  className,
  size = 'icon',
  variant = 'ghost',
}: FavoriteStarButtonProps) {
  const { favorites, addFavorite, removeFavorite } = useFavorites();
  const existing = favoriteId
    ? { id: favoriteId }
    : favorites.find((f) => f.resourceType === resourceType && f.resourceId === resourceId);
  const resolvedId = existing?.id;

  const handleClick = () => {
    if (resolvedId) {
      removeFavorite.mutate(resolvedId);
    } else {
      addFavorite.mutate({ resourceType, resourceId });
    }
  };

  return (
    <Button
      variant={variant}
      size={size}
      className={cn(className)}
      onClick={handleClick}
      disabled={addFavorite.isPending || removeFavorite.isPending}
      aria-label={resolvedId ? 'Remove from favorites' : 'Add to favorites'}
    >
      {resolvedId ? (
        <Star className="h-4 w-4 fill-current" />
      ) : (
        <Star className="h-4 w-4" />
      )}
    </Button>
  );
}
