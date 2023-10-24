#!/usr/bin/env bash

echo "This script will write a new test to tests/deleteme.ts"
echo "then delete it, leaving only the auth config."
echo ""
echo "When the playwright browser opens, log in to the site then exit."
echo "After recording your test, close the test browser."
echo "Recording auth token to georepo-auth.json"

# File exists and write permission granted to user
# show prompt
echo "Continue? y/n"
read ANSWER
case $ANSWER in 
  [yY] ) echo "Writing georepo-auth.json" ;;
  [nN] ) echo "Cancelled."; exit ;;
esac

npx playwright \
  codegen \
  --save-storage=georepo-auth.json \
  -o tests/deleteme.ts \
  --ignore-https-errors \
  https://localhost:51102
  # https://staging-georepo.unitst.org

# We are only interested in georepo-auth.json
rm tests/deleteme.ts

echo "Auth file creation completed."
