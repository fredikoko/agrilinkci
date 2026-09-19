from kivy.app import App
from kivy.uix.screenmanager import ScreenManager

try:
    from .screens.onboarding_screen import OnboardingScreen
    from .screens.login_screen import LoginScreen
    from .screens.signup_screen import SignupScreen
    from .screens.signup_verify_screen import SignupVerifyScreen
    from .screens.notifications_screen import NotificationsScreen
    from .screens.buyer_profile_screen import BuyerProfileScreen
    from .screens.home_screen import HomeScreen
    from .screens.vendor_list_screen import VendorListScreen
    from .screens.results_screen import ResultsScreen
    from .screens.vendor_detail_screen import VendorDetailScreen
    from .screens.contact_screen import ContactScreen
    from .screens.advanced_search_screen import AdvancedSearchScreen
    from .screens.favorites_screen import FavoritesScreen
    from .screens.tips_screen import TipsScreen
    from .screens.user_profile_screen import UserProfileScreen
    from .screens.seller_screen import SellerScreen
    from .screens.seller_subscription_screen import SellerSubscriptionScreen
    from .screens.seller_analytics_screen import SellerAnalyticsScreen
    from .screens.seller_stock_screen import SellerStockScreen
    from .screens.conseil_screen import ConseilScreen
    from .screens.article_detail_screen import ArticleDetailScreen
    from .screens.alertes_screen import AlertesScreen
    from .screens.conseil_subscription_screen import ConseilSubscriptionScreen
    from .screens.conseil_diagnostic_screen import ConseilDiagnosticScreen
    from .screens.conseil_dashboard_screen import ConseilDashboardScreen
    from .screens.provider_list_screen import ProviderListScreen
    from .screens.provider_detail_screen import ProviderDetailScreen
    from .screens.provider_screen import ProviderScreen
except ImportError:
    from screens.onboarding_screen import OnboardingScreen
    from screens.login_screen import LoginScreen
    from screens.signup_screen import SignupScreen
    from screens.signup_verify_screen import SignupVerifyScreen
    from screens.notifications_screen import NotificationsScreen
    from screens.buyer_profile_screen import BuyerProfileScreen
    from screens.home_screen import HomeScreen
    from screens.vendor_list_screen import VendorListScreen
    from screens.results_screen import ResultsScreen
    from screens.vendor_detail_screen import VendorDetailScreen
    from screens.contact_screen import ContactScreen
    from screens.advanced_search_screen import AdvancedSearchScreen
    from screens.favorites_screen import FavoritesScreen
    from screens.tips_screen import TipsScreen
    from screens.user_profile_screen import UserProfileScreen
    from screens.seller_screen import SellerScreen
    from screens.seller_subscription_screen import SellerSubscriptionScreen
    from screens.seller_analytics_screen import SellerAnalyticsScreen
    from screens.seller_stock_screen import SellerStockScreen
    from screens.conseil_screen import ConseilScreen
    from screens.article_detail_screen import ArticleDetailScreen
    from screens.alertes_screen import AlertesScreen
    from screens.conseil_subscription_screen import ConseilSubscriptionScreen
    from screens.conseil_diagnostic_screen import ConseilDiagnosticScreen
    from screens.conseil_dashboard_screen import ConseilDashboardScreen
    from screens.provider_list_screen import ProviderListScreen
    from screens.provider_detail_screen import ProviderDetailScreen
    from screens.provider_screen import ProviderScreen


class AgriLinkApp(App):
    title = "AgriLink CI"

    def build(self):
        manager = ScreenManager()
        manager.add_widget(OnboardingScreen(name="onboarding"))
        manager.add_widget(LoginScreen(name="login"))
        manager.add_widget(SignupScreen(name="signup"))
        manager.add_widget(SignupVerifyScreen(name="signup-verify"))
        manager.add_widget(NotificationsScreen(name="notifications"))
        manager.add_widget(BuyerProfileScreen(name="buyer-profile"))
        manager.add_widget(HomeScreen(name="home"))
        manager.add_widget(VendorListScreen(name="vendors"))
        manager.add_widget(ResultsScreen(name="results"))
        manager.add_widget(VendorDetailScreen(name="detail"))
        manager.add_widget(ContactScreen(name="contact"))
        manager.add_widget(AdvancedSearchScreen(name="advanced-search"))
        manager.add_widget(FavoritesScreen(name="favorites"))
        manager.add_widget(TipsScreen(name="tips"))
        manager.add_widget(UserProfileScreen(name="user-profile"))
        manager.add_widget(SellerScreen(name="seller"))
        manager.add_widget(SellerSubscriptionScreen(name="seller-subscription"))
        manager.add_widget(SellerAnalyticsScreen(name="seller-analytics"))
        manager.add_widget(SellerStockScreen(name="seller-stock"))
        manager.add_widget(ConseilScreen(name="conseil"))
        manager.add_widget(ArticleDetailScreen(name="article-detail"))
        manager.add_widget(AlertesScreen(name="alertes"))
        manager.add_widget(ConseilSubscriptionScreen(name="conseil-subscription"))
        manager.add_widget(ConseilDiagnosticScreen(name="conseil-diagnostic"))
        manager.add_widget(ConseilDashboardScreen(name="conseil-dashboard"))
        manager.add_widget(ProviderListScreen(name="providers"))
        manager.add_widget(ProviderDetailScreen(name="provider-detail"))
        manager.add_widget(ProviderScreen(name="provider-space"))
        manager.current = "onboarding"
        return manager


if __name__ == "__main__":
    AgriLinkApp().run()
