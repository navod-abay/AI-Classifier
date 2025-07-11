#!/usr/bin/env python3
"""
Worker script for synchronization between NAS and local cache.
This script runs as a Windows scheduled task every 10 minutes.
"""

import os
import subprocess
import logging
import sys
import time
from pathlib import Path
import socket
import platform

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sync_worker.log'),
        logging.StreamHandler()  # Also log to console
    ]
)
logger = logging.getLogger("SyncWorker")

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, 'cache')
IMAGES_DIR = os.path.join(CACHE_DIR, 'images')
OCR_DIR = os.path.join(CACHE_DIR, 'ocr')
LABELS_CSV = os.path.join(CACHE_DIR, 'labels.csv')
FACES_PKL = os.path.join(CACHE_DIR, 'faces.pkl')

# NAS paths (using Windows mapped drive)
NAS_DRIVE = "Z:"
NAS_PHOTOS = os.path.join(NAS_DRIVE, "photos_preprocessed")
NAS_OCR = os.path.join(NAS_DRIVE, "ocr_data")
NAS_LABELS = os.path.join(NAS_DRIVE, "labels")
NAS_FACES = os.path.join(NAS_DRIVE, "known_faces")

# Ensure directories exist
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(OCR_DIR, exist_ok=True)
os.makedirs(NAS_LABELS, exist_ok=True)
os.makedirs(NAS_FACES, exist_ok=True)

def check_wifi_ssid():
    """Check if connected to the required SSID (Abayasekera)"""
    try:
        if platform.system() == 'Windows':
            # Use netsh to get SSID on Windows
            output = subprocess.check_output("netsh wlan show interfaces", shell=True).decode('utf-8')
            for line in output.split('\n'):
                if "SSID" in line and ":" in line and not "BSSID" in line:
                    ssid = line.split(":")[1].strip()
                    logger.info(f"Connected to SSID: {ssid}")
                    return ssid == "Abayasekera"
        else:
            logger.warning("Not running on Windows, can't check SSID")
            
        return False
    except Exception as e:
        logger.error(f"Error checking SSID: {e}")
        return False

def check_nas_connection():
    """Check if NAS is accessible"""
    try:
        if not os.path.exists(NAS_DRIVE):
            logger.error(f"NAS drive {NAS_DRIVE} not found")
            return False
            
        # Try to access a directory on the NAS
        if not os.path.exists(NAS_PHOTOS):
            logger.error(f"NAS photos directory {NAS_PHOTOS} not accessible")
            return False
            
        logger.info("NAS connection verified")
        return True
    except Exception as e:
        logger.error(f"Error checking NAS connection: {e}")
        return False

def run_rsync(source, dest, flags="--ignore-existing"):
    """Run rsync command with proper flags"""
    try:
        if platform.system() == 'Windows':
            # Using rsync for Windows (cwRsync or similar)
            cmd = f"rsync -av {flags} \"{source}/\" \"{dest}/\""
        else:
            # Linux/Mac
            cmd = f"rsync -av {flags} '{source}/' '{dest}/'"
        
        logger.info(f"Running: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Rsync successful: {source} -> {dest}")
            if result.stdout:
                logger.info(f"Output: {result.stdout[:500]}")
            return True
        else:
            logger.error(f"Rsync failed with code {result.returncode}: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error running rsync: {e}")
        return False

def sync_files():
    """Synchronize files between NAS and local cache"""
    logger.info("Starting file synchronization...")
    
    # Check if we're on the right network
    if not check_wifi_ssid():
        logger.warning("Not connected to Abayasekera WiFi, skipping sync")
        return False
    
    # Check NAS connection
    if not check_nas_connection():
        logger.warning("NAS not accessible, skipping sync")
        return False
        
    # Sync photos from NAS to local (only new files)
    run_rsync(NAS_PHOTOS, IMAGES_DIR)
    
    # Sync OCR data from NAS to local (only new files)
    run_rsync(NAS_OCR, OCR_DIR)
    
    # Sync labels from local to NAS (always update)
    if os.path.exists(LABELS_CSV):
        run_rsync(os.path.dirname(LABELS_CSV), NAS_LABELS, "--update")
    
    # Sync faces from local to NAS (always update)
    if os.path.exists(FACES_PKL):
        run_rsync(os.path.dirname(FACES_PKL), NAS_FACES, "--update")
    
    logger.info("Synchronization completed successfully")
    return True

if __name__ == "__main__":
    logger.info("Sync worker starting...")
    try:
        sync_files()
    except Exception as e:
        logger.error(f"Unhandled exception in sync worker: {e}", exc_info=True)
        sys.exit(1)
    
    logger.info("Sync worker completed")
