from pathlib import Path
import re

project = Path('/home/ubuntu/agri_link_ci')
mobile = project / 'mobile'
screens_dir = mobile / 'screens'
screens_dir.mkdir(exist_ok=True)
source_path = mobile / 'main.py'
source = source_path.read_text(encoding='utf-8')

class_names = {
    'OnboardingScreen': 'onboarding_screen.py',
    'LoginScreen': 'login_screen.py',
    'BuyerProfileScreen': 'buyer_profile_screen.py',
    'HomeScreen': 'home_screen.py',
    'VendorListScreen': 'vendor_list_screen.py',
    'VendorDetailScreen': 'vendor_detail_screen.py',
    'ContactScreen': 'contact_screen.py',
    'AdvancedSearchScreen': 'advanced_search_screen.py',
    'FavoritesScreen': 'favorites_screen.py',
    'TipsScreen': 'tips_screen.py',
    'UserProfileScreen': 'user_profile_screen.py',
    'SellerScreen': 'seller_screen.py',
}

matches = list(re.finditer(r'^class (\w+)\b', source, flags=re.MULTILINE))
positions = {m.group(1): (m.start(), matches[i + 1].start() if i + 1 < len(matches) else source.find('\nclass AgriLinkApp')) for i, m in enumerate(matches)}
first_screen_start = positions['OnboardingScreen'][0]
core_source = source[:first_screen_start].rstrip() + '\n'
core_source = core_source.replace('from kivy.app import App\n', '')
(mobile / 'core.py').write_text(core_source, encoding='utf-8')

common_header = '''import json\nimport os\nimport re\nimport webbrowser\nfrom typing import Any\nfrom urllib.parse import urlencode\n\nfrom kivy.clock import Clock\nfrom kivy.metrics import dp\nfrom kivy.uix.boxlayout import BoxLayout\nfrom kivy.uix.button import Button\nfrom kivy.uix.gridlayout import GridLayout\nfrom kivy.uix.label import Label\nfrom kivy.uix.screenmanager import Screen\nfrom kivy.uix.scrollview import ScrollView\nfrom kivy.uix.spinner import Spinner\nfrom kivy.uix.textinput import TextInput\n\ntry:\n    from ..core import *\nexcept ImportError:\n    from core import *\n\n'''

for class_name, filename in class_names.items():
    start, end = positions[class_name]
    body = source[start:end].rstrip() + '\n'
    (screens_dir / filename).write_text(common_header + body, encoding='utf-8')

(screens_dir / '__init__.py').write_text('', encoding='utf-8')

main_source = '''from kivy.app import App\nfrom kivy.screenmanager import ScreenManager\n\ntry:\n    from .screens.onboarding_screen import OnboardingScreen\n    from .screens.login_screen import LoginScreen\n    from .screens.buyer_profile_screen import BuyerProfileScreen\n    from .screens.home_screen import HomeScreen\n    from .screens.vendor_list_screen import VendorListScreen\n    from .screens.vendor_detail_screen import VendorDetailScreen\n    from .screens.contact_screen import ContactScreen\n    from .screens.advanced_search_screen import AdvancedSearchScreen\n    from .screens.favorites_screen import FavoritesScreen\n    from .screens.tips_screen import TipsScreen\n    from .screens.user_profile_screen import UserProfileScreen\n    from .screens.seller_screen import SellerScreen\nexcept ImportError:\n    from screens.onboarding_screen import OnboardingScreen\n    from screens.login_screen import LoginScreen\n    from screens.buyer_profile_screen import BuyerProfileScreen\n    from screens.home_screen import HomeScreen\n    from screens.vendor_list_screen import VendorListScreen\n    from screens.vendor_detail_screen import VendorDetailScreen\n    from screens.contact_screen import ContactScreen\n    from screens.advanced_search_screen import AdvancedSearchScreen\n    from screens.favorites_screen import FavoritesScreen\n    from screens.tips_screen import TipsScreen\n    from screens.user_profile_screen import UserProfileScreen\n    from screens.seller_screen import SellerScreen\n\n\nclass AgriLinkApp(App):\n    title = "AgriLink CI"\n\n    def build(self):\n        manager = ScreenManager()\n        manager.add_widget(OnboardingScreen(name="onboarding"))\n        manager.add_widget(LoginScreen(name="login"))\n        manager.add_widget(BuyerProfileScreen(name="buyer-profile"))\n        manager.add_widget(HomeScreen(name="home"))\n        manager.add_widget(VendorListScreen(name="vendors"))\n        manager.add_widget(VendorDetailScreen(name="detail"))\n        manager.add_widget(ContactScreen(name="contact"))\n        manager.add_widget(AdvancedSearchScreen(name="advanced-search"))\n        manager.add_widget(FavoritesScreen(name="favorites"))\n        manager.add_widget(TipsScreen(name="tips"))\n        manager.add_widget(UserProfileScreen(name="user-profile"))\n        manager.add_widget(SellerScreen(name="seller"))\n        manager.current = "onboarding"\n        return manager\n\n\nif __name__ == "__main__":\n    AgriLinkApp().run()\n'''
source_path.write_text(main_source, encoding='utf-8')

readme = mobile / 'STRUCTURE.md'
readme.write_text('''# Structure modulaire de l’application Kivy\n\n`main.py` assemble uniquement le `ScreenManager`. Les services partagés et chaque écran sont séparés dans des fichiers dédiés.\n\n- `core.py` : thème blanc, constantes, composants communs et `ApiClient`.\n- `screens/onboarding_screen.py` : onboarding.\n- `screens/login_screen.py` : connexion OTP.\n- `screens/buyer_profile_screen.py` : localisation acheteur.\n- `screens/home_screen.py` : accueil personnalisé.\n- `screens/vendor_list_screen.py` : liste des vendeurs.\n- `screens/vendor_detail_screen.py` : fiche vendeur.\n- `screens/contact_screen.py` : appel et WhatsApp.\n- `screens/advanced_search_screen.py` : recherche avancée.\n- `screens/favorites_screen.py` : favoris.\n- `screens/tips_screen.py` : conseils agricoles.\n- `screens/user_profile_screen.py` : profil utilisateur.\n- `screens/seller_screen.py` : inscription vendeur, abonnement Paystack et défilement.\n\nDepuis le dossier `mobile`, lancer `python main.py`.\n''', encoding='utf-8')
print('Refactorisation terminée:', len(class_names), 'écrans extraits')
