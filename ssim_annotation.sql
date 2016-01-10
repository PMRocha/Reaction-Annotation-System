/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;

--
-- Database: `ssim_annotation`
--
CREATE DATABASE IF NOT EXISTS `ssim_annotation` DEFAULT CHARACTER SET latin1 COLLATE latin1_swedish_ci;
USE `ssim_annotation`;

-- --------------------------------------------------------

--
-- Table structure for table `annotation`
--

DROP TABLE IF EXISTS `annotation`;
CREATE TABLE IF NOT EXISTS `annotation` (
  `idUser` int(11) NOT NULL,
  `idTweet` bigint(20) NOT NULL,
  `idRun` int(11) NOT NULL,
  `annotationDate` datetime DEFAULT NULL,
  `isClosed` tinyint(4) NOT NULL DEFAULT '0',
  `idClassification_label` int(11) DEFAULT '1',
  `agreement` bit(1) DEFAULT b'0',
  PRIMARY KEY (`idUser`,`idTweet`,`idRun`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `annotation_one_shot`
--

DROP TABLE IF EXISTS `annotation_one_shot`;
CREATE TABLE IF NOT EXISTS `annotation_one_shot` (
  `idUser` int(11) NOT NULL,
  `idTweet` bigint(20) NOT NULL,
  `idRun` int(11) NOT NULL,
  `annotationDate` datetime DEFAULT NULL,
  `isClosed` tinyint(4) NOT NULL DEFAULT '0',
  `idClassification_label` int(11) DEFAULT '1',
  PRIMARY KEY (`idUser`,`idTweet`,`idRun`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `campaign`
--

DROP TABLE IF EXISTS `campaign`;
CREATE TABLE IF NOT EXISTS `campaign` (
  `idCampaign` int(11) NOT NULL AUTO_INCREMENT,
  `campaignName` varchar(100) NOT NULL,
  `startDate` datetime NOT NULL,
  `endDate` datetime NOT NULL,
  `periodOfEachRun` int(11) NOT NULL,
  `deltaTimeForQuery` int(11) NOT NULL,
  `idScript` int(11) NOT NULL,
  `numberAnnotations` int(11) NOT NULL DEFAULT '30',
  PRIMARY KEY (`idCampaign`),
  UNIQUE KEY `idCampaign_UNIQUE` (`idCampaign`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 AUTO_INCREMENT=50 ;

-- --------------------------------------------------------

--
-- Table structure for table `campaign_classification_labels`
--

DROP TABLE IF EXISTS `campaign_classification_labels`;
CREATE TABLE IF NOT EXISTS `campaign_classification_labels` (
  `idCampaign` int(11) NOT NULL,
  `idClassification_label` int(11) NOT NULL,
  PRIMARY KEY (`idCampaign`,`idClassification_label`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `campaign_users`
--

DROP TABLE IF EXISTS `campaign_users`;
CREATE TABLE IF NOT EXISTS `campaign_users` (
  `idCampaign` int(11) NOT NULL,
  `idUser` int(11) NOT NULL,
  PRIMARY KEY (`idCampaign`,`idUser`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `candidate_for_selection`
--

DROP TABLE IF EXISTS `candidate_for_selection`;
CREATE TABLE IF NOT EXISTS `candidate_for_selection` (
  `idRun` int(11) NOT NULL,
  `idTweet` bigint(20) NOT NULL,
  `selectedForAttribution` tinyint(4) NOT NULL DEFAULT '0',
  PRIMARY KEY (`idRun`,`idTweet`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `classification_label`
--

DROP TABLE IF EXISTS `classification_label`;
CREATE TABLE IF NOT EXISTS `classification_label` (
  `idClassification_label` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(45) NOT NULL,
  `description` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`idClassification_label`)
) ENGINE=InnoDB  DEFAULT CHARSET=latin1 AUTO_INCREMENT=12 ;

-- --------------------------------------------------------

--
-- Table structure for table `one_shot_user`
--

DROP TABLE IF EXISTS `one_shot_user`;
CREATE TABLE IF NOT EXISTS `one_shot_user` (
  `idUser` int(11) NOT NULL AUTO_INCREMENT,
  `isOccupied` tinyint(4) NOT NULL DEFAULT '0',
  `idRun` int(11) NOT NULL,
  PRIMARY KEY (`idUser`),
  UNIQUE KEY `idUser_UNIQUE` (`idUser`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 AUTO_INCREMENT=1 ;

-- --------------------------------------------------------

--
-- Table structure for table `run`
--

DROP TABLE IF EXISTS `run`;
CREATE TABLE IF NOT EXISTS `run` (
  `idRun` int(11) NOT NULL AUTO_INCREMENT,
  `initDate` datetime NOT NULL,
  `endDate` datetime NOT NULL,
  `idCampaign` int(11) NOT NULL,
  `solrQuery` varchar(300) NOT NULL,
  `status` varchar(45) NOT NULL DEFAULT 'schedulled',
  PRIMARY KEY (`idRun`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 AUTO_INCREMENT=680 ;

-- --------------------------------------------------------

--
-- Table structure for table `script`
--

DROP TABLE IF EXISTS `script`;
CREATE TABLE IF NOT EXISTS `script` (
  `idScript` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `filepath` varchar(150) NOT NULL,
  PRIMARY KEY (`idScript`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 AUTO_INCREMENT=2 ;

-- --------------------------------------------------------

--
-- Table structure for table `tweets`
--

DROP TABLE IF EXISTS `tweets`;
CREATE TABLE IF NOT EXISTS `tweets` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_campaign` int(11) DEFAULT NULL,
  `target` varchar(150) DEFAULT NULL,
  `id_tweet` varchar(30) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB  DEFAULT CHARSET=latin1 AUTO_INCREMENT=10059 ;

-- --------------------------------------------------------

--
-- Table structure for table `user`
--

DROP TABLE IF EXISTS `user`;
CREATE TABLE IF NOT EXISTS `user` (
  `iduser` int(11) NOT NULL AUTO_INCREMENT,
  `fullname` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password_codified` varchar(100) NOT NULL,
  `isActive` tinyint(4) NOT NULL DEFAULT '1',
  `isAdmin` tinyint(4) NOT NULL DEFAULT '0',
  PRIMARY KEY (`iduser`),
  UNIQUE KEY `email_UNIQUE` (`email`),
  UNIQUE KEY `iduser_UNIQUE` (`iduser`)
) ENGINE=InnoDB  DEFAULT CHARSET=latin1 AUTO_INCREMENT=19 ;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
