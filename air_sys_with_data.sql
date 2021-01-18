/*
 Navicat Premium Data Transfer

 Source Server         : test1
 Source Server Type    : MySQL
 Source Server Version : 80019
 Source Host           : localhost:3306
 Source Schema         : air_sys

 Target Server Type    : MySQL
 Target Server Version : 80019
 File Encoding         : 65001

 Date: 11/06/2020 14:32:34
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for log
-- ----------------------------
DROP TABLE IF EXISTS `log`;
CREATE TABLE `log` (
  `log_id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `day` varchar(25) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL,
  `roomid` int NOT NULL,
  `log` varchar(255) CHARACTER SET utf8 COLLATE utf8_bin DEFAULT NULL,
  `level` varchar(255) COLLATE utf8_bin DEFAULT NULL,
  `target_temp` int DEFAULT NULL,
  `cur_temp` float DEFAULT NULL,
  `end_energy` float(255,5) DEFAULT NULL,
  PRIMARY KEY (`log_id`)
) ENGINE=InnoDB AUTO_INCREMENT=134 DEFAULT CHARSET=utf8 COLLATE=utf8_bin;

-- ----------------------------
-- Records of log
-- ----------------------------

-- ----------------------------
-- Table structure for roomsg
-- ----------------------------
DROP TABLE IF EXISTS `roomsg`;
CREATE TABLE `roomsg` (
  `roomid` int NOT NULL,
  `personid` varchar(255) CHARACTER SET utf8 COLLATE utf8_bin DEFAULT NULL,
  PRIMARY KEY (`roomid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;

-- ----------------------------
-- Records of roomsg
-- ----------------------------
BEGIN;
INSERT INTO `roomsg` VALUES (0, '12345');
INSERT INTO `roomsg` VALUES (1, '12345');
INSERT INTO `roomsg` VALUES (2, '12345');
INSERT INTO `roomsg` VALUES (3, '12345');
INSERT INTO `roomsg` VALUES (4, '12345');
COMMIT;

-- ----------------------------
-- Table structure for staff
-- ----------------------------
DROP TABLE IF EXISTS `staff`;
CREATE TABLE `staff` (
  `account` varchar(255) COLLATE utf8_bin NOT NULL,
  `password` varchar(255) CHARACTER SET utf8 COLLATE utf8_bin DEFAULT NULL,
  `title` varchar(255) COLLATE utf8_bin DEFAULT NULL,
  `name` varchar(255) COLLATE utf8_bin DEFAULT NULL,
  PRIMARY KEY (`account`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;

-- ----------------------------
-- Records of staff
-- ----------------------------
BEGIN;
INSERT INTO `staff` VALUES ('xiaohua', 'xiaohua', '管理员', '小花');
COMMIT;

SET FOREIGN_KEY_CHECKS = 1;
