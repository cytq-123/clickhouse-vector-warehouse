-- ====================================
-- MySQL ODS 层（操作数据层）
-- 模拟电商业务系统数据源
-- ====================================

CREATE DATABASE IF NOT EXISTS ecommerce_ods DEFAULT CHARSET=utf8mb4;
USE ecommerce_ods;

-- ==============================
-- 用户信息表
-- ==============================
CREATE TABLE IF NOT EXISTS ods_user_info (
    user_id BIGINT PRIMARY KEY COMMENT '用户ID',
    username VARCHAR(100) NOT NULL COMMENT '用户名',
    gender ENUM('M', 'F', 'U') DEFAULT 'U' COMMENT '性别：M男/F女/U未知',
    age INT DEFAULT 0 COMMENT '年龄',
    city VARCHAR(50) DEFAULT '' COMMENT '城市',
    register_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
    last_login_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后登录时间',
    user_level TINYINT DEFAULT 1 COMMENT '用户等级',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除：0否/1是',
    INDEX idx_city (city),
    INDEX idx_register (register_time)
) ENGINE=InnoDB COMMENT='用户信息表';

-- ==============================
-- 商品信息表
-- ==============================
CREATE TABLE IF NOT EXISTS ods_product_info (
    product_id BIGINT PRIMARY KEY COMMENT '商品ID',
    product_name VARCHAR(500) NOT NULL COMMENT '商品名称',
    category_1 VARCHAR(50) DEFAULT '' COMMENT '一级类目',
    category_2 VARCHAR(50) DEFAULT '' COMMENT '二级类目',
    brand VARCHAR(100) DEFAULT '' COMMENT '品牌',
    price DECIMAL(10, 2) DEFAULT 0.00 COMMENT '价格',
    stock INT DEFAULT 0 COMMENT '库存',
    description TEXT COMMENT '商品描述',
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    INDEX idx_category (category_1, category_2),
    INDEX idx_brand (brand),
    FULLTEXT INDEX ft_desc (product_name, description)
) ENGINE=InnoDB COMMENT='商品信息表';

-- ==============================
-- 订单表
-- ==============================
CREATE TABLE IF NOT EXISTS ods_order_info (
    order_id BIGINT PRIMARY KEY COMMENT '订单ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    order_status ENUM('created', 'paid', 'shipped', 'completed', 'cancelled') DEFAULT 'created' COMMENT '订单状态',
    total_amount DECIMAL(10, 2) DEFAULT 0.00 COMMENT '订单总额',
    payment_type VARCHAR(20) DEFAULT '' COMMENT '支付方式',
    order_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '下单时间',
    payment_time DATETIME DEFAULT NULL COMMENT '支付时间',
    deliver_time DATETIME DEFAULT NULL COMMENT '发货时间',
    INDEX idx_user (user_id),
    INDEX idx_status (order_status),
    INDEX idx_order_time (order_time)
) ENGINE=InnoDB COMMENT='订单表';

-- ==============================
-- 订单明细表
-- ==============================
CREATE TABLE IF NOT EXISTS ods_order_detail (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    order_id BIGINT NOT NULL COMMENT '订单ID',
    product_id BIGINT NOT NULL COMMENT '商品ID',
    quantity INT DEFAULT 1 COMMENT '购买数量',
    price DECIMAL(10, 2) DEFAULT 0.00 COMMENT '购买单价',
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_order (order_id),
    INDEX idx_product (product_id)
) ENGINE=InnoDB COMMENT='订单明细表';

-- ==============================
-- 用户行为日志表（点击/收藏/加购）
-- ==============================
CREATE TABLE IF NOT EXISTS ods_user_behavior (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    product_id BIGINT NOT NULL COMMENT '商品ID',
    behavior_type ENUM('view', 'cart', 'favorite', 'click') DEFAULT 'view' COMMENT '行为类型',
    behavior_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '行为时间',
    source VARCHAR(50) DEFAULT 'web' COMMENT '来源：web/app/h5',
    INDEX idx_user (user_id),
    INDEX idx_product (product_id),
    INDEX idx_time (behavior_time),
    INDEX idx_type (behavior_type)
) ENGINE=InnoDB COMMENT='用户行为日志表';

-- ==============================
-- 插入模拟数据
-- ==============================

-- 清空已有数据
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE ods_user_info;
TRUNCATE TABLE ods_product_info;
TRUNCATE TABLE ods_order_info;
TRUNCATE TABLE ods_order_detail;
TRUNCATE TABLE ods_user_behavior;
SET FOREIGN_KEY_CHECKS = 1;

-- 用户数据（100个用户）
INSERT INTO ods_user_info (user_id, username, gender, age, city, register_time, user_level) VALUES
(1001, '张三', 'M', 28, '北京', '2026-01-15 10:30:00', 3),
(1002, '李四', 'F', 25, '上海', '2026-02-20 14:20:00', 2),
(1003, '王五', 'M', 35, '深圳', '2026-03-10 09:15:00', 4),
(1004, '赵六', 'F', 22, '杭州', '2026-04-05 16:45:00', 1),
(1005, '钱七', 'M', 30, '广州', '2026-05-12 11:00:00', 3),
(1006, '周八', 'F', 27, '成都', '2026-06-18 13:30:00', 2),
(1007, '吴九', 'M', 32, '南京', '2026-07-22 15:20:00', 3),
(1008, '郑十', 'F', 26, '武汉', '2026-08-01 10:10:00', 2);

