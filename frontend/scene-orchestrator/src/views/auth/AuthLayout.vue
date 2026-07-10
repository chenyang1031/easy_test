<template>
  <div class="auth-layout">
    <!-- ========== 科技感背景层 ========== -->
    <div class="auth-bg">
      <!-- 1. 动态极光基底 -->
      <div class="bg-aurora"></div>

      <!-- 2. 3D 透视网格地板 -->
      <div class="bg-grid-floor"></div>

      <!-- 3. 浮动光晕 -->
      <div class="bg-glow bg-glow-1"></div>
      <div class="bg-glow bg-glow-2"></div>
      <div class="bg-glow bg-glow-3"></div>

      <!-- 4. 几何线框装饰 (六边形/菱形/三角) -->
      <div class="bg-shapes">
        <div class="geo geo-hex"></div>
        <div class="geo geo-diamond"></div>
        <div class="geo geo-triangle"></div>
      </div>

      <!-- 5. 扫描光带 (多层, 不同速度) -->
      <div class="bg-scanner bg-scanner-1"></div>
      <div class="bg-scanner bg-scanner-2"></div>
      <div class="bg-scanner bg-scanner-3"></div>

      <!-- 6. HUD 边角装饰 -->
      <div class="hud-corner hud-corner-tl"></div>
      <div class="hud-corner hud-corner-tr"></div>
      <div class="hud-corner hud-corner-bl"></div>
      <div class="hud-corner hud-corner-br"></div>

      <!-- 7. 边缘辉光线 -->
      <div class="bg-edge-line bg-edge-line-top"></div>
      <div class="bg-edge-line bg-edge-line-bottom"></div>

      <!-- 8. 浮游粒子群 (大颗可见) -->
      <div class="bg-particles" aria-hidden="true"></div>
      <div class="bg-particles bg-particles-fast" aria-hidden="true"></div>

      <!-- 9. CRT 扫描线纹理 -->
      <div class="bg-crt"></div>
    </div>

    <!-- ========== 主体内容 ========== -->
    <div class="auth-container">
      <!-- 品牌标识 -->
      <div class="auth-brand">
        <svg class="brand-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="32" height="32">
          <rect x="3" y="3" width="7" height="7" rx="1" />
          <rect x="14" y="3" width="7" height="7" rx="1" />
          <rect x="3" y="14" width="7" height="7" rx="1" />
          <rect x="14" y="14" width="7" height="7" rx="1" />
        </svg>
        <span class="brand-text">EasyTesting</span>
      </div>

      <!-- 卡片 -->
      <div class="auth-card">
        <div class="auth-card-inner">
          <router-view v-slot="{ Component }">
            <transition name="auth-fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </div>
      </div>

      <!-- 页脚 -->
      <div class="auth-footer">
        <span>&copy; 2024 EasyTesting. All rights reserved.</span>
      </div>
    </div>
  </div>
</template>

<script setup>
// AuthLayout — 空白布局，无侧栏/顶栏
// 用于登录、注册、密码重置等未认证页面
</script>

<style scoped>
/* ===================================================================
   布局容器
   =================================================================== */
.auth-layout {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  font-family: var(--font-body, 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif);
  background: #080C16;
}

/* ===================================================================
   背景层 — 9 层叠加
   =================================================================== */
.auth-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

/* ---------- 1. 动态极光基底 ---------- */
.bg-aurora {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 90% 50% at 10% 20%, rgba(59, 130, 246, 0.12) 0%, transparent 60%),
    radial-gradient(ellipse 70% 40% at 90% 30%, rgba(139, 92, 246, 0.10) 0%, transparent 50%),
    radial-gradient(ellipse 60% 30% at 50% 80%, rgba(6, 182, 212, 0.08) 0%, transparent 50%),
    radial-gradient(ellipse 50% 25% at 30% 50%, rgba(236, 72, 153, 0.04) 0%, transparent 40%),
    linear-gradient(180deg, #080C16 0%, #0D1525 25%, #111D33 50%, #0D1525 75%, #080C16 100%);
  animation: auroraShift 20s ease-in-out infinite alternate;
}

