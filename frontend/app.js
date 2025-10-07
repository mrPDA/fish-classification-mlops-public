/**
 * 🐟 Fish Classification Frontend
 * JavaScript для взаимодействия с API
 */

// API Configuration - будет настраиваться через переменные окружения
const API_BASE_URL = window.API_BASE_URL || '/api';

// DOM Elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const previewContainer = document.getElementById('previewContainer');
const previewImage = document.getElementById('previewImage');
const analyzeBtn = document.getElementById('analyzeBtn');
const resetBtn = document.getElementById('resetBtn');
const loadingSpinner = document.getElementById('loadingSpinner');
const resultContainer = document.getElementById('resultContainer');

// Result elements
const speciesName = document.getElementById('speciesName');
const confidenceBar = document.getElementById('confidenceBar');
const confidenceText = document.getElementById('confidenceText');
const processingTime = document.getElementById('processingTime');
const speciesId = document.getElementById('speciesId');
const cacheStatus = document.getElementById('cacheStatus');
const speciesDescription = document.getElementById('speciesDescription');

let selectedFile = null;

// Species information (расширенная информация о видах)
const speciesInfo = {
    "Perca Fluviatilis": "Окунь речной - хищная пресноводная рыба, обитающая в реках и озёрах Европы и Азии. Имеет характерные тёмные полосы на боках.",
    "Perccottus Glenii": "Ротан-головешка - инвазивный вид, способный выживать в экстремальных условиях. Обитает в пресных водоёмах Дальнего Востока.",
    "Esox Lucius": "Щука обыкновенная - крупная хищная рыба с вытянутым телом и мощными челюстями. Важный объект спортивного и промыслового рыболовства.",
    "Alburnus Alburnus": "Уклейка - мелкая стайная рыба с серебристой чешуёй. Служит кормовой базой для хищных рыб.",
    "Abramis Brama": "Лещ обыкновенный - крупная мирная рыба с высоким сжатым телом. Ценный промысловый вид.",
    "Carassius Gibelio": "Карась серебряный - выносливая рыба, способная жить в водоёмах с низким содержанием кислорода.",
    "Squalius Cephalus": "Голавль - всеядная рыба из семейства карповых. Предпочитает быстрые реки с чистой водой.",
    "Scardinius Erythrophthalmus": "Красноперка - мирная рыба с яркими красными плавниками. Обитает в зарослях водной растительности.",
    "Rutilus Lacustris": "Плотва озёрная - пресноводная рыба, образующая крупные стаи. Важна в пищевой цепи водоёмов.",
    "Rutilus Rutilus": "Плотва обыкновенная - одна из самых распространённых рыб в водоёмах Европы и Азии.",
    "Blicca Bjoerkna": "Густера - стайная мирная рыба, внешне похожая на леща, но меньших размеров.",
    "Gymnocephalus Cernua": "Ёрш обыкновенный - мелкая донная рыба с колючими плавниками. Активен круглый год.",
    "Leuciscus Idus": "Язь - крупная всеядная рыба с золотистым отливом. Обитает в реках и озёрах с чистой водой.",
    "Sander Lucioperca": "Судак обыкновенный - ценная хищная рыба с отличными вкусовыми качествами. Активный ночной хищник.",
    "Leuciscus Baicalensis": "Елец сибирский - пресноводная рыба, обитающая в холодных быстрых реках Сибири.",
    "Gobio Gobio": "Пескарь обыкновенный - небольшая донная рыба, предпочитающая песчаное дно рек.",
    "Tinca Tinca": "Линь - мирная донная рыба с толстым слизистым телом. Обитает в заросших водоёмах."
};

// ========================================
// Event Listeners
// ========================================

// Click to upload
uploadArea.addEventListener('click', () => {
    fileInput.click();
});

// Drag and drop
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    handleFileSelect(file);
});

// File input change
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    handleFileSelect(file);
});

// Analyze button
analyzeBtn.addEventListener('click', () => {
    if (selectedFile) {
        analyzeFish();
    }
});

// Reset button
resetBtn.addEventListener('click', () => {
    resetUpload();
});

// ========================================
// Functions
// ========================================

