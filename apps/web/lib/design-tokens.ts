// Claustor AI — Single source of truth for colors + styles
import React from "react";

export const C = {
  primary:      "#0066FF",
  primaryHover: "#0052CC",
  primaryLight: "#E6F0FF",
  accent:       "#00A3FF",
  navy:         "#0A1128",
  success:      "#22C55E",
  successLight: "#F0FDF4",
  warning:      "#F59E0B",
  warningLight: "#FFFBEB",
  error:        "#EF4444",
  errorLight:   "#FEF2F2",
  heading:      "#111827",
  body:         "#374151",
  muted:        "#6B7280",
  border:       "#E5E7EB",
  surface:      "#FFFFFF",
  bg:           "#FAFBFC",
};

export const BTN: Record<string, React.CSSProperties> = {
  primary:   {padding:"8px 20px",borderRadius:20,border:"none",fontSize:13,fontWeight:600,cursor:"pointer",background:"#0066FF",color:"white",transition:"all 0.15s"},
  secondary: {padding:"8px 20px",borderRadius:20,border:"1px solid #E5E7EB",fontSize:13,fontWeight:600,cursor:"pointer",background:"transparent",color:"#374151",transition:"all 0.15s"},
  danger:    {padding:"8px 20px",borderRadius:20,border:"none",fontSize:13,fontWeight:600,cursor:"pointer",background:"#EF4444",color:"white",transition:"all 0.15s"},
  ghost:     {padding:"8px 20px",borderRadius:20,border:"1px solid #E6F0FF",fontSize:13,fontWeight:600,cursor:"pointer",background:"#E6F0FF",color:"#0066FF",transition:"all 0.15s"},
};

export const BADGE: Record<string, React.CSSProperties> = {
  primary: {fontSize:11,fontWeight:700,padding:"3px 10px",borderRadius:20,background:"#E6F0FF",color:"#0066FF"},
  success: {fontSize:11,fontWeight:700,padding:"3px 10px",borderRadius:20,background:"#F0FDF4",color:"#22C55E"},
  error:   {fontSize:11,fontWeight:700,padding:"3px 10px",borderRadius:20,background:"#FEF2F2",color:"#EF4444"},
  warning: {fontSize:11,fontWeight:700,padding:"3px 10px",borderRadius:20,background:"#FFFBEB",color:"#F59E0B"},
};

export const CARD: Record<string, React.CSSProperties> = {
  base: {background:"#FFFFFF",border:"1px solid #E5E7EB",borderRadius:12,padding:20},
};