@keyframes auroraShift {
  0%   { filter: hue-rotate(-5deg) saturate(0.8); }
  50%  { filter: hue-rotate(3deg) saturate(1.1); }
  100% { filter: hue-rotate(-3deg) saturate(0.9); }
}

/* ---------- 2. 3D 透视网格地板 ---------- */
.bg-grid-floor {
  position: absolute;
  left: -15%;
  right: -15%;
  bottom: -10%;
  height: 65%;
  background-image:
    /* 横向网格线 */
    repeating-linear-gradient(
      90deg,
      transparent 0px,
      rgba(59, 130, 246, 0.035) 1px,
      transparent 2px,
      transparent 48px
    ),
    /* 纵向网格线 */
    repeating-linear-gradient(
      0deg,
      transparent 0px,
      rgba(59, 130, 246, 0.035) 1px,
      transparent 2px,
      transparent 48px
    );
  background-size: 96px 96px;
  transform: perspective(500px) rotateX(65deg);
  transform-origin: center bottom;
  mask-image: linear-gradient(to top, black 15%, transparent 75%);
  -webkit-mask-image: linear-gradient(to top, black 15%, transparent 75%);
  animation: gridPulse 4s ease-in-out infinite alternate;
}

@keyframes gridPulse {
  0%   { opacity: 0.6; }
  100% { opacity: 1; }
}

/* ---------- 3. 浮动光晕 ---------- */
.bg-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  will-change: transform, opacity;
  mix-blend-mode: screen;
}

.bg-glow-1 {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.30) 0%, transparent 70%);
  top: -20%;
  left: -5%;
  animation: glowOrbit1 30s ease-in-out infinite;
}

.bg-glow-2 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.25) 0%, transparent 70%);
  bottom: -25%;
  right: -10%;
  animation: glowOrbit2 26s ease-in-out infinite;
}

.bg-glow-3 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(6, 182, 212, 0.20) 0%, transparent 70%);
  top: 15%;
  left: 55%;
  animation: glowOrbit3 22s ease-in-out infinite;
}

@keyframes glowOrbit1 {
  0%, 100% { transform: translate(0, 0) scale(1); opacity: 0.5; }
  20%      { transform: translate(120px, 80px) scale(1.2); opacity: 0.8; }
  40%      { transform: translate(60px, 160px) scale(0.9); opacity: 0.4; }
  60%      { transform: translate(-80px, 100px) scale(1.15); opacity: 0.7; }
  80%      { transform: translate(-40px, 20px) scale(0.95); opacity: 0.6; }
}

@keyframes glowOrbit2 {
  0%, 100% { transform: translate(0, 0) scale(1); opacity: 0.4; }
  25%      { transform: translate(-100px, -60px) scale(1.3); opacity: 0.7; }
  50%      { transform: translate(-160px, 50px) scale(0.85); opacity: 0.3; }
  75%      { transform: translate(-40px, 120px) scale(1.1); opacity: 0.6; }
}

@keyframes glowOrbit3 {
  0%, 100% { transform: translate(0, 0) scale(1); opacity: 0.4; }
  33%      { transform: translate(80px, -100px) scale(1.25); opacity: 0.7; }
  66%      { transform: translate(-60px, 30px) scale(0.8); opacity: 0.3; }
}

/* ---------- 4. 几何线框装饰 ---------- */
.bg-shapes {
  position: absolute;
  inset: 0;
}

.geo {
  position: absolute;
  border: 1px solid rgba(59, 130, 246, 0.06);
  will-change: transform;
}

/* 六边形 */
.geo-hex {
  width: 180px;
  height: 200px;
  top: 12%;
  right: 8%;
  clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
  animation: geoFloat1 35s ease-in-out infinite;
}
.geo-hex::after {
  content: '';
  position: absolute;
  inset: 15%;
  border: 1px solid rgba(139, 92, 246, 0.05);
  clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
}

