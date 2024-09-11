#!/bin/bash
URL=https://sy3brp8ko1.execute-api.ap-south-1.amazonaws.com/qa/
while true; do
	echo "$(date +%F_%H%M%S) - $(curl -s $URL)"
	sleep 5
done