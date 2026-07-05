#!/bin/bash
# Build iOS IPA cho CFL Auto Giftcode
# Yêu cầu: macOS + Xcode + Flutter SDK
# Cách dùng: bash build_ios.sh

# Thiết lập PATH cho Flutter
export PATH="$PATH:$HOME/flutter/bin"

# Cài đặt Flet nếu chưa có
pip install flet

# Build iOS IPA
flet build ipa \
  --project "CFL Giftcode" \
  --product "CFL Auto Giftcode" \
  --org "com.dtmcfl" \
  --bundle-id "com.dtmcfl.giftcode" \
  --description "Auto giftcode cho Crossfire Legends VNG" \
  --build-version "1.0.0" \
  --build-number "1" \
  --module-name "cfl_app" \
  --no-rich-output \
  --yes

echo "✅ iOS IPA đã build xong! Tìm trong thư mục build/ipa/"
