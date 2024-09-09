export RS_USER=
export RS_PWD=
export RS_API="https://localhost:9443/v1/cluster/"

curl -L -k  -u "$RS_USER:$RS_PWD" -H "Content-Type: application/json" -X GET $RS_API/services_configuration
curl -L -k -u "$RS_USER:$RS_PWD" -H "Content-Type: application/json" -X PUT -d '{"entraid_agent_mgr": {"operating_mode": "enabled"}}' $RS_API/services_configuration