/* 菱形 */
.geo-diamond {
  width: 140px;
  height: 140px;
  bottom: 15%;
  left: 6%;
  transform-origin: center;
  clip-path: polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%);
  animation: geoFloat2 40s ease-in-out infinite;
  border-color: rgba(6, 182, 212, 0.07);
}

/* 三角形 */
.geo-triangle {
  width: 120px;
  height: 110px;
  top: 35%;
  left: 20%;
  clip-path: polygon(50% 0%, 100% 100%, 0% 100%);
  animation: geoFloat3 30s ease-in-out infinite;
  border-color: rgba(236, 72, 153, 0.06);
}

@keyframes geoFloat1 {
  0%, 100% { transform: translateY(0) rotate(0deg) scale(1); opacity: 0.4; }
  25%      { transform: translateY(-30px) rotate(90deg) scale(1.1); opacity: 0.7; }
  50%      { transform: translateY(20px) rotate(180deg) scale(0.9); opacity: 0.3; }
  75%      { transform: translateY(-15px) rotate(270deg) scale(1.05); opacity: 0.6; }
}

@keyframes geoFloat2 {
  0%, 100% { transform: translateY(0) rotate(0deg); opacity: 0.3; }
  33%      { transform: translateY(25px) rotate(120deg); opacity: 0.6; }
  66%      { transform: translateY(-20px) rotate(240deg); opacity: 0.4; }
}

@keyframes geoFloat3 {
  0%, 100% { transform: translateY(0) scale(1); opacity: 0.3; }
  50%      { transform: translateY(-35px) scale(1.15); opacity: 0.6; }
}

/* ---------- 5. 扫描光带 ---------- */
.bg-scanner {
  position: absolute;
  left: 0;
  right: 0;
  height: 2px;
  border-radius: 1px;
  will-change: transform;
}

.bg-scanner-1 {
  background: linear-gradient(90deg, transparent 0%, rgba(59, 130, 246, 0.15) 30%, rgba(59, 130, 246, 0.25) 50%, rgba(59, 130, 246, 0.15) 70%, transparent 100%);
  animation: scannerSweep1 8s ease-in-out infinite;
  filter: blur(1px);
}

.bg-scanner-2 {
  background: linear-gradient(90deg, transparent 0%, rgba(139, 92, 246, 0.10) 40%, rgba(139, 92, 246, 0.20) 50%, rgba(139, 92, 246, 0.10) 60%, transparent 100%);
  animation: scannerSweep2 11s ease-in-out infinite;
  height: 1.5px;
  filter: blur(2px);
}

.bg-scanner-3 {
  background: linear-gradient(90deg, transparent 0%, rgba(6, 182, 212, 0.08) 35%, rgba(6, 182, 212, 0.18) 50%, rgba(6, 182, 212, 0.08) 65%, transparent 100%);
  animation: scannerSweep3 14s ease-in-out infinite;
  height: 1px;
  filter: blur(3px);
}

@keyframes scannerSweep1 {
  0%, 100% { transform: translateY(10vh); opacity: 0; }
  10%      { opacity: 1; }
  50%      { transform: translateY(85vh); opacity: 1; }
  60%      { opacity: 0; }
}

@keyframes scannerSweep2 {
  0%, 100% { transform: translateY(85vh); opacity: 0; }
  15%      { opacity: 0; }
  30%      { transform: translateY(20vh); opacity: 0.8; }
  70%      { transform: translateY(70vh); opacity: 0.8; }
  85%      { opacity: 0; }
}

@keyframes scannerSweep3 {
  0%, 100% { transform: translateY(50vh); opacity: 0; }
  20%      { opacity: 0; }
  35%      { transform: translateY(15vh); opacity: 0.6; }
  65%      { transform: translateY(60vh); opacity: 0.6; }
  80%      { opacity: 0; }
}

/* ---------- 6. HUD 边角装饰 ---------- */
.hud-corner {
  position: absolute;
  width: 40px;
  height: 40px;
  z-index: 1;
}

