#include "urma_failure_639.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure639> g_urma("urma_639");

bool UrmaFailure639::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_tlv_ioctl") != std::string::npos &&
           message.find("ioctl failed, ret:") != std::string::npos && message.find(", errno:") != std::string::npos &&
           message.find(", cmd:") != std::string::npos && message.find(", kdrv_err:") != std::string::npos;
}

std::string UrmaFailure639::GetName() const
{
    return "tlvTLV、ioctl ioctl驱动命令返回失败";
}

std::string UrmaFailure639::GetRootCauseDesc() const
{
    return "URMA用户态通过TLV "
           "ioctl调用内核态驱动时，驱动侧处理异常并返回错误码，若errno为2048通常表示故障发生在内核态驱动。";
}

RootCause UrmaFailure639::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure639::GetFixSuggDesc() const
{
    return "UDMA驱动相关，需进一步排查硬件";
}

std::string UrmaFailure639::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_tlv_ioctl，ioctl failed, ret:，, errno:，, cmd:，, kdrv_err:。";
}

std::string UrmaFailure639::GetId() const
{
    return "urma_639";
}
} // namespace diag
