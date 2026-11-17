import React from "react";
import { createRoot } from "react-dom/client";
import Sandbox from "./Sandbox.jsx";
import "../../../shared/maps-theme.css";

// 브라우저 단독 실행이라 theme.json이 없다 → OS 설정을 따른다
if (window.matchMedia?.("(prefers-color-scheme: dark)").matches) document.documentElement.setAttribute("data-theme", "dark");

createRoot(document.getElementById("root")).render(<Sandbox />);