function handleFileSelect(file) {
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
        alert('Пожалуйста, выберите изображение!');
        return;
    }

    // Validate file size (10MB max)
    if (file.size > 10 * 1024 * 1024) {
        alert('Файл слишком большой! Максимальный размер: 10MB');
        return;
    }

    selectedFile = file;

    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => {
        previewImage.src = e.target.result;
        uploadArea.style.display = 'none';
        previewContainer.style.display = 'block';
        resultContainer.style.display = 'none';
    };
    reader.readAsDataURL(file);
}

function resetUpload() {
    selectedFile = null;
    fileInput.value = '';
    uploadArea.style.display = 'block';
    previewContainer.style.display = 'none';
    loadingSpinner.style.display = 'none';
    resultContainer.style.display = 'none';
}

async function analyzeFish() {
    if (!selectedFile) return;

    // Hide buttons, show loading
    analyzeBtn.disabled = true;
    resetBtn.style.display = 'none';
    loadingSpinner.style.display = 'block';
    resultContainer.style.display = 'none';

    try {
        // Create FormData
        const formData = new FormData();
        formData.append('file', selectedFile);

        // Call API
        const response = await fetch(`${API_BASE_URL}/predict`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }

        const result = await response.json();
        displayResult(result);

    } catch (error) {
        console.error('Error:', error);
        alert(`Ошибка при анализе изображения: ${error.message}\n\nПожалуйста, убедитесь, что:\n1. API сервер запущен\n2. Изображение корректное\n3. Есть подключение к сети`);
        
        // Reset to allow retry
        analyzeBtn.disabled = false;
        resetBtn.style.display = 'inline-block';
        loadingSpinner.style.display = 'none';
    }
}

function displayResult(result) {
    // Hide loading, show results
    loadingSpinner.style.display = 'none';
    resultContainer.style.display = 'block';
    resetBtn.style.display = 'inline-block';

    // Populate result data
    speciesName.textContent = result.species_name || 'Unknown';
    speciesId.textContent = result.species_id || '-';
    
    // Confidence bar
    const confidence = Math.round(result.confidence * 100);
    confidenceBar.style.width = `${confidence}%`;
    confidenceBar.setAttribute('aria-valuenow', confidence);
    confidenceText.textContent = `${confidence}%`;
    
    // Set confidence bar color based on value
    if (confidence >= 80) {
        confidenceBar.style.background = 'linear-gradient(90deg, #198754 0%, #20c997 100%)';
    } else if (confidence >= 60) {
        confidenceBar.style.background = 'linear-gradient(90deg, #ffc107 0%, #ffca2c 100%)';
    } else {
        confidenceBar.style.background = 'linear-gradient(90deg, #dc3545 0%, #e35d6a 100%)';
    }
    
    // Processing time
    processingTime.textContent = Math.round(result.processing_time_ms || 0);
    
    // Cache status
    cacheStatus.textContent = result.cached ? '🟢 Cached' : '🔵 New';
    
    // Species description
    speciesDescription.textContent = speciesInfo[result.species_name] || 
        'Информация о данном виде рыбы недоступна.';

    // Scroll to results
    resultContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ========================================
// API Health Check on Load
// ========================================

async function checkAPIHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        console.log('✅ API Health:', data);
        
        if (!data.model_loaded) {
            console.warn('⚠️ Model not loaded yet. Predictions may be slow on first request.');
        }
    } catch (error) {
        console.error('❌ API не доступен:', error);
        console.log('Убедитесь, что Inference API запущен на', API_BASE_URL);
    }
}

// Check API on page load
checkAPIHealth();

// ========================================
// Statistics (можно расширить)
// ========================================

let stats = {
    totalRequests: 0,
    cachedRequests: 0,
    avgConfidence: 0
};

function updateStats(result) {
    stats.totalRequests++;
    if (result.cached) {
        stats.cachedRequests++;
    }
    
    // Update average confidence
    const confidences = JSON.parse(localStorage.getItem('confidences') || '[]');
    confidences.push(result.confidence);
    if (confidences.length > 100) {
        confidences.shift(); // Keep last 100
    }
    localStorage.setItem('confidences', JSON.stringify(confidences));
    
    stats.avgConfidence = confidences.reduce((a, b) => a + b, 0) / confidences.length;
    
    console.log('📊 Stats:', stats);
}

