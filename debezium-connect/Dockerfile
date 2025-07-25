# Use the Confluent Kafka Connect base image which includes the Avro converter
FROM confluentinc/cp-kafka-connect-base:7.6.1

# Define the plugin path for Kafka Connect, which is a standard location for this base image.
ARG CONNECT_PLUGIN_PATH="/usr/share/confluent-hub-components"

# Download and install the Debezium PostgreSQL connector manually.
# This method is more reliable than using confluent-hub if it fails to resolve the component.
RUN curl -sO https://repo1.maven.org/maven2/io/debezium/debezium-connector-postgres/2.6.2.Final/debezium-connector-postgres-2.6.2.Final-plugin.tar.gz && \
    mkdir -p ${CONNECT_PLUGIN_PATH}/debezium-connector-postgres && \
    tar -xzf debezium-connector-postgres-2.6.2.Final-plugin.tar.gz -C ${CONNECT_PLUGIN_PATH}
