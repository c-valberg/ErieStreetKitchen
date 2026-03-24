// =============================================
// ERIE STREET KITCHEN — script.js
// =============================================

// Smooth Scroll — offset by fixed navbar height
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            const navHeight = document.querySelector('.navbar').offsetHeight;
            const top = target.getBoundingClientRect().top + window.scrollY - navHeight;
            window.scrollTo({ top, behavior: 'smooth' });
        }
        closeMobileMenu();
    });
});

// Navbar background on scroll
window.addEventListener('scroll', function () {
    const nav = document.querySelector('.navbar');
    nav.classList.toggle('scrolled', window.scrollY > 50);
});

// Hamburger toggle
const hamburger = document.querySelector('.hamburger');
const mobileMenu = document.querySelector('.mobile-menu');
const navbar    = document.querySelector('.navbar');

hamburger.addEventListener('click', function () {
    const isOpen = mobileMenu.classList.contains('open');

    if (!isOpen) {
        openMobileMenu();
    } else {
        closeMobileMenu();
    }
});

function openMobileMenu() {
    mobileMenu.classList.add('open');
    hamburger.classList.add('open');
    hamburger.setAttribute('aria-expanded', 'true');
    navbar.classList.add('scrolled', 'menu-open');
}

function closeMobileMenu() {
    mobileMenu.classList.remove('open');
    hamburger.classList.remove('open');
    hamburger.setAttribute('aria-expanded', 'false');
    navbar.classList.remove('menu-open');

    // Only remove scrolled background if user hasn't scrolled
    if (window.scrollY <= 50) {
        navbar.classList.remove('scrolled');
    }
}
// Scroll-triggered animations
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
        }
    });
}, { threshold: 0.15 });


// Scroll hint click
document.querySelectorAll('.animate-up').forEach(el => observer.observe(el));

// Loading screen
const loader = document.getElementById('loader');
const bar = document.querySelector('.loader-bar');

let progress = 0;
const interval = setInterval(() => {
    progress += Math.random() * 15;
    if (progress > 90) progress = 90;
    bar.style.width = progress + '%';
}, 100);

const minDisplay = new Promise(res => setTimeout(res, 1400));
const pageLoad   = new Promise(res => window.addEventListener('load', res));

Promise.all([minDisplay, pageLoad]).then(() => {
    clearInterval(interval);
    bar.style.width = '100%';
    setTimeout(() => {
        loader.classList.add('hidden');
        loader.addEventListener('transitionend', () => loader.remove(), { once: true });
    }, 400);
});