.hud-corner-tl {
  top: 24px;
  left: 24px;
  border-top: 1px solid rgba(59, 130, 246, 0.10);
  border-left: 1px solid rgba(59, 130, 246, 0.10);
}

.hud-corner-tr {
  top: 24px;
  right: 24px;
  border-top: 1px solid rgba(139, 92, 246, 0.10);
  border-right: 1px solid rgba(139, 92, 246, 0.10);
}

.hud-corner-bl {
  bottom: 24px;
  left: 24px;
  border-bottom: 1px solid rgba(6, 182, 212, 0.10);
  border-left: 1px solid rgba(6, 182, 212, 0.10);
}

.hud-corner-br {
  bottom: 24px;
  right: 24px;
  border-bottom: 1px solid rgba(236, 72, 153, 0.10);
  border-right: 1px solid rgba(236, 72, 153, 0.10);
}

/* HUD 角标 - 每个拐角加个小光点 */
.hud-corner::before {
  content: '';
  position: absolute;
  width: 3px;
  height: 3px;
  border-radius: 50%;
  box-shadow: 0 0 6px currentColor;
}

.hud-corner-tl::before { bottom: -1px; right: -1px; color: rgba(59, 130, 246, 0.4); background: rgba(59, 130, 246, 0.4); }
.hud-corner-tr::before { bottom: -1px; left: -1px; color: rgba(139, 92, 246, 0.4); background: rgba(139, 92, 246, 0.4); }
.hud-corner-bl::before { top: -1px; right: -1px; color: rgba(6, 182, 212, 0.4); background: rgba(6, 182, 212, 0.4); }
.hud-corner-br::before { top: -1px; left: -1px; color: rgba(236, 72, 153, 0.4); background: rgba(236, 72, 153, 0.4); }

/* ---------- 7. 边缘辉光线 ---------- */
.bg-edge-line {
  position: absolute;
}

.bg-edge-line-top {
  top: 0;
  left: 10%;
  right: 10%;
  height: 1px;
  background: linear-gradient(90deg, transparent 0%, rgba(59, 130, 246, 0.10) 30%, rgba(139, 92, 246, 0.12) 50%, rgba(59, 130, 246, 0.10) 70%, transparent 100%);
  animation: edgeGlow 3s ease-in-out infinite alternate;
}

.bg-edge-line-bottom {
  bottom: 0;
  left: 15%;
  right: 15%;
  height: 1px;
  background: linear-gradient(90deg, transparent 0%, rgba(6, 182, 212, 0.08) 30%, rgba(59, 130, 246, 0.10) 50%, rgba(6, 182, 212, 0.08) 70%, transparent 100%);
  animation: edgeGlow 4s ease-in-out infinite alternate-reverse;
}

@keyframes edgeGlow {
  0%   { opacity: 0.3; transform: scaleX(0.95); }
  100% { opacity: 1; transform: scaleX(1.05); }
}

/* ---------- 8. 浮游粒子群 (大颗可见) ---------- */
.bg-particles {
  position: absolute;
  inset: 0;
}

