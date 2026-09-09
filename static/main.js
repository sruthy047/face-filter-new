document.addEventListener('DOMContentLoaded', () => {
    const videoElement = document.getElementById('webcam');
    const canvasElement = document.getElementById('canvas');
    const outputElement = document.getElementById('output');
    const filterButtons = document.querySelectorAll('.filter-btn');
    const ctx = canvasElement.getContext('2d');

    const btnStart = document.getElementById('btn-start');
    const btnStop = document.getElementById('btn-stop');
    const btnTake = document.getElementById('btn-take');
    const btnDownload = document.getElementById('btn-download');
    const btnRemove = document.getElementById('btn-remove');
    const downloadLink = document.getElementById('download-link');

    let currentFilter = 'none';
    let isProcessing = false;
    let cameraActive = false;
    let mediaStream = null;
    let lastPhotoData = null;

    // Request webcam access
    async function startCamera() {
        if (cameraActive) return;
        try {
            mediaStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640 }, 
                    height: { ideal: 480 },
                    facingMode: 'user'
                }
            });
            videoElement.srcObject = mediaStream;
            
            videoElement.onloadedmetadata = () => {
                canvasElement.width = videoElement.videoWidth;
                canvasElement.height = videoElement.videoHeight;
                cameraActive = true;
                processFrame(); 
            };
        } catch (err) {
            console.error('Error accessing webcam: ', err);
            alert('Unable to access webcam. Please ensure you have granted permission.');
        }
    }

    function stopCamera() {
        if (mediaStream) {
            mediaStream.getTracks().forEach(track => track.stop());
            cameraActive = false;
            outputElement.src = ''; // Clear image
        }
    }

    // Capture frame and send to server
    async function processFrame() {
        if (!cameraActive) return;
        
        if (!isProcessing) {
            isProcessing = true;
            
            ctx.drawImage(videoElement, 0, 0, canvasElement.width, canvasElement.height);
            
            // If no filter, just show the webcam frame directly to save network!
            if (currentFilter === 'none') {
                outputElement.src = canvasElement.toDataURL('image/jpeg', 0.8);
                isProcessing = false;
                requestAnimationFrame(processFrame);
                return;
            }

            const imageData = canvasElement.toDataURL('image/jpeg', 0.5); // lower quality to speed up transfer
            
            try {
                const response = await fetch('/process_frame', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        image: imageData,
                        filter: currentFilter
                    })
                });
                
                const data = await response.json();
                
                if (data.image) {
                    outputElement.src = data.image;
                }
            } catch (err) {
                console.error("Error processing frame on server:", err);
            } finally {
                isProcessing = false;
            }
        }
        
        requestAnimationFrame(processFrame);
    }

    // Set Filter UI
    function setFilter(filterName) {
        currentFilter = filterName;
        filterButtons.forEach(btn => {
            if(btn.getAttribute('data-filter') === filterName) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }

    // Handle filter selection (Click)
    filterButtons.forEach(button => {
        button.addEventListener('click', () => {
            setFilter(button.getAttribute('data-filter'));
        });
    });

    // Handle Keyboard Shortcuts
    document.addEventListener('keydown', (e) => {
        const keyMap = {
            '1': 'sunglasses',
            '2': 'cat',
            '3': 'crown',
            '4': 'heart_eyes',
            '5': 'mustache',
            '6': 'robot',
            '0': 'none'
        };
        if (keyMap[e.key]) {
            setFilter(keyMap[e.key]);
        }
    });

    // Control Buttons
    btnStart.addEventListener('click', startCamera);
    btnStop.addEventListener('click', stopCamera);
    
    btnRemove.addEventListener('click', () => {
        setFilter('none');
    });

    btnTake.addEventListener('click', () => {
        if (!cameraActive) {
            alert("Start camera first!");
            return;
        }
        // Save the current src of the output element (which is base64)
        lastPhotoData = outputElement.src;
        
        // Visual flash effect
        outputElement.style.opacity = '0';
        setTimeout(() => outputElement.style.opacity = '1', 100);

        btnDownload.disabled = false;
    });

    btnDownload.addEventListener('click', () => {
        if (lastPhotoData) {
            downloadLink.href = lastPhotoData;
            downloadLink.download = `FaceFun_${Date.now()}.jpg`;
            downloadLink.click();
        }
    });

});