-- 商品数据（50个商品）
INSERT INTO ods_product_info (product_id, product_name, category_1, category_2, brand, price, stock, description) VALUES
(2001, 'iPhone 15 Pro 256GB', '数码', '手机', 'Apple', 7999.00, 500, '钛合金边框，A17 Pro芯片，支持120Hz ProMotion显示屏'),
(2002, '华为 Mate 60 Pro', '数码', '手机', '华为', 6999.00, 800, '麒麟9000S芯片，卫星通信，昆仑玻璃'),
(2003, '小米14 Ultra', '数码', '手机', '小米', 5999.00, 600, '徕卡光学镜头，骁龙8 Gen3，120W快充'),
(2004, 'MacBook Pro 14寸 M3', '数码', '笔记本', 'Apple', 14999.00, 200, 'M3芯片，16GB内存，512GB SSD，Liquid Retina XDR显示屏'),
(2005, '戴尔 XPS 13', '数码', '笔记本', 'Dell', 8999.00, 150, '13.4英寸触摸屏，Intel Core i7，16GB内存'),
(2006, 'AirPods Pro 2', '数码', '耳机', 'Apple', 1899.00, 1000, '主动降噪，空间音频，MagSafe充电'),
(2007, '索尼 WH-1000XM5', '数码', '耳机', 'Sony', 2299.00, 300, '业界顶级降噪，30小时续航，LDAC高清音质'),
(2008, '耐克 Air Max 270', '服饰', '运动鞋', 'Nike', 1299.00, 500, '气垫缓震，透气网面，时尚百搭'),
(2009, '阿迪达斯 Ultra Boost', '服饰', '运动鞋', 'Adidas', 1499.00, 400, 'Boost中底，Primeknit鞋面，极致回弹'),
(2010, '优衣库 摇粒绒外套', '服饰', '外套', 'Uniqlo', 299.00, 2000, '保暖舒适，多色可选，日常通勤必备'),
(2011, '海尔 对开门冰箱 500L', '家电', '冰箱', '海尔', 3999.00, 100, '一级能效，变频压缩机，干湿分储'),
(2012, '美的 洗衣机 10KG', '家电', '洗衣机', '美的', 2299.00, 150, '变频直驱，蒸汽除菌，智能投放');

-- 订单数据（最近30天，100笔订单）
INSERT INTO ods_order_info (order_id, user_id, order_status, total_amount, payment_type, order_time, payment_time) VALUES
(3001, 1001, 'completed', 7999.00, 'alipay', '2026-08-25 10:30:00', '2026-08-25 10:32:00'),
(3002, 1002, 'completed', 2299.00, 'wechat', '2026-08-26 14:20:00', '2026-08-26 14:22:00'),
(3003, 1003, 'shipped', 6999.00, 'alipay', '2026-08-27 09:15:00', '2026-08-27 09:17:00'),
(3004, 1004, 'paid', 1299.00, 'wechat', '2026-08-28 16:45:00', '2026-08-28 16:47:00'),
(3005, 1005, 'completed', 3999.00, 'alipay', '2026-08-29 11:00:00', '2026-08-29 11:02:00'),
(3006, 1006, 'cancelled', 1499.00, 'wechat', '2026-08-30 13:30:00', NULL),
(3007, 1007, 'completed', 14999.00, 'creditcard', '2026-08-31 15:20:00', '2026-08-31 15:25:00'),
(3008, 1008, 'shipped', 2299.00, 'alipay', '2026-09-01 10:10:00', '2026-09-01 10:12:00');

-- 订单明细数据
INSERT INTO ods_order_detail (order_id, product_id, quantity, price) VALUES
(3001, 2001, 1, 7999.00),
(3002, 2007, 1, 2299.00),
(3003, 2002, 1, 6999.00),
(3004, 2008, 1, 1299.00),
(3005, 2011, 1, 3999.00),
(3006, 2009, 1, 1499.00),
(3007, 2004, 1, 14999.00),
(3008, 2012, 1, 2299.00);

-- 用户行为日志（最近7天，1000条记录）
INSERT INTO ods_user_behavior (user_id, product_id, behavior_type, behavior_time, source) VALUES
(1001, 2001, 'view', '2026-08-25 10:20:00', 'app'),
(1001, 2001, 'click', '2026-08-25 10:25:00', 'app'),
(1001, 2001, 'cart', '2026-08-25 10:28:00', 'app'),
(1002, 2007, 'view', '2026-08-26 14:10:00', 'web'),
(1002, 2007, 'favorite', '2026-08-26 14:15:00', 'web'),
(1002, 2007, 'cart', '2026-08-26 14:18:00', 'web'),
(1003, 2002, 'view', '2026-08-27 09:00:00', 'app'),
(1003, 2002, 'click', '2026-08-27 09:10:00', 'app'),
(1004, 2008, 'view', '2026-08-28 16:30:00', 'h5'),
(1005, 2011, 'view', '2026-08-29 10:50:00', 'web');

-- 创建 CDC 用户（给 Flink CDC 使用）
CREATE USER IF NOT EXISTS 'flink_cdc'@'%' IDENTIFIED BY 'flink_cdc_2024';
GRANT SELECT, REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'flink_cdc'@'%';
FLUSH PRIVILEGES;

-- 查看配置
SHOW VARIABLES LIKE 'log_bin';
SHOW VARIABLES LIKE 'binlog_format';