/* 粒子层 1 — 白色光点, 慢速 */
.bg-particles::before {
  content: '';
  position: absolute;
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
  background-repeat: no-repeat;
  background-size: 5px 5px, 4px 4px, 6px 6px, 4px 4px, 5px 5px,
                    3px 3px, 5px 5px, 4px 4px, 6px 6px, 3px 3px,
                    4px 4px, 5px 5px, 3px 3px, 6px 6px, 4px 4px;
  background-image:
    radial-gradient(circle, rgba(255,255,255,0.50) 0%, transparent 70%),
    radial-gradient(circle, rgba(255,255,255,0.35) 0%, transparent 70%),
    radial-gradient(circle, rgba(255,255,255,0.60) 0%, transparent 70%),
    radial-gradient(circle, rgba(255,255,255,0.30) 0%, transparent 70%),
    radial-gradient(circle, rgba(255,255,255,0.45) 0%, transparent 70%),
    radial-gradient(circle, rgba(255,255,255,0.25) 0%, transparent 70%),
    radial-gradient(circle, rgba(255,255,255,0.55) 0%, transparent 70%),
    radial-gradient(circle, rgba(255,255,255,0.35) 0%, transparent 70%),
    radial-gradient(circle, rgba(255,255,255,0.50) 0%, transparent 70%),
    radial-gradient(circle, rgba(255,255,255,0.30) 0%, transparent 70%),
    radial-gradient(circle, rgba(59, 130, 246, 0.40) 0%, transparent 70%),
    radial-gradient(circle, rgba(139, 92, 246, 0.35) 0%, transparent 70%),
    radial-gradient(circle, rgba(6, 182, 212, 0.40) 0%, transparent 70%),
    radial-gradient(circle, rgba(255,255,255,0.45) 0%, transparent 70%),
    radial-gradient(circle, rgba(236, 72, 153, 0.30) 0%, transparent 70%);
  background-position:
    8% 15%, 22% 35%, 35% 8%, 50% 22%, 65% 12%,
    78% 38%, 12% 68%, 28% 82%, 42% 52%, 58% 75%,
    72% 85%, 88% 58%, 5% 85%, 52% 42%, 82% 22%;
  animation: particleDrift1 35s ease-in-out infinite;
  filter: blur(0.5px);
}

/* 粒子层 2 — 快速小颗粒 */
.bg-particles-fast::after {
  content: '';
  position: absolute;
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
  background-repeat: no-repeat;
  background-size: 3px 3px, 2px 2px, 3px 3px, 2px 2px, 3px 3px,
                    2px 2px, 3px 3px, 2px 2px, 3px 3px, 2px 2px,
                    3px 3px, 2px 2px, 3px 3px, 2px 2px, 3px 3px;
  background-image:
    radial-gradient(circle, rgba(255,255,255,0.30) 0%, transparent 70%),
    radial-gradient(circle, rgba(59, 130, 246, 0.25) 0%, transparent 70%),
    radial-gradient(circle, rgba(255,255,255,0.35) 0%, transparent 70%),
    radial-gradient(circle, rgba(139, 92, 246, 0.20) 0%, transparent 70%),
    radial-gradient(circle, rgba(255,255,255,0.25) 0%, transparent 70%),
    radial-gradient(circle, rgba(6, 182, 212, 0.20) 0%, transparent 70%),
    radial-gradient(circle, rgba(255,255,255,0.30) 0%, transparent 70%),
    radial-gradient(circle, rgba(59, 130, 246, 0.25) 0%, transparent 70%),
    radial-gradient(circle, rgba(255,255,255,0.20) 0%, transparent 70%),
    radial-gradient(circle, rgba(139, 92, 246, 0.30) 0%, transparent 70%),
    radial-gradient(circle, rgba(255,255,255,0.25) 0%, transparent 70%),
    radial-gradient(circle, rgba(6, 182, 212, 0.25) 0%, transparent 70%),
    radial-gradient(circle, rgba(255,255,255,0.30) 0%, transparent 70%),
    radial-gradient(circle, rgba(59, 130, 246, 0.20) 0%, transparent 70%),
    radial-gradient(circle, rgba(236, 72, 153, 0.20) 0%, transparent 70%);
  background-position:
    3% 22%, 16% 45%, 28% 12%, 42% 32%, 55% 8%,
    68% 28%, 8% 72%, 22% 88%, 35% 62%, 52% 78%,
    65% 90%, 82% 52%, 12% 92%, 38% 78%, 75% 18%;
  animation: particleDrift2 18s ease-in-out infinite;
}

@keyframes particleDrift1 {
  0%, 100% { transform: translate(0, 0); opacity: 0.5; }
  20%      { transform: translate(25px, -40px); opacity: 0.8; }
  40%      { transform: translate(-15px, -70px); opacity: 0.4; }
  60%      { transform: translate(30px, -30px); opacity: 0.7; }
  80%      { transform: translate(-20px, -50px); opacity: 0.6; }
}

