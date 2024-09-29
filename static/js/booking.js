
var stripe = Stripe('pk_test_51PoO6PCoTdGj90U5E5DOanokwNOooPCC1CD4372cLYGiYdzVp4ZYyH3wtL1I85OeQM3OOWy202swRECDAYrA7ngs001l8v2VuH');

function updateButtonText() {
    var servicePrice = parseInt(document.getElementById('service').value);
    var checkoutButton = document.getElementById('checkout-button');
    var birthDetails = document.getElementById('birth-details');
    var messageContainer = document.getElementById('message-container');
    
    // Update button text
    checkoutButton.textContent = 'Pay for Your Reading - $' + servicePrice;

    // Show or hide birth details and message based on service selection
    if (servicePrice === 150 || servicePrice === 250) {
        birthDetails.classList.remove('hidden');
        messageContainer.classList.add('hidden');
    } else {
        birthDetails.classList.add('hidden');
        messageContainer.classList.remove('hidden');
    }
}

// Initialize button text and fields on load
document.getElementById('service').addEventListener('change', updateButtonText);
updateButtonText(); // Call on page load

function validateForm() {
    var isValid = true;

    var name = document.getElementById('name').value.trim();
    var email = document.getElementById('email').value.trim();
    var zodiacSign = document.getElementById('zodiac').value;
    var servicePrice = parseInt(document.getElementById('service').value);
    var dob = document.getElementById('dob').value;
    var tob = document.getElementById('tob').value;
    var pob = document.getElementById('pob').value;
    var message = document.getElementById('message').value.trim();

    // Clear error messages
    document.querySelectorAll('.error-message').forEach(el => el.classList.add('hidden'));

    // Name validation with regex (allowing only letters and spaces)
    var namePattern = /^[A-Za-zÀ-ÿ\s]+$/; // Allows letters (including accented) and spaces only
    if (!name || name.length < 2 || !namePattern.test(name)) {
        document.getElementById('name-error').classList.remove('hidden');
        isValid = false;
    }


    // Validate zodiac sign
    if (!zodiacSign) {
        document.getElementById('zodiac-error').classList.remove('hidden');
        isValid = false;
    }

    // Email validation with regex
    var emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email || !emailPattern.test(email)) {
        document.getElementById('email-error').classList.remove('hidden');
        isValid = false;
    }

    // If the service requires birth details, validate those fields
    if (servicePrice === 150 || servicePrice === 250) {
        if (!dob) {
            document.getElementById('dob-error').classList.remove('hidden');
            isValid = false;
        }
        if (!tob) {
            document.getElementById('tob-error').classList.remove('hidden');
            isValid = false;
        }
        if (!pob) {
            document.getElementById('pob-error').classList.remove('hidden');
            isValid = false;
        }
    }
    // Additional message validation
    if (servicePrice != 150 && servicePrice != 250) {
        if (message === "") {
            document.getElementById('message-error').classList.remove('hidden');
            isValid = false;
        }
    } else {
        // Clear message error if valid input
        if (message !== "") {
            document.getElementById('message-error').classList.add('hidden');
        }
    }

    return isValid;
}

// Clear message error on input
document.getElementById('message').addEventListener('input', function () {
    document.getElementById('message-error').classList.add('hidden');
});

document.getElementById('checkout-button').addEventListener('click', function(e) {
    e.preventDefault(); // Prevent form submission

    if (!validateForm()) {
        return;
    }

var name = document.getElementById('name').value;
var email = document.getElementById('email').value;
var zodiacSign = document.getElementById('zodiac').value; // Capture zodiac sign
var servicePrice = document.getElementById('service').value;
var message = document.getElementById('message').value;
var dob = document.getElementById('dob').value;
var tob = document.getElementById('tob').value;
var pob = document.getElementById('pob').value;
var csrfToken = document.querySelector('input[name="csrf_token"]').value;

var requestData = {
        name: name,
        email: email,
        zodiacSign: zodiacSign,
        servicePrice: servicePrice,
        message: servicePrice == 150 || servicePrice == 250
            ? `Date of Birth: ${dob}, Time of Birth: ${tob}, Place of Birth: ${pob}`
            : message // Message for other services
    };
    
    fetch('/create-checkout-session', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken  // Add CSRF token to headers
        },
        body: JSON.stringify(requestData)
    })
    .then(function (response) {
        return response.json();
    })
    .then(function (session) {
        return stripe.redirectToCheckout({ sessionId: session.id });
    })
    .then(function (result) {
        if (result.error) {
            alert(result.error.message);
        }
    })
    .catch(function (error) {
        console.error('Error:', error);
    });
    });



document.getElementById('hamburger').addEventListener('click', function() {
    var menu = document.getElementById('mobile-menu');
    menu.classList.toggle('hidden');
});
