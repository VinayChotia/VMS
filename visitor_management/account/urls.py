from django.urls import path
from . import views
from .views import *

urlpatterns = [
    # Authentication endpoints
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('auth/refresh/', views.RefreshTokenView.as_view(), name='token_refresh'),
    
    # Employee endpoints
    path('employees/', views.EmployeeListView.as_view(), name='employee-list'),
    path('employees/me/', views.CurrentEmployeeView.as_view(), name='employee-me'),
    path('employees/<int:pk>/', views.EmployeeDetailView.as_view(), name='employee-detail'),
    
    # Visitor endpoints
    path('visitors/', views.VisitorListView.as_view(), name='visitor-list'),
    path('visitors/<int:pk>/', views.VisitorDetailView.as_view(), name='visitor-detail'),
    path('visitors/<int:pk>/approve/', views.VisitorApproveView.as_view(), name='visitor-approve'),
    path('visitors/<int:pk>/check-in/', views.VisitorCheckInView.as_view(), name='visitor-checkin'),
    path('visitors/<int:pk>/check-out/', views.VisitorCheckOutView.as_view(), name='visitor-checkout'),
    
    # Specialized queries
    path('visitors/status/<str:status>/', views.VisitorsByStatusView.as_view(), name='visitors-by-status'),
    path('my-approvals/', views.MyApprovalsView.as_view(), name='my-approvals'),
    path('visitor-stats/', views.VisitorStatsView.as_view(), name='visitor-stats'),
    path('visitors/bulk-approve/', views.BulkVisitorApprovalView.as_view(), name='bulk-approve'),

    # new urls including sections and site and locations 

    path('api/sites/', SiteListView.as_view(), name='site-list'),
    path('api/sites/<int:pk>/', SiteDetailView.as_view(), name='site-detail'),
    path('api/sites/<int:site_id>/available-sections/', AvailableSectionsView.as_view(), name='available-sections'),
    path('api/sites/<int:site_id>/cooldown-status/', SiteCooldownStatusView.as_view(), name='site-cooldown'),
    
    # Location Management
    path('api/locations/', LocationListView.as_view(), name='location-list'),
    path('api/sites/<int:site_id>/locations/', LocationListView.as_view(), name='site-locations'),
    
    # Section Management
    path('api/sections/', SectionListView.as_view(), name='section-list'),
    path('api/locations/<int:location_id>/sections/', SectionListView.as_view(), name='location-sections'),
    
    # Cooldown Management (Superadmin only)
    path('api/admin/cooldowns/', CooldownPeriodListView.as_view(), name='cooldown-list'),
    path('api/admin/cooldowns/<int:pk>/', CooldownPeriodDetailView.as_view(), name='cooldown-detail'),
    
    # Section-based Approvals
    path('api/visitors/<int:visitor_id>/approve-sections/', VisitorSectionApprovalView.as_view(), name='approve-sections'),
    path('api/visitors/<int:visitor_id>/pending-sections/', VisitorPendingSectionsView.as_view(), name='pending-sections'),
    path('api/visitors/<int:visitor_id>/access-matrix/', VisitorAccessMatrixView.as_view(), name='access-matrix'),

    # need to filter down these urls

    path('api/daily-capacity/', DailyCapacityLimitView.as_view(), name='daily-capacity'),
    path('api/daily-capacity/<int:site_id>/', DailyCapacityLimitView.as_view(), name='daily-capacity-site'),
    
    path('api/today-visitors/', TodayVisitorCountView.as_view(), name='today-visitors'),
    path('api/today-visitors/<int:site_id>/', TodayVisitorCountView.as_view(), name='today-visitors-site'),
    
    path('api/capacity-status/', VisitorCapacityStatusView.as_view(), name='capacity-status'),
    path('api/capacity-status/<int:site_id>/', VisitorCapacityStatusView.as_view(), name='capacity-status-site'),
]