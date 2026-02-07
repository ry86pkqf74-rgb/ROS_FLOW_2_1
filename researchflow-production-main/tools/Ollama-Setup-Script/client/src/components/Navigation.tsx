import { 
  Bot, 
  Settings, 
  MessageSquare, 
  Box, 
  Activity 
} from "lucide-react";
import { Link, useLocation } from "wouter";

import { cn } from "@/lib/utils";

export function Navigation() {
  const [location] = useLocation();

  const navItems = [
    { href: "/", label: "Dashboard", icon: Activity },
    { href: "/chat", label: "Chat", icon: MessageSquare },
    { href: "/models", label: "Models", icon: Box },
    { href: "/settings", label: "Settings", icon: Settings },
  ];

  return (
    <nav className="h-screen w-64 bg-card border-r border-border flex flex-col fixed left-0 top-0 z-50">
      <div className="p-6 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground shadow-lg shadow-primary/20">
          <Bot className="w-5 h-5" />
        </div>
        <span className="font-display font-bold text-xl tracking-tight">OllamaUI</span>
      </div>

      <div className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => {
          const isActive = location === item.href || (item.href !== "/" && location.startsWith(item.href));
          return (
            <Link key={item.href} href={item.href}>
              <div 
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 cursor-pointer group",
                  isActive 
                    ? "bg-primary/10 text-primary shadow-sm" 
                    : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                )}
              >
                <item.icon className={cn(
                  "w-4 h-4 transition-colors",
                  isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground"
                )} />
                {item.label}
              </div>
            </Link>
          );
        })}
      </div>

      <div className="p-4 border-t border-border">
        <div className="bg-muted/30 rounded-lg p-3 text-xs text-muted-foreground">
          <p className="font-medium text-foreground mb-1">Local Instance</p>
          <p>v0.1.0-alpha</p>
        </div>
      </div>
    </nav>
  );
}
