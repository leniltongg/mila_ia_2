document.addEventListener('DOMContentLoaded', function() {
    // Toggle Sidebar
    const sidebarCollapse = document.getElementById('sidebarCollapse');
    const sidebar = document.getElementById('sidebar');
    
    if (sidebarCollapse) {
        sidebarCollapse.addEventListener('click', function() {
            sidebar.classList.toggle('active');
        });
    }

    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'))
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl)
    });

    // Auto-hide flash messages
    const flashMessages = document.querySelectorAll('.alert:not(.alert-permanent)');
    flashMessages.forEach(function(flash) {
        setTimeout(function() {
            const alert = new bootstrap.Alert(flash);
            alert.close();
        }, 5000);
    });

    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Password strength meter
    const passwordInput = document.querySelector('input[type="password"]');
    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            const password = this.value;
            let strength = 0;
            
            // Length check
            if (password.length >= 8) strength += 1;
            
            // Contains number
            if (/\d/.test(password)) strength += 1;
            
            // Contains letter
            if (/[a-zA-Z]/.test(password)) strength += 1;
            
            // Contains special char
            if (/[^A-Za-z0-9]/.test(password)) strength += 1;

            const strengthMeter = document.getElementById('password-strength');
            if (strengthMeter) {
                switch(strength) {
                    case 0:
                        strengthMeter.style.width = '0%';
                        strengthMeter.className = 'progress-bar bg-danger';
                        break;
                    case 1:
                        strengthMeter.style.width = '25%';
                        strengthMeter.className = 'progress-bar bg-danger';
                        break;
                    case 2:
                        strengthMeter.style.width = '50%';
                        strengthMeter.className = 'progress-bar bg-warning';
                        break;
                    case 3:
                        strengthMeter.style.width = '75%';
                        strengthMeter.className = 'progress-bar bg-info';
                        break;
                    case 4:
                        strengthMeter.style.width = '100%';
                        strengthMeter.className = 'progress-bar bg-success';
                        break;
                }
            }
        });
    }

    // DataTable defaults
    if ($.fn.dataTable !== undefined) {
        $.extend(true, $.fn.dataTable.defaults, {
            language: {
                url: "//cdn.datatables.net/plug-ins/1.10.24/i18n/Portuguese-Brasil.json"
            },
            pageLength: 10,
            responsive: true,
            dom: '<"top"<"left-col"B><"center-col"l><"right-col"f>>rtip',
            buttons: [
                {
                    extend: 'excel',
                    className: 'btn btn-sm btn-success',
                    text: '<i class="fas fa-file-excel"></i> Excel'
                },
                {
                    extend: 'pdf',
                    className: 'btn btn-sm btn-danger',
                    text: '<i class="fas fa-file-pdf"></i> PDF'
                },
                {
                    extend: 'print',
                    className: 'btn btn-sm btn-info',
                    text: '<i class="fas fa-print"></i> Imprimir'
                }
            ]
        });
    }
});
