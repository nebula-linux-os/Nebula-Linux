document.addEventListener('DOMContentLoaded', () => {
    // Dark/Light Mode Toggle
    const toggleBtn = document.getElementById('theme-toggle');
    const body = document.body;
    
    // Check local storage for theme
    const currentTheme = localStorage.getItem('theme');
    if (currentTheme === 'light') {
        body.classList.add('light-mode');
        if (toggleBtn) toggleBtn.textContent = '🌙';
    }

    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            body.classList.toggle('light-mode');
            let theme = 'dark';
            if (body.classList.contains('light-mode')) {
                theme = 'light';
                toggleBtn.textContent = '🌙';
            } else {
                toggleBtn.textContent = '☀️';
            }
            localStorage.setItem('theme', theme);
        });
    }

    // Typing Animation
    const typedTextSpan = document.querySelector(".typed-text");
    const cursorSpan = document.querySelector(".cursor");
    
    if (typedTextSpan && cursorSpan) {
        const textArray = ["sudo systemctl start nebula-linux", "Two editions. One nebula.", "Initializing desktop...", "Welcome to the future."];
        const typingDelay = 100;
        const erasingDelay = 50;
        const newTextDelay = 2000;
        let textArrayIndex = 0;
        let charIndex = 0;

        function type() {
            if (charIndex < textArray[textArrayIndex].length) {
                if(!cursorSpan.classList.contains("typing")) cursorSpan.classList.add("typing");
                typedTextSpan.textContent += textArray[textArrayIndex].charAt(charIndex);
                charIndex++;
                setTimeout(type, typingDelay);
            } 
            else {
                cursorSpan.classList.remove("typing");
                setTimeout(erase, newTextDelay);
            }
        }

        function erase() {
            if (charIndex > 0) {
                if(!cursorSpan.classList.contains("typing")) cursorSpan.classList.add("typing");
                typedTextSpan.textContent = textArray[textArrayIndex].substring(0, charIndex-1);
                charIndex--;
                setTimeout(erase, erasingDelay);
            } 
            else {
                cursorSpan.classList.remove("typing");
                textArrayIndex++;
                if(textArrayIndex >= textArray.length) textArrayIndex = 0;
                setTimeout(type, typingDelay + 1100);
            }
        }

        setTimeout(type, newTextDelay + 250);
    }

    // ── Navbar: solid background once scrolled ──────────────────
    const navbar = document.querySelector('nav');
    if (navbar) {
        const onScroll = () => navbar.classList.toggle('scrolled', window.scrollY > 30);
        onScroll();
        window.addEventListener('scroll', onScroll, { passive: true });
    }

    // ── Scroll reveal for cards / gallery ───────────────────────
    // Scroll-position based (not IntersectionObserver) so anchor jumps
    // can never leave content stuck invisible: anything at or above the
    // viewport is revealed immediately.
    const revealTargets = document.querySelectorAll(
        '.card, .gallery-img, .software-item, .hw-box, .edition-card'
    );
    if (revealTargets.length) {
        revealTargets.forEach(el => el.classList.add('reveal'));
        const revealOnScroll = () => {
            const trigger = window.innerHeight * 0.92;
            revealTargets.forEach(el => {
                if (!el.classList.contains('visible') &&
                    el.getBoundingClientRect().top < trigger) {
                    el.classList.add('visible');
                }
            });
        };
        revealOnScroll();
        window.addEventListener('scroll', revealOnScroll, { passive: true });
        window.addEventListener('resize', revealOnScroll, { passive: true });
    }

    // ── Lightbox for gallery screenshots ────────────────────────
    const lightbox = document.getElementById('lightbox');
    if (lightbox) {
        const lbImg = document.getElementById('lightbox-img');
        const lbCaption = document.getElementById('lightbox-caption');
        const btnClose = document.getElementById('lightbox-close');
        const btnPrev = document.getElementById('lightbox-prev');
        const btnNext = document.getElementById('lightbox-next');
        const images = Array.from(document.querySelectorAll('.gallery-img'));
        let current = 0;

        const show = (i) => {
            current = (i + images.length) % images.length;
            const img = images[current];
            lbImg.src = img.src;
            lbImg.alt = img.alt;
            lbCaption.textContent = img.alt || '';
        };
        const open = (i) => {
            show(i);
            lightbox.classList.add('open');
            lightbox.setAttribute('aria-hidden', 'false');
            document.body.style.overflow = 'hidden';
        };
        const close = () => {
            lightbox.classList.remove('open');
            lightbox.setAttribute('aria-hidden', 'true');
            document.body.style.overflow = '';
        };

        images.forEach((img, i) => img.addEventListener('click', () => open(i)));
        btnClose.addEventListener('click', close);
        btnPrev.addEventListener('click', (e) => { e.stopPropagation(); show(current - 1); });
        btnNext.addEventListener('click', (e) => { e.stopPropagation(); show(current + 1); });
        lightbox.addEventListener('click', (e) => { if (e.target === lightbox) close(); });
        document.addEventListener('keydown', (e) => {
            if (!lightbox.classList.contains('open')) return;
            if (e.key === 'Escape') close();
            else if (e.key === 'ArrowLeft') show(current - 1);
            else if (e.key === 'ArrowRight') show(current + 1);
        });
    }
});
