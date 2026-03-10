import { chromium } from "playwright"

// Funciones principales:
// ---------------------
async function precioRealTime() {
    const url = "https://www.investing.com/commodities/gold";
    const priceSelector = '[data-test="instrument-price-last"]';
    while (true) {
        console.log(`\n[${new Date().toLocaleTimeString()}] Iniciando nueva sesión del navegador...`);
        let browser;
        try {
            browser = await chromium.launch({ headless: true });
            const context = await browser.newContext({
                userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                viewport: { width: 1280, height: 720 }
            });
            const page = await context.newPage();

            // Exponer función para recibir actualizaciones desde el navegador
            await page.exposeFunction('onPriceChange', (newPrice) => {
                console.log(`✅ [${new Date().toLocaleTimeString()}] Oro: ${newPrice}`);
                verificarSR(newPrice);
                precio = newPrice.replace(",", "");
            });

            console.log(`Navegando a ${url}...`);
            await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 63000 });

            console.log("Esperando selector de precio...");
            await page.waitForSelector(priceSelector, { timeout: 15000 });

            const initialPrice = await page.textContent(priceSelector);
            console.log(`Precio inicial encontrado: ${initialPrice}`);
            console.log("Escuchando cambios en tiempo real (MutationObserver activo)...");

            // Inyectar MutationObserver en la página
            await page.evaluate((selector) => {
                const targetNode = document.querySelector(selector);
                if (!targetNode) return;

                const observer = new MutationObserver(() => {
                    const price = targetNode.textContent.trim();
                    window.onPriceChange(price);
                });

                observer.observe(targetNode, {
                    characterData: true,
                    childList: true,
                    subtree: true
                });
            }, priceSelector);

            // Mantener la página abierta indefinidamente. 
            // Si el navegador se cierra o falla, el catch reiniciará el loop.
            await page.waitForEvent('close', { timeout: 0 });

        } catch (error) {
            console.error(`⚠️ [Error]: ${error.message}`);
            console.log("Reintentando en 10 segundos...");
            if (browser) await browser.close().catch(() => { });
            await new Promise(resolve => setTimeout(resolve, 10000));
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

    Promise.all([
        precioRealTime(),
        obtenerSR("sr")
    ])

    // Volver a cargar los datos:
    setInterval(async () => {
        await obtenerSR("sr")
        if (precio != "") await enviarPrecio(url, precio)
        cicloActual++
        if (cicloActual >= cicloFinal) {
            console.log("✅ Proceso finalizado.")
            process.exit()
        }
    }, minutosParaRecargarSR * 60 * 1000)
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
const minutosParaRecargarSR = 1/9
const cicloFinal = 18*9
let cicloActual = 0
let precio = ""
// ---------------------

// Funciones principales:
// ---------------------
main()
// ---------------------
