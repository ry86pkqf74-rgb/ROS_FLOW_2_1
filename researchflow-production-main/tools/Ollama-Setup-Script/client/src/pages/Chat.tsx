import { useState, useEffect, useRef } from "react";
import { useLocation, useRoute } from "wouter";
import { useSessions, useSession, useCreateSession, useCreateMessage } from "@/hooks/use-sessions";
import { useChat, useOllamaModels } from "@/hooks/use-ollama";
import ReactMarkdown from "react-markdown";
import { format } from "date-fns";
import { 
  Send, 
  Plus, 
  Bot, 
  User, 
  MessageSquare, 
  Loader2,
  Trash2,
  MoreVertical 
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

// --- Subcomponents ---

function Sidebar({ 
  currentId, 
  onNewChat 
}: { 
  currentId: number | null, 
  onNewChat: () => void 
}) {
  const { data: sessions, isLoading } = useSessions();
  const [, setLocation] = useLocation();

  return (
    <div className="w-80 border-r border-border h-full flex flex-col bg-card/50">
      <div className="p-4 border-b border-border">
        <Button onClick={onNewChat} className="w-full gap-2 shadow-sm" variant="outline">
          <Plus className="w-4 h-4" /> New Chat
        </Button>
      </div>
      <ScrollArea className="flex-1">
        <div className="p-3 space-y-2">
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-12 bg-muted/50 animate-pulse rounded-lg" />
              ))}
            </div>
          ) : sessions?.length === 0 ? (
            <div className="text-center py-10 text-muted-foreground text-sm">
              No chat history yet.
            </div>
          ) : (
            sessions?.map((session) => (
              <div
                key={session.id}
                onClick={() => setLocation(`/chat/${session.id}`)}
                className={cn(
                  "p-3 rounded-lg cursor-pointer transition-all hover:bg-muted/50 group flex items-start gap-3",
                  currentId === session.id ? "bg-primary/10 hover:bg-primary/15" : "bg-transparent"
                )}
              >
                <MessageSquare className={cn(
                  "w-4 h-4 mt-1 transition-colors",
                  currentId === session.id ? "text-primary" : "text-muted-foreground"
                )} />
                <div className="overflow-hidden">
                  <h4 className={cn(
                    "font-medium text-sm truncate",
                    currentId === session.id ? "text-foreground" : "text-muted-foreground group-hover:text-foreground"
                  )}>
                    {session.title}
                  </h4>
                  <p className="text-xs text-muted-foreground truncate opacity-70">
                    {session.model} • {format(new Date(session.createdAt), 'MMM d, HH:mm')}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

// --- Main Chat Component ---

export default function Chat() {
  const [match, params] = useRoute("/chat/:id?");
  const [, setLocation] = useLocation();
  const sessionId = params?.id ? parseInt(params.id) : null;
  
  // State
  const [input, setInput] = useState("");
  const [selectedModel, setSelectedModel] = useState<string>("");
  const scrollRef = useRef<HTMLDivElement>(null);

  // Queries & Mutations
  const { data: session, isLoading: sessionLoading } = useSession(sessionId || 0);
  const { data: models } = useOllamaModels();
  const createSession = useCreateSession();
  const createMessage = useCreateMessage();
  const chatMutation = useChat();

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [session?.messages, chatMutation.isPending]);

  // If viewing an existing session, sync the model selector
  useEffect(() => {
    if (session) {
      setSelectedModel(session.model);
    } else if (models?.models.length && !selectedModel) {
      setSelectedModel(models.models[0].name); // Default to first available
    }
  }, [session, models]);

  const handleSendMessage = async () => {
    if (!input.trim() || !selectedModel) return;

    let currentSessionId = sessionId;

    // 1. If no session, create one first
    if (!currentSessionId) {
      try {
        const newSession = await createSession.mutateAsync({
          model: selectedModel,
          title: input.slice(0, 30) + (input.length > 30 ? "..." : ""),
        });
        currentSessionId = newSession.id;
        setLocation(`/chat/${newSession.id}`);
      } catch (err) {
        return; // Error handled in hook
      }
    }

    const userContent = input;
    setInput(""); // Clear input early for UX

    try {
      // 2. Save User Message
      await createMessage.mutateAsync({
        sessionId: currentSessionId!,
        role: "user",
        content: userContent,
      });

      // 3. Call Ollama (Assistant)
      // We need chat history. If this is a new session, history is just the new message.
      const history = session?.messages.map(m => ({ 
        role: m.role as "user"|"assistant"|"system", 
        content: m.content 
      })) || [];
      
      history.push({ role: "user", content: userContent });

      const response = await chatMutation.mutateAsync({
        model: selectedModel,
        messages: history,
      });

      // 4. Save Assistant Message
      // Note: In a real app with streaming, we'd save chunks or final text.
      // Here we assume non-streaming response structure from Ollama API wrapper
      const assistantContent = response.message?.content || response.response || ""; // Adjust based on actual API response structure
      
      await createMessage.mutateAsync({
        sessionId: currentSessionId!,
        role: "assistant",
        content: assistantContent,
      });

    } catch (err) {
      console.error("Chat error:", err);
    }
  };

  const handleNewChat = () => {
    setLocation("/chat");
    setSelectedModel(models?.models[0]?.name || "");
    setInput("");
  };

  return (
    <div className="h-screen bg-background pl-64 flex overflow-hidden">
      {/* Sidebar Overlay Fix: The layout is fixed sidebar in App, so we need to account for it. 
          Actually, the Navigation component is fixed left-0 w-64. 
          So this div starts at pl-64.
          BUT we want a secondary sidebar for history. 
          So the total layout: [Nav 64px] [History 80px] [Chat Area Rest]
      */}
      
      {/* Secondary Sidebar for Chat History */}
      <Sidebar currentId={sessionId} onNewChat={handleNewChat} />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full relative bg-background">
        {/* Header */}
        <header className="h-16 border-b border-border flex items-center justify-between px-6 bg-background/80 backdrop-blur z-10">
          <div className="flex items-center gap-3">
            {sessionId ? (
              <div>
                <h2 className="font-semibold text-sm">{session?.title || "Loading..."}</h2>
                <p className="text-xs text-muted-foreground">{session?.model}</p>
              </div>
            ) : (
              <h2 className="font-semibold text-sm">New Conversation</h2>
            )}
          </div>

          <div className="flex items-center gap-2">
            {!sessionId && (
              <Select value={selectedModel} onValueChange={setSelectedModel}>
                <SelectTrigger className="w-[200px] h-9 bg-muted/30 border-border">
                  <SelectValue placeholder="Select a model" />
                </SelectTrigger>
                <SelectContent>
                  {models?.models.map((model) => (
                    <SelectItem key={model.name} value={model.name}>
                      {model.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <MoreVertical className="w-4 h-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem className="text-destructive focus:text-destructive">
                  <Trash2 className="w-4 h-4 mr-2" /> Delete Chat
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* Messages Area */}
        <ScrollArea className="flex-1 px-4 py-6">
          <div className="max-w-3xl mx-auto space-y-6 pb-4">
            {!sessionId && !sessionLoading ? (
              <div className="flex flex-col items-center justify-center h-[50vh] text-center space-y-4 opacity-50">
                <Bot className="w-16 h-16 text-muted-foreground/50" />
                <div>
                  <h3 className="text-lg font-medium">Start a new conversation</h3>
                  <p className="text-sm text-muted-foreground">Select a model and type a message to begin</p>
                </div>
              </div>
            ) : (
              session?.messages.map((msg, idx) => (
                <div 
                  key={msg.id || idx} 
                  className={cn(
                    "flex gap-4 group",
                    msg.role === "user" ? "flex-row-reverse" : "flex-row"
                  )}
                >
                  <div className={cn(
                    "w-8 h-8 rounded-lg flex items-center justify-center shrink-0 shadow-sm mt-1",
                    msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted text-foreground"
                  )}>
                    {msg.role === "user" ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
                  </div>
                  
                  <div className={cn(
                    "max-w-[80%] rounded-2xl px-5 py-3 shadow-sm text-sm leading-relaxed",
                    msg.role === "user" 
                      ? "bg-primary text-primary-foreground rounded-tr-sm" 
                      : "bg-card border border-border rounded-tl-sm"
                  )}>
                    {msg.role === "assistant" ? (
                      <div className="prose prose-neutral dark:prose-invert prose-sm max-w-none">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </div>
                    ) : (
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    )}
                  </div>
                </div>
              ))
            )}

            {chatMutation.isPending && (
              <div className="flex gap-4">
                 <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 shadow-sm bg-muted text-foreground">
                    <Bot className="w-5 h-5" />
                  </div>
                  <div className="bg-card border border-border rounded-2xl rounded-tl-sm px-5 py-4 shadow-sm flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin text-primary" />
                    <span className="text-sm text-muted-foreground">Thinking...</span>
                  </div>
              </div>
            )}
            <div ref={scrollRef} />
          </div>
        </ScrollArea>

        {/* Input Area */}
        <div className="p-4 bg-background border-t border-border">
          <div className="max-w-3xl mx-auto flex gap-3 items-end">
            <div className="relative flex-1">
              <Input
                placeholder="Message..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                className="pr-12 py-6 rounded-xl shadow-sm border-border bg-card focus-visible:ring-primary/20"
                disabled={chatMutation.isPending || (!sessionId && !selectedModel)}
              />
            </div>
            <Button 
              size="icon" 
              className={cn(
                "h-12 w-12 rounded-xl shadow-md transition-all",
                input.trim() ? "bg-primary text-primary-foreground hover:bg-primary/90" : "bg-muted text-muted-foreground hover:bg-muted/80"
              )}
              onClick={handleSendMessage}
              disabled={!input.trim() || chatMutation.isPending}
            >
              <Send className="w-5 h-5" />
            </Button>
          </div>
          <div className="max-w-3xl mx-auto text-center mt-2">
             <p className="text-[10px] text-muted-foreground opacity-60">
               AI responses may be inaccurate. Check important info.
             </p>
          </div>
        </div>
      </div>
    </div>
  );
}
