// Función para alternar el tema oscuro
function toggleDarkMode() {
    const isDark = document.documentElement.classList.contains('dark');
    
    if (isDark) {
        document.documentElement.classList.remove('dark');
        localStorage.theme = 'light';
    } else {
        document.documentElement.classList.add('dark');
        localStorage.theme = 'dark';
    }
}

// Función para inicializar el tema
function initTheme() {
    if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark');
    }
}

// Función para manejar el menú móvil
function setupMobileMenu() {
    const menuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');

    if (!menuButton || !mobileMenu) return;
    
    // Prevenir múltiples listeners
    if (menuButton.dataset.initialized === 'true') return;
    menuButton.dataset.initialized = 'true';

    const closeMenu = () => {
        menuButton.setAttribute('aria-expanded', 'false');
        mobileMenu.style.maxHeight = '0px';
        
        const icon = menuButton.querySelector('i');
        if (icon) {
            icon.classList.remove('fa-times');
            icon.classList.add('fa-bars');
        }
        
        // Ocultar después de la animación
        setTimeout(() => {
            if (menuButton.getAttribute('aria-expanded') === 'false') {
                mobileMenu.classList.add('hidden');
            }
        }, 300);
    };

    const openMenu = () => {
        mobileMenu.classList.remove('hidden');
        // Forzar reflow para que la animación funcione
        mobileMenu.offsetHeight;
        // Usar setTimeout para asegurar que el navegador procese el cambio
        setTimeout(() => {
            mobileMenu.style.maxHeight = mobileMenu.scrollHeight + 'px';
            menuButton.setAttribute('aria-expanded', 'true');
            const icon = menuButton.querySelector('i');
            if (icon) {
                icon.classList.remove('fa-bars');
                icon.classList.add('fa-times');
            }
        }, 10);
    };

    // Toggle del menú
    menuButton.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const isExpanded = menuButton.getAttribute('aria-expanded') === 'true';
        
        if (isExpanded) {
            closeMenu();
        } else {
            openMenu();
        }
    });

    // Cerrar menú al hacer clic fuera
    document.addEventListener('click', (e) => {
        const isExpanded = menuButton.getAttribute('aria-expanded') === 'true';
        if (isExpanded && !mobileMenu.contains(e.target) && !menuButton.contains(e.target)) {
            closeMenu();
        }
    }, true); // Usar capture para capturar antes

    // Cerrar menú al cambiar tamaño de ventana
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            if (window.innerWidth >= 768) {
                const isExpanded = menuButton.getAttribute('aria-expanded') === 'true';
                if (isExpanded) {
                    closeMenu();
                }
            }
        }, 250);
    });

    // Cerrar menú al hacer clic en un enlace o botón del menú
    const menuItems = mobileMenu.querySelectorAll('a, button');
    menuItems.forEach(item => {
        item.addEventListener('click', (e) => {
            // Si es el botón de tema, no cerrar el menú
            if (item.id === 'theme-toggle-mobile') {
                e.stopPropagation();
                return;
            }
            // Para enlaces, cerrar el menú
            setTimeout(() => closeMenu(), 100);
        });
    });
}

// Inicializar cuando el DOM está listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

function init() {
    // Inicializar tema
    initTheme();
    
    // Configurar botón de tema (desktop)
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle && !themeToggle.dataset.initialized) {
        themeToggle.dataset.initialized = 'true';
        themeToggle.addEventListener('click', (e) => {
            e.preventDefault();
            toggleDarkMode();
        });
    }
    
    // Configurar botón de tema (mobile)
    const themeToggleMobile = document.getElementById('theme-toggle-mobile');
    if (themeToggleMobile && !themeToggleMobile.dataset.initialized) {
        themeToggleMobile.dataset.initialized = 'true';
        themeToggleMobile.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            toggleDarkMode();
        });
    }
    
    // Configurar menú móvil
    setupMobileMenu();
}
