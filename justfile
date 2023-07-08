parse_tool_versions := "
while IFS= read -r line; do
  NAME=\"$(echo $line | cut -d' ' -f1)_tool_version\"
  NAME=\"$(echo $NAME | tr [:lower:] [:upper:])\"
  VALUE=$(echo $line | cut -d' ' -f2-)
  export \"$NAME=$VALUE\"
done < ./.tool-versions
"

build:
    #!/usr/bin/env bash

    {{ parse_tool_versions }}

    earthly +image \
        --python_version=${PYTHON_TOOL_VERSION} \
        --image=ghcr.io/djeebus/pvc-backup-operator \
        --tag=dev
