#!/usr/bin/env zsh

echo "Starting macOS Setup"

# Set location for screenshots
mkdir "${HOME}/Downloads/Screenshots"
defaults write com.apple.screencapture location "${HOME}/Downloads/Screenshots"
defaults write com.apple.menuextra.battery ShowPercent -string "YES"
killall SystemUIServer

# Add Bluetooth to Menu Bar for battery percentages
defaults write com.apple.controlcenter "NSStatusItem Visible Bluetooth" -bool true
killall ControlCenter

# Show allFiles
defaults write com.apple.Finder AppleShowAllFiles true
# Disable .DS_Store creation on network volumes
defaults write com.apple.desktopservices DSDontWriteNetworkStores -bool true
# Disable .DS_Store creation on USB/External drives (optional)
defaults write com.apple.desktopservices DSDontWriteUSBStores -bool true
killall Finder

# Enable install applications from anywhere
sudo spctl --master-disable

echo "macOS Setup complete!"