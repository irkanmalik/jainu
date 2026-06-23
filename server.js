const express = require('express');
const bodyParser = require('body-parser');
const session = require('express-session');
const path = require('path');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.static(__dirname));

app.use(session({
    secret: 'jainu_ai_secure_2026',
    resave: false,
    saveUninitialized: true,
    cookie: { secure: false }
}));

const ADMIN_EMAIL = "IRKANMALIK244255@GMAIL.COM";
const ADMIN_PASSWORD = "admin@786";

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'login.html'));
});

app.post('/api/login', (req, res) => {
    const { email, password } = req.body;
    if (email && email.toUpperCase() === ADMIN_EMAIL.toUpperCase() && password === ADMIN_PASSWORD) {
        return res.json({ success: true, redirect: '/index.html' });
    } else {
        return res.json({ success: true, redirect: '/index.html' });
    }
});

app.post('/api/generate', (req, res) => {
    const { prompt, type } = req.body;
    const randomId = Math.floor(Math.random() * 3);
    
    if (type === 'video') {
        const randomVideos = [
            "https://assets.mixkit.co/videos/preview/mixkit-neon-light-from-a-futuristic-tunnel-41865-large.mp4",
            "https://assets.mixkit.co/videos/preview/mixkit-waves-crashing-on-rocks-from-above-41642-large.mp4",
            "https://assets.mixkit.co/videos/preview/mixkit-forest-stream-with-clear-water-41712-large.mp4"
        ];
        return res.json({ success: true, type: 'video', url: randomVideos[randomId] });
    } else {
        const seed = Math.floor(Math.random() * 9999999);
        const imageUrl = `https://image.pollinations.ai/p/${encodeURIComponent(prompt)}?width=1024&height=1024&seed=${seed}&nologo=true`;
        return res.json({ success: true, type: 'image', url: imageUrl });
    }
});

app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});