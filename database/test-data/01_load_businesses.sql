-- Load 10 test businesses
INSERT INTO runtime.business (business_id, name, industry, country, created_at) VALUES
('biz_001', 'TechGadgets Online', 'Electronics', 'US', NOW()),
('biz_002', 'FashionHub Direct', 'Apparel', 'US', NOW()),
('biz_003', 'Downtown Bookstore', 'Books', 'US', NOW()),
('biz_004', 'Main St Hardware', 'Hardware', 'US', NOW()),
('biz_005', 'Holiday Decorations Inc', 'Home Decor', 'US', NOW()),
('biz_006', 'Summer Gear Shop', 'Sports', 'US', NOW()),
('biz_007', 'Premium Coffee Roastery', 'Food & Beverage', 'US', NOW()),
('biz_008', 'Artisan Jewelry Studio', 'Jewelry', 'US', NOW()),
('biz_009', 'Omni Retail Group', 'General Merchandise', 'US', NOW()),
('biz_010', 'Cross-Channel Fashion', 'Apparel', 'US', NOW());

SELECT COUNT(*) as business_count FROM runtime.business WHERE business_id LIKE 'biz_%';
