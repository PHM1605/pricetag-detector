import { useEffect, useRef, useState } from "react"
import axios from "axios";
import {FontAwesomeIcon} from "@fortawesome/react-fontawesome"
import { faChevronLeft, faChevronRight } from "@fortawesome/free-solid-svg-icons";

const BACKEND = "http://localhost:8000"

function OverlayBoxes({boxes, resultById}) {
  return (
  <div>
  {boxes.map(box => {
    return (
      <div key={box.id} className="pointer-events-auto">
        <div className="h-full w-full">
          box.id
        </div>
      </div>
    )
  })}
  </div>
  )
}

export default function PricetagViewer() {
  const [images, setImages] = useState([]);
  const [current, setCurrent] = useState(0);
  const [boxes, setBoxes] = useState([]);
  const [results, setResults] = useState([]) // [{box_id,...}]
  const imgRef = useRef(null);
  const currentFile = images[current] || null;
  const baseName = currentFile ? currentFile.substring(0, currentFile.lastIndexOf('.')) : null;

  useEffect(() => {
    axios.get(`${BACKEND}/images`).then(res => setImages(res.data || []));
  }, []);

  useEffect(() => {
    setBoxes([]);
    setResults([]);
    if (!baseName) return;
    axios.get(`${BACKEND}/labels/${baseName}`).then(res => setBoxes(res.data || []))
  }, [baseName])

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

    <main className="grid grid-cols-6 flex-1">
      {/* Images */}
      <div className="col-span-5 flex items-center justify-center">
        <div className="w-[900px] h-[600px] overflow-auto">
        { currentFile && (
          <img ref={imgRef} 
            className="block"
            src={`${BACKEND}/static/images/${currentFile}`}
            alt={currentFile}
          />
        )}          
        </div>        
      </div>
      <aside className="p-4 border-l">
        <div className="mb-2 font-semibold">Results</div>
        <ul className="space-y-2 text-sm">
        { results.map(res => (
        <li>

        </li>
        ))}
        </ul>
      </aside>
    </main>
  </div>
  </>
)}