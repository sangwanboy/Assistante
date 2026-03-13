const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
require('dotenv').config();

const app = express();
app.use(cors());
app.use(bodyParser.json());

const PORT = process.env.PORT || 3001;

// Store active clients by profile name
const clients = new Map();
// Store latest QR codes by profile name
const qrCodes = new Map();

const axios = require('axios');

// Map of profile -> integrationId for webhooks
const profileToIntegration = new Map();

app.post('/api/whatsapp/connect', async (req, res) => {
    const { profile, integrationId } = req.body;

    if (!profile) {
        return res.status(400).json({ error: 'Profile name is required' });
    }

    if (integrationId) {
        profileToIntegration.set(profile, integrationId);
    }

    // SANITIZE: clientId must be alphanumeric/underscores/hyphens
    const clientId = profile.replace(/[^a-zA-Z0-9_\-]/g, '_');

    if (clients.has(profile)) {
        return res.json({ status: 'already_running', qr: qrCodes.get(profile) });
    }

    console.log(`Initializing WhatsApp client for profile: ${profile} (ID: ${clientId})`);

    const client = new Client({
        authStrategy: new LocalAuth({ clientId: clientId }),
        puppeteer: {
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-extensions'],
        }
    });

    clients.set(profile, client);

    client.on('qr', (qr) => {
        console.log(`[${profile}] QR RECEIVED`);
        qrCodes.set(profile, qr);
    });

    client.on('ready', () => {
        console.log(`[${profile}] Client is ready!`);
        qrCodes.delete(profile);
    });

    client.on('message', async msg => {
        console.log(`[${profile}] Received: ${msg.body}`);
        const iid = profileToIntegration.get(profile);
        if (iid) {
            const webhookUrl = `http://localhost:8322/api/integrations/${iid}/webhook/whatsapp_web`;
            try {
                await axios.post(webhookUrl, {
                    profile: profile,
                    from: msg.from,
                    text: msg.body,
                    pushname: msg._data?.notifyName || msg.from
                });
            } catch (err) {
                console.error(`[${profile}] Webhook failed:`, err.message);
            }
        }
    });

    client.on('disconnected', (reason) => {
        console.log(`[${profile}] Disconnected:`, reason);
        clients.delete(profile);
        qrCodes.delete(profile);
    });

    // Handle initialization without crashing the process
    client.initialize().catch(err => {
        console.error(`[${profile}] Critical Initialization error:`, err.message);
        qrCodes.set(profile, `ERROR: ${err.message}`);
        clients.delete(profile);
    });

    res.json({ status: 'initializing' });
});

app.post('/api/whatsapp/send', async (req, res) => {
    const { profile, to, text } = req.body;
    const client = clients.get(profile);
    if (!client) {
        return res.status(404).json({ error: 'Client not found for this profile' });
    }

    try {
        // Ensure 'to' has @c.us suffix if it's just a number
        const chatId = to.includes('@') ? to : `${to}@c.us`;
        await client.sendMessage(chatId, text);
        res.json({ ok: true });
    } catch (err) {
        console.error(`[${profile}] Send failed:`, err.message);
        res.status(500).json({ error: err.message });
    }
});

app.get('/api/whatsapp/qr/:profile', (req, res) => {
    const { profile } = req.params;
    const qr = qrCodes.get(profile);

    // Check if we captured an error in the QR slot
    if (qr && qr.startsWith('ERROR:')) {
        return res.json({ status: 'error', message: qr.replace('ERROR: ', '') });
    }

    if (clients.has(profile) && !qr) {
        // If client exists but no QR, it might be connected or still booting
        return res.json({ status: 'checking' });
    }

    if (qr) {
        return res.json({ status: 'qr_ready', qr });
    }

    res.json({ status: 'not_running' });
});

app.listen(PORT, () => {
    console.log(`WhatsApp Microservice running on port ${PORT}`);
});
