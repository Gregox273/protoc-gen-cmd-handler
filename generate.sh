mkdir -p generated

# Generate nanopb C files.
protoc \
    -I proto \
    --plugin=protoc-gen-nanopb=.venv/bin/protoc-gen-nanopb \
    --nanopb_out=generated \
    proto/commands.proto

# Generate the command dispatcher.
protoc \
    -I proto \
    --plugin=protoc-gen-command=tools/protoc-gen-command.py \
    --command_out=generated \
    proto/commands.proto