@keyframes particleDrift2 {
  0%, 100% { transform: translate(0, 0); opacity: 0.3; }
  25%      { transform: translate(-18px, -35px); opacity: 0.6; }
  50%      { transform: translate(12px, -55px); opacity: 0.2; }
  75%      { transform: translate(-25px, -20px); opacity: 0.5; }
}

/* ---------- 9. CRT 扫描线纹理 ---------- */
.bg-crt {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(255, 255, 255, 0.012) 2.5px,
    rgba(255, 255, 255, 0.012) 3px
  );
  animation: crtScroll 10s linear infinite;
}

@keyframes crtScroll {
  0%   { background-position: 0 0; }
  100% { background-position: 0 6px; }
}

/* ===================================================================
   主容器
   =================================================================== */
.auth-container {
  position: relative;
  z-index: 2;
  width: 100%;
  max-width: 440px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 28px;
}

/* ===================================================================
   品牌标识
   =================================================================== */
.auth-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #fff;
  user-select: none;
  position: relative;
  padding-bottom: 12px;
}

.auth-brand::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 60px;
  height: 1.5px;
  background: linear-gradient(90deg, transparent 0%, rgba(59, 130, 246, 0.5) 50%, transparent 100%);
  border-radius: 1px;
}

.brand-icon {
  color: var(--secondary-color, #3B82F6);
  flex-shrink: 0;
  filter: drop-shadow(0 0 10px rgba(59, 130, 246, 0.35));
}

.brand-text {
  font-size: 1.6rem;
  font-weight: 700;
  font-family: var(--font-heading, 'Fira Code', Consolas, monospace);
  letter-spacing: -0.5px;
  background: linear-gradient(135deg, #E2E8F0 20%, #60A5FA 80%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* ===================================================================
   卡片 — 浅色玻璃面板（与主应用风格一致）
   =================================================================== */
.auth-card {
  width: 100%;
  position: relative;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 16px;
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.08),
    0 10px 30px -5px rgba(0, 0, 0, 0.12),
    0 0 0 1px rgba(255, 255, 255, 0.06),
    0 0 60px rgba(59, 130, 246, 0.04);
  overflow: hidden;
  transition: box-shadow 0.3s ease;
}

.auth-card:hover {
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.08),
    0 15px 40px -5px rgba(0, 0, 0, 0.18),
    0 0 0 1px rgba(255, 255, 255, 0.08),
    0 0 80px rgba(59, 130, 246, 0.06);
}

.auth-card-inner {
  padding: 40px 36px 36px;
}

/* ===================================================================
   页脚
   =================================================================== */
.auth-footer {
  color: rgba(255, 255, 255, 0.35);
  font-size: 0.8rem;
  text-align: center;
  letter-spacing: 0.3px;
}

/* ===================================================================
   过渡动画
   =================================================================== */
.auth-fade-enter-active,
.auth-fade-leave-active {
  transition: opacity 0.25s ease, transform 0.2s ease;
}
.auth-fade-enter-from {
  opacity: 0;
  transform: translateY(12px);
}
.auth-fade-leave-to {
  opacity: 0;
  transform: translateY(-12px);
}

/* ===================================================================
   响应式
   =================================================================== */
@media (max-width: 480px) {
  .auth-card-inner { padding: 28px 20px 24px; }
  .brand-text { font-size: 1.3rem; }
  .auth-container { padding: 16px; }
  .hud-corner { display: none; }
}

@media (max-width: 768px) {
  .bg-glow-1 { width: 300px; height: 300px; }
  .bg-glow-2 { width: 250px; height: 250px; }
  .bg-glow-3 { width: 200px; height: 200px; }
  .geo-hex { width: 100px; height: 110px; }
  .geo-diamond { width: 80px; height: 80px; }
  .geo-triangle { width: 70px; height: 65px; }
}
</style>
