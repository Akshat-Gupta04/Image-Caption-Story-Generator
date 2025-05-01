document.addEventListener('DOMContentLoaded', function() {
    // Initialize particles background
    if (typeof particlesJS !== 'undefined') {
        particlesJS('particles-js', {
            particles: {
                number: {
                    value: 50,
                    density: {
                        enable: true,
                        value_area: 800
                    }
                },
                color: {
                    value: ['#6c5ce7', '#00cec9', '#a29bfe', '#74b9ff']
                },
                shape: {
                    type: 'circle',
                    stroke: {
                        width: 0,
                        color: '#000000'
                    },
                    polygon: {
                        nb_sides: 5
                    }
                },
                opacity: {
                    value: 0.3,
                    random: true,
                    anim: {
                        enable: true,
                        speed: 0.5,
                        opacity_min: 0.1,
                        sync: false
                    }
                },
                size: {
                    value: 3,
                    random: true,
                    anim: {
                        enable: true,
                        speed: 2,
                        size_min: 0.1,
                        sync: false
                    }
                },
                line_linked: {
                    enable: true,
                    distance: 150,
                    color: '#6c5ce7',
                    opacity: 0.2,
                    width: 1
                },
                move: {
                    enable: true,
                    speed: 1,
                    direction: 'none',
                    random: true,
                    straight: false,
                    out_mode: 'out',
                    bounce: false,
                    attract: {
                        enable: true,
                        rotateX: 600,
                        rotateY: 1200
                    }
                }
            },
            interactivity: {
                detect_on: 'canvas',
                events: {
                    onhover: {
                        enable: true,
                        mode: 'grab'
                    },
                    onclick: {
                        enable: true,
                        mode: 'push'
                    },
                    resize: true
                },
                modes: {
                    grab: {
                        distance: 140,
                        line_linked: {
                            opacity: 0.5
                        }
                    },
                    bubble: {
                        distance: 400,
                        size: 4,
                        duration: 2,
                        opacity: 0.8,
                        speed: 3
                    },
                    repulse: {
                        distance: 200,
                        duration: 0.4
                    },
                    push: {
                        particles_nb: 4
                    },
                    remove: {
                        particles_nb: 2
                    }
                }
            },
            retina_detect: true
        });
    }

    // File upload preview
    const fileInput = document.getElementById('images');
    const filePreview = document.querySelector('.file-preview');

    if (fileInput && filePreview) {
        fileInput.addEventListener('change', function() {
            filePreview.innerHTML = '';

            if (this.files.length > 0) {
                document.querySelector('.file-upload-text').textContent = `${this.files.length} file(s) selected`;

                for (let i = 0; i < this.files.length; i++) {
                    const file = this.files[i];
                    if (file.type.startsWith('image/')) {
                        const reader = new FileReader();

                        reader.onload = function(e) {
                            const previewItem = document.createElement('div');
                            previewItem.className = 'file-preview-item';
                            previewItem.innerHTML = `
                                <img src="${e.target.result}" alt="Preview">
                                <div class="file-preview-remove" data-index="${i}">×</div>
                            `;
                            filePreview.appendChild(previewItem);

                            // Add animation delay for staggered effect
                            previewItem.style.animationDelay = `${i * 0.1}s`;
                        };

                        reader.readAsDataURL(file);
                    }
                }
            } else {
                document.querySelector('.file-upload-text').textContent = 'Drag & drop images here or click to browse';
            }
        });

        // Handle file removal (note: this is visual only, would need a more complex solution for actual file removal)
        filePreview.addEventListener('click', function(e) {
            if (e.target.classList.contains('file-preview-remove')) {
                e.target.parentElement.remove();
            }
        });
    }

    // Form submission loading animation
    const uploadForm = document.querySelector('form');
    const loadingContainer = document.querySelector('.loading-container');
    const progressBar = document.querySelector('.loading-progress-bar');

    if (uploadForm && loadingContainer && progressBar) {
        uploadForm.addEventListener('submit', function(e) {
            // Show loading screen
            loadingContainer.classList.add('active');

            // Simulate progress (in a real app, you'd use AJAX to track actual progress)
            let progress = 0;
            const interval = setInterval(function() {
                progress += Math.random() * 10;
                if (progress > 100) progress = 100;

                progressBar.style.width = `${progress}%`;

                if (progress === 100) {
                    clearInterval(interval);
                }
            }, 500);
        });
    }

    // Typewriter effect for story text
    const storyText = document.querySelector('.story-text');
    if (storyText && !storyText.classList.contains('typewriter-applied')) {
        const text = storyText.textContent;
        storyText.textContent = '';
        storyText.classList.add('typewriter-applied');

        let i = 0;
        const speed = 20; // typing speed in milliseconds

        function typeWriter() {
            if (i < text.length) {
                storyText.textContent += text.charAt(i);
                i++;
                setTimeout(typeWriter, speed);
            }
        }

        // Start the typewriter effect with a slight delay
        setTimeout(typeWriter, 500);
    }

    // Image hover effects
    const imageCards = document.querySelectorAll('.image-card');
    imageCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px)';
            this.style.boxShadow = '0 20px 40px rgba(0, 0, 0, 0.5)';
        });

        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 8px 30px rgba(0, 0, 0, 0.3)';
        });
    });

    // Smooth scroll to top when clicking "Generate Another Story" button
    const generateAgainBtn = document.querySelector('a[href="/"]');
    if (generateAgainBtn) {
        generateAgainBtn.addEventListener('click', function(e) {
            e.preventDefault();
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
            setTimeout(() => {
                window.location.href = this.getAttribute('href');
            }, 500);
        });
    }
});
