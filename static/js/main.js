// JavaScript personalizado para SIGRP

// Configuración global de HTMX
document.body.addEventListener('htmx:configRequest', (event) => {
    // Agregar CSRF token automáticamente
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfToken) {
        event.detail.headers['X-CSRFToken'] = csrfToken.value;
    }
});

// Utilidad para formatear moneda
function formatCurrency(amount) {
    return new Intl.NumberFormat('es-CO', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

// Utilidad para formatear fechas
function formatDate(dateString) {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('es-ES', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    }).format(date);
}

// Componente Vue para gráficos (reutilizable)
const ChartComponent = {
    props: ['chartData', 'chartType'],
    template: '<canvas ref="chartCanvas"></canvas>',
    mounted() {
        this.renderChart();
    },
    methods: {
        renderChart() {
            const ctx = this.$refs.chartCanvas.getContext('2d');
            new Chart(ctx, {
                type: this.chartType || 'line',
                data: this.chartData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        }
    }
};

console.log('SIGRP JavaScript initialized');
