
// saudacao_localizacao.js

function carregarMarcos(callback) {
    fetch('marcos_geo_filtrados.json')
        .then(response => response.json())
        .then(data => callback(data))
        .catch(error => console.error('Erro ao carregar marcos:', error));
}

function calcularDistancia(lat1, lon1, lat2, lon2) {
    const R = 6371; // km
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a =
        Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
        Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
}

let saudado = false;

function iniciarLocalizacao(map) {
    if (!navigator.geolocation) {
        alert("Geolocalização não suportada.");
        return;
    }

    carregarMarcos(function(marcos) {
        navigator.geolocation.watchPosition(function(position) {
            const userLat = position.coords.latitude;
            const userLon = position.coords.longitude;

            let maisProximo = null;
            let menorDistancia = Infinity;

            marcos.forEach(function(marco) {
                const dist = calcularDistancia(userLat, userLon, marco.lat, marco.lon);
                if (dist < menorDistancia) {
                    menorDistancia = dist;
                    maisProximo = marco;
                }
            });

            if (maisProximo && menorDistancia < 3) { // até 3 km de distância
                if (!saudado) {
                    saudado = true;
                    alert("👋 Bem-vindo à área da Companhia!");
                }

                const popup = L.popup()
                    .setLatLng([userLat, userLon])
                    .setContent(
                        "<b>Rodovia:</b> " + maisProximo.rodovia +
                        "<br><b>KM:</b> " + maisProximo.km +
                        "<br><b>Município:</b> (estimado)"
                    )
                    .openOn(map);
            } else {
                // fora da área da companhia
                map.closePopup();
            }

        }, function(error) {
            console.error("Erro ao obter localização:", error);
        }, { enableHighAccuracy: true });
    });
}

// Aguarda o mapa carregar para iniciar
document.addEventListener("DOMContentLoaded", function() {
    const map = window.map; // Folium define isso
    if (map) {
        iniciarLocalizacao(map);
    }
});
