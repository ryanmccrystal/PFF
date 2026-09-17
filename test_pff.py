name: Test PFF API

on:
  workflow_dispatch:

jobs:
  test-pff:
    runs-on: ubuntu-latest

    steps:
      - name: Install Restish
        run: |
          curl -L https://github.com/rest-sh/restish/releases/download/v2.3.0/restish-2.3.0-linux-amd64.tar.gz -o restish.tar.gz
          tar -xzf restish.tar.gz
          chmod +x restish
          sudo mv restish /usr/local/bin/restish

      - name: Check Restish version
        run: |
          restish --version

      - name: Connect Restish to PFF
        run: |
          restish api connect pff https://api.pff.com

      - name: Configure PFF authentication
        env:
          PFF_API_KEY: ${{ secrets.PFF_API_KEY }}
        run: |
          restish api set pff 'profiles.ci.credentials.pffApiKey.auth.type: bearer'
          restish api set pff 'profiles.ci.credentials.pffApiKey.auth.params.token: env:PFF_API_KEY'

      - name: Test PFF authentication
        env:
          PFF_API_KEY: ${{ secrets.PFF_API_KEY }}
        run: |
          restish pff whoami -p ci
