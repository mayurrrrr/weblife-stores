# targets.py

LENOVO_E14_INTEL_URL = "https://www.lenovo.com/us/en/p/laptops/thinkpad/thinkpade/thinkpad-e14-gen-5-14-inch-intel/21jk0053us"
LENOVO_E14_AMD_URL   = "https://www.lenovo.com/us/en/p/laptops/thinkpad/thinkpade/thinkpad-e14-gen-5-14-inch-amd/21jk0008us"

HP_PROBOOK_440_PDP   = "https://www.hp.com/us-en/shop/pdp/hp-probook-440-14-inch-g11-notebook-pc"
HP_PROBOOK_450_PDP   = "https://www.hp.com/us-en/shop/pdp/hp-probook-450-156-inch-g10-notebook-pc-wolf-pro-security-edition-p-8l0e0ua-aba-1"

HP_PROBOOK_440_REVIEWS = "https://www.hp.com/us-en/shop/reviews/hp-probook-440-14-inch-g11-notebook-pc"
HP_PROBOOK_440_REVIEWS_SKU = "https://www.hp.com/us-en/shop/reviews/hp-probook-440-14-inch-g11-notebook-pc-p-a3rn0ua-aba-1"
HP_PROBOOK_450_REVIEWS = "https://www.hp.com/us-en/shop/reviews/hp-probook-450-156-inch-g10-notebook-pc-wolf-pro-security-edition-p-8l0e0ua-aba-1"

TARGETS = {
    "lenovo_e14_intel": {
        "pdp": LENOVO_E14_INTEL_URL,
        "reviews": [],
        "qna": []
    },
    "lenovo_e14_amd": {
        "pdp": LENOVO_E14_AMD_URL,
        "reviews": [],
        "qna": []
    },
    "hp_probook_440": {
        "pdp": HP_PROBOOK_440_PDP,
        "reviews": [HP_PROBOOK_440_REVIEWS, HP_PROBOOK_440_REVIEWS_SKU],
        "qna": [HP_PROBOOK_440_REVIEWS, HP_PROBOOK_440_REVIEWS_SKU]
    },
    "hp_probook_450": {
        "pdp": HP_PROBOOK_450_PDP,
        "reviews": [HP_PROBOOK_450_REVIEWS],
        "qna": [HP_PROBOOK_450_REVIEWS]
    }
}
