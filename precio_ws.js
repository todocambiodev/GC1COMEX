import puppeteer from 'puppeteer-extra';
import StealthPlugin from 'puppeteer-extra-plugin-stealth';

// Usar el plugin de stealth
puppeteer.use(StealthPlugin());

// Funciones principales:
// ---------------------
async function precioRealTime() {
    const url = "https://www.investing.com/commodities/gold";
    const priceSelector = '[data-test="instrument-price-last"]';
    let retryCount = 0;
    const maxRetries = 5;

    while (true) {
        console.log(`\n[${new Date().toLocaleTimeString()}] Iniciando nueva sesión del navegador...`);
        let browser;
        try {
            browser = await puppeteer.launch({
                headless: 'new',
                args: [
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-default-apps',
                    '--disable-popup-blocking',
                    '--disable-prompt-on-repost',
                    '--disable-background-networking',
                    '--disable-client-side-phishing-detection',
                    '--disable-default-apps',
                    '--disable-hang-monitor',
                    '--disable-popup-blocking',
                    '--disable-prompt-on-repost',
                    '--disable-sync',
                    '--enable-automation=false',
                ],
                defaultViewport: {
                    width: 1920,
                    height: 1080
                }
            });

            const page = await browser.newPage();

            // Configurar headers más realistas
            await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0');
            
            await page.setViewport({
                width: 1920,
                height: 1080,
                deviceScaleFactor: 1
            });

            await page.setExtraHTTPHeaders({
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'max-age=0',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1'
            });

            // Exponer función para recibir actualizaciones desde el navegador
            page.on('console', msg => {
                if (msg.type() === 'log' && msg.text().includes('PRECIO:')) {
                    const newPrice = msg.text().replace('PRECIO:', '').trim();
                    console.log(`✅ [${new Date().toLocaleTimeString()}] Oro: ${newPrice}`);
                    verificarSR(newPrice);
                    precio = newPrice.replace(",", "");
                    retryCount = 0;
                }
            });

            console.log(`Navegando a ${url}...`);
            
            // Navegar con espera más agresiva
            await page.goto(url, {
                waitUntil: ['domcontentloaded', 'networkidle0'],
                timeout: 90000
            });

            // Esperar a que Cloudflare se resuelva
            console.log("Esperando resolución de Cloudflare...");
            await page.waitForTimeout(5000);

            // Validar que la página cargó correctamente
            const isBlocked = await page.evaluate(() => {
                return document.body.textContent.includes('Challenge');
            });

            if (isBlocked) {
                throw new Error("Cloudflare sigue bloqueando la página");
            }

            console.log("Esperando selector de precio...");
            await page.waitForSelector(priceSelector, { timeout: 20000 }).catch(() => {
                throw new Error("Precio selector no encontrado");
            });

            const initialPrice = await page.$eval(priceSelector, el => el.textContent.trim());
            console.log(`Precio inicial encontrado: ${initialPrice}`);
            console.log("Escuchando cambios en tiempo real...");

            // Inyectar MutationObserver
            await page.evaluate((selector) => {
                const targetNode = document.querySelector(selector);
                if (!targetNode) return;

                // Rastrear el precio anterior para detectar cambios
                let previousPrice = targetNode.textContent.trim();
                console.log(`PRECIO:${previousPrice}`);

                const observer = new MutationObserver(() => {
                    const price = targetNode.textContent.trim();
                    if (price && price !== previousPrice) {
                        previousPrice = price;
                        console.log(`PRECIO:${price}`);
                    }
                });

                observer.observe(targetNode, {
                    characterData: true,
                    childList: true,
                    subtree: true
                });
            }, priceSelector);

            // Mantener la página abierta
            await new Promise(() => {}); // Never resolve

        } catch (error) {
            retryCount++;
            console.error(`⚠️ [Error]: ${error.message}`);
            console.log(`Reintentos: ${retryCount}/${maxRetries}`);

            if (browser) {
                try {
                    await browser.close();
                } catch (e) {
                    console.error("Error al cerrar navegador:", e.message);
                }
            }

            if (retryCount >= maxRetries) {
                console.log("Máximo de reintentos alcanzado, esperando 60 segundos...");
                retryCount = 0;
                await new Promise(resolve => setTimeout(resolve, 60000));
            } else {
                const waitTime = (retryCount * 8 + 15) * 1000;
                console.log(`Reintentando en ${waitTime / 1000} segundos...`);
                await new Promise(resolve => setTimeout(resolve, waitTime));
            }
        }
    }
}

