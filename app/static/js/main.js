// Función para alternar el tema oscuro
function toggleDarkMode() {
    if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
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

    if (menuButton && mobileMenu) {
        const closeMenu = () => {
            menuButton.setAttribute('aria-expanded', 'false');
            mobileMenu.style.maxHeight = '0px';
            
            const icon = menuButton.querySelector('i');
            if (icon) {
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            }
        };

        mobileMenu.addEventListener('transitionend', () => {
            if (mobileMenu.style.maxHeight === '0px') {
                mobileMenu.classList.add('hidden');
            }
        });

        menuButton.addEventListener('click', (e) => {
            e.stopPropagation();
            const isExpanded = menuButton.getAttribute('aria-expanded') === 'true';

            if (isExpanded) {
                closeMenu();
            } else {
                mobileMenu.classList.remove('hidden');
                requestAnimationFrame(() => {
                    mobileMenu.style.maxHeight = mobileMenu.scrollHeight + 'px';
                    menuButton.setAttribute('aria-expanded', 'true');
                    const icon = menuButton.querySelector('i');
                    if (icon) {
                        icon.classList.remove('fa-bars');
                        icon.classList.add('fa-times');
                    }
                });
            }
        });

        document.addEventListener('click', (e) => {
            const isExpanded = menuButton.getAttribute('aria-expanded') === 'true';
            if (isExpanded && !mobileMenu.contains(e.target) && !menuButton.contains(e.target)) {
                closeMenu();
            }
        });

        window.addEventListener('resize', () => {
            if (window.innerWidth >= 768) {
                const isExpanded = menuButton.getAttribute('aria-expanded') === 'true';
                if (isExpanded) {
                    closeMenu();
                }
            }
        });
    }
}

// Inicializar cuando el DOM está listo
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar tema
    initTheme();
    
    // Configurar botón de tema
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleDarkMode);
    }
    
    // Configurar menú móvil
    setupMobileMenu();
});