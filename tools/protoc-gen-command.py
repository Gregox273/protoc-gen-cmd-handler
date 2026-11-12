#!/usr/bin/env python3

import re
import sys

from google.protobuf.compiler import plugin_pb2


def c_identifier(name):
    """Convert a protobuf name into a C identifier."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", name)


def message_c_type(full_name):
    """
    Convert a protobuf fully qualified name to nanopb's C type.

    Example:
        device.StartRequest -> device_StartRequest
    """
    return c_identifier(full_name.replace(".", "_"))


def generate(request):
    response = plugin_pb2.CodeGeneratorResponse()

    for filename in request.file_to_generate:
        proto_file = next(f for f in request.proto_file if f.name == filename)

        # Find CommandRequest in this proto file.
        message = next(
            (m for m in proto_file.message_type if m.name == "CommandRequest"), None
        )

        if message is None:
            continue

        # Find the oneof named "command".
        oneof_index = next(
            (i for i, o in enumerate(message.oneof_decl) if o.name == "command"), None
        )

        if oneof_index is None:
            continue

        # Find fields belonging to that oneof.
        fields = [
            f
            for f in message.field
            if f.HasField("oneof_index") and f.oneof_index == oneof_index
        ]

        if not fields:
            continue

        package = proto_file.package

        request_type = message_c_type(
            f"{package}.{message.name}" if package else message.name
        )

        base_name = filename.rsplit(".", 1)[0]

        header_name = base_name + "_dispatch.h"
        source_name = base_name + "_dispatch.c"
        handlers_header_name = "command_handlers.h"

        guard = c_identifier(header_name.upper().replace(".", "_"))

        # Generate the header.
        header = []

        header.append(f"#ifndef {guard}")
        header.append(f"#define {guard}")
        header.append("")
        header.append("#include <stdbool.h>")
        header.append(f'#include "{base_name}.pb.h"')
        header.append("")
        header.append(f"bool command_dispatch(const {request_type} *request);")
        header.append("")
        header.append("#endif")

        # Generate the C implementation.
        source = []

        source.append(f'#include "{header_name}"')
        source.append(f'#include "{handlers_header_name}"')
        source.append("")
        source.append(f"bool command_dispatch(const {request_type} *request)")
        source.append("{")
        source.append("    if (request == NULL)")
        source.append("        return false;")
        source.append("")
        source.append("    switch (request->which_command)")
        source.append("    {")

        for field in fields:
            if field.type != field.TYPE_MESSAGE:
                raise ValueError(f"Command '{field.name}' must be a message")

            payload_type = message_c_type(field.type_name.lstrip("."))

            handler_name = f"handle_{field.name}"

            source.append(f"        case {field.number}:")
            source.append(
                f"            return {handler_name}(&request->command.{field.name});"
            )
            source.append("")

        source.append("        default:")
        source.append("            return false;")
        source.append("    }")
        source.append("}")
        source.append("")

        # Generate command_handlers.h

        handlers = []

        handlers.append("#ifndef COMMAND_HANDLERS_H")
        handlers.append("#define COMMAND_HANDLERS_H")
        handlers.append("")
        handlers.append("#include <stdbool.h>")
        handlers.append(f'#include "{base_name}.pb.h"')
        handlers.append("")

        for field in fields:
            if field.type != field.TYPE_MESSAGE:
                raise ValueError(f"Command '{field.name}' must be a message")

            payload_type = message_c_type(field.type_name.lstrip("."))

            handler_name = f"handle_{field.name}"

            handlers.append(f"bool {handler_name}(const {payload_type} *request);")
            handlers.append("")

        handlers.append("#endif")
        handlers.append("")

        # Add generated files to the response.
        f = response.file.add()
        f.name = header_name
        f.content = "\n".join(header) + "\n"

        f = response.file.add()
        f.name = source_name
        f.content = "\n".join(source) + "\n"

        f = response.file.add()
        f.name = handlers_header_name
        f.content = "\n".join(handlers)

    return response


def main():
    request = plugin_pb2.CodeGeneratorRequest.FromString(sys.stdin.buffer.read())

    response = generate(request)

    sys.stdout.buffer.write(response.SerializeToString())


if __name__ == "__main__":
    main()
