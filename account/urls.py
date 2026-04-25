from django.urls import path
from account import views

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
    # path('visitors/<int:pk>/approve/', views.VisitorApproveView.as_view(), name='visitor-approve'),
    path('visitors/<int:pk>/check-in/', views.VisitorCheckInView.as_view(), name='visitor-checkin'),
    path('visitors/<int:pk>/check-out/', views.VisitorCheckOutView.as_view(), name='visitor-checkout'),
    path('api/my-pending-section-approvals/', views.MyPendingSectionApprovalsView.as_view(), name='my-pending-section-approvals'),
    
    # Specialized queries
    path('visitors/status/<str:status>/', views.VisitorsByStatusView.as_view(), name='visitors-by-status'),
    path('my-approvals/', views.MyApprovalsView.as_view(), name='my-approvals'),
    path('visitor-stats/', views.VisitorStatsView.as_view(), name='visitor-stats'),
    path('visitors/bulk-approve/', views.BulkVisitorApprovalView.as_view(), name='bulk-approve'),

    # new urls including sections and site and locations 

    path('api/sites/', views.SiteListView.as_view(), name='site-list'),
    path('api/sites/<int:pk>/', views.SiteDetailView.as_view(), name='site-detail'),
    path('api/sites/<int:site_id>/available-sections/', views.AvailableSectionsView.as_view(), name='available-sections'),
    path('api/sites/<int:site_id>/cooldown-status/', views.SiteCooldownStatusView.as_view(), name='site-cooldown'),
    
    # Location Management
    path('api/locations/', views.LocationListView.as_view(), name='location-list'),
    path('api/sites/<int:site_id>/locations/', views.LocationListView.as_view(), name='site-locations'),
    
    # Section Management
    path('api/sections/', views.SectionListView.as_view(), name='section-list'),
    path('api/locations/<int:location_id>/sections/', views.SectionListView.as_view(), name='location-sections'),
    
    # Cooldown Management (Superadmin only)
    path('api/admin/cooldowns/', views.CooldownPeriodListView.as_view(), name='cooldown-list'),
    path('api/admin/cooldowns/<int:pk>/', views.CooldownPeriodDetailView.as_view(), name='cooldown-detail'),
    
    # Section-based Approvals
    path('api/visitors/<int:visitor_id>/approve-sections/', views.VisitorSectionApprovalView.as_view(), name='approve-sections'),
    path('api/visitors/<int:visitor_id>/pending-sections/', views.VisitorPendingSectionsView.as_view(), name='pending-sections'),
    path('api/visitors/<int:visitor_id>/access-matrix/', views.VisitorAccessMatrixView.as_view(), name='access-matrix'),

    # need to filter down these urls

    path('api/daily-capacity/', views.DailyCapacityLimitView.as_view(), name='daily-capacity'),
    path('api/daily-capacity/<int:site_id>/', views.DailyCapacityLimitView.as_view(), name='daily-capacity-site'),
    
    path('api/today-visitors/', views.TodayVisitorCountView.as_view(), name='today-visitors'),
    path('api/today-visitors/<int:site_id>/', views.TodayVisitorCountView.as_view(), name='today-visitors-site'),
    
    path('api/capacity-status/', views.VisitorCapacityStatusView.as_view(), name='capacity-status'),
    path('api/capacity-status/<int:site_id>/', views.VisitorCapacityStatusView.as_view(), name='capacity-status-site'),

    path('api/visitors/<int:visitor_id>/section-tracking/', 
         views.VisitorSectionTrackingView.as_view(), 
         name='section-tracking'),
    
    path('api/visitors/<int:visitor_id>/section-checkin/', 
         views.VisitorSectionCheckInView.as_view(), 
         name='section-checkin'),
    
    path('api/visitors/<int:visitor_id>/section-checkout/', 
         views.VisitorSectionCheckOutView.as_view(), 
         name='section-checkout'),
    
    path('api/visitors/<int:visitor_id>/complete-profile/', 
         views.VisitorCompleteProfileView.as_view(), 
         name='visitor-complete-profile'),
    
    path('api/visitors/<int:visitor_id>/auto-create-tracking/', 
         views.AutoCreateSectionTrackingView.as_view(), 
         name='auto-create-tracking'),

     # export reports

     path('api/export/visitors/', views.ExportVisitorsToExcelView.as_view(), name='export-visitors'),
     path('dashboard-counts/',views.DashboardCountsView.as_view(),name='dashboard-count'),
     path('api/visitors/search/', views.VisitorSearchView.as_view(), name='visitor-search'),


     # QR Code and ID Card endpoints
    path('api/visitors/<int:pk>/qr-code/', views.VisitorQRCodeView.as_view(), name='visitor-qr-code'),
    path('api/visitors/<int:pk>/id-card/', views.VisitorIDCardView.as_view(), name='visitor-id-card'),
    path('api/visitors/bulk-id-cards/', views.VisitorBulkIDCardView.as_view(), name='bulk-id-cards'),
]