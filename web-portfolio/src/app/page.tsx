"use client";

import { useEffect, useRef, useState, useCallback, ReactNode } from "react";
import { HandLandmarker, FilesetResolver, Landmark } from "@mediapipe/tasks-vision";
import { Play, Square, MousePointer2, Loader2, MousePointerClick, Move, CheckCircle2, Video, Activity, Zap, Cpu, Settings2, ShieldCheck, Crosshair, Target } from "lucide-react";

type ProgramState = "IDLE" | "RUNNING" | "PAUSED";

export default function Home() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasOverlayRef = useRef<HTMLCanvasElement>(null);
  const requestRef = useRef<number>(null);

  const [isModelLoaded, setIsModelLoaded] = useState(false);
  const [programState, setProgramState] = useState<ProgramState>("IDLE");
  const programStateRef = useRef<ProgramState>("IDLE");
  const [error, setError] = useState<string | null>(null);

  // States for Playground
  const [score, setScore] = useState(0);
  const [clickCount, setClickCount] = useState(0);
  const [hoverBoxStatus, setHoverBoxStatus] = useState<"IDLE" | "HOVERED" | "SUCCESS">("IDLE");
  
  // Refs untuk sinkronisasi state di dalam loop Kamera (yang menghindari stale closure React)
  const hoverBoxStatusRef = useRef<"IDLE" | "HOVERED" | "SUCCESS">("IDLE");
  const hoverTimerRef = useRef<number | undefined>(undefined);

  const [switches, setSwitches] = useState([false, false, false, false]);
  const [scrollTestItems] = useState(Array.from({ length: 30 }).map((_, i) => `Secure Data Log System_${100 + i}`));

  const [activeAction, setActiveAction] = useState<string>("Standby");
  const [activeHandInfo, setActiveHandInfo] = useState<string>("Scanning...");
  const [cursorPos, setCursorPos] = useState({ x: -100, y: -100 });
  const [isClicking, setIsClicking] = useState(false);

  const handLandmarkerRef = useRef<HandLandmarker | null>(null);
  const lastVideoTimeRef = useRef<number>(-1);
  const previousCursorRef = useRef({ x: 0, y: 0 });
  const lastClickTimeRef = useRef<number>(0);
  const lastScrollTimeRef = useRef<number>(0);

  const wsRef = useRef<WebSocket | null>(null);
  const currentlyHoveredElementRef = useRef<Element | null>(null);

  const smooth = (val: number, prev: number, factor: number) => prev + (val - prev) / factor;
  const calculateDistance = (pt1: Landmark, pt2: Landmark) => Math.sqrt(Math.pow(pt2.x - pt1.x, 2) + Math.pow(pt2.y - pt1.y, 2));

  useEffect(() => {
    const connectWS = () => {
      const ws = new WebSocket("ws://localhost:8765");
      ws.onopen = () => console.log("🟢 Connected to Python Mouse Server!");
      ws.onclose = () => setTimeout(connectWS, 4000);
      wsRef.current = ws;
    };
    connectWS();
    return () => { if (wsRef.current) wsRef.current.close(); };
  }, []);

  useEffect(() => {
    const loadModel = async () => {
      try {
        const vision = await FilesetResolver.forVisionTasks("https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm");
        const landmarker = await HandLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath: "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
            delegate: "GPU"
          },
          runningMode: "VIDEO",
          numHands: 1,
        });
        handLandmarkerRef.current = landmarker;
        setIsModelLoaded(true);
      } catch (err: any) {
        setError(`Failed to load AI model: ${err.message}`);
      }
    };
    loadModel();
    return () => {
      if (handLandmarkerRef.current) handLandmarkerRef.current.close();
      if (requestRef.current) cancelAnimationFrame(requestRef.current);
    };
  }, []);

  const simulateHoverDOM = (x: number, y: number) => {
    const el = document.elementFromPoint(x, y);
    if (el !== currentlyHoveredElementRef.current) {
      if (currentlyHoveredElementRef.current) currentlyHoveredElementRef.current.dispatchEvent(new MouseEvent('mouseleave', { bubbles: true }));
      currentlyHoveredElementRef.current = el;
      if (el) el.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
    }
  }

  const simulateScrollDOM = (x: number, y: number, amount: number) => {
    const el = document.elementFromPoint(x, y);
    const scrollParent = el?.closest('.sp-scrollable') as HTMLElement; // sp-scrollable class for allowed areas
    if (scrollParent) {
      scrollParent.scrollBy({ top: amount, behavior: 'instant' });
    } else if (el instanceof HTMLElement) {
      el.scrollBy({ top: amount, behavior: 'instant' });
    }
  }

  const predictWebcam = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasOverlayRef.current;
    const landmarker = handLandmarkerRef.current;

    if (!video || !canvas || !landmarker || programStateRef.current !== "RUNNING") return;
    if (video.videoWidth === 0 || video.videoHeight === 0) {
      if (programStateRef.current === "RUNNING") requestRef.current = requestAnimationFrame(predictWebcam);
      return;
    }

    if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
    }

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let startTimeMs = performance.now();
    if (video.currentTime !== lastVideoTimeRef.current) {
      lastVideoTimeRef.current = video.currentTime;
      const results = landmarker.detectForVideo(video, startTimeMs);
      ctx.clearRect(0, 0, canvas.width, canvas.height); // Camera Overlay clear

      if (results.landmarks && results.landmarks.length > 0) {
        setActiveHandInfo("Tangan Terlacak ✓");
        const landmarks = results.landmarks[0];
        const indexFinger = landmarks[8];
        const thumb = landmarks[4];
        const middleFinger = landmarks[12];

        const rawX = (1 - indexFinger.x) * window.innerWidth;
        const rawY = indexFinger.y * window.innerHeight;

        const smoothedX = smooth(rawX, previousCursorRef.current.x, 3);
        const smoothedY = smooth(rawY, previousCursorRef.current.y, 3);
        previousCursorRef.current = { x: smoothedX, y: smoothedY };
        setCursorPos({ x: smoothedX, y: smoothedY });

        // -- MANUAL Bounding Box Hit-Test untuk MODULE 02 (Hover Stability) --
        const hoverMod = document.getElementById("hover-module");
        if (hoverMod) {
           const rect = hoverMod.getBoundingClientRect();
           const isHovering = smoothedX >= rect.left && smoothedX <= rect.right && smoothedY >= rect.top && smoothedY <= rect.bottom;
           
           if (isHovering && hoverBoxStatusRef.current === "IDLE") {
              setHoverBoxStatus("HOVERED");
              hoverBoxStatusRef.current = "HOVERED";
              hoverTimerRef.current = window.setTimeout(() => {
                 if (hoverBoxStatusRef.current === "HOVERED") {
                    setHoverBoxStatus("SUCCESS");
                    hoverBoxStatusRef.current = "SUCCESS";
                    setScore(s => s + 20);
                 }
              }, 2000);
           } else if (!isHovering && hoverBoxStatusRef.current !== "IDLE") {
              setHoverBoxStatus("IDLE");
              hoverBoxStatusRef.current = "IDLE";
              clearTimeout(hoverTimerRef.current);
           }
        }
        // ---------------------------------------------------------------------

        const pinchDist = calculateDistance(indexFinger, thumb);
        const openDist = calculateDistance(indexFinger, middleFinger);

        if (wsRef.current?.readyState === WebSocket.OPEN) {
          const normX = 1 - indexFinger.x;
          const normY = indexFinger.y;

          if (pinchDist < 0.05) {
            const now = performance.now();
            if (now - lastClickTimeRef.current > 500) {
              wsRef.current.send(JSON.stringify({ action: "click" }));
              lastClickTimeRef.current = now;
            }
          } else if (openDist < 0.05) {
            wsRef.current.send(JSON.stringify({ action: "scroll", amount: -25 })); // Standard desktop scroll value
          } else {
            wsRef.current.send(JSON.stringify({ action: "move", x: normX, y: normY }));
          }
        }

        if (pinchDist < 0.05) {
          setActiveAction("Mencubit (Klik Kiri)");
          setIsClicking(true);

          const now = performance.now();
          if (now - lastClickTimeRef.current > 600) {
            lastClickTimeRef.current = now;
            const targetDom = document.elementFromPoint(smoothedX, smoothedY);
            if (targetDom && targetDom instanceof HTMLElement) targetDom.click();
          }

          ctx.beginPath();
          const cx = indexFinger.x * canvas.width;
          const cy = indexFinger.y * canvas.height;
          ctx.arc(canvas.width - cx, cy, 18, 0, 2 * Math.PI);
          ctx.fillStyle = "rgba(245, 158, 11, 0.4)";
          ctx.fill();

        } else if (openDist < 0.05) {
          setActiveAction("Jari V (Mode Gulir)");
          setIsClicking(false);

          // Simulasi scroll internal saat tidak tersambung ke OS PYTHON (Fallback testing)
          const now = performance.now();
          if (now - lastScrollTimeRef.current > 100) { // Throttle scroll simulation
            lastScrollTimeRef.current = now;
            simulateScrollDOM(smoothedX, smoothedY, 40); // 40px scroll falllback
          }
        } else {
          setActiveAction("Telunjuk Aktif (Gerak)");
          setIsClicking(false);
        }
      } else {
        setActiveActiveHandInfo("Kehilangan Jejak");
        setActiveAction("Standby");
        setIsClicking(false);
      }
    }
    if (programStateRef.current === "RUNNING") requestRef.current = requestAnimationFrame(predictWebcam);
  }, []);

  const setActiveActiveHandInfo = (t: string) => setActiveHandInfo(t);

  const updateProgramState = (newState: ProgramState) => {
    setProgramState(newState);
    programStateRef.current = newState;
  };

  const handleStart = async () => {
    if (!isModelLoaded) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
      updateProgramState("RUNNING");
      setActiveAction("Inisialisasi Sensor...");
      if (requestRef.current) cancelAnimationFrame(requestRef.current);
      requestRef.current = requestAnimationFrame(predictWebcam);
    } catch (err) {
      setError("Akses kamera ditolak.");
    }
  };

  const handleStop = () => {
    updateProgramState("IDLE");
    setActiveAction("Kamera Mati");
    setActiveHandInfo("OFFLINE");
    if (requestRef.current) cancelAnimationFrame(requestRef.current);
    if (videoRef.current && videoRef.current.srcObject) {
      const tracks = (videoRef.current.srcObject as MediaStream).getTracks();
      tracks.forEach(track => track.stop());
      videoRef.current.srcObject = null;
    }
    const ctx = canvasOverlayRef.current?.getContext("2d");
    if (ctx && canvasOverlayRef.current) ctx.clearRect(0, 0, canvasOverlayRef.current.width, canvasOverlayRef.current.height);
  };

  return (
    <main className="h-screen w-screen bg-[#070707] text-white selection:bg-orange-500/30 font-sans flex flex-col md:flex-row overflow-hidden relative">

      {/* GLOWING AMBIENCE BACKDROP */}
      <div className="fixed top-[-10%] left-[-5%] w-[800px] h-[800px] bg-amber-600/10 rounded-full blur-[180px] pointer-events-none z-0" />
      <div className="fixed bottom-[-10%] right-[-5%] w-[800px] h-[800px] bg-orange-700/10 rounded-full blur-[150px] pointer-events-none z-0" />

      {/* SVG VIRTUAL CURSOR (Native DOM Injector Focus) */}
      {programState === "RUNNING" && cursorPos.x > 0 && (
        <div
          className="fixed z-[999] pointer-events-none"
          style={{
            left: `${cursorPos.x}px`, top: `${cursorPos.y}px`,
            transform: `translate(-50%, -50%) ${isClicking ? 'scale(0.85)' : 'scale(1)'}`,
            transition: 'transform 0.1s cubic-bezier(0.4, 0, 0.2, 1)'
          }}
        >
          <div className={`w-10 h-10 rounded-full border border-orange-400 flex items-center justify-center
                          ${isClicking ? 'bg-orange-600 shadow-[0_0_30px_rgba(249,115,22,0.9)]' : 'bg-orange-500/20 shadow-[0_0_15px_rgba(245,158,11,0.5)] backdrop-blur-xl'}`}>
            <div className={`w-2 h-2 rounded-full ${isClicking ? 'bg-white' : 'bg-orange-300'}`} />
          </div>
        </div>
      )}

      {/* =======================================
          SIDEBAR KIRI (CAMERA, SYSTEM STATUS)
          ======================================= */}
      <aside className="w-full md:w-[320px] lg:w-[380px] h-full bg-[#0a0a0a]/80 backdrop-blur-3xl border-r border-orange-900/40 p-5 flex flex-col z-20 overflow-y-auto" style={{ scrollbarWidth: 'none' }}>

        <div className="mb-6 flex items-center gap-3 mt-1">
          <div className="w-8 h-8 rounded bg-gradient-to-br from-amber-500 to-orange-700 flex items-center justify-center p-1.5 shadow-[0_0_15px_rgba(245,158,11,0.4)]"><Cpu className="w-full h-full text-black" /></div>
          <div>
            <h2 className="text-xl font-black tracking-tight leading-none text-white">leafyEyes.</h2>
            <p className="text-[10px] uppercase font-bold text-orange-500 tracking-widest mt-0.5">Virtual cursor</p>
          </div>
        </div>

        {/* SMALL CAMERA MODULE IN TOP LEFT */}
        <div className="bg-[#111] p-[2px] rounded-[1.5rem] border border-orange-500/20 shadow-[0_10px_30px_rgba(0,0,0,0.8)] relative group overflow-hidden mb-6">
          <div className="absolute top-2 right-3 z-30 flex items-center gap-1.5">
            <div className={`w-2 h-2 rounded-full ${programState === "RUNNING" ? 'bg-red-500 animate-pulse' : 'bg-zinc-600'}`} />
            <span className="text-[9px] font-black tracking-widest text-white/70 items-start">REC</span>
            <div className="hidden lg:flex items-center gap-2 bg-black border border-zinc-800 px-4 py-2 rounded-full">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-bold text-zinc-400 tracking-wider">Score: <span className="text-white ml-2">{score} XP</span></span>
            </div>
          </div>

          <div className="aspect-[4/3] bg-black rounded-[1.4rem] overflow-hidden relative flex items-center justify-center">
            {!isModelLoaded && !error && (
              <div className="text-orange-400/50 flex flex-col items-center">
                <Loader2 className="w-6 h-6 animate-spin mb-1" />
                <span className="text-[10px] font-bold">BOOTING...</span>
              </div>
            )}
            {error && <span className="text-xs text-red-500 font-bold p-4 text-center">{error}</span>}

            <video ref={videoRef} playsInline muted
              className={`w-full h-full object-cover transition-opacity duration-500 ${programState === "RUNNING" ? 'opacity-100' : 'opacity-0'}`}
              style={{ transform: 'scaleX(-1)' }} />
            <canvas ref={canvasOverlayRef} className={`absolute inset-0 w-full h-full pointer-events-none z-10 ${programState === "RUNNING" ? 'opacity-100' : 'opacity-0'}`} />
          </div>

          {/* Kamera KONTROL Cuma 2 aja (Mulai/Stop) menempel pada kamera */}
          <div className="flex border-t border-zinc-800">
            <button onClick={handleStart} disabled={!isModelLoaded || programState === "RUNNING"}
              className="flex-1 py-3 text-xs font-bold transition-all disabled:opacity-30 disabled:text-zinc-600 hover:text-orange-400 text-zinc-400 hover:bg-orange-500/10 flex justify-center items-center gap-2">
              <Play className="w-3.5 h-3.5" /> AKTIFKAN
            </button>
            <div className="w-[1px] bg-zinc-800" />
            <button onClick={handleStop} disabled={programState === "IDLE"}
              className="flex-1 py-3 text-xs font-bold transition-all disabled:opacity-30 disabled:text-zinc-600 hover:text-red-400 text-zinc-400 hover:bg-red-500/10 flex justify-center items-center gap-2">
              <Square className="w-3.5 h-3.5" /> MATIKAN
            </button>
          </div>
        </div>

        {/* SENSORS & SYSTEM METRICS LIST */}
        <div className="flex-1 space-y-3">
          <div className="p-3.5 bg-black/50 rounded-xl border border-zinc-800/80 items-center justify-between flex">
            <span className="text-xs font-bold text-zinc-500 uppercase tracking-widest flex gap-2 items-center"><Activity className="w-4 h-4" /> Hand Tracker</span>
            <span className={`text-xs font-black ${activeHandInfo.includes('Terlacak') ? "text-emerald-400" : "text-amber-500"}`}>{activeHandInfo}</span>
          </div>

          <div className="p-3.5 bg-black/50 rounded-xl border border-zinc-800/80 items-center justify-between flex">
            <span className="text-xs font-bold text-zinc-500 uppercase tracking-widest flex gap-2 items-center"><Zap className="w-4 h-4" /> Command Out</span>
            <span className="text-xs font-black text-orange-400">{activeAction}</span>
          </div>
        </div>

        {/* PANDUAN GESTURE MINIMALIS */}
        <div className="mt-8 bg-zinc-900/40 p-4 border border-zinc-800 rounded-2xl">
          <h4 className="text-[11px] font-black text-zinc-400 mb-3 tracking-widest flex items-center gap-2"><Settings2 className="w-3 h-3" /> GESTURE INDEX</h4>
          <div className="space-y-3">
            <div className="flex gap-3">
              <div className="bg-zinc-800 rounded p-1.5 text-zinc-400 shrink-0"><MousePointer2 className="w-3 h-3" /></div>
              <div className="font-medium text-xs text-zinc-300 leading-snug"><span className="text-white font-bold">Gerak Pindah</span> <br /><span className="text-zinc-500">Angkat Jari Telunjuk</span></div>
            </div>
            <div className="flex gap-3">
              <div className="bg-zinc-800 rounded p-1.5 text-zinc-400 shrink-0"><MousePointerClick className="w-3 h-3" /></div>
              <div className="font-medium text-xs text-zinc-300 leading-snug"><span className="text-white font-bold">Kilk/Tekan</span> <br /><span className="text-zinc-500">Cubit Jempol + Telunjuk</span></div>
            </div>
            <div className="flex gap-3">
              <div className="bg-zinc-800 rounded p-1.5 text-zinc-400 shrink-0"><Move className="w-3 h-3" /></div>
              <div className="font-medium text-xs text-zinc-300 leading-snug"><span className="text-white font-bold">Gulir Bawah/Atas</span> <br /><span className="text-zinc-500">Angkat Telunjuk + Tengah (V)</span></div>
            </div>
          </div>
        </div>
      </aside>

      {/* =======================================
          MAIN BOARD KANAN (TESTING SUITE UI/UX)
          ======================================= */}
      <section className="flex-1 h-full px-4 md:px-10 py-8 md:py-10 flex flex-col z-10 overflow-y-auto" style={{ scrollbarWidth: 'none' }}>
        {/* GRID TESTING MODULES */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 flex-1 pb-20">

          {/* 1. CLICK ACCURACY SIMULATOR */}
          <div
            className="bg-black/40 border border-zinc-800 hover:border-orange-500/50 rounded-3xl p-6 transition-all flex flex-col relative overflow-hidden group shadow-2xl cursor-pointer"
            onClick={() => { setClickCount(c => c + 1); setScore(s => s + 5); }}
          >
            <div className="absolute top-0 right-0 p-4 text-zinc-700 group-hover:text-orange-500 transition-colors"><MousePointerClick className="w-8 h-8" /></div>
            <h3 className="text-lg font-bold text-white mb-1 tracking-wide">01 // TARGET KLIK</h3>
            <p className="text-xs text-zinc-500 font-medium max-w-[80%] mb-4">Cubit terus kotak ini dengan telunjuk dan jempol Anda secara persisi untuk menambah skor matriks.</p>

            <div className="mt-auto flex justify-center">
              <div className="relative group-active:scale-95 transition-transform flex items-center justify-center w-full h-28 bg-gradient-to-b from-zinc-900 to-[#0a0a0a] rounded-2xl border border-zinc-800 shadow-inner">
                <span className="absolute -top-3 px-3 py-0.5 bg-orange-600 text-black text-[10px] font-black rounded-full uppercase tracking-widest">Hit Rate</span>
                <span className="text-6xl font-black text-transparent bg-clip-text bg-gradient-to-b from-white to-zinc-600">{clickCount}</span>
              </div>
            </div>
          </div>

          {/* 2. HOVER STABILIZER MODULE */}
          <div
            id="hover-module"
            className={`border rounded-3xl p-6 transition-all flex flex-col relative overflow-hidden shadow-2xl cursor-crosshair
                         ${hoverBoxStatus === "SUCCESS" ? "bg-emerald-950/20 border-emerald-500/50" : hoverBoxStatus === "HOVERED" ? "bg-orange-950/20 border-orange-500/50" : "bg-black/40 border-zinc-800"}`}
          >
            <div className={`absolute top-0 right-0 p-4 transition-colors ${hoverBoxStatus === "SUCCESS" ? 'text-emerald-500' : 'text-zinc-700'}`}><Crosshair className="w-8 h-8" /></div>
            <h3 className="text-lg font-bold text-white mb-1 tracking-wide">02 // STABILITY LOCK</h3>
            <p className="text-xs text-zinc-500 font-medium max-w-[80%] mb-4">Pertahankan letak kursor virtual Anda diam melayang di atas panel ini selama 2.0 detik penuh.</p>

            <div className="mt-auto flex items-center justify-center p-4">
              <div className={`w-28 h-28 rounded-full border-[6px] border-dashed flex items-center justify-center transition-all duration-[2000ms] ease-out
                     ${hoverBoxStatus === "IDLE" ? "border-zinc-800 rotate-0" : hoverBoxStatus === "HOVERED" ? "border-orange-500 rotate-180 scale-110 shadow-[0_0_20px_rgba(245,158,11,0.3)]" : "border-emerald-500 rotate-[360deg] shadow-[0_0_30px_rgba(16,185,129,0.5)]"}
                  `}>
                {hoverBoxStatus === "SUCCESS" ? <CheckCircle2 className="w-10 h-10 text-emerald-400" /> : <Target className={`w-8 h-8 ${hoverBoxStatus === "HOVERED" ? "text-orange-400" : "text-zinc-700"}`} />}
              </div>
            </div>
          </div>

          {/* 3. COMMAND SWITCHES (Toggle Buttons) */}
          <div className="xl:col-span-1 md:col-span-2 bg-black/40 border border-zinc-800 rounded-3xl p-6 transition-all flex flex-col relative shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-1 tracking-wide">03 // SYSTEM TOGGLES</h3>
            <p className="text-xs text-zinc-500 font-medium mb-6">Latih presisi kursor ganda untuk membidik target tombol-tombol kecil (Checkbox).</p>

            <div className="flex flex-col gap-3 mt-auto">
              {switches.map((isActive, index) => (
                <label key={index} className="flex items-center justify-between p-3.5 bg-[#0a0a0a] border border-zinc-800 rounded-xl cursor-pointer hover:border-orange-500/30 transition-colors group">
                  <span className="text-sm font-bold text-zinc-300 group-hover:text-orange-300 transition-colors">Relay Switch #{index + 1}</span>
                  <div className="relative">
                    <input type="checkbox" className="sr-only" onChange={(e) => {
                      const newSwitches = [...switches]; newSwitches[index] = e.target.checked; setSwitches(newSwitches);
                      if (e.target.checked) setScore(s => s + 2);
                    }} />
                    <div className={`block w-10 h-6 border rounded-full transition-colors ${isActive ? 'bg-orange-500 border-orange-500' : 'bg-black border-zinc-600'}`}></div>
                    <div className={`dot absolute left-1 top-1 bg-white w-4 h-4 rounded-full transition-transform ${isActive ? 'translate-x-4' : ''}`}></div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* 4. DRAG / SCROLL TERMINAL AREA */}
          <div className="md:col-span-2 xl:col-span-3 bg-black/60 border border-zinc-800 rounded-3xl p-6 shadow-2xl flex flex-col md:flex-row gap-6 lg:h-64 h-[400px]">
            <div className="md:w-1/3 flex flex-col justify-center">
              <h3 className="text-lg font-bold text-white mb-1 tracking-wide text-orange-500">04 // DATA STREAM (SCROLL)</h3>
              <p className="text-xs text-zinc-400 font-medium mb-4 leading-relaxed tracking-wide">
                Posisikan jari <b>Telunjuk dan Tengah (Terbuka/V)</b> di depan kamera. Saat terdeteksi Mode Scroll, gerakkan kedua jari tersebut naik atau turun di atas area Hitam sebelah kanan untuk melihat log data tergulir sendiri.
              </p>
              <div className="bg-orange-950/30 border border-orange-500/20 px-4 py-3 rounded-lg text-orange-400/80 text-[10px] uppercase font-black tracking-widest text-center mt-auto">
                Arahkan kursor ke dalam panel Scroll -&gt;
              </div>
            </div>

            <div className="md:w-2/3 h-full bg-[#050505] border border-zinc-800 rounded-2xl overflow-hidden relative group">
              <div className="absolute top-0 left-0 right-0 bg-gradient-to-b from-orange-500/20 to-transparent h-6 z-10 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity" />

              {/* Tambahkan sp-scrollable agar fungsi DOM interaktor tahu ini areanya */}
              <div className="w-full h-full overflow-y-auto px-4 py-2 sp-scrollable custom-scroll cursor-ns-resize" style={{ scrollbarWidth: 'thin', scrollbarColor: '#f97316 #111' }}>
                {scrollTestItems.map((logStr, i) => (
                  <div key={i} className="py-2.5 border-b border-zinc-900 flex justify-between items-center group/log hover:bg-zinc-900/40">
                    <span className="font-mono text-[11px] text-zinc-500 group-hover/log:text-orange-400 transition-colors">[{new Date().toISOString()}]</span>
                    <span className="font-mono text-xs font-bold text-zinc-300 tracking-wider group-hover/log:text-white transition-colors">#{logStr}</span>
                    <span className="font-mono text-[10px] text-emerald-500 font-bold opacity-0 group-hover/log:opacity-100 transition-opacity">INSPECT</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

        </div>
      </section>

    </main>
  );
}
