// FIX: Removed duplicate autoFillFromPDF() definition that was at the top of the file.
// The complete version below (with the redaction flow) is the correct one.
// FIX: openAIAssistant now uses dynamic context label instead of hardcoded "ITR-2 context".

// Helper: collect options from a select field by data-key
function getFieldOptions(key) {
    const el = document.querySelector(`[data-key="${key}"]`);
    if (el && el.tagName === "SELECT") {
        return Array.from(el.options).map(o => ({ value: o.value, label: o.text }));
    }
    return null;
}

async function openAIAssistant(key, label) {

    currentFieldKey = key;

    document.getElementById("aiTitle").innerText = label;
    document.getElementById("aiPanel").style.right = "0";

    const chatBox = document.getElementById("aiChat");

    // Show loading indicator
    chatBox.innerHTML = `<div class="ai-typing">AI is thinking...</div>`;

    const fieldOptions = getFieldOptions(key);

    const response = await fetch("http://127.0.0.1:8000/field-assist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            field: key,
            message: `Explain the meaning of "${label}" in the context of Indian Income Tax Return filing briefly.`,
            ...(fieldOptions ? { options: fieldOptions } : {})
        })
    });

    const data = await response.json();

    chatBox.innerHTML = ""; // Clear loading

    appendChat("AI", data.reply);
}


function closeAIPanel() {
    document.getElementById("aiPanel").style.right = "-400px";
}

async function askLLM(message) {

    const response = await fetch("http://127.0.0.1:8000/field-assist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            field: currentFieldKey,
            message: message
        })
    });

    const data = await response.json();

    appendChat("AI", data.reply);
}

function appendChat(sender, message) {

    const chatBox = document.getElementById("aiChat");

    const msgDiv = document.createElement("div");

    if (sender === "You") {
        msgDiv.className = "chat-user";
    } else {
        msgDiv.className = "chat-ai";
    }

    msgDiv.innerText = message;

    chatBox.appendChild(msgDiv);

    chatBox.scrollTop = chatBox.scrollHeight;
}



async function sendAIMessage() {

    const userText = document.getElementById("aiInput").value.trim();
    if (!userText) return;

    appendChat("You", userText);

    const fieldOptions = getFieldOptions(currentFieldKey);

    const response = await fetch("http://127.0.0.1:8000/field-assist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            field: currentFieldKey,
            message: userText,
            ...(fieldOptions ? { options: fieldOptions } : {})
        })
    });

    const data = await response.json();

    appendChat("AI", data.reply || "");

    // ===============================
    // 🔥 CORRECT AUTO FILL LOGIC
    // ===============================

    if (data.fillValue !== undefined && data.fillValue !== "") {

        // 🔥 use backend mapped field if exists
        const targetKey = data.field ? data.field : currentFieldKey;

        const input = document.querySelector(`[data-key="${targetKey}"]`);

        if (input) {
            input.value = data.fillValue;
            input.dispatchEvent(new Event("input", { bubbles: true }));
            recalc();
        } else {
            console.log("No input found for key:", targetKey);
        }
    }

    document.getElementById("aiInput").value = "";
}



// ===============================
// REDACTION FLOW
// ===============================

let pdfDoc;
let pageCanvases = [];   // all pages
let pageBoxes = {};      // per-page rectangles
let drawing=false,startX,startY,currentCanvas,currentPage;
let currentFile=null;

async function autoFillFromPDF(){

  const fileInput=document.getElementById("aiPdf");
  const file=fileInput.files[0];

  if(!file){
     alert("Please select PDF");
     return;
  }

  document.getElementById("aiStatus").innerText=
     "Open editor & redact personal info...";

  openRedactionEditor(file);
}

 // store boxes per page


async function openRedactionEditor(file){

 currentFile=file;
 pageCanvases=[];
 pageBoxes={};

 document.getElementById("redactModal").style.display="block";

 const buffer=await file.arrayBuffer();
 pdfDoc=await pdfjsLib.getDocument({data:buffer}).promise;

 const scrollArea=document.getElementById("pdfScrollArea");
 scrollArea.innerHTML="";

 // 🔥 LOAD ALL PAGES
 for(let i=1;i<=pdfDoc.numPages;i++){

   const page=await pdfDoc.getPage(i);

   const viewport=page.getViewport({scale:1.4});

   const canvas=document.createElement("canvas");
   canvas.className="redact-canvas";
   canvas.width=viewport.width;
   canvas.height=viewport.height;
   canvas.dataset.page=i;

   const wrap=document.createElement("div");
   wrap.className="redact-page";

   wrap.appendChild(canvas);
   scrollArea.appendChild(wrap);

   const ctx=canvas.getContext("2d");
   await page.render({canvasContext:ctx,viewport}).promise;

   pageCanvases.push(canvas);
   pageBoxes[i]=[];

   enableDrawing(canvas,i);
 }
}


const pageSnapshots = new WeakMap();

function enableDrawing(canvas, pageNo) {
  // Save clean snapshot
  const snap = document.createElement("canvas");
  snap.width = canvas.width;
  snap.height = canvas.height;
  snap.getContext("2d").drawImage(canvas, 0, 0);
  pageSnapshots.set(canvas, snap);

  canvas.onmousedown = (e) => {
    drawing = true;
    startX = e.offsetX;
    startY = e.offsetY;
    currentCanvas = canvas;
    currentPage = pageNo;
  };

  canvas.onmousemove = (e) => {
    if (!drawing) return;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(pageSnapshots.get(canvas), 0, 0); // restore clean page
    ctx.fillStyle = "rgba(0,0,0,0.5)";
    ctx.fillRect(startX, startY, e.offsetX - startX, e.offsetY - startY);
  };

  canvas.onmouseup = (e) => {
    if (!drawing) return;
    drawing = false;
    const rx = Math.min(startX, e.offsetX);
    const ry = Math.min(startY, e.offsetY);
    const rw = Math.abs(e.offsetX - startX);
    const rh = Math.abs(e.offsetY - startY);
    if (rw < 4 || rh < 4) return;
    pageBoxes[currentPage].push({ x: rx, y: ry, w: rw, h: rh }); // 1-based pageNo
    // Commit box to snapshot
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "black";
    ctx.fillRect(rx, ry, rw, rh);
    const newSnap = document.createElement("canvas");
    newSnap.width = canvas.width;
    newSnap.height = canvas.height;
    newSnap.getContext("2d").drawImage(canvas, 0, 0);
    pageSnapshots.set(canvas, newSnap);
  };
}

async function applyRedaction(){

  document.getElementById("aiStatus").innerText = "Applying redaction...";

  const formData = new FormData();
  formData.append("file", currentFile, "original.pdf");
  formData.append("boxes", JSON.stringify(pageBoxes));
  formData.append("scale", "1.4");

  const response = await fetch("http://127.0.0.1:8000/upload", {
      method: "POST",
      body: formData
  });

  const data = await response.json();

  // Always close the modal first
  document.getElementById("redactModal").style.display = "none";

  // Support both { updated_data: {...} } and flat { key: value } response shapes
  const payload = data.updated_data ?? data;

  if(!payload || Object.keys(payload).length === 0){
      document.getElementById("aiStatus").innerText = "Extraction failed — no data returned.";
      return;
  }

  fillFormFromJSON(payload);
  document.getElementById("aiStatus").innerText = "✅ Auto-filled successfully!";
}




async function askAI(field, message){

const res = await fetch("/api/chat",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({
field_key:field,
message:message
})
});

return await res.json();
}