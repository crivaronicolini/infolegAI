import * as React from "react"
import { cn } from "@/lib/utils"

const SIDEBAR_WIDTH = "16rem"
const SIDEBAR_WIDTH_COLLAPSED = "0rem"

type SidebarContextValue = {
  open: boolean
  setOpen: (open: boolean) => void
  toggle: () => void
}

const SidebarContext = React.createContext<SidebarContextValue>({
  open: true,
  setOpen: () => {},
  toggle: () => {},
})

export function useSidebar() {
  return React.useContext(SidebarContext)
}

export type SidebarProviderProps = {
  defaultOpen?: boolean
  children: React.ReactNode
}

function SidebarProvider({ defaultOpen = true, children }: SidebarProviderProps) {
  const [open, setOpen] = React.useState(defaultOpen)
  const toggle = React.useCallback(() => setOpen((prev) => !prev), [])

  return (
    <SidebarContext.Provider value={{ open, setOpen, toggle }}>
      <div className="flex h-screen w-full">{children}</div>
    </SidebarContext.Provider>
  )
}

export type SidebarProps = {
  children: React.ReactNode
  className?: string
} & React.HTMLAttributes<HTMLElement>

function Sidebar({ children, className, ...props }: SidebarProps) {
  const { open } = useSidebar()

  return (
    <aside
      className={cn(
        "bg-card border-border flex shrink-0 flex-col border-r transition-[width] duration-200",
        className
      )}
      style={{ width: open ? SIDEBAR_WIDTH : SIDEBAR_WIDTH_COLLAPSED }}
      {...props}
    >
      {open && children}
    </aside>
  )
}

export type SidebarHeaderProps = {
  children: React.ReactNode
  className?: string
} & React.HTMLAttributes<HTMLDivElement>

function SidebarHeader({ children, className, ...props }: SidebarHeaderProps) {
  return (
    <div className={cn("flex flex-col gap-2 p-4", className)} {...props}>
      {children}
    </div>
  )
}

export type SidebarContentProps = {
  children: React.ReactNode
  className?: string
} & React.HTMLAttributes<HTMLDivElement>

function SidebarContent({ children, className, ...props }: SidebarContentProps) {
  return (
    <div className={cn("flex-1 overflow-y-auto", className)} {...props}>
      {children}
    </div>
  )
}

export type SidebarGroupProps = {
  children: React.ReactNode
  className?: string
} & React.HTMLAttributes<HTMLDivElement>

function SidebarGroup({ children, className, ...props }: SidebarGroupProps) {
  return (
    <div className={cn("px-2 py-2", className)} {...props}>
      {children}
    </div>
  )
}

export type SidebarGroupLabelProps = {
  children: React.ReactNode
  className?: string
} & React.HTMLAttributes<HTMLDivElement>

function SidebarGroupLabel({ children, className, ...props }: SidebarGroupLabelProps) {
  return (
    <div
      className={cn("text-muted-foreground px-2 py-1.5 text-xs font-medium", className)}
      {...props}
    >
      {children}
    </div>
  )
}

export type SidebarMenuProps = {
  children: React.ReactNode
  className?: string
} & React.HTMLAttributes<HTMLUListElement>

function SidebarMenu({ children, className, ...props }: SidebarMenuProps) {
  return (
    <ul className={cn("flex flex-col gap-0.5", className)} {...props}>
      {children}
    </ul>
  )
}

export type SidebarMenuItemProps = {
  children: React.ReactNode
  className?: string
} & React.HTMLAttributes<HTMLLIElement>

function SidebarMenuItem({ children, className, ...props }: SidebarMenuItemProps) {
  return (
    <li className={cn("", className)} {...props}>
      {children}
    </li>
  )
}

export type SidebarMenuButtonProps = {
  children: React.ReactNode
  className?: string
  isActive?: boolean
} & React.ButtonHTMLAttributes<HTMLButtonElement>

function SidebarMenuButton({ children, className, isActive, ...props }: SidebarMenuButtonProps) {
  return (
    <button
      className={cn(
        "hover:bg-accent flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors",
        isActive && "bg-accent",
        className
      )}
      {...props}
    >
      {children}
    </button>
  )
}

export type SidebarInsetProps = {
  children: React.ReactNode
  className?: string
} & React.HTMLAttributes<HTMLDivElement>

function SidebarInset({ children, className, ...props }: SidebarInsetProps) {
  return (
    <div className={cn("flex flex-1 flex-col overflow-hidden", className)} {...props}>
      {children}
    </div>
  )
}

export type SidebarTriggerProps = {
  className?: string
} & React.ButtonHTMLAttributes<HTMLButtonElement>

function SidebarTrigger({ className, ...props }: SidebarTriggerProps) {
  const { toggle, open } = useSidebar()

  return (
    <button
      onClick={toggle}
      className={cn(
        "hover:bg-accent inline-flex h-9 w-9 items-center justify-center rounded-md text-sm font-medium transition-colors",
        className
      )}
      {...props}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={cn("transition-transform", !open && "rotate-180")}
      >
        <rect width="18" height="18" x="3" y="3" rx="2" />
        <path d="M9 3v18" />
      </svg>
    </button>
  )
}

export {
  SidebarProvider,
  Sidebar,
  SidebarHeader,
  SidebarContent,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarInset,
  SidebarTrigger,
}
