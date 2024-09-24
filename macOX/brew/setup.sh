#!/usr/bin/env zsh

# Install Homebrew if it isn't already installed
install_homebrew() {
  if ! command -v brew &>/dev/null; then
      echo "Homebrew not installed. Installing Homebrew."
      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

      # Attempt to set up Homebrew PATH automatically for this session
      if [ -x "/opt/homebrew/bin/brew" ]; then
          # For Apple Silicon Macs
          echo "Configuring Homebrew in PATH for Apple Silicon Mac..."
          export PATH="/opt/homebrew/bin:$PATH"
      fi
  else
      echo "Homebrew is already installed."
  fi
}

# Verify brew is now accessible
verify_homebrew_installation() {
  if ! command -v brew &>/dev/null; then
      echo "Failed to configure Homebrew in PATH. Please add Homebrew to your PATH manually."
      exit 1
  else
    echo "Homebrew is working!"
  fi
}

# Update Homebrew and Upgrade any already-installed formulae
update_homebrew(){
  brew update
  brew upgrade
  brew upgrade --cask
  brew cleanup
}

handle_choice(){
    # Evaluating the user's choice
  case $choice in
      1)
          echo "Basic"
          brew bundle --file=brew/Brewfile-basic -v --no-lock
          ;;
      2)
          echo "Work"
          brew bundle --file=brew/Brewfile-work -v --no-lock
          ;;
      3)
          echo "Extra"
          brew bundle --file=brew/Brewfile-extra -v --no-lock
          ;;
      4)
          echo "Security"
          brew bundle --file=brew/Brewfile-extra -v --no-lock
          ;;
      9)
          echo "Exiting..."
          # shellcheck disable=SC2104
          break
          ;;
      *)
          echo "Invalid choice, please try again."
          ;;
  esac
}

homebrew_bundle_file_selection(){
  while true; do
    # Displaying the menu
    echo "Please select one of the following options for the Homebrew setup:"
    echo "1) Basic"
    echo "2) Work"
    echo "3) Extra"
    echo "4) Security"
    echo "9) EXIT"

    # Display prompt using echo instead of -p flag
    echo -n "Enter the number of your choice: "
    read choice
    handle_choice $choice

        # Ensure we break out of the loop when Option 4 is chosen
    if [[ $choice -eq 4 ]]; then
        break
    fi
  done

}

homebrew_doctor(){
  # check for issues
  brew doctor

}
# Main Script Execution
echo "Starting HomeBrew Setup"

install_homebrew
verify_homebrew_installation
update_homebrew
homebrew_bundle_file_selection
homebrew_doctor

echo "HomeBrew Setup complete!"
