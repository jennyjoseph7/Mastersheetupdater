"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import {
  Home,
  Users,
  FileText,
  LinkIcon,
  TrendingUp,
  Bell,
  CreditCard,
  Settings,
  User,
  LogOut,
  Coins,
  Menu,
  Target,
  LayoutDashboard,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import ThemeSwitcher from "@/components/theme-switcher";
import { useEffect, useState } from "react";
import { getDealershipDetails } from "@/lib/api";

export default function TopNavigation() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  // const [dealershipId, setDealershipId] = useState<string | null>(null);

  // useEffect(() => {
  //   const fetchDealershipId = async () => {
  //     if (user) {
  //       try {
  //         const data = await getDealershipDetails();
  //         if (data?.dealership_id) {
  //           setDealershipId(data.dealership_id);
  //         }
  //       } catch (error) {
  //         console.error(
  //           "[TopNavigation] Failed to fetch dealership ID:",
  //           error
  //         );
  //       }
  //     }
  //   };

  //   fetchDealershipId();
  // }, [user]);

  const isActive = (path: string) => {
    return pathname === path;
  };

  const navigationItems = [
    { href: "/", label: "Home", icon: Home },
    { href: "/dealership_summary", label: "Dealership Summary", icon: LayoutDashboard },
    { href: "/audience", label: "Audience", icon: Users },
    { href: "/template", label: "Template", icon: FileText },
    // { href: "/connection", label: "Connection", icon: LinkIcon },
    { href: "/conversions", label: "Conversions", icon: Target },
    { href: "/insights", label: "Live Status", icon: TrendingUp },
  ];

  if (!user) {
    return (
      <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/80 backdrop-blur-xl supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between px-4 md:px-6">
          <Link href="/" className="flex items-center gap-2 group">
            <Image
              src="/images/logo.png"
              alt="DaveAI Logo"
              width={120}
              height={24}
              className="w-auto h-6 transition-transform group-hover:scale-105 "
            />
          </Link>
          <div className="flex items-center gap-3">
            <ThemeSwitcher />
            <Link href="/login">
              <Button
                variant="default"
                size="sm"
                className="font-medium shadow-sm"
              >
                Sign in
              </Button>
            </Link>
          </div>
        </div>
      </header>
    );
  }
  return (
    <>
      <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/80 backdrop-blur-xl supports-[backdrop-filter]:bg-background/60">
        <div className="w-full max-w-[1920px] mx-auto h-16 px-4 md:px-6 flex items-center gap-6 lg:gap-8">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 group shrink-0">
            <Image
              src="/images/logo.png"
              alt="DaveAI Logo"
              width={120}
              height={24}
              className="w-auto h-6 transition-transform group-hover:scale-105 "
            />
          </Link>

          {/* Center Nav */}
          <nav className="hidden lg:flex flex-1 items-center justify-center gap-1">
            {navigationItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200",
                    "hover:bg-accent/80 hover:text-accent-foreground",
                    active
                      ? "bg-primary/10 text-primary shadow-sm"
                      : "text-muted-foreground"
                  )}
                >
                  <Icon className={cn("h-4 w-4", active && "text-primary")} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Right Actions */}
          <div className="flex items-center gap-2 shrink-0 ml-auto">
            {/* Mobile Menu */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild className="lg:hidden">
                <Button variant="ghost" size="icon" className="h-9 w-9">
                  <Menu className="h-5 w-5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-56">
                <DropdownMenuLabel>Navigation</DropdownMenuLabel>
                <DropdownMenuSeparator />
                {navigationItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <DropdownMenuItem key={item.href} asChild>
                      <Link href={item.href} className="flex items-center">
                        <Icon className="mr-2 h-4 w-4" />
                        {item.label}
                      </Link>
                    </DropdownMenuItem>
                  );
                })}
              </DropdownMenuContent>
            </DropdownMenu>

            <ThemeSwitcher />

            <Button
              variant="ghost"
              size="icon"
              className="relative h-9 w-9 hover:bg-accent"
            >
              <Bell className="h-5 w-5" />
              <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-primary ring-2 ring-background animate-pulse" />
            </Button>

            {/* User Menu */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  className="relative h-9 w-9 rounded-full p-0 hover:ring-2 hover:ring-primary/20 transition-all"
                >
                  <Avatar className="h-9 w-9 border-2 border-primary/20">
                    <AvatarImage
                      src={user.avatar || "/placeholder.svg"}
                      alt={user.name}
                    />
                    <AvatarFallback className="bg-primary/10 text-primary font-semibold">
                      {user.name.charAt(0).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="w-64" align="end" forceMount>
                <DropdownMenuLabel className="font-normal">
                  <div className="flex flex-col space-y-2 py-2">
                    <p className="text-sm font-semibold leading-none">
                      {user.name}
                    </p>
                    <p className="text-xs leading-none text-muted-foreground">
{user.dealershipId || user.email}

                    </p>
                    <Badge variant="secondary" className="w-fit mt-1">
                      <Coins className="mr-1 h-3 w-3" />
                      {user.credits.toLocaleString()} Credits
                    </Badge>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link
                    href="/profile"
                    className="flex items-center cursor-pointer"
                  >
                    <User className="mr-2 h-4 w-4" />
                    Profile
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link
                    href="/billing"
                    className="flex items-center cursor-pointer"
                  >
                    <CreditCard className="mr-2 h-4 w-4" />
                    Billing & Usage
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link
                    href="/account"
                    className="flex items-center cursor-pointer"
                  >
                    <Settings className="mr-2 h-4 w-4" />
                    Settings
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={logout}
                  className="cursor-pointer text-destructive focus:text-destructive"
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>
    </>
  );
}