async function obtenerSR(sr) {
    try {
        console.log("\nCargando nuevos datos de soportes y resistencias...")
        const url = `https://script.google.com/macros/s/AKfycbyJyyN7WFPtao1u_y8jgwsaKVYf2j8TL4vtg-Xe3kAotmBsUAEyFFjt2K-NgHauYxJjHw/exec?sr=${sr}`
        const respuesta = await fetch(url)
        const datos = await respuesta.json()
        soportes = JSON.parse(datos.soportes)
        resistencias = JSON.parse(datos.resistencias)
        console.log("✅ Datos cargados.")
    } catch (error) {
        console.log("Error al obtener soportes y resistencias", error)
    }
}

async function verificarSR(precio) {

    // Verificamos soportes
    precio = precio.replace(",", "")
    let sopActivosNuevos = []
    for (const soporte of soportes) {
        if (Number(soporte[1]) / factor <= Number(precio) && Number(precio) <= Number(soporte[1]) * factor) {
            console.log(`🔷 Soporte activo de ${soporte[2]} en ${soporte[1]}`)
            sopActivosNuevos.push({ soporte: soporte })
        }
    }
    if (!arraysSonIguales(sopActuales, sopActivosNuevos)) {
        sopActuales = sopActivosNuevos
        console.log("✅ Soportes activos actualizados.✅")
        await enviarPrecio(url, precio)
    }

    // Verificamos resistencias
    let resActivasNuevos = []
    for (const resistencia of resistencias) {
        if (Number(resistencia[1]) / factor <= Number(precio) && Number(precio) <= Number(resistencia[1]) * factor) {
            console.log(`🔶 Resistencia activa de ${resistencia[2]} en ${resistencia[1]}`)
            resActivasNuevos.push({ resistencia: resistencia })
        }
    }
    if (!arraysSonIguales(resActuales, resActivasNuevos)) {
        resActuales = resActivasNuevos
        console.log("✅ Resistencias activas actualizadas.✅")
        await enviarPrecio(url, precio)
    }
}

function arraysSonIguales(arr1, arr2) {
    if (arr1.length !== arr2.length) return false

    // Función auxiliar para convertir a string y comparar
    const sorter = (a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b))

    // Creamos copias, ordenamos y comparamos
    const s1 = JSON.stringify([...arr1].sort(sorter))
    const s2 = JSON.stringify([...arr2].sort(sorter))

    return s1 === s2
}

async function enviarPrecio(url, precio) {
    url += `?verificarSR=${precio}`
    console.log("Enviando precio: ", precio)
    const respuesta = await fetch(url, {method: "POST"})
    console.log(await respuesta.text())
}

async function main() {

    try {
        await Promise.all([
            precioRealTime(),
            obtenerSR("sr")
        ]);
    } catch (error) {
        console.error("Error en main:", error);
        process.exit(1);
    }

    // Volver a cargar los datos:
    setInterval(async () => {
        await obtenerSR("sr");
        cicloActual++;
        if (cicloActual >= cicloFinal) {
            console.log("✅ Proceso finalizado.");
            process.exit(0);
        }
    }, minutosParaRecargarSR * 60 * 1000);

    // Enviar precio actual
    setInterval(async () => {
        if (precio != "") await enviarPrecio(url, precio);
    }, segundosParaEnviarPrecioActual * 1000);
}
// ---------------------

// Variables globales:
// ---------------------
let url = "https://script.google.com/macros/s/AKfycbyJyyN7WFPtao1u_y8jgwsaKVYf2j8TL4vtg-Xe3kAotmBsUAEyFFjt2K-NgHauYxJjHw/exec"
let soportes = []
let resistencias = []
let sopActuales = []
let resActuales = []
const factor = 1.00126
const minutosParaRecargarSR = 1
const segundosParaEnviarPrecioActual = 3.69
const cicloFinal = 18
let cicloActual = 0
let precio = ""
// ---------------------

// Funciones principales:
// ---------------------
main()
// ---------------------

