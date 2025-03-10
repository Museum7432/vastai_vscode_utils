#!/bin/bash
# delete or stop the instance if there is no activity for too long (1 hour since last connected with ssh)
# should be used with tools like sftp in vscode to sync from local to 
# server (useful for testing heavy cuda code on gpu)

# only support ssh connection for now

# Configuration
# expect $CONTAINER_ID to be set in the instance

echo CONTAINER_ID: $CONTAINER_ID
API_KEY="$(cat ~/.ssh/authorized_keys | md5sum | awk '{print $1}' > ssh_key_hv; echo -n $VAST_CONTAINERLABEL | md5sum | awk '{print $1}' > instance_id_hv; head -c -1 -q ssh_key_hv instance_id_hv)"

DELETE_URL="https://console.vast.ai/api/v0/instances/$CONTAINER_ID/"

INACTIVITY_LIMIT=20 # 1 hour

check_ssh_activity() {
    # tested on the nvidia image
    # skip the tmux session
    if [ "$(who | grep -v 'tmux')" ]; then
        return 0 # Active SSH session found
    else
        return 1 # No active SSH session
    fi
}

# maybe when their api respone make sense
# send_request() {
#     local attempt=1

#     while [ $attempt -le $MAX_RETRIES ]; do
#         echo "Sending request... $attempt/$MAX_RETRIES"

#         # delete instance
#         # response=$(curl --location --globoff --request DELETE "https://console.vast.ai/api/v0/instances/$CONTAINER_ID/" \
#         #     --header 'Accept: application/json' \
#         #     --header 'Content-Type: application/json' \
#         #     --header "Authorization: Bearer $API_KEY" \
#         #     -s
#         # )

#         # stop instance
#         response=$(curl --location --request PUT "https://console.vast.ai/api/v0/instances/$CONTAINER_ID/" \
#             --header 'Accept: application/json' \
#             --header 'Content-Type: application/json' \
#             --header "Authorization: Bearer $API_KEY" \
#             --data '{"body":{}}' \
#             -s
#         )

#         if echo "$response" | grep -q "success"; then
#             echo "Successfully deleted the instance."
#             return 0
#         else
#             echo "Failed to delete the instance. Response: $response"
#             attempt=$((attempt + 1))

#             sleep 5
#         fi
#     done

#     # maybe send an email here
# }

send_delete_request() {
    echo "Sending DELETE request..."

    curl --location --globoff --request DELETE "https://console.vast.ai/api/v0/instances/$CONTAINER_ID/" \
        --header 'Accept: application/json' \
        --header 'Content-Type: application/json' \
        --header "Authorization: Bearer $API_KEY"
}

send_stop_request() {
    echo "Sending STOP request..."
    curl --location --request PUT "https://console.vast.ai/api/v0/instances/$CONTAINER_ID/" \
        --header 'Accept: application/json' \
        --header 'Content-Type: application/json' \
        --header "Authorization: Bearer $API_KEY" \
        --data '{"body":{}}'
}

last_activity_time=$(date +%s)

while true; do
    # Get the current time
    current_time=$(date +%s)

    # Check for SSH activity
    if check_ssh_activity; then
        # If there's an active SSH connection, reset the timer
        last_activity_time=$current_time
    fi

    # Check the time since last activity
    idle_time=$((current_time - last_activity_time))

    if [ "$idle_time" -ge "$INACTIVITY_LIMIT" ]; then
        # If idle for too long, send the request
        
        send_stop_request
        break
    fi

    # Sleep for a bit before checking again
    sleep 1
done