#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "pb_decode.h"
#include "commands.pb.h"
#include "commands_dispatch.h"

bool receive_command(
    const uint8_t *data,
    size_t length)
{
    device_CommandRequest request =
        device_CommandRequest_init_zero;

    pb_istream_t stream =
        pb_istream_from_buffer(data, length);

    if (!pb_decode(
            &stream,
            device_CommandRequest_fields,
            &request))
    {
        return false;
    }

    return command_dispatch(&request);
}
