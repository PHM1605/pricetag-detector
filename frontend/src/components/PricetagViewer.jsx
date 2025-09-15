import { useEffect, useRef, useState } from "react"
import axios from "axios";
import {FontAwesomeIcon} from "@fortawesome/react-fontawesome"
import { faChevronLeft, faChevronRight } from "@fortawesome/free-solid-svg-icons";

const BACKEND = "http://localhost:8000"

const CANVAS_SIZES = [
  {max:800, width:640, height:360}, // phones/tiny tablets
  {max:1200, width:800, height:450}, // small laptops 
  {max:1600, width:1024, height:576}, // mid-size screens
  {max:Infinity, width:1280, height:720} // large monitors
]

const {width:canvasWidth, height:canvasHeight} = CANVAS_SIZES.find(s=>window.innerWidth<=s.max);

const renderReadItem = (s, idx) => {
  const prefix = "debug_crop: ";
  if (typeof s === "string" && s.startsWith(prefix)) {
    const path = s.slice(prefix.length); // e.g. "/static/crops/IMG_001_box3.png"
    const href = `${BACKEND}${path}`; 
    return (
      <li key={idx}>
        <a href={href} target="_blank" rel="noreferrer" className="text-blue-600 underline">
          Open debug crop
        </a>
      </li>
    )
  }
  return <li key={idx}>{String(s)}</li>
}

export default function PricetagViewer() {
  const [images, setImages] = useState([]);
  const [current, setCurrent] = useState(0);
  const [boxes, setBoxes] = useState([]);
  const [results, setResults] = useState([]) // [{box_id,...}]

  const imgRef = useRef(null);
  const canvasRef = useRef(null);
  const currentImage = images[current] || null;
  const baseName = currentImage ? currentImage.substring(0, currentImage.lastIndexOf('.')) : null;
  const drawRef = useRef({scale:1, ox:0, oy:0, imgW:0, imgH:0});

  const drawBoxes = () => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const {scale, offsetX, offsetY, imgW, imgH} = drawRef.current;
    ctx.lineWidth = 2;
    
    boxes.forEach(box => {
      const [xn, yn, wn, hn] = box.box;
      // convert to image pixel coords
      const wImg = wn * imgW;
      const hImg = hn * imgH;
      const xImg = xn * imgW - wImg / 2;
      const yImg = yn * imgH - hImg / 2;
      // convert to canvas coordinates
      const x = offsetX + xImg*scale;
      const y = offsetY + yImg*scale;
      const w = wImg * scale;
      const h = hImg * scale;

      // choose color: green if pricetag analyzed, red otherwise
      const hasResult = results.some(res => res.box_id === box.id)
      ctx.strokeStyle = hasResult ? "limegreen" : "red";
      ctx.strokeRect(x, y, w, h);
    })
  }

  const drawCurrentImage = () => {
    const img = imgRef.current;
    if (!img) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    // scale image to fit canvas when ZOOM/PAN not yet applied
    const scale = Math.min(canvas.width/img.width, canvas.height/img.height);
    const drawWidth = img.width * scale;
    const drawHeight = img.height * scale;
    const baseOffsetX = (canvas.width-drawWidth) / 2;
    const baseOffsetY = (canvas.height-drawHeight) / 2;
    
    drawRef.current = {
      scale,
      offsetX: baseOffsetX,
      offsetY: baseOffsetY,
      imgW: img.width,
      imgH: img.height
    };

    ctx.drawImage(img, baseOffsetX, baseOffsetY, drawWidth, drawHeight);
    drawBoxes();
  }
  const analyze = async () => {
    if (!currentImage || boxes.length == 0) return;
    for (const b of boxes) {
      const payload = {
        image: currentImage, // test1.jpg
        box: b.box, // [xn, yn, wn, hn]
        box_id: b.id 
      };
      const {data} = await axios.post(`${BACKEND}/analyze-price-tag`, payload)
      console.log(data)
      setResults(prev => {
        const others = prev.filter(r=>r.box_id !== data.box_id);
        return [...others, data];
      })
    }
  }

  useEffect(() => {
    axios.get(`${BACKEND}/images`)
    .then(res => {
      setImages(res.data);
    });
  }, []);

  useEffect(() => {
    if (images.length == 0) return;
    const img = new Image();
    img.src = `${BACKEND}/static/images/${currentImage}`;
    img.onload = () => {
      imgRef.current = img;
      drawCurrentImage();
    }
  }, [images, current])

  useEffect(() => {
    setBoxes([]);
    setResults([]);
    if (!baseName) return;
    axios.get(`${BACKEND}/labels/${baseName}`).then(res => {
      setBoxes(res.data || [])
    })
  }, [baseName])

  useEffect(() => {
    if (!imgRef.current) return;
    drawCurrentImage();
  }, [boxes, results])

  return (
  <>
  <div className="h-screen flex flex-col">
    <header className="border-b py-3">
      <div className="gap-2 flex justify-center">
        <button onClick={() => setCurrent(c => Math.max(0, c-1))}
          disabled={current===0}
          className="rounded-xl border px-3 py-1.5 gap-2 hover:cursor-pointer hover:bg-slate-100"
        >
          <FontAwesomeIcon icon={faChevronLeft} /> 
          Prev
        </button>
        <button onClick={() => setCurrent(c => Math.min(c+1, Math.max(0, images.length-1)))}
        disabled={current>=images.length-1}
          className="rounded-xl border px-3 py-1.5 gap-2 hover:cursor-pointer hover:bg-slate-100"
        >
          Next
          <FontAwesomeIcon icon={faChevronRight} /> 
        </button>
      </div>
    </header>

    <main className="flex flex-1">
      {/* Images */}
      <div className="w-[80%] flex justify-center items-center">
        <canvas ref={canvasRef} className="border" width={canvasWidth} height={canvasHeight}/>
      </div>
      <div className="p-4 border-l w-[20%]">
        <button className="border rounded px-2 py-1 w-full mb-2 font-semibold cursor-pointer hover:bg-gray-100"
          onClick={analyze}>
          Analyze
        </button>
        <div className="mb-2 font-semibold">Results</div>
        <ul className="space-y-2 text-sm max-h-[calc(100vh-200px)] overflow-y-auto">
        { results
        .slice()
        .sort((a, b) => a.box_id - b.box_id)
        .map(res => (
          <li key={res.box_id} className="border rounded p-2">
            <div className="font-medium">Box {res.product_name}</div>
            <div>Main: {res.main_price ?? "-"}</div>
            <div>Discount: {res.discount_price ?? "-"}</div>
            <div>Type: {res.discount_type ?? "-"}</div>
            <div>
              Time Discount: 
              {res.time_discount
                ? `${res.time_discount.time_start || "-"} - ${res.time_discount.time_end || "-"}`
                : "-"}
            </div>
            {Array.isArray(res.what_was_read) && res.what_was_read.length>0 && (
              <details className="mt-1">
                <summary className="cursor-pointer">Details</summary>
                <ul className="list-disc ml-4">
                  {res.what_was_read.map((s,i) => renderReadItem(s,i))}
                </ul>
              </details>
            )}
          </li>
        ))}
        </ul>
      </div>
    </main>
  </div>
  </>
)}